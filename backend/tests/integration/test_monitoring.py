"""Monitoring: schedules, change detection, notifications (v0.2)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.db.models import (
    Asset,
    AssetObservation,
    MonitoringEvent,
    ScanJob,
    ScheduledScan,
    ToolRun,
)
from app.services.monitoring import finalize_scan_changes, run_due_schedules
from tests.helpers import csrf_headers, register_user


def _setup(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = client.post(
        "/api/v1/programs", json={"name": "Mon", "platform": "other"}, headers=csrf_headers(csrf)
    ).json()
    client.post(
        f"/api/v1/programs/{program['id']}/scope/rules",
        json={"kind": "domain_wildcard", "value": "*.example.com", "effect": "allow", "priority": 10},
        headers=csrf_headers(csrf),
    )
    client.post(
        f"/api/v1/programs/{program['id']}/scope/versions",
        json={"change_summary": "v1"},
        headers=csrf_headers(csrf),
    )
    return me, program


class TestScheduleApi:
    def test_create_list_update_delete(self, client):
        me, program = _setup(client)
        csrf = me["csrf_token"]

        r = client.post(
            "/api/v1/schedules",
            json={"program_id": program["id"], "profile": "passive", "interval_minutes": 60},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 201, r.text
        schedule = r.json()
        assert schedule["enabled"] is True
        assert schedule["notify"] is True

        listed = client.get(f"/api/v1/schedules?program_id={program['id']}").json()
        assert len(listed) == 1

        r = client.patch(
            f"/api/v1/schedules/{schedule['id']}",
            json={"enabled": False, "interval_minutes": 120},
            headers=csrf_headers(csrf),
        )
        assert r.status_code == 200
        assert r.json()["enabled"] is False
        assert r.json()["interval_minutes"] == 120

        assert client.delete(
            f"/api/v1/schedules/{schedule['id']}", headers=csrf_headers(csrf)
        ).status_code == 200
        assert client.get("/api/v1/schedules").json() == []

    def test_interval_below_minimum_rejected(self, client):
        me, program = _setup(client)
        r = client.post(
            "/api/v1/schedules",
            json={"program_id": program["id"], "profile": "passive", "interval_minutes": 1},
            headers=csrf_headers(me["csrf_token"]),
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "VALIDATION"

    def test_out_of_scope_target_rejected(self, client):
        me, program = _setup(client)
        r = client.post(
            "/api/v1/schedules",
            json={
                "program_id": program["id"],
                "profile": "passive",
                "interval_minutes": 60,
                "targets": ["https://evil.net/"],
            },
            headers=csrf_headers(me["csrf_token"]),
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "SCOPE_DENIED"

    def test_run_now_creates_job(self, client):
        me, program = _setup(client)
        csrf = me["csrf_token"]
        schedule = client.post(
            "/api/v1/schedules",
            json={"program_id": program["id"], "profile": "passive", "interval_minutes": 60},
            headers=csrf_headers(csrf),
        ).json()

        with patch("app.api.v1.monitoring.enqueue_scan", return_value=None):
            r = client.post(
                f"/api/v1/schedules/{schedule['id']}/run-now", headers=csrf_headers(csrf)
            )
        assert r.status_code == 202, r.text
        job_id = r.json()["job_id"]
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        assert job["status"] == "queued"


class TestChangeDetection:
    def _job(self, db, program_id, profile="passive", schedule_id=None, started=None):
        job = ScanJob(
            program_id=program_id,
            profile=profile,
            status="completed",
            schedule_id=schedule_id,
            started_at=started or datetime.now(UTC),
            finished_at=datetime.now(UTC),
        )
        db.add(job)
        db.flush()
        return job

    def test_new_asset_event(self, db, client):
        me, program = _setup(client)
        job = self._job(db, program["id"])
        run = ToolRun(scan_job_id=job.id, tool="subfinder", args=[], timeout_seconds=60)
        db.add(run)
        db.flush()
        asset = Asset(
            program_id=program["id"],
            type="subdomain",
            value_normalized="fresh.example.com",
            value_original="fresh.example.com",
            scope_status="in_scope",
            first_seen=datetime.now(UTC) + timedelta(seconds=1),
        )
        db.add(asset)
        db.flush()
        db.add(AssetObservation(program_id=program["id"], tool_run_id=run.id, raw={}, normalized_to=asset.id))
        db.commit()

        events = finalize_scan_changes(db, job)
        kinds = [e.kind for e in events]
        assert "new_asset" in kinds
        assert any(e.entity_value == "fresh.example.com" for e in events)

    def test_removal_requires_two_misses(self, db, client):
        me, program = _setup(client)
        schedule = ScheduledScan(
            program_id=program["id"],
            profile="passive",
            interval_minutes=60,
            enabled=True,
            next_run_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.flush()

        old = datetime.now(UTC) - timedelta(days=2)
        asset = Asset(
            program_id=program["id"],
            type="subdomain",
            value_normalized="gone.example.com",
            value_original="gone.example.com",
            scope_status="in_scope",
            first_seen=old,
            last_seen=old,
        )
        db.add(asset)
        db.commit()

        job1 = self._job(db, program["id"], schedule_id=schedule.id)
        db.add(ToolRun(scan_job_id=job1.id, tool="subfinder", args=[], timeout_seconds=60))
        db.commit()
        events1 = finalize_scan_changes(db, job1)
        assert [e.kind for e in events1] == ["possibly_removed_asset"]

        job2 = self._job(db, program["id"], schedule_id=schedule.id)
        db.add(ToolRun(scan_job_id=job2.id, tool="subfinder", args=[], timeout_seconds=60))
        db.commit()
        events2 = finalize_scan_changes(db, job2)
        assert [e.kind for e in events2] == ["removed_asset"]

    def test_observed_asset_resets_miss_counter(self, db, client):
        me, program = _setup(client)
        schedule = ScheduledScan(
            program_id=program["id"], profile="passive", interval_minutes=60,
            enabled=True, next_run_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.flush()
        old = datetime.now(UTC) - timedelta(days=2)
        asset = Asset(
            program_id=program["id"], type="subdomain",
            value_normalized="back.example.com", value_original="back.example.com",
            scope_status="in_scope", first_seen=old, last_seen=old, missed_scans=1,
        )
        db.add(asset)
        db.commit()

        job = self._job(db, program["id"], schedule_id=schedule.id)
        run = ToolRun(scan_job_id=job.id, tool="subfinder", args=[], timeout_seconds=60)
        db.add(run)
        db.flush()
        asset.last_seen = datetime.now(UTC)
        db.add(AssetObservation(program_id=program["id"], tool_run_id=run.id, raw={}, normalized_to=asset.id))
        db.commit()

        events = finalize_scan_changes(db, job)
        db.refresh(asset)
        assert asset.missed_scans == 0
        assert "removed_asset" not in [e.kind for e in events]

    def test_dry_run_and_failed_jobs_emit_nothing(self, db, client):
        me, program = _setup(client)
        job = self._job(db, program["id"])
        job.dry_run = True
        db.commit()
        assert finalize_scan_changes(db, job) == []
        job.dry_run = False
        job.status = "failed"
        db.commit()
        assert finalize_scan_changes(db, job) == []


class TestNotifications:
    def test_webhook_sent_when_configured(self, db, client, settings, monkeypatch):
        from app.services import monitoring

        me, program = _setup(client)
        schedule = ScheduledScan(
            program_id=program["id"], profile="passive", interval_minutes=60,
            enabled=True, notify=True, next_run_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.flush()
        job = ScanJob(
            program_id=program["id"], profile="passive", status="completed",
            schedule_id=schedule.id, started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()

        calls = []

        class FakeResp:
            status_code = 204

        def fake_post(url, json=None, timeout=None):
            calls.append((url, json))
            return FakeResp()

        monkeypatch.setattr("httpx.post", fake_post)
        settings.webhook_url = "https://hooks.example.test/abc"

        from app.db.models import Program

        program_row = db.get(Program, program["id"])
        events = [MonitoringEvent(
            program_id=program["id"], scan_job_id=job.id, kind="new_asset",
            entity_type="asset", entity_value="new.example.com",
        )]
        monitoring.notify_changes(db, program_row, job, events, settings)
        assert len(calls) == 1
        assert "new.example.com" in calls[0][1]["content"]

    def test_no_webhook_without_url(self, db, client, settings, monkeypatch):
        from app.services import monitoring

        me, program = _setup(client)
        schedule = ScheduledScan(
            program_id=program["id"], profile="passive", interval_minutes=60,
            enabled=True, notify=True, next_run_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.flush()
        job = ScanJob(
            program_id=program["id"], profile="passive", status="completed",
            schedule_id=schedule.id, started_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()

        calls = []
        monkeypatch.setattr("httpx.post", lambda *a, **k: calls.append(1))
        settings.webhook_url = None

        from app.db.models import Program

        monitoring.notify_changes(
            db, db.get(Program, program["id"]), job,
            [MonitoringEvent(program_id=program["id"], scan_job_id=job.id, kind="new_asset",
                             entity_type="asset", entity_value="x")],
            settings,
        )
        assert calls == []


class TestScheduler:
    def test_due_schedule_creates_job_and_advances(self, db, client, settings):
        me, program = _setup(client)
        schedule = ScheduledScan(
            program_id=program["id"], profile="passive", interval_minutes=60,
            enabled=True, notify=False, next_run_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db.add(schedule)
        db.commit()

        with patch("app.jobs.actors.enqueue_scan", return_value=None):
            count = run_due_schedules(db, settings)
        assert count == 1

        db.refresh(schedule)
        assert schedule.last_job_id is not None
        from app.db.base import ensure_utc

        assert ensure_utc(schedule.next_run_at) > datetime.now(UTC)
        job = db.get(ScanJob, schedule.last_job_id)
        assert job.schedule_id == schedule.id

    def test_disabled_schedule_not_run(self, db, client, settings):
        me, program = _setup(client)
        db.add(ScheduledScan(
            program_id=program["id"], profile="passive", interval_minutes=60,
            enabled=False, notify=False, next_run_at=datetime.now(UTC) - timedelta(minutes=1),
        ))
        db.commit()
        with patch("app.jobs.actors.enqueue_scan", return_value=None):
            assert run_due_schedules(db, settings) == 0
