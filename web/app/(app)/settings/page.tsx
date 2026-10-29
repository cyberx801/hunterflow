"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAudit, useAiStatus, useCsrfToken, useSettings, useUsers } from "@/lib/api/hooks";
import { useAuthContext } from "@/lib/api/auth-context";
import { apiFetch } from "@/lib/api/client";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  Checkbox,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Label,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/primitives";
import { PageHeader } from "@/components/domain/shared";
import { formatTime, timeAgo } from "@/lib/utils";

export default function SettingsPage() {
  const csrf = useCsrfToken();
  const { me } = useAuthContext();
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useSettings();
  const { data: ai } = useAiStatus();
  const { data: users } = useUsers(!!me?.is_admin);
  const [page, setPage] = useState(1);
  const [userDialog, setUserDialog] = useState(false);
  const [newUser, setNewUser] = useState({ username: "", password: "", is_admin: false });
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

  const createUser = useMutation({
    mutationFn: () =>
      apiFetch("/api/v1/users", {
        method: "POST",
        body: JSON.stringify(newUser),
        csrf,
      }),
    onSuccess: () => {
      setUserDialog(false);
      setNewUser({ username: "", password: "", is_admin: false });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const updateUser = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Record<string, boolean> }) =>
      apiFetch(`/api/v1/users/${id}`, { method: "PATCH", body: JSON.stringify(patch), csrf }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
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
          {me?.is_admin && <TabsTrigger value="users">Users</TabsTrigger>}
          <TabsTrigger value="ai">AI</TabsTrigger>
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

        <TabsContent value="users" className="pt-4">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-text-primary">Team members</h2>
                <p className="mt-0.5 text-xs text-text-muted">
                  Shared workspace: every member sees the same programs and data.
                </p>
              </div>
              <Dialog open={userDialog} onOpenChange={setUserDialog}>
                <DialogTrigger asChild>
                  <Button size="sm">New user</Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create user</DialogTitle>
                  </DialogHeader>
                  <div className="space-y-3">
                    <div className="space-y-1.5">
                      <Label>Username</Label>
                      <Input
                        value={newUser.username}
                        onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label>Password (min 12 chars)</Label>
                      <Input
                        type="password"
                        value={newUser.password}
                        onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                      />
                    </div>
                    <label className="flex cursor-pointer items-center gap-2 text-[13px] text-text-primary">
                      <Checkbox
                        checked={newUser.is_admin}
                        onCheckedChange={(v) => setNewUser({ ...newUser, is_admin: !!v })}
                      />
                      Administrator
                    </label>
                    {createUser.error && <p className="text-xs text-danger">{createUser.error.message}</p>}
                    <div className="flex justify-end gap-2">
                      <Button variant="ghost" onClick={() => setUserDialog(false)}>
                        Cancel
                      </Button>
                      <Button
                        onClick={() => createUser.mutate()}
                        disabled={createUser.isPending || !newUser.username || newUser.password.length < 12}
                      >
                        Create user
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {updateUser.error && <p className="text-xs text-danger">{updateUser.error.message}</p>}
              {(users ?? []).map((u) => (
                <div
                  key={u.id}
                  className="flex items-center justify-between gap-3 rounded border border-border bg-app px-3 py-2"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="text-[13px] font-medium text-text-primary">{u.username}</span>
                    {u.id === me?.id && <Badge tone="accent">you</Badge>}
                    <Badge tone={u.is_admin ? "info" : "muted"}>{u.is_admin ? "admin" : "member"}</Badge>
                    <Badge tone={u.is_active ? "success" : "muted"}>{u.is_active ? "active" : "disabled"}</Badge>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    {u.id !== me?.id && (
                      <>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => updateUser.mutate({ id: u.id, patch: { is_admin: !u.is_admin } })}
                        >
                          {u.is_admin ? "Demote" : "Promote"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => updateUser.mutate({ id: u.id, patch: { is_active: !u.is_active } })}
                        >
                          {u.is_active ? "Disable" : "Enable"}
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {!users && <Skeleton className="h-12 w-full" />}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="ai" className="pt-4">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">AI assistant (optional)</h2>
            </CardHeader>
            <CardContent className="space-y-2 text-[13px]">
              <p className="flex items-center gap-2 text-text-secondary">
                Status: <Badge tone={ai?.enabled ? "success" : "muted"}>{ai?.enabled ? "enabled" : "disabled"}</Badge>
              </p>
              <p className="text-text-secondary">
                Model: <span className="mono text-text-primary">{ai?.model}</span>
              </p>
              <p className="text-text-secondary">
                Endpoint: <span className="text-text-primary">{ai?.endpoint_configured ? "configured" : "not set"}</span>
              </p>
              <p className="text-text-secondary">
                API key: <span className="text-text-primary">{ai?.api_key_configured ? "set" : "not set"}</span>
              </p>
              <p className="pt-2 text-xs text-text-muted">
                Configured by environment only: HF_AI_ENABLED=true, HF_AI_BASE_URL (any
                OpenAI-compatible endpoint; local Ollama is the default), HF_AI_MODEL,
                HF_AI_API_KEY. The assistant only reads the workspace data on the page you
                open, has no tool access, and its output is advisory — never a finding.
              </p>
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
