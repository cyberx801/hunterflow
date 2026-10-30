"use client";

import { useState, use } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { useTransaction } from "@/lib/api/hooks";
import { Badge, Button, Card, CardContent, CardHeader, Skeleton } from "@/components/ui/primitives";
import { MethodBadge, MonoValue, PageHeader } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";

export default function TransactionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { data: tx, isLoading } = useTransaction(id);

  if (isLoading || !tx) return <Skeleton className="h-64 w-full" />;

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <MethodBadge method={tx.method} />
            <MonoValue value={tx.url} />
          </span>
        }
        description={`Imported ${formatTime(tx.created_at)} · redacted on import`}
        actions={
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4" /> Back
          </Button>
        }
      />

      {tx.account_tag && <Badge tone="accent" className="mb-3">{tx.account_tag}</Badge>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">Request</h2>
          </CardHeader>
          <CardContent>
            <HeaderTable headers={tx.request_headers} />
            {tx.request_body && (
              <BodyBlock label="Request body" body={tx.request_body} />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">
              Response{" "}
              {tx.response_status !== null && (
                <span className="mono ml-1 text-text-secondary">{tx.response_status}</span>
              )}
            </h2>
          </CardHeader>
          <CardContent>
            <HeaderTable headers={tx.response_headers} />
            {tx.response_body && (
              <BodyBlock label="Response body" body={tx.response_body} />
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function HeaderTable({ headers }: { headers: Record<string, string> | null }) {
  const entries = Object.entries(headers ?? {});
  if (entries.length === 0) return <p className="text-xs text-text-muted">No headers.</p>;
  return (
    <div className="space-y-0.5">
      {entries.map(([k, v]) => (
        <div key={k} className="flex gap-3 text-[13px]">
          <span className="mono w-44 shrink-0 truncate text-text-secondary" title={k}>{k}</span>
          <span className="mono break-all text-text-primary">{v}</span>
        </div>
      ))}
    </div>
  );
}

function BodyBlock({ label, body }: { label: string; body: string }) {
  const [expanded, setExpanded] = useState(false);
  const long = body.length > 2000;
  return (
    <div className="mt-3">
      <p className="mb-1 text-xs text-text-secondary">
        {label} ({body.length} chars)
        {long && (
          <button className="ml-2 text-info hover:underline" onClick={() => setExpanded(!expanded)}>
            {expanded ? "collapse" : "expand"}
          </button>
        )}
      </p>
      <pre className="mono max-h-80 overflow-auto rounded border border-border bg-app p-2 text-xs text-text-primary whitespace-pre-wrap break-all">
        {long && !expanded ? body.slice(0, 2000) + "…" : body}
      </pre>
    </div>
  );
}
