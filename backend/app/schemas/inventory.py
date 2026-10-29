"""Pydantic schemas: assets, endpoints, research, traffic."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AssetOut(BaseModel):
    id: str
    program_id: str
    type: str
    value_normalized: str
    value_original: str
    scope_status: str
    http_status: int | None
    tech: list | None
    tags: list | None
    notes: str | None
    first_seen: datetime
    last_seen: datetime
    endpoint_count: int = 0
    card_count: int = 0
    priority_score: int = 0


class AssetUpdate(BaseModel):
    tags: list[str] | None = None
    notes: str | None = None


class EndpointOut(BaseModel):
    id: str
    program_id: str
    asset_id: str
    method: str
    path: str
    category: str
    category_manual: bool
    auth_indicators: dict | None
    status_distribution: dict | None
    content_types: list | None
    first_seen: datetime
    last_seen: datetime
    card_count: int = 0
    priority_score: int = 0
    asset_value: str | None = None


class EndpointUpdate(BaseModel):
    category: str = Field(
        pattern=r"^(auth|account|profile|admin|file|payment|object_access|resource_mgmt|api_versioning|other)$"
    )


class ResearchCardCreate(BaseModel):
    program_id: str
    asset_id: str | None = None
    endpoint_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    hypothesis: str | None = None
    test_category: str | None = None
    required_authorization: str | None = None
    required_accounts: str | None = None
    methodology: str | None = None
    notes_md: str | None = None
    next_action: str | None = None
    template_id: str | None = None


class ResearchCardUpdate(BaseModel):
    title: str | None = None
    hypothesis: str | None = None
    test_category: str | None = None
    required_authorization: str | None = None
    required_accounts: str | None = None
    methodology: str | None = None
    observations_md: str | None = None
    notes_md: str | None = None
    next_action: str | None = None


class CardTransition(BaseModel):
    to: str


class ChecklistItemOut(BaseModel):
    id: str
    label: str
    checked: bool
    position: int


class ResearchCardOut(BaseModel):
    id: str
    program_id: str
    asset_id: str | None
    endpoint_id: str | None
    title: str
    hypothesis: str | None
    test_category: str | None
    required_authorization: str | None
    required_accounts: str | None
    methodology: str | None
    status: str
    observations_md: str | None
    notes_md: str | None
    next_action: str | None
    priority_score: int
    priority_factors: dict | None
    checklist: list[ChecklistItemOut] = []
    created_at: datetime
    updated_at: datetime


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    title_pattern: str | None = None
    hypothesis: str | None = None
    test_category: str | None = None
    methodology: str | None = None
    checklist: list[str] = Field(default_factory=list)


class TemplateOut(BaseModel):
    id: str
    name: str
    body: dict
    created_at: datetime


class TransactionOut(BaseModel):
    id: str
    program_id: str
    source: str
    account_tag: str | None
    method: str
    url: str
    response_status: int | None
    redacted: bool
    created_at: datetime


class ManualTransactionCreate(BaseModel):
    program_id: str
    account_tag: str | None = None
    method: str = Field(pattern=r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")
    url: str = Field(min_length=1, max_length=4096)
    request_headers: dict | None = None
    request_body: str | None = None
    response_status: int | None = None
    response_headers: dict | None = None
    response_body: str | None = None


class ComparisonCreate(BaseModel):
    program_id: str
    name: str = Field(min_length=1, max_length=200)
    transaction_ids: list[str] = Field(min_length=2, max_length=4)


class ComparisonOut(BaseModel):
    id: str
    program_id: str
    name: str
    created_at: datetime
    member_count: int = 0


class NormalizationProfileOut(BaseModel):
    id: str
    name: str
    ignore_headers: list | None
    dynamic_rules: list | None
