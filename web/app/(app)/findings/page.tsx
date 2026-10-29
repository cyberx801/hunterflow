"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, useFindings, useProgramId } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { useUrlFilters } from "@/lib/hooks/use-url-filters";
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea, Skeleton } from "@/components/ui/primitives";
import { EmptyState, PageHeader, SeverityBadge, StatusBadge, ValidationBadge } from "@/components/domain/shared";
import { timeAgo } from "@/lib/utils";
import type { Finding } from "@/lib/api/types";

const schema = z.object({
  title: z.string().min(1).max(300),
  description: z.string().optional(),
  category: z.string().optional(),
  cwe: z.string().optional(),
  severity: z.string().optional(),
  impact: z.string().optional(),
});

export default function FindingsPage() {
  const router = useRouter();
  const csrf = useCsrfToken();
  const programId = useProgramId();
  const queryClient = useQueryClient();
  const { filters, setFilter } = useUrlFilters(["status", "severity", "q"]);
  const { data, isLoading } = useFindings({
    program_id: programId,
    status: filters.status,
    severity: filters.severity,
    q: filters.q,
  });
  const [open, setOpen] = useState(false);

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { title: "", description: "", category: "", cwe: "", severity: "", impact: "" },
  });

  const create = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      apiFetch<Finding>("/api/v1/findings", {
        method: "POST",
        body: JSON.stringify({ program_id: programId, ...values }),
        csrf,
      }),
    onSuccess: () => {
      setOpen(false);
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["findings"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
  });

  return (
    <>
      <PageHeader
        title="Findings"
        description="Structured vulnerability investigation: observation → hypothesis → verified finding."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button disabled={!programId}>
                <Plus className="h-4 w-4" /> New finding
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Record a finding</DialogTitle>
              </DialogHeader>
              <form className="space-y-3" onSubmit={form.handleSubmit((v) => create.mutate(v))}>
                <div className="space-y-1.5">
                  <Label>Title</Label>
                  <Input {...form.register("title")} placeholder="e.g. BOLA on orders endpoint" />
                </div>
                <div className="space-y-1.5">
                  <Label>Description</Label>
                  <Textarea rows={3} {...form.register("description")} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <Label>Category</Label>
                    <Input {...form.register("category")} placeholder="object_access" />
                  </div>
                  <div className="space-y-1.5">
                    <Label>CWE</Label>
                    <Input {...form.register("cwe")} placeholder="CWE-639" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Severity</Label>
                  <Select value={form.watch("severity")} onValueChange={(v) => form.setValue("severity", v)}>
                    <SelectTrigger><SelectValue placeholder="Select severity" /></SelectTrigger>
                    <SelectContent>
                      {["info", "low", "medium", "high", "critical"].map((s) => (
                        <SelectItem key={s} value={s}>{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Impact</Label>
                  <Textarea rows={2} {...form.register("impact")} />
                </div>
                <p className="text-xs text-text-muted">
                  New findings start as <span className="text-text-secondary">potential / unverified</span>.
                  Only an explicit human confirmation can verify a finding.
                </p>
                {create.error && <p className="text-xs text-danger">{create.error.message}</p>}
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
                  <Button type="submit" disabled={create.isPending || !programId}>Create finding</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search findings…"
          className="max-w-xs"
          defaultValue={filters.q}
          onKeyDown={(e) => {
            if (e.key === "Enter") setFilter("q", (e.target as HTMLInputElement).value || null);
          }}
        />
        <Select value={filters.status ?? "all"} onValueChange={(v) => setFilter("status", v === "all" ? null : v)}>
          <SelectTrigger className="w-48"><SelectValue placeholder="All statuses" /></SelectTrigger>
          <SelectContent>
            {["potential", "under_investigation", "verified", "false_positive", "duplicate", "report_ready", "reported", "resolved"].map((s) => (
              <SelectItem key={s} value={s}>{s.replace(/_/g, " ")}</SelectItem>
            ))}
            <SelectItem value="all">All statuses</SelectItem>
          </SelectContent>
        </Select>
        <Select value={filters.severity ?? "all"} onValueChange={(v) => setFilter("severity", v === "all" ? null : v)}>
          <SelectTrigger className="w-40"><SelectValue placeholder="All severities" /></SelectTrigger>
          <SelectContent>
            {["info", "low", "medium", "high", "critical"].map((s) => (
              <SelectItem key={s} value={s}>{s}</SelectItem>
            ))}
            <SelectItem value="all">All severities</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          title="No findings"
          description="Scanner observations and your verified research produce findings here. Nothing is labeled verified without human confirmation."
        />
      ) : (
        <div className="overflow-x-auto rounded-panel border border-border bg-surface">
          <table className="w-full min-w-[860px] border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="px-3 py-2.5 font-medium">Title</th>
                <th className="px-3 py-2.5 font-medium">Severity</th>
                <th className="px-3 py-2.5 font-medium">Validation</th>
                <th className="px-3 py-2.5 font-medium">Status</th>
                <th className="px-3 py-2.5 font-medium">CWE</th>
                <th className="px-3 py-2.5 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {(data?.items ?? []).map((f) => (
                <tr
                  key={f.id}
                  className="cursor-pointer border-b border-border/50 hover:bg-raised/50"
                  onClick={() => router.push(`/findings/${f.id}`)}
                >
                  <td className="max-w-[380px] px-3 py-2.5">
                    <span className="line-clamp-1 font-medium text-text-primary">{f.title}</span>
                  </td>
                  <td className="px-3 py-2.5"><SeverityBadge severity={f.severity} /></td>
                  <td className="px-3 py-2.5"><ValidationBadge status={f.validation_status} /></td>
                  <td className="px-3 py-2.5"><StatusBadge status={f.status} /></td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{f.cwe ?? "—"}</td>
                  <td className="px-3 py-2.5 text-xs text-text-muted">{timeAgo(f.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
