"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Copy, Download, FileText, Upload } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, useFinding, useFindingDuplicates } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton, Textarea } from "@/components/ui/primitives";
import { PageHeader, SeverityBadge, StatusBadge, ValidationBadge } from "@/components/domain/shared";
import { AiAssistCard } from "@/components/domain/ai-assist";
import { formatTime } from "@/lib/utils";
import type { Evidence, Finding, Report } from "@/lib/api/types";

const FINDING_STATUSES = ["potential", "under_investigation", "verified", "false_positive", "duplicate", "report_ready", "reported", "resolved"];

const NEXT: Record<string, string[]> = {
  potential: ["under_investigation", "false_positive", "duplicate"],
  under_investigation: ["verified", "false_positive", "duplicate", "report_ready", "potential"],
  verified: ["report_ready", "reported", "resolved", "false_positive", "duplicate"],
  false_positive: ["potential", "under_investigation"],
  duplicate: ["potential", "under_investigation"],
  report_ready: ["reported", "resolved", "under_investigation"],
  reported: ["resolved"],
  resolved: ["reported", "under_investigation"],
};

export default function FindingDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const { data: finding, isLoading } = useFinding(params.id);
  const { data: duplicates } = useFindingDuplicates(params.id);
  const [confirmedVerify, setConfirmedVerify] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["findings"] });
    queryClient.invalidateQueries({ queryKey: ["overview"] });
  };

  const transition = useMutation({
    mutationFn: ({ to, confirm }: { to: string; confirm: boolean }) =>
      apiFetch<Finding>(`/api/v1/findings/${params.id}/transition`, {
        method: "POST",
        body: JSON.stringify({ to, verified_human_confirmation: confirm }),
        csrf,
      }),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: (patch: Record<string, string | null>) =>
      apiFetch<Finding>(`/api/v1/findings/${params.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
        csrf,
      }),
    onSuccess: invalidate,
  });

  const upload = useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return apiFetch<Evidence>(
        `/api/v1/evidence?program_id=${finding!.program_id}&finding_id=${params.id}`,
        { method: "POST", body: fd, csrf }
      );
    },
    onSuccess: (ev) => setEvidence((prev) => [ev, ...prev]),
  });

  const generate = useMutation({
    mutationFn: (format: "markdown" | "json" | "html" | "pdf") =>
      apiFetch<Report>("/api/v1/reports", {
        method: "POST",
        body: JSON.stringify({ finding_id: params.id, format }),
        csrf,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["reports"] }),
  });

  if (isLoading || !finding) return <Skeleton className="h-96 w-full" />;

  const next = NEXT[finding.status] ?? [];

  return (
    <>
      <PageHeader
        title={finding.title}
        description={`Recorded ${formatTime(finding.created_at)} · source: ${finding.discovery_source}`}
        actions={
          <>
            <SeverityBadge severity={finding.severity} />
            <ValidationBadge status={finding.validation_status} />
            <StatusBadge status={finding.status} />
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </>
        }
      />

      {transition.error && (
        <div className="mb-4 rounded-panel border border-danger/30 bg-danger/10 px-4 py-2.5 text-[13px] text-danger">
          {transition.error.message}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Description</h2></CardHeader>
            <CardContent><EditableArea value={finding.description} onSave={(v) => update.mutate({ description: v })} rows={3} placeholder="Describe the weakness…" /></CardContent>
          </Card>
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Reproduction steps</h2></CardHeader>
            <CardContent><EditableArea value={finding.reproduction_steps} onSave={(v) => update.mutate({ reproduction_steps: v })} rows={6} placeholder="Step-by-step reproduction…" /></CardContent>
          </Card>
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Security impact</h2></CardHeader>
            <CardContent><EditableArea value={finding.impact} onSave={(v) => update.mutate({ impact: v })} rows={3} placeholder="Concrete impact…" /></CardContent>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-text-primary">Evidence</h2>
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])}
              />
              <Button size="sm" variant="secondary" onClick={() => fileRef.current?.click()} disabled={upload.isPending}>
                <Upload className="h-3.5 w-3.5" /> {upload.isPending ? "Uploading…" : "Upload evidence"}
              </Button>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {upload.error && <p className="text-xs text-danger">{upload.error.message}</p>}
              {evidence.length === 0 && (
                <p className="text-[13px] text-text-muted">No evidence uploaded in this session. Upload sanitized requests, responses, and screenshots.</p>
              )}
              {evidence.map((ev) => (
                <div key={ev.id} className="flex items-center justify-between rounded border border-border bg-app px-3 py-2 text-[13px]">
                  <span className="truncate text-text-primary">{ev.filename}</span>
                  <a
                    href={`/api/v1/evidence/${ev.id}/download`}
                    className="flex items-center gap-1 text-info hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Download className="h-3.5 w-3.5" /> download
                  </a>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Status & verification</h2></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs text-text-secondary">Transition to</label>
                <Select
                  value=""
                  onValueChange={(to) => {
                    if (to === "verified" && !confirmedVerify) {
                      if (!window.confirm("Mark this finding VERIFIED? This is an explicit human confirmation that the vulnerability is real.")) return;
                    }
                    transition.mutate({ to, confirm: to === "verified" });
                  }}
                >
                  <SelectTrigger><SelectValue placeholder="Select next status" /></SelectTrigger>
                  <SelectContent>
                    {FINDING_STATUSES.map((s) => (
                      <SelectItem key={s} value={s} disabled={!next.includes(s)}>
                        {s.replace(/_/g, " ")}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-xs text-text-muted">
                Valid next: {next.map((s) => s.replace(/_/g, " ")).join(", ")}. Verification is human-only.
              </p>
              {finding.validation_status !== "verified_human" && (
                <label className="flex cursor-pointer items-center gap-2 text-[13px] text-text-primary">
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={confirmedVerify}
                    onChange={(e) => setConfirmedVerify(e.target.checked)}
                  />
                  I confirm I have manually verified this finding
                </label>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Classification</h2></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <label className="text-xs text-text-secondary">Severity</label>
                <Select value={finding.severity ?? ""} onValueChange={(v) => update.mutate({ severity: v || null })}>
                  <SelectTrigger><SelectValue placeholder="Unset" /></SelectTrigger>
                  <SelectContent>
                    {["info", "low", "medium", "high", "critical"].map((s) => (
                      <SelectItem key={s} value={s}>{s}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-text-secondary">CWE</label>
                <Input
                  defaultValue={finding.cwe ?? ""}
                  placeholder="CWE-639"
                  onBlur={(e) => {
                    const v = e.target.value.trim();
                    if (v !== (finding.cwe ?? "")) update.mutate({ cwe: v || null });
                  }}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-xs text-text-secondary">Category</label>
                <Input
                  defaultValue={finding.category ?? ""}
                  placeholder="object_access"
                  onBlur={(e) => {
                    const v = e.target.value.trim();
                    if (v !== (finding.category ?? "")) update.mutate({ category: v || null });
                  }}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><h2 className="text-sm font-semibold text-text-primary">Report</h2></CardHeader>
            <CardContent className="space-y-2">
              <div className="flex flex-wrap gap-2">
                {(["markdown", "json", "html", "pdf"] as const).map((f) => (
                  <Button key={f} size="sm" variant="secondary" onClick={() => generate.mutate(f)} disabled={generate.isPending}>
                    <FileText className="h-3.5 w-3.5" /> {f}
                  </Button>
                ))}
              </div>
              {generate.data && (
                <a
                  href={
                    generate.data.format === "pdf"
                      ? `/api/v1/reports/${generate.data.id}/download`
                      : `/reports/${generate.data.id}`
                  }
                  className="text-xs text-info hover:underline"
                >
                  {generate.data.format === "pdf"
                    ? "Download PDF report"
                    : `View generated ${generate.data.format} report`}
                </a>
              )}
              <p className="text-xs text-text-muted">
                Reports include the verification banner — unverified findings are labeled as such.
              </p>
            </CardContent>
          </Card>

          <AiAssistCard kind="finding" id={finding.id} />

          {duplicates && duplicates.length > 0 && (
            <Card>
              <CardHeader><h2 className="text-sm font-semibold text-text-primary">Duplicate candidates</h2></CardHeader>
              <CardContent className="space-y-2">
                {duplicates.slice(0, 5).map((d) => (
                  <button
                    key={d.finding_id}
                    className="block w-full rounded border border-border bg-app px-3 py-2 text-left hover:border-border-strong"
                    onClick={() => router.push(`/findings/${d.finding_id}`)}
                  >
                    <p className="text-[13px] font-medium text-text-primary">{d.title}</p>
                    <p className="mt-0.5 text-xs text-text-muted">
                      score {d.score.toFixed(2)} · {d.reasons.join(", ")}
                    </p>
                  </button>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}

function EditableArea({
  value,
  onSave,
  rows,
  placeholder,
}: {
  value: string | null;
  onSave: (v: string | null) => void;
  rows: number;
  placeholder?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? "");
  if (!editing) {
    return (
      <button
        className="block w-full rounded border border-transparent px-2 py-1.5 text-left text-[13px] text-text-primary hover:border-border hover:bg-raised/50"
        onClick={() => {
          setDraft(value ?? "");
          setEditing(true);
        }}
      >
        {value ? <span className="whitespace-pre-wrap">{value}</span> : <span className="text-text-muted">{placeholder}</span>}
      </button>
    );
  }
  return (
    <div className="space-y-1.5">
      <Textarea autoFocus rows={rows} value={draft} onChange={(e) => setDraft(e.target.value)} />
      <div className="flex gap-2">
        <Button size="sm" onClick={() => { onSave(draft.trim() ? draft : null); setEditing(false); }}>Save</Button>
        <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
      </div>
    </div>
  );
}
