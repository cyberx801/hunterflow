"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck, Trash2 } from "lucide-react";
import { useCsrfToken, usePolicyVersions, useScopeRules } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from "@/components/ui/primitives";
import { EmptyState } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";
import type { ScopeRule } from "@/lib/api/types";

const KINDS: { value: string; label: string; placeholder: string }[] = [
  { value: "domain_exact", label: "Exact domain", placeholder: "example.com" },
  { value: "domain_wildcard", label: "Wildcard domain", placeholder: "*.example.com" },
  { value: "cidr", label: "IP / CIDR", placeholder: "10.0.0.0/24" },
  { value: "url_path", label: "URL path restriction", placeholder: "/admin" },
  { value: "method", label: "HTTP method", placeholder: "POST" },
  { value: "automation", label: "Automation policy", placeholder: "allowed | denied | confirm" },
  { value: "rate_limit", label: "Rate limit", placeholder: "5" },
];

const EFFECTS = [
  { value: "allow", label: "Allow" },
  { value: "deny", label: "Deny" },
  { value: "restrict", label: "Restrict" },
];

function effectTone(effect: string) {
  return effect === "allow" ? "success" : effect === "deny" ? "danger" : "warning";
}

export function ScopePanel({ programId }: { programId: string }) {
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const { data: rules } = useScopeRules(programId);
  const { data: versions } = usePolicyVersions(programId);

  const [kind, setKind] = useState("domain_wildcard");
  const [value, setValue] = useState("");
  const [effect, setEffect] = useState("allow");
  const [priority, setPriority] = useState("10");
  const [notes, setNotes] = useState("");
  const [previewTargets, setPreviewTargets] = useState("");
  const [previewResult, setPreviewResult] = useState<null | {
    target: string;
    allowed: boolean;
    requires_confirmation: boolean;
    matched_rules: string[];
    reason: string;
  }[]>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["scope", programId] });
    queryClient.invalidateQueries({ queryKey: ["programs"] });
  };

  const addRule = useMutation({
    mutationFn: () =>
      apiFetch<ScopeRule>(`/api/v1/programs/${programId}/scope/rules`, {
        method: "POST",
        body: JSON.stringify({ kind, value, effect, priority: parseInt(priority, 10) || 100, notes: notes || null }),
        csrf,
      }),
    onSuccess: () => {
      invalidate();
      setValue("");
      setNotes("");
    },
  });

  const deleteRule = useMutation({
    mutationFn: (ruleId: string) =>
      apiFetch(`/api/v1/programs/${programId}/scope/rules/${ruleId}`, { method: "DELETE", csrf }),
    onSuccess: invalidate,
  });

  const preview = useMutation({
    mutationFn: () =>
      apiFetch<
        { target: string; allowed: boolean; requires_confirmation: boolean; matched_rules: string[]; reason: string }[]
      >(`/api/v1/programs/${programId}/scope/preview`, {
        method: "POST",
        body: JSON.stringify({
          targets: previewTargets.split("\n").map((t) => t.trim()).filter(Boolean).slice(0, 50),
          methods: ["GET"],
        }),
      }),
    onSuccess: (r) => setPreviewResult(r),
  });

  const publishVersion = useMutation({
    mutationFn: () =>
      apiFetch(`/api/v1/programs/${programId}/scope/versions`, {
        method: "POST",
        body: JSON.stringify({ change_summary: "Manual policy publish" }),
        csrf,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scope", programId, "versions"] });
      queryClient.invalidateQueries({ queryKey: ["programs"] });
    },
  });

  const kindInfo = KINDS.find((k) => k.value === kind);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-text-primary">Scope rules</h2>
          <p className="mt-0.5 text-xs text-text-muted">
            Every active network operation is gated by these rules. Denies win over allows; anything not
            explicitly allowed requires confirmation.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {!rules || rules.length === 0 ? (
            <EmptyState
              title="No scope rules"
              description="Add your first rule. Wildcard rules like *.example.com authorize subdomains but not the apex domain itself."
            />
          ) : (
            <div className="space-y-1">
              {rules.map((rule) => (
                <div
                  key={rule.id}
                  className="flex items-center justify-between gap-3 rounded border border-border bg-app px-3 py-2"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <Badge tone={effectTone(rule.effect)}>{rule.effect}</Badge>
                    <span className="text-xs text-text-muted">{rule.kind.replace(/_/g, " ")}</span>
                    <span className="mono truncate text-[13px] text-text-primary">{rule.value}</span>
                    {rule.notes && <span className="truncate text-xs text-text-muted">— {rule.notes}</span>}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-text-muted">prio {rule.priority}</span>
                    <button
                      className="rounded p-1 text-text-muted hover:bg-raised hover:text-danger"
                      onClick={() => deleteRule.mutate(rule.id)}
                      aria-label={`Delete rule ${rule.value}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="grid gap-2 md:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-xs text-text-secondary">Rule kind</label>
              <Select value={kind} onValueChange={setKind}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {KINDS.map((k) => (
                    <SelectItem key={k.value} value={k.value}>
                      {k.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-text-secondary">Value</label>
              <Input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={kindInfo?.placeholder}
                className="mono"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-text-secondary">Effect</label>
              <Select value={effect} onValueChange={setEffect}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EFFECTS.map((e) => (
                    <SelectItem key={e.value} value={e.value}>
                      {e.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-text-secondary">Priority (lower wins)</label>
              <Input
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                inputMode="numeric"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs text-text-secondary">Notes (optional)</label>
            <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. per program policy section 3" />
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={() => addRule.mutate()} disabled={addRule.isPending || !value.trim()}>
              <Plus className="h-4 w-4" /> Add rule
            </Button>
            {addRule.error && <span className="text-xs text-danger">{addRule.error.message}</span>}
            <div className="ml-auto flex items-center gap-2">
              {versions && versions.length > 0 && (
                <span className="text-xs text-text-muted">
                  policy v{versions[0].version} · {versions[0].rule_count} rules
                </span>
              )}
              <Button
                variant="secondary"
                onClick={() => publishVersion.mutate()}
                disabled={!rules || rules.length === 0 || publishVersion.isPending}
                title="Snapshot the current rules into an immutable policy version"
              >
                <ShieldCheck className="h-4 w-4" /> Publish policy version
              </Button>
            </div>
          </div>
          {publishVersion.error && (
            <p className="text-xs text-danger">{publishVersion.error.message}</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h2 className="text-sm font-semibold text-text-primary">Scope preview</h2>
          <p className="mt-0.5 text-xs text-text-muted">
            Test candidate targets against the effective policy — no network activity.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={previewTargets}
            onChange={(e) => setPreviewTargets(e.target.value)}
            placeholder={"https://api.example.com/v1\nhttps://evil.net/admin"}
            rows={3}
            className="mono"
          />
          <Button variant="secondary" onClick={() => preview.mutate()} disabled={preview.isPending}>
            Evaluate targets
          </Button>
          {previewResult && (
            <div className="space-y-1">
              {previewResult.map((r, i) => (
                <div
                  key={i}
                  className="rounded border border-border bg-app px-3 py-2 text-[13px]"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="mono truncate text-text-primary">{r.target}</span>
                    {r.allowed ? (
                      <Badge tone="success">allowed</Badge>
                    ) : r.requires_confirmation ? (
                      <Badge tone="warning">needs confirmation</Badge>
                    ) : (
                      <Badge tone="danger">blocked</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-text-muted">{r.reason}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {versions && versions.length > 0 && (
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Policy version history</h2>
          </CardHeader>
          <CardContent className="space-y-1">
            {versions.slice(0, 10).map((v) => (
              <div key={v.id} className="flex items-center justify-between text-[13px]">
                <span className="mono text-text-primary">v{v.version}</span>
                <span className="truncate text-text-secondary">{v.change_summary || "—"}</span>
                <span className="shrink-0 text-xs text-text-muted">{formatTime(v.created_at)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
