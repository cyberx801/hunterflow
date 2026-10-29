"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { useComparison } from "@/lib/api/hooks";
import { Badge, Button, Card, CardContent, Skeleton } from "@/components/ui/primitives";
import { PageHeader } from "@/components/domain/shared";
import { cn } from "@/lib/utils";

export default function ComparePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: cmp, isLoading } = useComparison(params.id);

  if (isLoading || !cmp) return <Skeleton className="h-96 w-full" />;

  return (
    <>
      <PageHeader
        title={cmp.name}
        description="Side-by-side comparison of authorized test responses. Normalized dynamic values (timestamps, UUIDs, tokens) are masked."
        actions={
          <Button variant="ghost" size="sm" onClick={() => router.push("/traffic")}>
            <ArrowLeft className="h-4 w-4" /> Back to traffic
          </Button>
        }
      />

      {cmp.review_required && (
        <div className="mb-4 flex items-start gap-2.5 rounded-panel border border-warning/40 bg-warning/10 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
          <div>
            <p className="text-sm font-medium text-warning">Review required</p>
            <p className="text-[13px] text-warning/80">{cmp.review_reason}</p>
          </div>
        </div>
      )}

      {cmp.status_diff && !cmp.review_required && (
        <div className="mb-4 flex items-start gap-2.5 rounded-panel border border-info/40 bg-info/10 px-4 py-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-info" />
          <p className="text-[13px] text-info">
            Status codes differ with other observable differences. Investigate — a status difference alone
            never proves a vulnerability.
          </p>
        </div>
      )}

      <Card className="p-0">
        <CardContent className="p-0">
          <div
            className="grid overflow-x-auto"
            style={{ gridTemplateColumns: `repeat(${cmp.panes.length}, minmax(320px, 1fr))` }}
          >
            {cmp.panes.map((pane, i) => (
              <div key={i} className={cn("min-w-[320px] border-border", i > 0 && "border-l")}>
                <div className="border-b border-border px-3 py-2">
                  <p className="text-sm font-medium text-text-primary">{pane.label}</p>
                  <p className="mono mt-0.5 truncate text-xs text-text-secondary">
                    {pane.method} {pane.url}
                  </p>
                  <p className="mono mt-0.5 text-xs">
                    status: <span className="text-info">{pane.status ?? "—"}</span>
                  </p>
                </div>
                <div className="max-h-[520px] overflow-y-auto">
                  <DiffPane lines={(pane.response_body ?? "").split("\n")} />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {Object.keys(cmp.header_diff).length > 0 && (
        <Card className="mt-4">
          <CardContent>
            <h2 className="mb-2 text-sm font-semibold text-text-primary">Header differences (normalized)</h2>
            <div className="space-y-1">
              {Object.entries(cmp.header_diff).map(([name, [left, right]]) => (
                <div key={name} className="flex items-center gap-2 text-[13px]">
                  <span className="mono w-44 shrink-0 text-text-secondary">{name}</span>
                  <span className="mono flex-1 truncate text-danger">{left ?? "—"}</span>
                  <span className="text-text-muted">→</span>
                  <span className="mono flex-1 truncate text-success">{right ?? "—"}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}

function DiffPane({ lines }: { lines: string[] }) {
  return (
    <div className="py-1">
      {lines.map((line, i) => (
        <div
          key={i}
          className={cn(
            "flex gap-2 px-2 py-0 text-xs leading-5",
            line.startsWith("[") ? "opacity-100" : "opacity-90"
          )}
        >
          <span className="mono w-8 shrink-0 select-none text-right text-text-muted">{i + 1}</span>
          <span className="mono whitespace-pre-wrap break-all text-text-primary">{line}</span>
        </div>
      ))}
    </div>
  );
}
