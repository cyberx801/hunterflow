"""Report generation: Markdown / JSON / HTML (HF-FR-100/101).

Honesty rules (Constitution P5):
- Verification banner always reflects validation_status/status.
- Nothing is fabricated; missing fields render as "not provided".
- No submission code path exists anywhere in this codebase.
"""

from __future__ import annotations

import html as html_module
import json
from datetime import UTC, datetime
from pathlib import Path

from ..core.config import Settings
from ..db.models import EvidenceFile, EvidenceLink, Finding

TEMPLATE_VERSION = 1

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _verification_banner(finding: Finding) -> str:
    if finding.validation_status == "verified_human" and finding.status in (
        "verified",
        "report_ready",
        "reported",
        "resolved",
    ):
        return "**Verification status: VERIFIED (human-confirmed)**"
    return "**Verification status: UNVERIFIED — this finding requires manual verification**"


def _section(title: str, content: str | None) -> str:
    return f"## {title}\n\n{content if content else '_Not provided._'}\n"


def _evidence_lines(finding: Finding, db) -> list[str]:
    links = db.query(EvidenceLink).filter(EvidenceLink.finding_id == finding.id).all()
    lines = []
    for link in links:
        ev = db.get(EvidenceFile, link.evidence_id)
        if ev is not None:
            lines.append(f"- {ev.filename} (sha256: `{ev.sha256}`, {ev.size} bytes)")
    return lines


def render_markdown(finding: Finding, db) -> str:
    lines = [
        f"# {finding.title}",
        "",
        _verification_banner(finding),
        "",
        "## Summary",
        "",
        finding.description or "_Not provided._",
        "",
    ]
    if finding.severity:
        lines += [f"**Severity:** {finding.severity}", ""]
    if finding.confidence:
        lines += [f"**Confidence:** {finding.confidence}", ""]
    if finding.cwe:
        lines += [f"**CWE:** {finding.cwe}", ""]
    if finding.category:
        lines += [f"**Category:** {finding.category}", ""]
    lines += [
        "",
        _section("Affected Asset / Endpoint", _affected(finding, db)),
        _section("Preconditions", "See reproduction steps."),
        _section("Reproduction Steps", finding.reproduction_steps),
        _section("Expected Behavior", "The application should enforce access control and validation as designed."),
        _section("Observed Behavior", finding.description),
        _section("Security Impact", finding.impact),
        "## Evidence",
        "",
    ]
    lines += _evidence_lines(finding, db) or ["_No evidence attached._"]
    lines += ["", "## Suggested Remediation", "", "Remediation guidance to be provided by the researcher.", ""]
    lines += ["## Additional Notes", "", finding.source_ref or "_None._", ""]
    return "\n".join(lines)


def _affected(finding: Finding, db) -> str | None:
    if finding.endpoint_id:
        from ..db.models import Endpoint

        ep = db.get(Endpoint, finding.endpoint_id)
        if ep is not None:
            return f"{ep.method} {ep.path}"
    if finding.asset_id:
        from ..db.models import Asset

        asset = db.get(Asset, finding.asset_id)
        if asset is not None:
            return asset.value_normalized
    return None


def render_json(finding: Finding, db) -> str:
    return json.dumps(
        {
            "title": finding.title,
            "verification_status": finding.validation_status,
            "status": finding.status,
            "severity": finding.severity,
            "confidence": finding.confidence,
            "cwe": finding.cwe,
            "category": finding.category,
            "affected": _affected(finding, db),
            "description": finding.description,
            "reproduction_steps": finding.reproduction_steps,
            "impact": finding.impact,
            "evidence": [
                {
                    "filename": ev.filename,
                    "sha256": ev.sha256,
                    "size": ev.size,
                }
                for ev in [
                    db.get(EvidenceFile, link.evidence_id)
                    for link in db.query(EvidenceLink).filter(EvidenceLink.finding_id == finding.id).all()
                ]
                if ev is not None
            ],
            "generated_at": datetime.now(UTC).isoformat(),
        },
        indent=2,
    )


def render_html(finding: Finding, db) -> str:
    md = render_markdown(finding, db)
    # Minimal, safe conversion: escape then wrap in <pre> with basic headings.
    body_lines = []
    for line in md.splitlines():
        if line.startswith("# "):
            body_lines.append(f"<h1>{html_module.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body_lines.append(f"<h2>{html_module.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body_lines.append(f"<li>{html_module.escape(line[2:])}</li>")
        elif line.strip():
            body_lines.append(f"<p>{html_module.escape(line)}</p>")
    banner_class = "verified" if finding.validation_status == "verified_human" else "unverified"
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>HunterFlow Report</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;"
        "color:#1a2027;line-height:1.5} .banner{padding:.75rem 1rem;border-radius:6px;font-weight:600}"
        ".verified{background:#d1fae5;color:#064e3b} .unverified{background:#fef3c7;color:#78350f}"
        "code{background:#f3f4f6;padding:2px 4px;border-radius:4px}</style></head><body>"
        f"<div class='banner {banner_class}'>{html_module.escape(_verification_banner(finding))}</div>"
        + "".join(body_lines)
        + "</body></html>"
    )


def _plain(text: str | None) -> str:
    return (text or "_Not provided._")


def render_pdf(finding: Finding, db) -> bytes:
    from io import BytesIO
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("HFh1", parent=styles["Heading1"], fontSize=16, leading=20, spaceAfter=6)
    h2 = ParagraphStyle("HFh2", parent=styles["Heading2"], fontSize=11.5, leading=15, spaceBefore=10)
    body = ParagraphStyle("HFbody", parent=styles["BodyText"], fontSize=9.5, leading=13)
    verified = finding.validation_status == "verified_human" and finding.status in (
        "verified",
        "report_ready",
        "reported",
        "resolved",
    )
    banner_style = ParagraphStyle(
        "HFbanner",
        parent=body,
        fontSize=9.5,
        leading=13,
        textColor=colors.white,
        backColor=colors.HexColor("#047857") if verified else colors.HexColor("#b45309"),
        borderPadding=6,
    )
    banner_text = (
        "Verification status: VERIFIED (human-confirmed)"
        if verified
        else "Verification status: UNVERIFIED - this finding requires manual verification"
    )

    def para(text: str | None, style=body) -> Paragraph:
        return Paragraph(escape(_plain(text)).replace("\n", "<br/>"), style)

    def section(title: str, content: str | None) -> list:
        return [Paragraph(escape(title), h2), para(content), Spacer(1, 2)]

    story: list = [
        Paragraph(escape(finding.title), h1),
        Paragraph(escape(banner_text), banner_style),
        Spacer(1, 8),
    ]
    story += section("Summary", finding.description)
    meta = (
        f"Severity: {finding.severity or 'unset'} | Confidence: {finding.confidence or 'unset'} | "
        f"CWE: {finding.cwe or 'unset'} | Category: {finding.category or 'unset'}"
    )
    story += [Paragraph(escape(meta), body), Spacer(1, 2)]
    story += section("Affected asset / endpoint", _affected(finding, db))
    story += section("Reproduction steps", finding.reproduction_steps)
    story += section("Security impact", finding.impact)
    evidence = _evidence_lines(finding, db)
    story += [Paragraph("Evidence", h2)]
    if evidence:
        for line in evidence:
            story.append(Paragraph(escape(line.lstrip("- ")), body))
    else:
        story.append(Paragraph("_No evidence attached._", body))
    story += section("Additional notes", finding.source_ref)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=finding.title,
    )
    doc.build(story)
    return buffer.getvalue()


def generate_pdf(db, finding: Finding, settings: Settings) -> tuple[bytes, Path]:
    content = render_pdf(finding, db)
    out_dir = settings.data_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{finding.id}-v{TEMPLATE_VERSION}.pdf"
    path.write_bytes(content)
    return content, path


def generate(db, finding: Finding, fmt: str, settings: Settings) -> tuple[str, Path]:
    renderers = {"markdown": render_markdown, "json": render_json, "html": render_html}
    renderer = renderers[fmt]
    content = renderer(finding, db)
    out_dir = settings.data_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{finding.id}-v{TEMPLATE_VERSION}.{fmt if fmt != 'markdown' else 'md'}"
    path.write_text(content, encoding="utf-8")
    return content, path
