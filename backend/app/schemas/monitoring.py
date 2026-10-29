"""Schemas: scheduled scans and monitoring events."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    program_id: str
    profile: str = Field(pattern=r"^(passive|light_recon|web_inventory|url_discovery|vuln_checks)$")
    interval_minutes: int = Field(default=360, le=10080)
    targets: list[str] = Field(default_factory=list, max_length=200)
    templates: list[str] = Field(default_factory=list, max_length=50)
    notify: bool = True
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    interval_minutes: int | None = Field(default=None, le=10080)
    targets: list[str] | None = None
    templates: list[str] | None = None
    notify: bool | None = None
    enabled: bool | None = None


class ScheduleOut(BaseModel):
    id: str
    program_id: str
    profile: str
    interval_minutes: int
    enabled: bool
    notify: bool
    targets: list | None
    templates: list | None
    next_run_at: datetime
    last_run_at: datetime | None
    last_job_id: str | None
    created_at: datetime


class MonitoringEventOut(BaseModel):
    id: str
    program_id: str
    scan_job_id: str | None
    kind: str
    entity_type: str
    entity_id: str | None
    entity_value: str
    detail: dict | None
    created_at: datetime
