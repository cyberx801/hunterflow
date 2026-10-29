"use client";

import { useRouter } from "next/navigation";
import { Download } from "lucide-react";
import { useReports } from "@/lib/api/hooks";
import { Badge, Button, Card, Skeleton } from "@/components/ui/primitives";
import { EmptyState, PageHeader } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";

export default function ReportsPage() {
  const router = useRouter();
  const { data: reports, isLoading } = useReports();

  return (
    <>
      <PageHeader
        title="Reports"
        description="Generated vulnerability reports in Markdown, JSON, and HTML. Verification status is always labeled."
      />
      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !reports || reports.length === 0 ? (
        <EmptyState
          title="No reports"
          description="Generate a report from a finding's workspace. Nothing is ever submitted automatically."
          action={<Button onClick={() => router.push("/findings")}>Open findings</Button>}
        />
      ) : (
        <div className="space-y-2">
          {reports.map((r) => (
            <Card key={r.id} className="p-0">
              <div className="flex items-center justify-between gap-4 px-4 py-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge tone="accent">{r.format}</Badge>
                    <span className="mono text-[13px] text-text-primary">{r.finding_id.slice(0, 8)}</span>
                  </div>
                  <p className="mt-0.5 text-xs text-text-muted">generated {formatTime(r.generated_at)}</p>
                </div>
                <div className="flex shrink-0 gap-2">
                  {r.format !== "pdf" && (
                    <Button size="sm" variant="secondary" onClick={() => router.push(`/reports/${r.id}`)}>
                      Preview
                    </Button>
                  )}
                  <a
                    href={`/api/v1/reports/${r.id}/download`}
                    className="inline-flex h-8 items-center rounded-md border border-border px-3 text-[13px] text-text-primary hover:bg-raised"
                  >
                    Download
                  </a>
                  <Button size="sm" variant="secondary" onClick={() => router.push(`/findings/${r.finding_id}`)}>
                    Open finding
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
