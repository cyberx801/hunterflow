"use client";

import { useState } from "react";
import { Play, Plus, Trash2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  useCsrfToken,
  useMonitoringEvents,
  useMonitoringStatus,
  usePrograms,
  useProgramId,
  useProfiles,
  useSchedules,
} from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { useUrlFilters } from "@/lib/hooks/use-url-filters";
import {
  Badge,
  Button,
  Checkbox,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
} from "@/components/ui/primitives";
import { EmptyState, PageHeader } from "@/components/domain/shared";
import { formatTime, timeAgo } from "@/lib/utils";
import type { Schedule } from "@/lib/api/types";

const KIND_LABEL: Record<string, string> = {
  new_asset: "new asset",
  new_endpoint: "new endpoint",
  possibly_removed_asset: "possibly removed",
  removed_asset: "removed",
};

function kindTone(kind: string): "success" | "info" | "warning" | "danger" | "muted" {
  if (kind === "new_asset") return "success";
  if (kind === "new_endpoint") return "info";
  if (kind === "possibly_removed_asset") return "warning";
  if (kind === "removed_asset") return "danger";
  return "muted";
}

export default function MonitoringPage() {
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const programId = useProgramId();
  const { data: schedules, isLoading } = useSchedules(programId);
  const { data: status } = useMonitoringStatus();
  const { data: programs } = usePrograms();
  const { data: profiles } = useProfiles();
  const { filters, setFilter } = useUrlFilters(["kind"]);
  const { data: events } = useMonitoringEvents({ program_id: programId, kind: filters.kind });

  const [open, setOpen] = useState(false);
  const [programIdForNew, setProgramIdForNew] = useState(programId ?? "");
  const [profile, setProfile] = useState("passive");
  const [interval, setIntervalMinutes] = useState("360");
  const [notify, setNotify] = useState(true);
  const [targets, setTargets] = useState("");

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["schedules"] });
    queryClient.invalidateQueries({ queryKey: ["monitoring-events"] });
  };

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Schedule>("/api/v1/schedules", {
        method: "POST",
        body: JSON.stringify({
          program_id: programIdForNew,
          profile,
          interval_minutes: parseInt(interval, 10) || 360,
          targets: targets.split("\n").map((t) => t.trim()).filter(Boolean),
          templates: [],
          notify,
          enabled: true,
        }),
        csrf,
      }),
    onSuccess: () => {
      setOpen(false);
      setTargets("");
      invalidate();
    },
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      apiFetch(`/api/v1/schedules/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
        csrf,
      }),
    onSuccess: invalidate,
  });

  const remove = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/schedules/${id}`, { method: "DELETE", csrf }),
    onSuccess: invalidate,
  });

  const runNow = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/v1/schedules/${id}/run-now`, { method: "POST", csrf }),
    onSuccess: invalidate,
  });

  const rows = schedules ?? [];

  return (
    <>
      <PageHeader
        title="Monitoring"
        description="Recurring scans with change detection. New assets and endpoints are recorded; removals require two consecutive misses."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button disabled={!programs || programs.items.length === 0}>
                <Plus className="h-4 w-4" /> New schedule
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New monitoring schedule</DialogTitle>
              </DialogHeader>
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label>Program</Label>
                  <Select value={programIdForNew} onValueChange={setProgramIdForNew}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select a program" />
                    </SelectTrigger>
                    <SelectContent>
                      {(programs?.items ?? [])
                        .filter((p) => !p.archived_at)
                        .map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.name}
                          </SelectItem>
                        ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Profile</Label>
                  <Select value={profile} onValueChange={setProfile}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(profiles ?? []).map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Every (minutes)</Label>
                  <Input
                    value={interval}
                    onChange={(e) => setIntervalMinutes(e.target.value)}
                    inputMode="numeric"
                  />
                  <p className="text-xs text-text-muted">
                    Minimum {status?.min_schedule_minutes ?? 15} minutes. Passive every 6–12h,
                    inventory daily is a sensible start.
                  </p>
                </div>
                <div className="space-y-1.5">
                  <Label>Targets (optional — defaults to scope allow rules)</Label>
                  <Textarea
                    rows={3}
                    className="mono"
                    placeholder={"https://api.example.com"}
                    value={targets}
                    onChange={(e) => setTargets(e.target.value)}
                  />
                </div>
                <label className="flex cursor-pointer items-center gap-2 text-[13px] text-text-primary">
                  <Checkbox checked={notify} onCheckedChange={(v) => setNotify(!!v)} />
                  Send webhook notifications for this schedule
                </label>
                {!status?.webhook_configured && (
                  <p className="text-xs text-warning">
                    HF_WEBHOOK_URL is not set, so notifications will be skipped.
                  </p>
                )}
                {create.error && <p className="text-xs text-danger">{create.error.message}</p>}
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" onClick={() => setOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={() => create.mutate()} disabled={!programIdForNew || create.isPending}>
                    Create schedule
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        }
      />

      <Tabs defaultValue="schedules">
        <TabsList>
          <TabsTrigger value="schedules">Schedules</TabsTrigger>
          <TabsTrigger value="changes">Changes</TabsTrigger>
        </TabsList>

        <TabsContent value="schedules" className="pt-4">
          {isLoading ? (
            <Skeleton className="h-40 w-full" />
          ) : rows.length === 0 ? (
            <EmptyState
              title="No schedules"
              description="Create a schedule to scan a program on an interval. Each run is checked against the program's scope policy."
            />
          ) : (
            <div className="overflow-x-auto rounded-panel border border-border bg-surface">
              <table className="w-full min-w-[860px] border-collapse text-[13px]">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="px-3 py-2.5 font-medium">Profile</th>
                    <th className="px-3 py-2.5 font-medium">Every</th>
                    <th className="px-3 py-2.5 font-medium">Next run</th>
                    <th className="px-3 py-2.5 font-medium">Last run</th>
                    <th className="px-3 py-2.5 font-medium">Notify</th>
                    <th className="px-3 py-2.5 font-medium">State</th>
                    <th className="px-3 py-2.5 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((s) => (
                    <tr key={s.id} className="border-b border-border/50">
                      <td className="px-3 py-2.5 text-text-primary">{s.profile.replace(/_/g, " ")}</td>
                      <td className="mono px-3 py-2.5 text-text-secondary">{s.interval_minutes} min</td>
                      <td className="px-3 py-2.5 text-xs text-text-secondary">{s.enabled ? formatTime(s.next_run_at) : "—"}</td>
                      <td className="px-3 py-2.5 text-xs text-text-secondary">
                        {s.last_run_at ? timeAgo(s.last_run_at) : "never"}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-text-secondary">{s.notify ? "on" : "off"}</td>
                      <td className="px-3 py-2.5">
                        <Badge tone={s.enabled ? "success" : "muted"}>
                          {s.enabled ? "enabled" : "disabled"}
                        </Badge>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => runNow.mutate(s.id)}
                            disabled={runNow.isPending}
                          >
                            <Play className="h-3.5 w-3.5" /> Run now
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => toggle.mutate({ id: s.id, enabled: !s.enabled })}
                          >
                            {s.enabled ? "Disable" : "Enable"}
                          </Button>
                          <button
                            className="rounded p-1.5 text-text-muted hover:bg-raised hover:text-danger"
                            onClick={() => remove.mutate(s.id)}
                            aria-label="Delete schedule"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>

        <TabsContent value="changes" className="pt-4">
          <div className="mb-3 flex items-center gap-2">
            <Select value={filters.kind ?? "all"} onValueChange={(v) => setFilter("kind", v === "all" ? null : v)}>
              <SelectTrigger className="w-52">
                <SelectValue placeholder="All changes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All changes</SelectItem>
                <SelectItem value="new_asset">New assets</SelectItem>
                <SelectItem value="new_endpoint">New endpoints</SelectItem>
                <SelectItem value="possibly_removed_asset">Possibly removed</SelectItem>
                <SelectItem value="removed_asset">Removed</SelectItem>
              </SelectContent>
            </Select>
            <span className="text-xs text-text-muted">Auto-refreshes every 15s</span>
          </div>

          {(events ?? []).length === 0 ? (
            <EmptyState
              title="No changes recorded"
              description="Run a schedule (or use Run now). New assets and endpoints will appear here; removals are only confirmed after two consecutive missed runs."
            />
          ) : (
            <div className="overflow-x-auto rounded-panel border border-border bg-surface">
              <table className="w-full min-w-[760px] border-collapse text-[13px]">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="px-3 py-2.5 font-medium">Change</th>
                    <th className="px-3 py-2.5 font-medium">Entity</th>
                    <th className="px-3 py-2.5 font-medium">When</th>
                  </tr>
                </thead>
                <tbody>
                  {(events ?? []).map((e) => (
                    <tr key={e.id} className="border-b border-border/50">
                      <td className="px-3 py-2.5">
                        <Badge tone={kindTone(e.kind)}>{KIND_LABEL[e.kind] ?? e.kind}</Badge>
                      </td>
                      <td className="mono max-w-[520px] px-3 py-2.5">
                        <span className="line-clamp-1 text-text-primary">{e.entity_value}</span>
                        <span className="text-xs text-text-muted"> {e.entity_type}</span>
                      </td>
                      <td className="px-3 py-2.5 text-xs text-text-muted" title={formatTime(e.created_at)}>
                        {timeAgo(e.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </>
  );
}
