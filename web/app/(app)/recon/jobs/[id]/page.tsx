"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useJob } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Skeleton } from "@/components/ui/primitives";
import { PageHeader, StatusBadge } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";

export default function JobDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: job, isLoading } = useJob(params.id);

  if (isLoading || !job) {
    return <Skeleton className="h-64 w-full" />;
  }

  return (
    <>
      <PageHeader
        title={`Scan job`}
        description={`${job.profile.replace(/_/g, " ")} · created ${formatTime(job.created_at)}`}
        actions={
          <>
            <StatusBadge status={job.status} />
            <Button variant="ghost" size="sm" onClick={() => router.push("/recon")}>
              <ArrowLeft className="h-4 w-4" /> Back to recon
            </Button>
          </>
        }
      />

      {job.error_code && (
        <div className="mb-4 rounded-panel border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
          Failure classified as <span className="mono">{job.error_code}</span>
        </div>
      )}

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Execution history</h2>
          </CardHeader>
          <CardContent>
            {job.tool_runs.length === 0 ? (
              <p className="text-[13px] text-text-muted">
                {job.dry_run ? "Dry run — no tools were executed." : "No tool runs recorded."}
              </p>
            ) : (
              <div className="space-y-2">
                {job.tool_runs.map((run) => (
                  <ToolRunRow key={run.id} jobId={job.id} runId={run.id} tool={run.tool} status={run.status} exitCode={run.exit_code} args={run.args} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function ToolRunRow({
  jobId,
  runId,
  tool,
  status,
  exitCode,
  args,
}: {
  jobId: string;
  runId: string;
  tool: string;
  status: string;
  exitCode: number | null;
  args: string[];
}) {
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["tool-output", jobId, runId],
    queryFn: () => apiFetch<{ content: string; truncated: boolean }>(`/api/v1/jobs/${jobId}/runs/${runId}/output`),
    enabled: open,
  });

  return (
    <div className="rounded border border-border bg-app">
      <button
        className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <div className="flex items-center gap-2">
          <span className="mono text-[13px] font-medium text-text-primary">{tool}</span>
          <StatusBadge status={status} />
          {exitCode !== null && <span className="text-xs text-text-muted">exit {exitCode}</span>}
        </div>
        {open ? <ChevronDown className="h-4 w-4 text-text-muted" /> : <ChevronRight className="h-4 w-4 text-text-muted" />}
      </button>
      {open && (
        <div className="border-t border-border px-3 py-2">
          <p className="mb-1.5 text-xs text-text-secondary">Arguments (secrets redacted):</p>
          <pre className="mono max-h-32 overflow-auto rounded bg-raised p-2 text-xs text-text-primary">
            {args.join(" ")}
          </pre>
          <p className="mb-1.5 mt-3 text-xs text-text-secondary">Output (tail):</p>
          <pre className="mono max-h-64 overflow-auto rounded bg-raised p-2 text-xs text-text-primary">
            {data ? data.content || "(empty)" : "Loading…"}
          </pre>
        </div>
      )}
    </div>
  );
}
