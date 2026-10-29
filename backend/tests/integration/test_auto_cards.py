"""Auto draft research cards from monitoring changes (opt-in per schedule)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.db.models import Asset, Endpoint, EndpointObservation, ResearchCard, ScanJob, ScheduledScan, ToolRun
from app.services.monitoring import finalize_scan_changes
from tests.helpers import register_user


def _setup(client):
    me = register_user(client)
    program = client.post(
        "/api/v1/programs", json={"name": "Auto", "platform": "other"},
        headers={"X-CSRF-Token": me["csrf_token"]},
    ).json()
    return program


def _job(db, program_id, schedule_id=None):
    job = ScanJob(
        program_id=program_id, profile="web_inventory", status="completed",
        schedule_id=schedule_id, started_at=datetime.now(UTC), finished_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()
    return job


def _new_endpoint(db, program_id, path):
    asset = Asset(
        program_id=program_id, type="url", value_original=f"http://x{path}",
        value_normalized=f"http://x{path}", scope_status="in_scope",
    )
    db.add(asset)
    db.flush()
    endpoint = Endpoint(
        program_id=program_id, asset_id=asset.id, method="GET", path=path,
        category="other", content_types=["application/json"],
    )
    db.add(endpoint)
    db.flush()
    return endpoint


def test_auto_cards_created_for_new_endpoint(client, db):
    program = _setup(client)
    schedule = ScheduledScan(
        program_id=program["id"], profile="web_inventory", interval_minutes=60,
        enabled=True, notify=False, auto_cards=True,
        next_run_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.add(schedule)
    db.flush()

    job = _job(db, program["id"], schedule.id)
    run = ToolRun(scan_job_id=job.id, tool="katana", args=[], timeout_seconds=60)
    db.add(run)
    db.flush()
    endpoint = _new_endpoint(db, program["id"], "/api/v1/fresh")
    db.add(EndpointObservation(endpoint_id=endpoint.id, tool_run_id=run.id, raw={}))
    db.commit()

    events = finalize_scan_changes(db, job)
    assert [e.kind for e in events] == ["new_endpoint"]

    cards = db.scalars(select(ResearchCard)).all()
    assert len(cards) == 1
    card = cards[0]
    assert card.endpoint_id == endpoint.id
    assert "Auto-created by monitoring" in (card.notes_md or "")
    assert card.status == "not_started"


def test_auto_cards_disabled_by_default(client, db):
    program = _setup(client)
    schedule = ScheduledScan(
        program_id=program["id"], profile="web_inventory", interval_minutes=60,
        enabled=True, notify=False, auto_cards=False,
        next_run_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.add(schedule)
    db.flush()
    job = _job(db, program["id"], schedule.id)
    run = ToolRun(scan_job_id=job.id, tool="katana", args=[], timeout_seconds=60)
    db.add(run)
    db.flush()
    endpoint = _new_endpoint(db, program["id"], "/api/v1/other")
    db.add(EndpointObservation(endpoint_id=endpoint.id, tool_run_id=run.id, raw={}))
    db.commit()

    finalize_scan_changes(db, job)
    assert db.scalars(select(ResearchCard)).all() == []


def test_auto_cards_skip_existing_card(client, db):
    program = _setup(client)
    schedule = ScheduledScan(
        program_id=program["id"], profile="web_inventory", interval_minutes=60,
        enabled=True, notify=False, auto_cards=True,
        next_run_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db.add(schedule)
    db.flush()
    job = _job(db, program["id"], schedule.id)
    run = ToolRun(scan_job_id=job.id, tool="katana", args=[], timeout_seconds=60)
    db.add(run)
    db.flush()
    endpoint = _new_endpoint(db, program["id"], "/api/v1/known")
    db.add(EndpointObservation(endpoint_id=endpoint.id, tool_run_id=run.id, raw={}))
    db.add(ResearchCard(
        program_id=program["id"], endpoint_id=endpoint.id, title="Already here",
        status="in_progress",
    ))
    db.commit()

    finalize_scan_changes(db, job)
    cards = db.scalars(select(ResearchCard)).all()
    assert len(cards) == 1
    assert cards[0].title == "Already here"


def test_manual_runs_never_create_cards(client, db):
    program = _setup(client)
    job = _job(db, program["id"], schedule_id=None)
    run = ToolRun(scan_job_id=job.id, tool="katana", args=[], timeout_seconds=60)
    db.add(run)
    db.flush()
    endpoint = _new_endpoint(db, program["id"], "/api/v1/manual")
    db.add(EndpointObservation(endpoint_id=endpoint.id, tool_run_id=run.id, raw={}))
    db.commit()

    finalize_scan_changes(db, job)
    assert db.scalars(select(ResearchCard)).all() == []
