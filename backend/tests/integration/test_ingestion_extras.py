"""Ingestion of dns_record and passive url observations."""

from __future__ import annotations

from sqlalchemy import select

from app.db.models import Asset, AssetRelation, Program
from app.domain.scope import Policy
from app.integrations.tools.base import Observation
from app.services.ingestion import ingest
from tests.helpers import register_user


def _program(client, db) -> tuple[Program, Policy]:
    me = register_user(client)
    csrf = me["csrf_token"]
    program = client.post(
        "/api/v1/programs", json={"name": "Ingest", "platform": "other"}, headers={"X-CSRF-Token": csrf}
    ).json()
    client.post(
        f"/api/v1/programs/{program['id']}/scope/rules",
        json={"kind": "domain_wildcard", "value": "*.example.com", "effect": "allow", "priority": 10},
        headers={"X-CSRF-Token": csrf},
    )
    row = db.get(Program, program["id"])
    policy = Policy.from_db_rules(row.scope_rules)
    return row, policy


def test_dns_record_creates_ip_relation(client, db):
    program, policy = _program(client, db)
    ingest(
        db,
        program,
        Observation(
            kind="dns_record",
            payload={"host": "api.example.com", "ips": ["203.0.113.10", "203.0.113.11"]},
            source="dnsx",
        ),
        policy,
        tool_run_id=None,
    )
    db.commit()

    host = db.scalar(select(Asset).where(Asset.value_normalized == "api.example.com"))
    assert host is not None
    assert host.scope_status == "in_scope"
    ips = {a.value_normalized for a in db.scalars(select(Asset).where(Asset.type == "ip")).all()}
    assert ips == {"203.0.113.10", "203.0.113.11"}
    relations = db.scalars(select(AssetRelation)).all()
    assert len(relations) == 2
    assert all(r.kind == "resolves_to" and r.parent_id == host.id for r in relations)


def test_passive_url_creates_url_asset(client, db):
    program, policy = _program(client, db)
    ingest(
        db,
        program,
        Observation(
            kind="url",
            payload={"url": "https://api.example.com/v1/orders?id=1", "source": "wayback"},
            source="gau",
        ),
        policy,
        tool_run_id=None,
    )
    db.commit()

    url_asset = db.scalar(select(Asset).where(Asset.type == "url"))
    assert url_asset is not None
    assert url_asset.value_normalized == "https://api.example.com/v1/orders?id=1"
    assert url_asset.scope_status == "in_scope"
