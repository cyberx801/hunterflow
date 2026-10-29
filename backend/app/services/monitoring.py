"""Continuous monitoring: change detection and opt-in webhook notifications.

Rules:
- Only scheduled, non-dry-run, completed jobs produce change events.
- "New" means discovered during this run (first_seen at/after the job start).
- "Removed" is never inferred from a single miss: the first miss is
  `possibly_removed_asset`, the second consecutive miss is `removed_asset`.
- Only asset types the scan profile can actually observe are considered for
  removal (a passive subdomain scan must not mark URLs as gone).
- Notifications are opt-in per schedule and require HF_WEBHOOK_URL to be set.
  They never make the scan fail.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings
from ..core.logging import get_logger
from ..db.base import ensure_utc
from ..db.models import (
    Asset,
    AssetObservation,
    Endpoint,
    EndpointObservation,
    MonitoringEvent,
    Program,
    ScanJob,
    ScheduledScan,
    ToolRun,
)

log = get_logger("hunterflow.monitoring")

PROFILE_ASSET_TYPES: dict[str, set[str]] = {
    "passive": {"domain", "subdomain"},
    "light_recon": {"domain", "subdomain", "url"},
    "web_inventory": {"domain", "subdomain", "url"},
    "vuln_checks": set(),
}

MAX_NEW_EVENTS_PER_RUN = 500


def finalize_scan_changes(db: Session, job: ScanJob) -> list[MonitoringEvent]:
    if job.dry_run or job.status != "completed":
        return []
    started = ensure_utc(job.started_at or job.created_at)

    observed_asset_ids = set(
        db.scalars(
            select(AssetObservation.normalized_to)
            .join(ToolRun, AssetObservation.tool_run_id == ToolRun.id)
            .where(
                ToolRun.scan_job_id == job.id,
                AssetObservation.normalized_to.is_not(None),
            )
        ).all()
    )
    observed_endpoint_ids = set(
        db.scalars(
            select(EndpointObservation.endpoint_id)
            .join(ToolRun, EndpointObservation.tool_run_id == ToolRun.id)
            .where(ToolRun.scan_job_id == job.id)
        ).all()
    )

    events: list[MonitoringEvent] = []

    if observed_asset_ids:
        for asset in db.scalars(select(Asset).where(Asset.id.in_(observed_asset_ids))).all():
            if len(events) >= MAX_NEW_EVENTS_PER_RUN:
                break
            if ensure_utc(asset.first_seen) >= started - timedelta(seconds=1):
                events.append(
                    MonitoringEvent(
                        program_id=job.program_id,
                        scan_job_id=job.id,
                        kind="new_asset",
                        entity_type="asset",
                        entity_id=asset.id,
                        entity_value=asset.value_normalized,
                        detail={"type": asset.type, "scope_status": asset.scope_status},
                    )
                )

    if observed_endpoint_ids:
        for endpoint in db.scalars(
            select(Endpoint).where(Endpoint.id.in_(observed_endpoint_ids))
        ).all():
            if len(events) >= MAX_NEW_EVENTS_PER_RUN:
                break
            if ensure_utc(endpoint.first_seen) >= started - timedelta(seconds=1):
                is_js = endpoint.path.lower().endswith(".js") or any(
                    "javascript" in str(ct).lower() for ct in (endpoint.content_types or [])
                )
                events.append(
                    MonitoringEvent(
                        program_id=job.program_id,
                        scan_job_id=job.id,
                        kind="new_js_file" if is_js else "new_endpoint",
                        entity_type="endpoint",
                        entity_id=endpoint.id,
                        entity_value=f"{endpoint.method} {endpoint.path}",
                        detail={"category": endpoint.category},
                    )
                )

    # Status / technology changes observed during this run (httpx).
    change_rows = db.scalars(
        select(AssetObservation)
        .join(ToolRun, AssetObservation.tool_run_id == ToolRun.id)
        .where(ToolRun.scan_job_id == job.id)
    ).all()
    for obs in change_rows:
        if len(events) >= MAX_NEW_EVENTS_PER_RUN:
            break
        raw = obs.raw or {}
        if raw.get("kind") != "web_probe":
            continue
        prev_status = raw.get("previous_http_status")
        new_status = raw.get("new_http_status")
        if prev_status is not None and new_status is not None and prev_status != new_status:
            events.append(
                MonitoringEvent(
                    program_id=job.program_id,
                    scan_job_id=job.id,
                    kind="changed_asset",
                    entity_type="asset",
                    entity_id=obs.normalized_to,
                    entity_value=str(raw.get("url") or ""),
                    detail={"field": "http_status", "from": prev_status, "to": new_status},
                )
            )
        prev_tech = {str(t) for t in (raw.get("previous_tech") or [])}
        new_tech = {str(t) for t in (raw.get("new_tech") or [])}
        added = sorted(new_tech - prev_tech)
        if added:
            events.append(
                MonitoringEvent(
                    program_id=job.program_id,
                    scan_job_id=job.id,
                    kind="changed_asset",
                    entity_type="asset",
                    entity_id=obs.normalized_to,
                    entity_value=str(raw.get("url") or ""),
                    detail={"field": "tech", "added": added},
                )
            )

    if job.schedule_id:
        covered = PROFILE_ASSET_TYPES.get(job.profile, set())
        if covered:
            candidates = db.scalars(
                select(Asset).where(
                    Asset.program_id == job.program_id,
                    Asset.scope_status == "in_scope",
                    Asset.type.in_(covered),
                )
            ).all()
            for asset in candidates:
                if asset.id in observed_asset_ids:
                    asset.missed_scans = 0
                    continue
                if ensure_utc(asset.first_seen) >= started or ensure_utc(asset.last_seen) >= started:
                    # Seen by another run in the meantime; not a miss.
                    continue
                asset.missed_scans = (asset.missed_scans or 0) + 1
                if asset.missed_scans == 1:
                    events.append(
                        MonitoringEvent(
                            program_id=job.program_id,
                            scan_job_id=job.id,
                            kind="possibly_removed_asset",
                            entity_type="asset",
                            entity_id=asset.id,
                            entity_value=asset.value_normalized,
                            detail={"missed_scans": asset.missed_scans},
                        )
                    )
                elif asset.missed_scans == 2:
                    events.append(
                        MonitoringEvent(
                            program_id=job.program_id,
                            scan_job_id=job.id,
                            kind="removed_asset",
                            entity_type="asset",
                            entity_id=asset.id,
                            entity_value=asset.value_normalized,
                            detail={"missed_scans": asset.missed_scans},
                        )
                    )

    if events:
        db.add_all(events)
    # Always commit: observed assets reset their miss counter even when a run
    # produces no change events.
    db.commit()
    if events:
        log.info("monitoring_events", job_id=job.id, count=len(events))

    if job.schedule_id:
        try:
            _maybe_create_draft_cards(db, job, events)
        except Exception:
            log.exception("auto_cards_failed", job_id=job.id)
            db.rollback()

    return events


MAX_AUTO_CARDS_PER_RUN = 20


def _maybe_create_draft_cards(db: Session, job: ScanJob, events: list[MonitoringEvent]) -> None:
    """Optional: turn new endpoints/JS files into draft research cards.

    Opt-in per schedule (`auto_cards`). Cards are marked as auto-created and need
    human review; duplicates for the same endpoint are skipped.
    """
    from ..db.models import ResearchCard
    from .research import refresh_priority

    schedule = db.get(ScheduledScan, job.schedule_id)
    if schedule is None or not schedule.auto_cards:
        return

    created = 0
    for event in events:
        if created >= MAX_AUTO_CARDS_PER_RUN:
            break
        if event.kind not in ("new_endpoint", "new_js_file") or not event.entity_id:
            continue
        existing = db.scalar(
            select(ResearchCard).where(
                ResearchCard.program_id == job.program_id,
                ResearchCard.endpoint_id == event.entity_id,
            )
        )
        if existing is not None:
            continue
        is_js = event.kind == "new_js_file"
        card = ResearchCard(
            program_id=job.program_id,
            endpoint_id=event.entity_id,
            title=("Review new JS: " if is_js else "Investigate new endpoint: ") + event.entity_value,
            hypothesis=(
                "This JavaScript file was discovered recently. Extract endpoints, parameters and "
                "secrets, and look for client-side authorization decisions."
                if is_js
                else "This endpoint was discovered recently. Verify authentication, object-level "
                "authorization, and input handling with authorized test accounts."
            ),
            test_category="js_analysis" if is_js else "new_endpoint",
            methodology=(
                "1) Fetch the file and note loaded modules.\n2) List API calls and parameters.\n"
                "3) Check for hardcoded secrets or debug flags.\n4) Record observations."
                if is_js
                else "1) Identify auth requirements.\n2) Try both test accounts.\n"
                "3) Compare responses across roles.\n4) Record evidence."
            ),
            notes_md=(
                f"Auto-created by monitoring scan {job.id[:8]} on "
                f"{datetime.now(UTC).date().isoformat()}. Review before testing."
            ),
            status="not_started",
        )
        db.add(card)
        db.flush()
        refresh_priority(db, card)
        created += 1

    if created:
        db.commit()
        log.info("auto_cards_created", job_id=job.id, count=created)


def notify_changes(
    db: Session, program: Program, job: ScanJob, events: list[MonitoringEvent], settings: Settings
) -> None:
    if not events or not job.schedule_id or not settings.webhook_url:
        return
    schedule = db.get(ScheduledScan, job.schedule_id)
    if schedule is None or not schedule.notify:
        return

    counts: dict[str, int] = {}
    for event in events:
        counts[event.kind] = counts.get(event.kind, 0) + 1
    summary = ", ".join(f"{kind.replace('_', ' ')}: {count}" for kind, count in sorted(counts.items()))

    highlights = [e.entity_value for e in events if e.kind in ("new_asset", "new_endpoint", "new_js_file", "changed_asset", "removed_asset")][
        :10
    ]
    lines = [
        f"HunterFlow: {program.name} — {job.profile.replace('_', ' ')} scan",
        summary,
    ]
    if highlights:
        lines.append("Changes: " + ", ".join(highlights))
    text = "\n".join(lines)

    try:
        import httpx

        resp = httpx.post(
            settings.webhook_url,
            json={"content": text, "text": text},
            timeout=10.0,
        )
        log.info("webhook_sent", status=resp.status_code, job_id=job.id)
    except Exception:
        # Notifications must never break a scan.
        log.exception("webhook_failed", job_id=job.id)


def run_due_schedules(db: Session, settings: Settings) -> int:
    """Create and enqueue scans whose next_run_at has passed. Returns count."""
    from ..jobs.actors import enqueue_scan
    from .scans import create_scan_job

    now = datetime.now(UTC)
    due = db.scalars(
        select(ScheduledScan)
        .where(ScheduledScan.enabled.is_(True), ScheduledScan.next_run_at <= now)
        .order_by(ScheduledScan.next_run_at)
    ).all()

    enqueued = 0
    for schedule in due:
        try:
            job = create_scan_job(
                db,
                program_id=schedule.program_id,
                profile=schedule.profile,
                targets=schedule.targets or [],
                templates=schedule.templates or [],
                dry_run=False,
                actor_id=schedule.created_by,
                schedule_id=schedule.id,
            )
        except Exception as exc:
            # Busy program or invalid policy: retry shortly instead of blocking.
            log.info("schedule_skipped", schedule_id=schedule.id, reason=str(exc))
            schedule.next_run_at = now + timedelta(minutes=2)
            db.commit()
            continue

        schedule.last_run_at = now
        schedule.last_job_id = job.id
        schedule.next_run_at = now + timedelta(
            minutes=max(schedule.interval_minutes, settings.min_schedule_minutes)
        )
        db.commit()
        enqueue_scan(job.id)
        enqueued += 1

    return enqueued




