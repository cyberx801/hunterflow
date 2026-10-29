"use client";

import { useRouter } from "next/navigation";
import { useEndpoints, useProgramId } from "@/lib/api/hooks";
import { useUrlFilters } from "@/lib/hooks/use-url-filters";
import { Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";
import { EmptyState, MethodBadge, PageHeader } from "@/components/domain/shared";
import { timeAgo } from "@/lib/utils";

const CATEGORIES = ["auth", "account", "profile", "admin", "file", "payment", "object_access", "resource_mgmt", "api_versioning", "other"];

export default function EndpointsPage() {
  const router = useRouter();
  const programId = useProgramId();
  const { filters, setFilter } = useUrlFilters(["method", "category", "q"]);
  const { data, isLoading } = useEndpoints({
    program_id: programId,
    method: filters.method,
    category: filters.category,
    q: filters.q,
  });

  return (
    <>
      <PageHeader
        title="Endpoint Explorer"
        description="Discovered endpoints with methods, parameters, classifications, and research actions."
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search paths…"
          className="max-w-xs"
          defaultValue={filters.q}
          onKeyDown={(e) => {
            if (e.key === "Enter") setFilter("q", (e.target as HTMLInputElement).value || null);
          }}
        />
        <Select value={filters.method ?? "all"} onValueChange={(v) => setFilter("method", v === "all" ? null : v)}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All methods" />
          </SelectTrigger>
          <SelectContent>
            {["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"].map((m) => (
              <SelectItem key={m} value={m}>{m}</SelectItem>
            ))}
            <SelectItem value="all">All methods</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.category ?? "all"} onValueChange={(v) => setFilter("category", v === "all" ? null : v)}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All categories" />
          </SelectTrigger>
          <SelectContent>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>{c.replace(/_/g, " ")}</SelectItem>
            ))}
            <SelectItem value="all">All categories</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          title="No endpoints"
          description="Crawl an authorized target (web_inventory profile) or import HAR traffic to populate endpoint intelligence."
        />
      ) : (
        <div className="overflow-x-auto rounded-panel border border-border bg-surface">
          <table className="w-full min-w-[860px] border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="px-3 py-2.5 font-medium">Method</th>
                <th className="px-3 py-2.5 font-medium">Path</th>
                <th className="px-3 py-2.5 font-medium">Category</th>
                <th className="px-3 py-2.5 font-medium">Auth</th>
                <th className="px-3 py-2.5 font-medium">Cards</th>
                <th className="px-3 py-2.5 font-medium">Priority</th>
                <th className="px-3 py-2.5 font-medium">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((ep) => (
                <tr
                  key={ep.id}
                  className="cursor-pointer border-b border-border/50 hover:bg-raised/50"
                  onClick={() => router.push(`/endpoints/${ep.id}`)}
                >
                  <td className="px-3 py-2.5"><MethodBadge method={ep.method} /></td>
                  <td className="mono max-w-[420px] px-3 py-2.5">
                    <span className="line-clamp-1 text-text-primary">{ep.path}</span>
                    {ep.asset_value && (
                      <span className="block truncate text-xs text-text-muted">{ep.asset_value}</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-text-secondary">{ep.category.replace(/_/g, " ")}</td>
                  <td className="px-3 py-2.5 text-xs text-text-secondary">
                    {(ep.auth_indicators as { auth_challenge?: boolean } | null)?.auth_challenge
                      ? "challenge observed"
                      : "—"}
                  </td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{ep.card_count}</td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{ep.priority_score}</td>
                  <td className="px-3 py-2.5 text-xs text-text-muted">{timeAgo(ep.last_seen)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
