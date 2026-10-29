"""Scan job pipeline: the worker-side executor (HF-FR-024/027/028/029/030)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.errors import ApiError, ErrorCode
from ..core.logging import get_logger, set_correlation_id
from ..core.redaction import redact_text
from ..db.models import JobStatus, Program, ScanJob, ToolRun
from ..domain.scope import Policy
from ..domain.state import JOB_TRANSITIONS, assert_transition
from ..integrations.tools.registry import get_adapter
from ..services.ingestion import ingest
from .profiles import resolve_profile
from .runner import ToolRunner

log = get_logger("hunterflow.pipeline")


def load_job(db: Session, job_id: str) -> ScanJob:
    job = db.get(ScanJob, job_id)
    if job is None:
        raise ApiError(ErrorCode.NOT_FOUND, "Job not found", 404)
    return job


def job_policy(db: Session, job: ScanJob) -> Policy:
    program = db.get(Program, job.program_id)
    if job.policy_version_id:
        from ..db.models import PolicyVersion

        pv = db.get(PolicyVersion, job.policy_version_id)
        if pv is not None:
            return Policy.from_snapshot(pv.snapshot)
    # Fall back to the current policy (rules not yet versioned).
    from ..services.programs import current_policy

    return current_policy(db, program)


def _rule_roots(policy: Policy) -> list[str]:
    """Enumeration seeds derived from allow rules (authorized inputs for passive tools)."""
    roots = set()
    for rule in policy.rules:
        if rule.effect.value == "allow":
            v = rule.value
            if rule.kind.value == "domain_wildcard" and v.startswith("*."):
                roots.add(v[2:])
            elif rule.kind.value == "domain_exact":
                roots.add(v)
    return sorted(roots)


def tool_targets(user_targets: list[str], tool_name: str) -> list[str]:
    """Shape user-provided targets for a tool.

    subfinder enumerates a eponymous domain and rejects URLs/ports, so it gets
    bare hostnames. httpx/katana/nuclei take URLs unchanged.
    """
    if tool_name not in ("subfinder", "gau", "dnsx"):
        return list(user_targets)
    hosts: list[str] = []
    for target in user_targets:
        if "://" in target:
            host = Policy.host_of_url(target)
        else:
            host = target.split("/", 1)[0].split(":", 1)[0]
        if host and host not in hosts:
            hosts.append(host)
    return hosts


def _step_targets(db: Session, job: ScanJob, policy: Policy, tool_name: str) -> tuple[list[str], set[str]]:
    """Targets per tool step; `trusted_seeds` are rule-derived enumeration inputs
    for passive tools (authorized by construction)."""
    user_targets = (job.target_filter or {}).get("targets")
    if user_targets:
        return tool_targets(user_targets, tool_name), set()

    if tool_name in ("subfinder", "gau"):
        seeds = _rule_roots(policy)
        return seeds, set(seeds)

    # Active tools probe previously discovered, in-scope assets.
    from ..db.models import Asset

    rows = db.scalars(
        select(Asset).where(
            Asset.program_id == job.program_id,
            Asset.scope_status == "in_scope",
        )
    ).all()
    if tool_name in ("httpx", "katana", "dnsx"):
        hosts = sorted({a.value_normalized for a in rows if a.type in ("subdomain", "domain")})
        if tool_name == "httpx":
            # Include known in-scope URLs (needed for screenshots and re-probing).
            urls = sorted({a.value_normalized for a in rows if a.type == "url"})[:200]
            return hosts + urls, set()
        return hosts, set()
    if tool_name == "nuclei":
        urls = sorted({a.value_normalized for a in rows if a.type == "url"})
        return urls, set()
    return [], set()


def cancel_checker(db_factory, job_id: str):
    def check() -> bool:
        db = db_factory()
        try:
            job = db.get(ScanJob, job_id)
            return bool(job is not None and job.cancel_requested)
        finally:
            db.close()

    return check


def run_scan_job(db_factory, settings: Settings, job_id: str) -> None:
    """Execute a scan job's pipeline. Called by the Dramatiq actor."""
    set_correlation_id(f"job:{job_id[:8]}")
    db = db_factory()
    runner = ToolRunner(settings)
    run_root = settings.data_dir / "runs" / job_id
    try:
        job = load_job(db, job_id)
        if job.status != JobStatus.queued.value:
            log.info("job_skip", job_id=job_id, status=job.status)
            return
        assert_transition(JOB_TRANSITIONS, job.status, "running")
        job.status = JobStatus.running.value
        job.started_at = datetime.now(UTC)
        job.progress = {"step": 0, "total_steps": 0, "current_tool": None, "done": 0, "items": 0}
        db.commit()

        spec = resolve_profile(job.profile, (job.target_filter or {}).get("templates"))
        steps = spec["steps"]
        job.progress = {**job.progress, "total_steps": len(steps)}
        db.commit()

        policy = job_policy(db, job)

        if job.dry_run:
            # Dry run: no tool execution at all (HF-FR-028).
            job.progress = {**job.progress, "dry_run": True, "note": "planned only"}
            job.status = JobStatus.completed.value
            job.finished_at = datetime.now(UTC)
            db.commit()
            log.info("job_dry_run_complete", job_id=job_id, steps=len(steps))
            return

        cancel = cancel_checker(db_factory, job_id)

        for idx, step in enumerate(steps, start=1):
            if cancel():
                raise InterruptedError("cancelled")
            tool_name = step["tool"]
            options = step.get("options", {})
            adapter = get_adapter(tool_name)

            binary = _resolve_binary(db, settings, tool_name)
            if binary is None:
                fail_job(db, job, "TOOL_NOT_FOUND", f"Tool not available: {tool_name}")
                return

            step_targets, trusted_seeds = _step_targets(db, job, policy, tool_name)
            step_targets = _filter_targets(policy, step_targets, tool_name, trusted_seeds)
            if not step_targets:
                log.info("step_no_targets", job_id=job_id, tool=tool_name)
                job.progress = {**job.progress, "step": idx, "current_tool": tool_name}
                db.commit()
                continue

            run_dir = run_root / f"{idx:02d}-{tool_name}"
            run_dir.mkdir(parents=True, exist_ok=True)
            targets_file = run_dir / "targets.txt"
            targets_file.write_text("\n".join(step_targets), encoding="utf-8")
            ctx = _build_context(
                tool_name, step_targets, policy, options, settings, targets_file=str(targets_file)
            )
            if tool_name == "katana":
                resolvers = _write_resolvers(run_dir)
                if resolvers:
                    ctx.extra["resolvers_file"] = resolvers
            args = adapter.build_args(ctx, binary)

            tool_run = ToolRun(
                scan_job_id=job.id,
                tool=tool_name,
                args=[redact_text(a) for a in args],
                timeout_seconds=settings.tool_timeout_seconds,
            )
            db.add(tool_run)
            db.flush()
            job.progress = {**job.progress, "step": idx, "current_tool": tool_name}
            db.commit()

            result = runner.run(args, run_dir, timeout_seconds=settings.tool_timeout_seconds, cancel=cancel)

            tool_run.exit_code = result.exit_code
            tool_run.status = result.status
            tool_run.stdout_ref = str(result.stdout_path) if result.stdout_path else None
            tool_run.stderr_ref = str(result.stderr_path) if result.stderr_path else None
            tool_run.finished_at = datetime.now(UTC)
            db.commit()

            if result.status == "cancelled":
                assert_transition(JOB_TRANSITIONS, job.status, "cancelled")
                job.status = JobStatus.cancelled.value
                job.finished_at = datetime.now(UTC)
                db.commit()
                log.info("job_cancelled", job_id=job_id)
                return
            if result.status in ("failed", "timeout"):
                fail_job(
                    db,
                    job,
                    "TIMEOUT" if result.status == "timeout" else "NONZERO_EXIT",
                    f"Tool {tool_name} {result.status}",
                )
                return

            if result.stdout_path and result.stdout_path.exists():
                stdout = result.stdout_path.read_bytes()
                count = 0
                for observation in adapter.parse(stdout, ctx):
                    ingest(
                        db,
                        program_of(db, job),
                        observation,
                        policy,
                        tool_run_id=tool_run.id,
                        settings=settings,
                    )
                    count += 1
                job.progress = {**job.progress, "done": idx, "items": count}
                db.commit()

        assert_transition(JOB_TRANSITIONS, job.status, "completed")
        job.status = JobStatus.completed.value
        job.finished_at = datetime.now(UTC)
        db.commit()
        log.info("job_completed", job_id=job_id)

        # Monitoring: change detection + opt-in notifications never fail the job.
        try:
            from ..services import monitoring

            program = program_of(db, job)
            events = monitoring.finalize_scan_changes(db, job)
            if events:
                monitoring.notify_changes(db, program, job, events, settings)
        except Exception:
            log.exception("monitoring_failed", job_id=job_id)
    except InterruptedError:
        job = load_job(db, job_id)
        job.status = JobStatus.cancelled.value
        job.finished_at = datetime.now(UTC)
        db.commit()
        log.info("job_cancelled", job_id=job_id)
    except Exception:
        log.exception("job_unexpected_failure", job_id=job_id)
        job = load_job(db, job_id)
        if job.status in (JobStatus.queued.value, JobStatus.running.value):
            fail_job(db, job, "JOB_ERROR", "Unexpected pipeline failure")
    finally:
        db.close()
        set_correlation_id(None)


def program_of(db: Session, job: ScanJob) -> Program:
    return db.get(Program, job.program_id)


def fail_job(db: Session, job: ScanJob, code: str, message: str) -> None:
    try:
        assert_transition(JOB_TRANSITIONS, job.status, "failed")
    except ValueError:
        pass
    job.status = JobStatus.failed.value
    job.error_code = code
    job.finished_at = datetime.now(UTC)
    db.commit()
    log.info("job_failed", job_id=job.id, error_code=code, message=message)


def _resolve_binary(db: Session, settings: Settings, tool_name: str) -> str | None:
    from ..db.models import Tool

    tool = db.scalar(select(Tool).where(Tool.name == tool_name))
    if tool is not None and tool.available and tool.path:
        return tool.path
    # Fallback: PATH lookup.
    import shutil

    found = shutil.which(tool_name)
    if found:
        return found
    bundled = settings.data_dir.parent / "tools" / tool_name / tool_name
    if bundled.exists():
        return str(bundled)
    return None


def _filter_targets(
    policy: Policy, targets: list[str], tool_name: str, trusted_seeds: set[str] | None = None
) -> list[str]:
    """Policy filter immediately before execution (HF-FR-029). Rule-derived
    enumeration seeds are authorized inputs for passive tools."""
    trusted_seeds = trusted_seeds or set()
    out = []
    for target in targets:
        if target in trusted_seeds:
            out.append(target)
            continue
        decision = policy.evaluate_url(target) if "://" in target else policy.evaluate(target)
        if decision.allowed:
            out.append(target)
        else:
            log.info("target_blocked", target=target, tool=tool_name, reason=decision.reason)
    return out


def _build_context(
    tool_name: str,
    targets: list[str],
    policy: Policy,
    options: dict,
    settings: Settings,
    targets_file: str | None = None,
):
    from ..integrations.tools.base import StepContext

    extra: dict = {}
    if tool_name in ("httpx", "katana", "nuclei"):
        extra["no_follow_redirects"] = True
    if tool_name == "httpx" and options.get("screenshots") and settings.screenshots_enabled:
        extra["screenshots"] = True
    if tool_name == "nuclei":
        extra["templates"] = options.get("templates") or []
        extra["no_interactsh"] = True
    if tool_name == "katana":
        allow, deny = _scope_regexes(policy)
        extra["in_scope_regexes"] = allow
        extra["out_of_scope_regexes"] = deny
    return StepContext(
        targets=targets,
        rate_limit=(options.get("rate_limit")),
        timeout_seconds=settings.tool_timeout_seconds,
        targets_file=targets_file,
        extra=extra,
    )


def _scope_regexes(policy: Policy):
    """URL patterns for katana's -cs/-cos (they match full URLs, not hostnames)."""
    import re

    allow, deny = [], []
    for rule in policy.rules:
        if rule.kind.value == "domain_exact":
            host = re.escape(rule.value)
            pattern = rf"(?i)^https?://{host}(:[0-9]+)?(/|$)"
        elif rule.kind.value == "domain_wildcard" and rule.value.startswith("*."):
            base = re.escape(rule.value[2:])
            pattern = rf"(?i)^https?://([a-z0-9-]+\.)+{base}(:[0-9]+)?(/|$)"
        else:
            continue
        (allow if rule.effect.value == "allow" else deny).append(pattern)
    return allow, deny

def _write_resolvers(run_dir) -> str | None:
    """Give katana the container resolver so it can resolve internal names."""
    from pathlib import Path

    try:
        text = Path("/etc/resolv.conf").read_text(encoding="utf-8")
    except OSError:
        return None
    servers = [
        line.split()[1]
        for line in text.splitlines()
        if line.startswith("nameserver") and len(line.split()) > 1
    ]
    if not servers:
        return None
    path = run_dir / "resolvers.txt"
    path.write_text("\n".join(servers), encoding="utf-8")
    return str(path)
