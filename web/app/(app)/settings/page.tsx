"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAudit, useCsrfToken, useSettings } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Input, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/primitives";
import { PageHeader } from "@/components/domain/shared";
import { formatTime, timeAgo } from "@/lib/utils";

export default function SettingsPage() {
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useSettings();
  const [page, setPage] = useState(1);
  const { data: audit } = useAudit(page);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [pwMessage, setPwMessage] = useState<string | null>(null);

  const refreshTools = useMutation({
    mutationFn: () => apiFetch("/api/v1/settings/tools/refresh", { method: "POST", csrf }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  const changePassword = useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: oldPassword, new_password: newPassword }),
        csrf,
      }),
    onSuccess: () => {
      setPwMessage("Password changed.");
      setOldPassword("");
      setNewPassword("");
    },
    onError: (e) => setPwMessage(e.message),
  });

  const saveWeights = useMutation({
    mutationFn: (weights: Record<string, number>) =>
      apiFetch("/api/v1/settings", { method: "PUT", body: JSON.stringify({ weights }), csrf }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings"] }),
  });

  if (isLoading || !settings) return <Skeleton className="h-64 w-full" />;

  const weights = settings.weights ?? {
    new_asset: 10,
    new_endpoint: 8,
    auth_sensitive: 12,
    unusual_response: 10,
    scanner_observation: 15,
    untested: 6,
    recent_change: 8,
    researcher_weight: 20,
  };

  return (
    <>
      <PageHeader title="Settings" description="Tools, authentication, storage, prioritization, and audit log." />
      <Tabs defaultValue="tools">
        <TabsList>
          <TabsTrigger value="tools">Tools</TabsTrigger>
          <TabsTrigger value="auth">Authentication</TabsTrigger>
          <TabsTrigger value="storage">Storage</TabsTrigger>
          <TabsTrigger value="prioritization">Prioritization</TabsTrigger>
          <TabsTrigger value="audit">Audit log</TabsTrigger>
        </TabsList>

        <TabsContent value="tools" className="pt-4">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-text-primary">Tool availability</h2>
              <Button size="sm" variant="secondary" onClick={() => refreshTools.mutate()} disabled={refreshTools.isPending}>
                <RefreshCw className="h-3.5 w-3.5" /> Detect
              </Button>
            </CardHeader>
            <CardContent className="space-y-2">
              {settings.tools.map((t) => (
                <div key={t.name} className="flex items-center justify-between rounded border border-border bg-app px-3 py-2 text-[13px]">
                  <span className="mono text-text-primary">{t.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="mono text-xs text-text-muted">{t.version ?? "no version"}</span>
                    <Badge tone={t.available ? "success" : "muted"}>{t.available ? "available" : "missing"}</Badge>
                  </div>
                </div>
              ))}
              <p className="pt-1 text-xs text-text-muted">
                Tools are bundled with the worker container. Nuclei runs only templates from the curated,
                explicitly selected subset — never the full template library automatically.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="auth" className="pt-4">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Change password</h2></CardHeader>
            <CardContent className="max-w-sm space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs text-text-secondary">Current password</label>
                <Input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-text-secondary">New password (min 12 chars)</label>
                <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              </div>
              {pwMessage && <p className="text-xs text-text-secondary">{pwMessage}</p>}
              <Button
                onClick={() => changePassword.mutate()}
                disabled={changePassword.isPending || newPassword.length < 12 || !oldPassword}
              >
                Change password
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="storage" className="pt-4">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Storage limits</h2></CardHeader>
            <CardContent className="space-y-2 text-[13px]">
              <p className="text-text-secondary">
                Evidence upload limit: <span className="mono text-text-primary">{settings.evidence_max_mb} MB</span> per file
              </p>
              <p className="text-text-secondary">
                Retention: <span className="mono text-text-primary">{settings.evidence_retention_days || "keep indefinitely"}</span>
              </p>
              <p className="pt-2 text-xs text-text-muted">
                Evidence files are stored on local disk with SHA-256 integrity checks and are only reachable through
                the authenticated download endpoint. Set these values via environment variables (HF_EVIDENCE_MAX_MB,
                HF_EVIDENCE_RETENTION_DAYS).
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="prioritization" className="pt-4">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Prioritization weights</h2>
              <p className="mt-0.5 text-xs text-text-muted">
                Deterministic, explainable scoring. A high score is a lead indicator — never a vulnerability claim.
              </p>
            </CardHeader>
            <CardContent className="max-w-md space-y-2">
              {Object.entries(weights).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between gap-3">
                  <span className="text-[13px] text-text-primary">{key.replace(/_/g, " ")}</span>
                  <input
                    type="number"
                    className="mono w-24 rounded border border-border bg-surface px-2 py-1 text-right text-[13px] text-text-primary focus-visible:border-border-strong focus-visible:outline-none"
                    value={value}
                    min={0}
                    max={100}
                    onChange={(e) => {
                      weights[key] = parseInt(e.target.value, 10) || 0;
                    }}
                  />
                </div>
              ))}
              <Button className="mt-3" onClick={() => saveWeights.mutate({ ...weights })} disabled={saveWeights.isPending}>
                Save weights
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="pt-4">
          <Card className="p-0">
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full min-w-[700px] border-collapse text-[13px]">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-text-muted">
                      <th className="px-3 py-2.5 font-medium">Action</th>
                      <th className="px-3 py-2.5 font-medium">Entity</th>
                      <th className="px-3 py-2.5 font-medium">Correlation</th>
                      <th className="px-3 py-2.5 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(audit?.items ?? []).map((e) => (
                      <tr key={e.id} className="border-b border-border/50">
                        <td className="mono px-3 py-2 text-text-primary">{e.action}</td>
                        <td className="px-3 py-2 text-text-secondary">
                          {e.entity_type}:{e.entity_id?.slice(0, 8) ?? "—"}
                        </td>
                        <td className="mono px-3 py-2 text-xs text-text-muted">{e.correlation_id ?? "—"}</td>
                        <td className="px-3 py-2 text-xs text-text-muted" title={formatTime(e.created_at)}>
                          {timeAgo(e.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-border px-3 py-2">
                <span className="text-xs text-text-muted">{audit?.total ?? 0} events</span>
                <div className="flex gap-1">
                  <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                    Previous
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setPage(page + 1)}>
                    Next
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </>
  );
}
