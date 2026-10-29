"""Pydantic schemas: scans, jobs, tool runs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ScanCreate(BaseModel):
    program_id: str
    profile: str = Field(pattern=r"^(passive|light_recon|web_inventory|url_discovery|web_crawl|screenshots|vuln_checks)$")
    targets: list[str] = Field(default_factory=list, max_length=200)
    templates: list[str] = Field(default_factory=list, max_length=50)
    dry_run: bool = False


class ScanOut(BaseModel):
    id: str
    program_id: str
    profile: str
    status: str
    dry_run: bool
    error_code: str | None
    progress: dict | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class ToolRunOut(BaseModel):
    id: str
    tool: str
    version: str | None
    args: list[str]
    exit_code: int | None
    status: str
    timeout_seconds: int
    started_at: datetime
    finished_at: datetime | None


class JobOut(ScanOut):
    policy_version: int | None
    tool_runs: list[ToolRunOut] = []


class ScanProfileOut(BaseModel):
    id: str
    label: str
    description: str
    steps: list[str]
    requires_templates: bool = False


class CuratedTemplateOut(BaseModel):
    id: str
    name: str
    severity: str
    category: str


