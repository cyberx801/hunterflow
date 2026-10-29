"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, useProgramId, useTransactions } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { useUrlFilters } from "@/lib/hooks/use-url-filters";
import { Badge, Button, Card, CardContent, CardHeader, Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";
import { EmptyState, MethodBadge, PageHeader } from "@/components/domain/shared";
import { timeAgo } from "@/lib/utils";

export default function TrafficPage() {
  const router = useRouter();
  const csrf = useCsrfToken();
  const programId = useProgramId();
  const queryClient = useQueryClient();
  const { filters, setFilter } = useUrlFilters(["host", "method", "status", "q"]);
  const { data, isLoading } = useTransactions({
    program_id: programId,
    host: filters.host,
    method: filters.method,
    status: filters.status,
    q: filters.q,
  });

  const fileRef = useRef<HTMLInputElement>(null);
  const [accountTag, setAccountTag] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<string | null>(null);

  async function onImport(file: File) {
    if (!programId) {
      setImportError("Select a program in the top bar first.");
      return;
    }
    setImporting(true);
    setImportError(null);
    setImportResult(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const result = await apiFetch<{ import_job_id: string; status: string }>(
        `/api/v1/traffic/import?program_id=${programId}${accountTag ? `&account_tag=${encodeURIComponent(accountTag)}` : ""}`,
        { method: "POST", body: fd, csrf }
      );
      setImportResult(`Import job started (${result.status})`);
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["traffic"] });
    } catch (e) {
      setImportError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <>
      <PageHeader
        title="HTTP Traffic"
        description="Imported transactions (HAR / proxy exports) and selected test requests."
        actions={
          <div className="flex items-center gap-2">
            <Input
              placeholder="Account tag (e.g. acct-a)"
              className="w-48"
              value={accountTag}
              onChange={(e) => setAccountTag(e.target.value)}
            />
            <input
              ref={fileRef}
              type="file"
              accept=".har,.json"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && onImport(e.target.files[0])}
              aria-label="Import HAR file"
            />
            <Button onClick={() => fileRef.current?.click()} disabled={importing}>
              <Upload className="h-4 w-4" /> {importing ? "Importing…" : "Import HAR"}
            </Button>
          </div>
        }
      />

      {(importError || importResult) && (
        <div className="mb-3 rounded-panel border border-border bg-surface px-4 py-2.5 text-[13px]">
          {importError && <p className="text-danger">{importError}</p>}
          {importResult && <p className="text-success">{importResult}</p>}
        </div>
      )}

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search URLs…"
          className="max-w-xs"
          defaultValue={filters.q}
          onKeyDown={(e) => {
            if (e.key === "Enter") setFilter("q", (e.target as HTMLInputElement).value || null);
          }}
        />
        <Select value={filters.method ?? "all"} onValueChange={(v) => setFilter("method", v === "all" ? null : v)}>
          <SelectTrigger className="w-32"><SelectValue placeholder="Method" /></SelectTrigger>
          <SelectContent>
            {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
            <SelectItem value="all">All methods</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.status ?? "all"} onValueChange={(v) => setFilter("status", v === "all" ? null : v)}>
          <SelectTrigger className="w-32"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            {["200", "201", "301", "302", "401", "403", "404", "500"].map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
            <SelectItem value="all">All statuses</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          title="No traffic imported"
          description="Export a HAR file from Burp Suite or Caido and import it here. Headers are redacted on import; nothing sensitive is stored."
        />
      ) : (
        <div className="overflow-x-auto rounded-panel border border-border bg-surface">
          <table className="w-full min-w-[860px] border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="px-3 py-2.5 font-medium">Method</th>
                <th className="px-3 py-2.5 font-medium">URL</th>
                <th className="px-3 py-2.5 font-medium">Status</th>
                <th className="px-3 py-2.5 font-medium">Account</th>
                <th className="px-3 py-2.5 font-medium">Source</th>
                <th className="px-3 py-2.5 font-medium">Time</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((tx) => (
                <tr
                  key={tx.id}
                  className="cursor-pointer border-b border-border/50 hover:bg-raised/50"
                  onClick={() => router.push(`/traffic/transactions/${tx.id}`)}
                >
                  <td className="px-3 py-2.5"><MethodBadge method={tx.method} /></td>
                  <td className="mono max-w-[420px] px-3 py-2.5">
                    <span className="line-clamp-1 text-text-primary">{tx.url}</span>
                  </td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{tx.response_status ?? "—"}</td>
                  <td className="px-3 py-2.5">{tx.account_tag ? <Badge tone="accent">{tx.account_tag}</Badge> : <span className="text-text-muted">—</span>}</td>
                  <td className="px-3 py-2.5 text-xs text-text-secondary">
                    {tx.source}
                    {tx.redacted && <Badge tone="success" className="ml-1.5">redacted</Badge>}
                  </td>
                  <td className="px-3 py-2.5 text-xs text-text-muted">{timeAgo(tx.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
