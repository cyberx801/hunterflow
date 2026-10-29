"""PDF report generation and download."""

from __future__ import annotations

from tests.helpers import csrf_headers, register_user


def test_pdf_report_generation_and_download(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = client.post(
        "/api/v1/programs", json={"name": "PDF", "platform": "other"}, headers=csrf_headers(csrf)
    ).json()
    finding = client.post(
        "/api/v1/findings",
        json={
            "program_id": program["id"],
            "title": "IDOR in orders",
            "description": "Object-level access issue",
            "severity": "high",
            "impact": "Account data disclosure",
            "reproduction_steps": "1. Login as A\n2. Fetch order of B",
        },
        headers=csrf_headers(csrf),
    ).json()

    r = client.post(
        "/api/v1/reports",
        json={"finding_id": finding["id"], "format": "pdf"},
        headers=csrf_headers(csrf),
    )
    assert r.status_code == 201, r.text
    report = r.json()
    assert report["format"] == "pdf"
    assert report["content"] is None

    dl = client.get(f"/api/v1/reports/{report['id']}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/pdf"
    assert dl.content.startswith(b"%PDF")
    assert len(dl.content) > 800


def test_markdown_download(client):
    me = register_user(client)
    csrf = me["csrf_token"]
    program = client.post(
        "/api/v1/programs", json={"name": "MD", "platform": "other"}, headers=csrf_headers(csrf)
    ).json()
    finding = client.post(
        "/api/v1/findings",
        json={"program_id": program["id"], "title": "Reflected XSS"},
        headers=csrf_headers(csrf),
    ).json()
    report = client.post(
        "/api/v1/reports",
        json={"finding_id": finding["id"], "format": "markdown"},
        headers=csrf_headers(csrf),
    ).json()
    dl = client.get(f"/api/v1/reports/{report['id']}/download")
    assert dl.status_code == 200
    assert b"UNVERIFIED" in dl.content
