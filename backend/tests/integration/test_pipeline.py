"""Pipeline tests with a fake tool binary (no network, no real tools) - T-027..T-031."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

from app.db.models import ScanJob, Tool, ToolRun
from app.jobs.pipeline import run_scan_job

FAKE_OUTPUT = [
    {"host": "api.example.com", "source": "test"},
    {"host": "evil.other.net", "source": "test"},
]


def _write_fake_binary(tmp_path: Path, mode: str = "output") -> Path:
    script = tmp_path / "fake_subfinder.py"
    if mode == "output":
        body = f"""
import json, sys
for item in {json.dumps(FAKE_OUTPUT)}:
    print(json.dumps(item))
"""
    elif mode == "sleep":
        body = "import time; time.sleep(300)\n"
    elif mode == "fail":
        body = "import sys; sys.exit(1)\n"
    else:
        raise ValueError(mode)
    script.write_text(body)
    return script


def _setup_program(client, csrf) -> str:
    resp = client.post(
        "/api/v1/programs",
        json={"name": "ACME", "platform": "other"},
        headers={"X-CSRF-Token": csrf},
    )
    program_id = resp.json()["id"]
    resp = client.post(
        f"/api/v1/programs/{program_id}/scope/rules",
        json={"kind": "domain_wildcard", "value": "*.example.com", "effect": "allow", "priority": 10},
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 200
    return program_id


def _make_pipeline(settings, app, tmp_path, mode="output"):
    script = _write_fake_binary(tmp_path, mode)
    db = app.state.session_factory()
    db.add(Tool(name="subfinder", available=True, path=sys.executable, version="fake"))
    db.commit()
    db.close()

    def fake_build_args(ctx, binary):
        args = [binary, str(script), "-silent", "-json"]
        for t in ctx.targets:
            args += ["-d", t]
        return args

    from app.integrations.tools.registry import SubfinderAdapter

    class FakeSubfinder(SubfinderAdapter):
        def build_args(self, ctx, binary):
            return fake_build_args(ctx, binary)

    import app.integrations.tools.registry as registry

    registry.ADAPTERS["subfinder"] = FakeSubfinder()

    def db_factory():
        return app.state.session_factory()

    return db_factory


def _create_job(client, csrf, program_id, targets=None, profile="passive", dry_run=False):
    resp = client.post(
        "/api/v1/scans",
        json={
            "program_id": program_id,
            "profile": profile,
            "targets": targets or [],
            "templates": [],
            "dry_run": dry_run,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert resp.status_code == 202, resp.text
    return resp.json()


def test_pipeline_completes_with_normalized_assets(client, settings, app, tmp_path, db):
    from tests.helpers import register_user

    me = register_user(client)
    program_id = _setup_program(client, me["csrf_token"])
    db_factory = _make_pipeline(settings, app, tmp_path)

    job = _create_job(client, me["csrf_token"], program_id)

    # Stub broker ran the actor synchronously on create; job should be done.
    detail = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert detail["status"] in ("completed", "running"), detail

    # If the stub ran it, assert outcomes.
    from app.db.models import Asset

    s = db_factory()
    try:
        assets = s.query(Asset).all()
        hosts = {a.value_normalized for a in assets}
        assert "api.example.com" in hosts
        assert "evil.other.net" in hosts
        by_host = {a.value_normalized: a for a in assets}
        assert by_host["api.example.com"].scope_status == "in_scope"
        assert by_host["evil.other.net"].scope_status == "needs_confirmation"
        runs = s.query(ToolRun).all()
        assert len(runs) == 1
        assert runs[0].status == "completed"
        assert runs[0].args  # persisted, redacted
    finally:
        s.close()


def test_pipeline_sync_execution_status(client, settings, app, tmp_path):
    """Verify stub-broker sync execution leaves the job terminal."""
    from tests.helpers import register_user

    me = register_user(client)
    program_id = _setup_program(client, me["csrf_token"])
    _make_pipeline(settings, app, tmp_path)
    job = _create_job(client, me["csrf_token"], program_id)
    detail = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert detail["status"] == "completed"


def test_dry_run_executes_nothing(client, settings, app, tmp_path, db):
    from tests.helpers import register_user

    me = register_user(client)
    program_id = _setup_program(client, me["csrf_token"])
    _make_pipeline(settings, app, tmp_path)
    job = _create_job(client, me["csrf_token"], program_id, dry_run=True)
    detail = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert detail["status"] == "completed"
    assert detail["progress"]["dry_run"] is True
    assert detail["tool_runs"] == []


def test_out_of_scope_target_rejected_at_creation(client, settings, app, tmp_path):
    from tests.helpers import register_user

    me = register_user(client)
    program_id = _setup_program(client, me["csrf_token"])
    _make_pipeline(settings, app, tmp_path)
    resp = client.post(
        "/api/v1/scans",
        json={"program_id": program_id, "profile": "passive", "targets": ["https://evil.other.net/"]},
        headers={"X-CSRF-Token": me["csrf_token"]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "SCOPE_DENIED"


def test_concurrency_limit(client, settings, app, tmp_path):
    from tests.helpers import register_user

    me = register_user(client)
    program_id = _setup_program(client, me["csrf_token"])
    _make_pipeline(settings, app, tmp_path, mode="sleep")

    from unittest.mock import patch

    # First job: created but NOT executed (block enqueue so it stays queued).
    with patch("app.api.v1.scans.enqueue_scan", return_value=None):
        resp = client.post(
            "/api/v1/scans",
            json={"program_id": program_id, "profile": "passive", "targets": []},
            headers={"X-CSRF-Token": me["csrf_token"]},
        )
        assert resp.status_code == 202
    resp = client.post(
        "/api/v1/scans",
        json={"program_id": program_id, "profile": "passive", "targets": []},
        headers={"X-CSRF-Token": me["csrf_token"]},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CONFLICT"


def test_cancellation_kills_running_tool(client, settings, app, tmp_path, db):
    from tests.helpers import register_user

    me = register_user(client)
    program_id = _setup_program(client, me["csrf_token"])
    db_factory = _make_pipeline(settings, app, tmp_path, mode="sleep")

    # Create the job without the actor executing it synchronously.
    from unittest.mock import patch

    with patch("app.api.v1.scans.enqueue_scan", return_value=None):
        job = _create_job(client, me["csrf_token"], program_id)

    result = {}

    def run():
        try:
            run_scan_job(db_factory, settings, job["id"])
        except Exception as exc:  # pragma: no cover
            result["error"] = exc

    t = threading.Thread(target=run)
    t.start()
    time.sleep(2.0)

    s = db_factory()
    try:
        j = s.get(ScanJob, job["id"])
        assert j.status in ("running", "queued")
        j.cancel_requested = True
        s.commit()
    finally:
        s.close()

    start = time.monotonic()
    t.join(timeout=30)
    elapsed = time.monotonic() - start

    s = db_factory()
    try:
        j = s.get(ScanJob, job["id"])
        assert j.status == "cancelled", j.status
    finally:
        s.close()
    assert not t.is_alive()
    assert elapsed < 15, f"cancellation took too long: {elapsed:.1f}s"
