"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, useProgramId, useResearchCards, useTemplates } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea, Skeleton } from "@/components/ui/primitives";
import { EmptyState, PageHeader, StatusBadge } from "@/components/domain/shared";
import { timeAgo } from "@/lib/utils";
import type { ResearchCard } from "@/lib/api/types";

const STATUSES = ["not_started", "in_progress", "needs_verification", "confirmed", "rejected", "blocked", "archived"];

const schema = z.object({
  title: z.string().min(1).max(300),
  hypothesis: z.string().optional(),
  test_category: z.string().optional(),
  methodology: z.string().optional(),
  required_accounts: z.string().optional(),
});

export default function ResearchPage() {
  const router = useRouter();
  const csrf = useCsrfToken();
  const programId = useProgramId();
  const queryClient = useQueryClient();
  const { data, isLoading } = useResearchCards(programId ? { program_id: programId } : {});
  const { data: templates } = useTemplates();
  const [open, setOpen] = useState(false);
  const [templateId, setTemplateId] = useState<string>("");

  const form = useForm({
    resolver: zodResolver(schema),
    defaultValues: { title: "", hypothesis: "", test_category: "", methodology: "", required_accounts: "" },
  });

  const create = useMutation({
    mutationFn: (values: z.infer<typeof schema>) =>
      apiFetch<ResearchCard>("/api/v1/research", {
        method: "POST",
        body: JSON.stringify(
          programId
            ? { program_id: programId, template_id: templateId || undefined, ...values }
            : { program_id: "", template_id: templateId || undefined, ...values }
        ),
        csrf,
      }),
    onSuccess: () => {
      setOpen(false);
      form.reset();
      queryClient.invalidateQueries({ queryKey: ["research"] });
    },
  });

  const cards = data?.items ?? [];

  return (
    <>
      <PageHeader
        title="Research Workspace"
        description="Hypotheses, test cases, observations, and evidence — the heart of your investigation."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4" /> New research card
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New research card</DialogTitle>
              </DialogHeader>
              <form className="space-y-3" onSubmit={form.handleSubmit((v) => create.mutate(v))}>
                <div className="space-y-1.5">
                  <Label>Template (optional)</Label>
                  <Select value={templateId} onValueChange={setTemplateId}>
                    <SelectTrigger>
                      <SelectValue placeholder="No template" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">No template</SelectItem>
                      {(templates ?? []).map((t) => (
                        <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Title</Label>
                  <Input {...form.register("title")} placeholder="e.g. BOLA check: orders endpoint" />
                </div>
                <div className="space-y-1.5">
                  <Label>Hypothesis</Label>
                  <Textarea rows={2} {...form.register("hypothesis")} placeholder="What do you expect to find or disprove?" />
                </div>
                <div className="space-y-1.5">
                  <Label>Test category</Label>
                  <Input {...form.register("test_category")} placeholder="object_access, auth, …" />
                </div>
                <div className="space-y-1.5">
                  <Label>Methodology</Label>
                  <Textarea rows={3} {...form.register("methodology")} />
                </div>
                <div className="space-y-1.5">
                  <Label>Required test accounts</Label>
                  <Input {...form.register("required_accounts")} placeholder="account A, account B" />
                </div>
                {create.error && <p className="text-xs text-danger">{create.error.message}</p>}
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
                  <Button type="submit" disabled={create.isPending || !programId}>
                    Create card
                  </Button>
                </div>
                {!programId && (
                  <p className="text-xs text-warning">Select a program in the top bar before creating a card.</p>
                )}
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : cards.length === 0 ? (
        <EmptyState
          title="No research cards"
          description="Turn a discovered endpoint into a testable hypothesis. Templates cover BOLA/IDOR, authn bypass, and parameter tampering."
        />
      ) : (
        <div className="overflow-x-auto rounded-panel border border-border bg-surface">
          <table className="w-full min-w-[900px] border-collapse text-[13px]">
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="px-3 py-2.5 font-medium">Title</th>
                <th className="px-3 py-2.5 font-medium">Hypothesis</th>
                <th className="px-3 py-2.5 font-medium">Category</th>
                <th className="px-3 py-2.5 font-medium">Status</th>
                <th className="px-3 py-2.5 font-medium">Priority</th>
                <th className="px-3 py-2.5 font-medium">Updated</th>
              </tr>
            </thead>
            <tbody>
              {cards.map((card) => (
                <tr
                  key={card.id}
                  className="cursor-pointer border-b border-border/50 hover:bg-raised/50"
                  onClick={() => router.push(`/research/${card.id}`)}
                >
                  <td className="max-w-[280px] px-3 py-2.5">
                    <span className="line-clamp-1 font-medium text-text-primary">{card.title}</span>
                  </td>
                  <td className="max-w-[320px] px-3 py-2.5">
                    <span className="line-clamp-1 text-text-secondary">{card.hypothesis ?? "—"}</span>
                  </td>
                  <td className="px-3 py-2.5 text-text-secondary">{card.test_category ?? "—"}</td>
                  <td className="px-3 py-2.5"><StatusBadge status={card.status} /></td>
                  <td className="mono px-3 py-2.5 text-text-secondary">{card.priority_score}</td>
                  <td className="px-3 py-2.5 text-xs text-text-muted">{timeAgo(card.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
