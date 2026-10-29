"use client";

import { useRouter } from "next/navigation";
import { useAssets, useProgramId } from "@/lib/api/hooks";
import { useUrlFilters } from "@/lib/hooks/use-url-filters";
import { Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";
import { EmptyState, MonoValue, PageHeader, ScopeBadge } from "@/components/domain/shared";
import { formatTime, timeAgo } from "@/lib/utils";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { useCsrfToken } from "@/lib/api/hooks";
import { Tag } from "lucide-react";

export default function AssetsPage() {
  const router = useRouter();
  const programId = useProgramId();
  const { filters, setFilter } = useUrlFilters(["type", "scope_status", "q"]);
  const { data, isLoading } = useAssets({ program_id: programId, type: filters.type, scope_status: filters.scope_status, q: filters.q });

  const rows = data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Assets"
        description="Normalized inventory with discovery provenance and scope status."
      />
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search assets…"
          className="max-w-xs"
          defaultValue={filters.q}
          onChange={(e) => {
            if (!e.target.value) setFilter("q", null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") setFilter("q", (e.target as HTMLInputElement).value || null);
          }}
        />
        <Select value={filters.type ?? "all"} onValueChange={(v) => setFilter("type", v === "all" ? null : v)}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            <SelectItem value="domain">domain</SelectItem>
            <SelectItem value="subdomain">subdomain</SelectItem>
            <SelectItem value="ip">ip</SelectItem>
            <SelectItem value="url">url</SelectItem>
            <SelectItem value="web_service">web_service</SelectItem>
            <SelectItem value="api_endpoint">api_endpoint</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.scope_status ?? "all"} onValueChange={(v) => setFilter("scope_status", v === "all" ? null : v)}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="All scope states" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All scope states</SelectItem>
            <SelectItem value="in_scope">In scope</SelectItem>
            <SelectItem value="out_of_scope">Out of scope</SelectItem>
            <SelectItem value="needs_confirmation">Needs confirmation</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          title="No assets"
          description="Run a recon scan against an authorized program to populate this inventory."
        />
      ) : (
        <div className="overflow-x-auto rounded-panel border border-border bg-surface">
          <table className="w-full min-w-[900px] border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="px-3 py-2.5 font-medium">Value</th>
                <th className="px-3 py-2.5 font-medium">Type</th>
                <th className="px-3 py-2.5 font-medium">Scope</th>
                <th className="px-3 py-2.5 font-medium">HTTP</th>
                <th className="px-3 py-2.5 font-medium">Tech</th>
                <th className="px-3 py-2.5 font-medium">Endpoints</th>
                <th className="px-3 py-2.5 font-medium">Last seen</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((asset) => (
                <tr
                  key={asset.id}
                  className="cursor-pointer border-b border-border/50 hover:bg-raised/50"
                  onClick={() => router.push(`/assets/${asset.id}`)}
                >
                  <td className="max-w-[380px] px-3 py-2.5">
                    <MonoValue value={asset.value_normalized} />
                    {asset.tags && asset.tags.length > 0 && (
                      <span className="mt-0.5 block text-xs text-text-muted">{asset.tags.join(", ")}</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-text-secondary">{asset.type}</td>
                  <td className="px-3 py-2.5">
                    <ScopeBadge status={asset.scope_status} />
                  </td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{asset.http_status ?? "—"}</td>
                  <td className="max-w-[220px] px-3 py-2.5">
                    <span className="line-clamp-1 text-xs text-text-secondary">
                      {(asset.tech ?? []).join(", ") || "—"}
                    </span>
                  </td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{asset.endpoint_count}</td>
                  <td className="px-3 py-2.5 text-xs text-text-muted" title={formatTime(asset.last_seen)}>
                    {timeAgo(asset.last_seen)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
