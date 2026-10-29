"""All SQLAlchemy models - the normalized schema from specs/architecture/database.md.

Design rules:
- Source observations (raw tool output / imports) are immutable and separate
  from normalized entities; provenance is always traceable.
- Timestamps are UTC; UUID primary keys; soft-delete via archived_at where noted.
- JSONB on PostgreSQL, JSON on dev SQLite (JSONVariant).
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import (
    GUID,
    Base,
    JSONVariant,
    TimestampMixin,
    new_uuid,
    utcnow,
)


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:
        return self.value


# --------------------------------------------------------------------------
# Identity & policy


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    sessions: Mapped[list[Session]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(GUID, ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="sessions")


class Program(Base, TimestampMixin):
    __tablename__ = "programs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(
        SAEnum("hackerone", "bugcrowd", "intigriti", "other", name="platform"),
        default="other",
        nullable=False,
    )
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    last_policy_review: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scope_rules: Mapped[list[ScopeRule]] = relationship(back_populates="program", cascade="all, delete-orphan")
    policy_versions: Mapped[list[PolicyVersion]] = relationship(back_populates="program")


class PolicyVersion(Base):
    __tablename__ = "policy_versions"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    program: Mapped[Program] = relationship(back_populates="policy_versions")

    __table_args__ = (UniqueConstraint("program_id", "version", name="uq_policy_version"),)


class ScopeRule(Base, TimestampMixin):
    __tablename__ = "scope_rules"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    policy_version_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("policy_versions.id"), nullable=True)
    kind: Mapped[str] = mapped_column(
        SAEnum(
            "domain_exact",
            "domain_wildcard",
            "cidr",
            "url_path",
            "method",
            "rate_limit",
            "automation",
            name="scope_rule_kind",
        ),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(String(2048), nullable=False)
    effect: Mapped[str] = mapped_column(SAEnum("allow", "deny", "restrict", name="scope_rule_effect"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    program: Mapped[Program] = relationship(back_populates="scope_rules")

    __table_args__ = (Index("ix_scope_rules_program_priority", "program_id", "priority"),)


# --------------------------------------------------------------------------
# Discovery: assets & endpoints


class AssetKind(StrEnum):
    domain = "domain"
    subdomain = "subdomain"
    ip = "ip"
    url = "url"
    web_service = "web_service"
    api_endpoint = "api_endpoint"


class ScopeStatus(StrEnum):
    in_scope = "in_scope"
    out_of_scope = "out_of_scope"
    needs_confirmation = "needs_confirmation"


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(SAEnum(AssetKind, name="asset_kind"), nullable=False)
    value_normalized: Mapped[str] = mapped_column(String(2048), nullable=False)
    value_original: Mapped[str] = mapped_column(String(2048), nullable=False)
    scope_status: Mapped[str] = mapped_column(
        SAEnum(ScopeStatus, name="scope_status"), default="out_of_scope", nullable=False
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tech: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    missed_scans: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    screenshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("program_id", "type", "value_normalized", name="uq_asset_program_type_value"),
        Index("ix_assets_program_last_seen", "program_id", "last_seen"),
    )


class AssetRelation(Base):
    __tablename__ = "asset_relations"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    parent_id: Mapped[str] = mapped_column(GUID, ForeignKey("assets.id"), nullable=False, index=True)
    child_id: Mapped[str] = mapped_column(GUID, ForeignKey("assets.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(
        SAEnum("resolves_to", "parent_domain", "redirects_to", "serves", name="asset_relation_kind"),
        nullable=False,
    )


class AssetObservation(Base):
    """Immutable raw discovery records with provenance."""

    __tablename__ = "asset_observations"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    tool_run_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("tool_runs.id"), nullable=True)
    import_job_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("import_jobs.id"), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    normalized_to: Mapped[str | None] = mapped_column(GUID, ForeignKey("assets.id"), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Endpoint(Base, TimestampMixin):
    __tablename__ = "endpoints"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(GUID, ForeignKey("assets.id"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    path: Mapped[str] = mapped_column(String(4096), nullable=False)
    query_params: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    content_types: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    body_shape: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    auth_indicators: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    category: Mapped[str] = mapped_column(
        SAEnum(
            "auth",
            "account",
            "profile",
            "admin",
            "file",
            "payment",
            "object_access",
            "resource_mgmt",
            "api_versioning",
            "other",
            name="endpoint_category",
        ),
        default="other",
        nullable=False,
    )
    category_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status_distribution: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("program_id", "asset_id", "method", "path", name="uq_endpoint_program_asset_method_path"),
        Index("ix_endpoints_category", "category"),
    )


class EndpointObservation(Base):
    __tablename__ = "endpoint_observations"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    endpoint_id: Mapped[str] = mapped_column(GUID, ForeignKey("endpoints.id"), nullable=False, index=True)
    tool_run_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("tool_runs.id"), nullable=True)
    raw: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# --------------------------------------------------------------------------
# Execution


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ScanJob(Base, TimestampMixin):
    __tablename__ = "scan_jobs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    profile: Mapped[str] = mapped_column(String(64), nullable=False)
    policy_version_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("policy_versions.id"), nullable=True)
    target_filter: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        SAEnum(JobStatus, name="job_status"), default="queued", nullable=False, index=True
    )
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    progress: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    schedule_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("scheduled_scans.id"), nullable=True)

    __table_args__ = (Index("ix_scan_jobs_program_status_created", "program_id", "status", "created_at"),)


class ScheduledScan(Base, TimestampMixin):
    __tablename__ = "scheduled_scans"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    profile: Mapped[str] = mapped_column(String(64), nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=360)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    targets: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    templates: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    notify: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_cards: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_job_id: Mapped[str | None] = mapped_column(GUID, nullable=True)
    created_by: Mapped[str | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)


class MonitoringEvent(Base):
    __tablename__ = "monitoring_events"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    scan_job_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("scan_jobs.id"), nullable=True)
    kind: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(GUID, nullable=True)
    entity_value: Mapped[str] = mapped_column(String(2048), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    __table_args__ = (Index("ix_monitoring_program_created", "program_id", "created_at"),)


class ToolRun(Base):
    __tablename__ = "tool_runs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    scan_job_id: Mapped[str] = mapped_column(GUID, ForeignKey("scan_jobs.id"), nullable=False, index=True)
    tool: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    args: Mapped[list] = mapped_column(JSONVariant, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    stdout_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    stderr_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    output_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("running", "completed", "failed", "cancelled", name="tool_run_status"),
        default="running",
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ImportJob(Base, TimestampMixin):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(SAEnum("har", name="import_kind"), nullable=False)
    file_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    account_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("queued", "running", "completed", "failed", name="import_status"),
        default="queued",
        nullable=False,
    )
    counts: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


# --------------------------------------------------------------------------
# Research & traffic


class HttpTransaction(Base, TimestampMixin):
    __tablename__ = "http_transactions"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(SAEnum("har_import", "manual", name="tx_source"), nullable=False)
    account_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str] = mapped_column(String(4096), nullable=False)
    url_host: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_headers: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    request_body_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    response_body_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    timing: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    endpoint_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("endpoints.id"), nullable=True)

    __table_args__ = (Index("ix_http_transactions_host_method", "url_host", "method"),)


class ComparisonSet(Base, TimestampMixin):
    __tablename__ = "comparison_sets"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalization_profile_id: Mapped[str | None] = mapped_column(
        GUID, ForeignKey("normalization_profiles.id"), nullable=True
    )


class ComparisonMember(Base):
    __tablename__ = "comparison_members"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    set_id: Mapped[str] = mapped_column(GUID, ForeignKey("comparison_sets.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(GUID, ForeignKey("http_transactions.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class NormalizationProfile(Base, TimestampMixin):
    __tablename__ = "normalization_profiles"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ignore_headers: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)
    dynamic_rules: Mapped[list | None] = mapped_column(JSONVariant, nullable=True)


class CardStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    needs_verification = "needs_verification"
    confirmed = "confirmed"
    rejected = "rejected"
    blocked = "blocked"
    archived = "archived"


class ResearchCard(Base, TimestampMixin):
    __tablename__ = "research_cards"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    asset_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("assets.id"), nullable=True, index=True)
    endpoint_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("endpoints.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    required_authorization: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_accounts: Mapped[str | None] = mapped_column(Text, nullable=True)
    methodology: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(CardStatus, name="card_status"), default="not_started", nullable=False, index=True
    )
    observations_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    priority_factors: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)


class CardStatusHistory(Base):
    __tablename__ = "card_status_history"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    card_id: Mapped[str] = mapped_column(GUID, ForeignKey("research_cards.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)


class ResearchTemplate(Base, TimestampMixin):
    __tablename__ = "research_templates"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("programs.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[dict] = mapped_column(JSONVariant, nullable=False)


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    card_id: Mapped[str] = mapped_column(GUID, ForeignKey("research_cards.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    checked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


# --------------------------------------------------------------------------
# Findings & evidence


class FindingStatus(StrEnum):
    potential = "potential"
    under_investigation = "under_investigation"
    verified = "verified"
    false_positive = "false_positive"
    duplicate = "duplicate"
    report_ready = "report_ready"
    reported = "reported"
    resolved = "resolved"


class ValidationStatus(StrEnum):
    unverified = "unverified"
    verified_human = "verified_human"


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cwe: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("assets.id"), nullable=True, index=True)
    endpoint_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("endpoints.id"), nullable=True, index=True)
    severity: Mapped[str | None] = mapped_column(
        SAEnum("info", "low", "medium", "high", "critical", name="severity"), nullable=True
    )
    confidence: Mapped[str | None] = mapped_column(
        SAEnum("tentative", "moderate", "high", name="confidence"), nullable=True
    )
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    reproduction_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum(FindingStatus, name="finding_status"), default="potential", nullable=False, index=True
    )
    validation_status: Mapped[str] = mapped_column(
        SAEnum(ValidationStatus, name="validation_status"),
        default="unverified",
        nullable=False,
    )
    discovery_source: Mapped[str] = mapped_column(
        SAEnum("tool_observation", "research_card", "manual", name="discovery_source"),
        default="manual",
        nullable=False,
    )
    source_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class FindingStatusHistory(Base):
    __tablename__ = "finding_status_history"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(GUID, ForeignKey("findings.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    changed_by: Mapped[str | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)


class FindingLink(Base):
    """Provenance-preserving relationships; duplicates are linked, never merged destructively."""

    __tablename__ = "finding_links"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    finding_id: Mapped[str] = mapped_column(GUID, ForeignKey("findings.id"), nullable=False, index=True)
    linked_finding_id: Mapped[str] = mapped_column(GUID, ForeignKey("findings.id"), nullable=False)
    kind: Mapped[str] = mapped_column(SAEnum("duplicate_of", "related", name="finding_link_kind"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EvidenceFile(Base, TimestampMixin):
    __tablename__ = "evidence_files"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    redacted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    evidence_id: Mapped[str] = mapped_column(GUID, ForeignKey("evidence_files.id"), nullable=False, index=True)
    finding_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("findings.id"), nullable=True)
    card_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("research_cards.id"), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("http_transactions.id"), nullable=True)


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str] = mapped_column(GUID, ForeignKey("programs.id"), nullable=False, index=True)
    finding_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("findings.id"), nullable=True)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    content_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# --------------------------------------------------------------------------
# Platform


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    actor_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    before: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONVariant, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SavedFilter(Base, TimestampMixin):
    __tablename__ = "saved_filters"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    program_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("programs.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    definition: Mapped[dict] = mapped_column(JSONVariant, nullable=False)
