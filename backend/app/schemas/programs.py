"""Pydantic schemas: programs and scope."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..domain.scope import Effect, RuleKind


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    platform: str = Field(default="other", pattern=r"^(hackerone|bugcrowd|intigriti|other)$")
    url: str | None = Field(default=None, max_length=2048)
    description: str | None = None
    notes_md: str | None = None
    policy_source_url: str | None = Field(default=None, max_length=2048)
    last_policy_review: datetime | None = None


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    platform: str | None = Field(default=None, pattern=r"^(hackerone|bugcrowd|intigriti|other)$")
    url: str | None = None
    description: str | None = None
    notes_md: str | None = None
    policy_source_url: str | None = None
    last_policy_review: datetime | None = None
    archived: bool | None = None


class ProgramOut(BaseModel):
    id: str
    name: str
    platform: str
    url: str | None
    description: str | None
    notes_md: str | None
    policy_source_url: str | None
    last_policy_review: datetime | None
    archived_at: datetime | None
    current_policy_version: int
    created_at: datetime
    updated_at: datetime


class ScopeRuleCreate(BaseModel):
    kind: RuleKind
    value: str = Field(min_length=1, max_length=2048)
    effect: Effect
    priority: int = Field(default=100, ge=1, le=10000)
    notes: str | None = None


class ScopeRuleOut(BaseModel):
    id: str
    kind: RuleKind
    value: str
    effect: Effect
    priority: int
    notes: str | None


class ScopePreviewRequest(BaseModel):
    targets: list[str] = Field(min_length=1, max_length=50)
    methods: list[str] = Field(default_factory=lambda: ["GET"])


class ScopePreviewResult(BaseModel):
    target: str
    allowed: bool
    requires_confirmation: bool
    matched_rules: list[str]
    reason: str


class PolicyVersionOut(BaseModel):
    id: str
    version: int
    change_summary: str | None
    created_at: datetime
    rule_count: int


class PolicyVersionDetail(PolicyVersionOut):
    rules: list[ScopeRuleOut]
    previous_rules: list[ScopeRuleOut] | None = None


class ConfirmationCreate(BaseModel):
    target: str = Field(min_length=1, max_length=2048)
    note: str | None = None
