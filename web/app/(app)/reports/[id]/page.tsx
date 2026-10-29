"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Download } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { Button, Card, CardContent, CardHeader, Skeleton } from "@/components/ui/primitives";
import { PageHeader } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";
import type { Report } from "@/lib/api/types";

export default function ReportDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: report, isLoading } = useQuery({
    queryKey: ["reports", params.id],
    queryFn: () => apiFetch<Report>(`/api/v1/reports/${params.id}`),
  });

  if (isLoading || !report) return <Skeleton className="h-96 w-full" />;

  return (
    <>
      <PageHeader
        title={`Report — ${report.format}`}
        description={`Generated ${formatTime(report.generated_at)}`}
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => window.print()}>
              <Download className="h-4 w-4" /> Print / save
            </Button>
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </>
        }
      />
      <Card>
        <CardContent className="p-5">
          {report.format === "html" ? (
            <div
              className="prose prose-invert max-w-none"
              dangerouslySetInnerHTML={{ __html: report.content ?? "" }}
            />
          ) : (
            <pre className="mono whitespace-pre-wrap break-words text-[13px] leading-relaxed text-text-primary">
              {report.content}
            </pre>
          )}
        </CardContent>
      </Card>
    </>
  );
}
