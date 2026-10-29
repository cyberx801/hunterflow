"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Play, Square } from "lucide-react";
import { useCsrfToken, useCuratedTemplates, useProfiles, usePrograms, useProgramId, useScans } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Checkbox, Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from "@/components/ui/primitives";
import { EmptyState, PageHeader, StatusBadge } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";
import type { ScanJob } from "@/lib/api/types";

export default function ReconPage() {
  const router = useRouter();
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const programId = useProgramId();
  const { data: programs } = usePrograms();
  const { data: profiles } = useProfiles();
  const { data: curated } = useCuratedTemplates();
  const { data: scans } = useScans(programId ? { program_id: programId } : {});

  const [open, setOpen] = useState(false);
  const [profile, setProfile] = useState("passive");
  const [targets, setTargets] = useState("");
  const [dryRun, setDryRun] = useState(false);
  const [selectedTemplates, setSelectedTemplates] = useState<string[]>([]);

  const profileSpec = profiles?.find((p) => p.id === profile);
  const activeProgram = programs?.items.find((p) => p.id === programId) ?? programs?.items[0];

  const create = useMutation({
    mutationFn: () =>
      apiFetch<ScanJob>("/api/v1/scans", {
        method: "POST",
        body: JSON.stringify({
          program_id: activeProgram!.id,
          profile,
          targets: targets.split("\n").map((t) => t.trim()).filter(Boolean),
          templates: selectedTemplates,
          dry_run: dryRun,
        }),
        csrf,
      }),
    onSuccess: () => {
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["scans"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const cancel = useMutation({
    mutationFn: (id: string) => apiFetch(`/api/v1/jobs/${id}/cancel`, { method: "POST", csrf }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["scans"] }),
  });

  const jobs = scans?.items ?? [];

  return (
    <>
      <PageHeader
        title="Recon"
        description="Run reconnaissance pipelines over authorized scope. Every target is validated against the program policy."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button disabled={!activeProgram}>
                <Play className="h-4 w-4" /> New scan
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New scan</DialogTitle>
              </DialogHeader>
              {!activeProgram ? (
                <p className="text-sm text-warning">
                  Create a program first — scans require an authorized program scope.
                </p>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    <label className="text-xs text-text-secondary">Program</label>
                    <p className="text-sm text-text-primary">{activeProgram.name}</p>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-xs text-text-secondary">Profile</label>
                    <Select value={profile} onValueChange={setProfile}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {profiles?.map((p) => (
                          <SelectItem key={p.id} value={p.id}>
                            {p.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {profileSpec && (
                      <p className="text-xs text-text-muted">
                        {profileSpec.description} Steps: {profileSpec.steps.join(" → ")}
                      </p>
                    )}
                  </div>

                  {profileSpec?.requires_templates && (
                    <div className="space-y-1.5">
                      <label className="text-xs text-text-secondary">
                        Curated templates (explicit selection required)
                      </label>
                      <div className="max-h-40 space-y-1 overflow-y-auto rounded border border-border bg-app p-2">
                        {curated?.map((t) => (
                          <label key={t.id} className="flex cursor-pointer items-center gap-2 text-[13px] text-text-primary">
                            <Checkbox
                              checked={selectedTemplates.includes(t.id)}
                              onCheckedChange={(v) =>
                                setSelectedTemplates((prev) =>
                                  v ? [...prev, t.id] : prev.filter((x) => x !== t.id)
                                )
                              }
                            />
                            <span className="mono truncate">{t.id}</span>
                            <Badge tone="muted">{t.severity}</Badge>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <label className="text-xs text-text-secondary">
                      Targets (optional — defaults to scope allow rules; must be in scope)
                    </label>
                    <Textarea
                      rows={3}
                      className="mono"
                      placeholder={"https://api.example.com\nstaging.example.com"}
                      value={targets}
                      onChange={(e) => setTargets(e.target.value)}
                    />
                  </div>

                  <label className="flex cursor-pointer items-center gap-2 text-[13px] text-text-primary">
                    <Checkbox checked={dryRun} onCheckedChange={(v) => setDryRun(!!v)} />
                    Dry run — plan steps without executing tools
                  </label>

                  {create.error && <p className="text-xs text-danger">{create.error.message}</p>}
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                      Cancel
                    </Button>
                    <Button onClick={() => create.mutate()} disabled={create.isPending}>
                      {create.isPending ? "Submitting…" : "Start scan"}
                    </Button>
                  </div>
                </div>
              )}
            </DialogContent>
          </Dialog>
        }
      />

      {jobs.length === 0 ? (
        <EmptyState
          title="No scans yet"
          description="Run a passive discovery scan against your program's authorized scope. Results land in the asset inventory."
        />
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <Card key={job.id} className="p-0">
              <button
                data-job-id={job.id}
                className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left"
                onClick={() => router.push(`/recon/jobs/${job.id}`)}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-text-primary">{job.profile.replace(/_/g, " ")}</span>
                    {job.dry_run && <Badge tone="muted">dry run</Badge>}
                    {job.progress && typeof job.progress.current_tool === "string" && (
                      <Badge tone="info">{job.progress.current_tool}</Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-text-muted">
                    created {formatTime(job.created_at)}
                    {job.error_code ? ` · error: ${job.error_code}` : ""}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <StatusBadge status={job.status} />
                  {(job.status === "running" || job.status === "queued") && (
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label="Cancel scan"
                      onClick={(e) => {
                        e.stopPropagation();
                        cancel.mutate(job.id);
                      }}
                      className="rounded p-1.5 text-text-muted hover:bg-raised hover:text-danger"
                    >
                      <Square className="h-4 w-4" />
                    </span>
                  )}
                </div>
              </button>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
