"use client";

import { Copy, SearchX } from "lucide-react";
import { useState } from "react";
import { Badge, Button } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

export function MonoValue({ value, className }: { value: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className={cn("group inline-flex max-w-full items-center gap-1.5 text-left", className)}
      onClick={() => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1200);
      }}
      title="Click to copy"
    >
      <span className="mono truncate text-[13px] text-text-primary">{value}</span>
      {copied ? (
        <span className="text-[10px] text-success">copied</span>
      ) : (
        <Copy className="h-3 w-3 shrink-0 text-text-muted opacity-0 transition-opacity group-hover:opacity-100" />
      )}
    </button>
  );
}

const SCOPE_TONES: Record<string, "success" | "muted" | "warning"> = {
  in_scope: "success",
  out_of_scope: "muted",
  needs_confirmation: "warning",
};

const SCOPE_LABELS: Record<string, string> = {
  in_scope: "in scope",
  out_of_scope: "out of scope",
  needs_confirmation: "needs confirmation",
};

export function ScopeBadge({ status }: { status: string }) {
  return (
    <Badge tone={SCOPE_TONES[status] ?? "muted"}>{SCOPE_LABELS[status] ?? status}</Badge>
  );
}

const STATUS_TONES: Record<string, "muted" | "info" | "success" | "warning" | "danger" | "accent"> = {
  not_started: "muted",
  in_progress: "info",
  needs_verification: "warning",
  confirmed: "success",
  rejected: "danger",
  blocked: "warning",
  archived: "muted",
  potential: "muted",
  under_investigation: "info",
  verified: "success",
  false_positive: "danger",
  duplicate: "muted",
  report_ready: "accent",
  reported: "info",
  resolved: "success",
  queued: "muted",
  running: "info",
  completed: "success",
  failed: "danger",
  cancelled: "muted",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge tone={STATUS_TONES[status] ?? "muted"}>{status.replace(/_/g, " ")}</Badge>
  );
}

const SEVERITY_TONES: Record<string, "muted" | "info" | "warning" | "danger"> = {
  info: "muted",
  low: "info",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

export function SeverityBadge({ severity }: { severity: string | null }) {
  if (!severity) return <Badge tone="muted">unset</Badge>;
  return <Badge tone={SEVERITY_TONES[severity] ?? "muted"}>{severity}</Badge>;
}

export function ValidationBadge({ status }: { status: string }) {
  return status === "verified_human" ? (
    <Badge tone="success">human-verified</Badge>
  ) : (
    <Badge tone="warning">unverified</Badge>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-panel border border-dashed border-border py-14 text-center">
      <SearchX className="h-6 w-6 text-text-muted" aria-hidden />
      <p className="text-sm font-medium text-text-primary">{title}</p>
      <p className="max-w-sm text-[13px] text-text-secondary">{description}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: React.ReactNode;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
        {description && <p className="mt-0.5 text-[13px] text-text-secondary">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function MethodBadge({ method }: { method: string }) {
  const tone: Record<string, "info" | "accent" | "success" | "danger" | "warning" | "muted"> = {
    GET: "info",
    POST: "accent",
    PUT: "warning",
    PATCH: "warning",
    DELETE: "danger",
    HEAD: "muted",
    OPTIONS: "muted",
  };
  return (
    <Badge tone={tone[method] ?? "muted"} className="mono min-w-[3.2rem] justify-center">
      {method}
    </Badge>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cn("inline-block animate-pulse", className)}>…</span>;
}
