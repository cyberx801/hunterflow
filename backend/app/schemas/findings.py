"""Pydantic schemas: findings, evidence, reports, overview, settings."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FindingCreate(BaseModel):
    program_id: str
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    category: str | None = None
    cwe: str | None = None
    asset_id: str | None = None
    endpoint_id: str | None = None
    severity: str | None = Field(default=None, pattern=r"^(info|low|medium|high|critical)$")
    confidence: str | None = Field(default=None, pattern=r"^(tentative|moderate|high)$")
    impact: str | None = None
    reproduction_steps: str | None = None
    discovery_source: str = Field(default="manual", pattern=r"^(tool_observation|research_card|manual)$")
    source_ref: str | None = None


class FindingUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    cwe: str | None = None
    severity: str | None = Field(default=None, pattern=r"^(info|low|medium|high|critical)$")
    confidence: str | None = Field(default=None, pattern=r"^(tentative|moderate|high)$")
    impact: str | None = None
    reproduction_steps: str | None = None


class FindingTransition(BaseModel):
    to: str
    verified_human_confirmation: bool = False


class FindingOut(BaseModel):
    id: str
    program_id: str
    title: str
    description: str | None
    category: str | None
    cwe: str | None
    asset_id: str | None
    endpoint_id: str | None
    severity: str | None
    confidence: str | None
    impact: str | None
    reproduction_steps: str | None
    status: str
    validation_status: str
    discovery_source: str
    source_ref: str | None
    created_at: datetime
    updated_at: datetime


class FindingLinkCreate(BaseModel):
    linked_finding_id: str
    kind: str = Field(pattern=r"^(duplicate_of|related)$")
    note: str | None = None


class ReportCreate(BaseModel):
    finding_id: str
    format: str = Field(pattern=r"^(markdown|json|html)$")


class ReportOut(BaseModel):
    id: str
    finding_id: str
    format: str
    generated_at: datetime
    content: str | None = None


class EvidenceOut(BaseModel):
    id: str
    program_id: str
    filename: str
    sha256: str
    size: int
    mime: str
    redacted: bool
    created_at: datetime


class OverviewOut(BaseModel):
    program_count: int
    asset_count: int
    endpoint_count: int
    finding_count: int
    unverified_finding_count: int
    active_scan_count: int
    research_queue: list[dict]
    findings_needing_verification: list[dict]
    recent_changes: list[dict]
    recent_activity: list[dict]


class SettingsUpdate(BaseModel):
    weights: dict[str, int] | None = None
    evidence_max_mb: int | None = Field(default=None, ge=1, le=1024)
    evidence_retention_days: int | None = Field(default=None, ge=0)


class ToolOut(BaseModel):
    name: str
    version: str | None
    available: bool
    last_checked: datetime | None
