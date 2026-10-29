"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, usePrograms } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Button, Card, Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from "@/components/ui/primitives";
import { EmptyState, PageHeader, StatusBadge } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";
import type { Program } from "@/lib/api/types";

const schema = z.object({
  name: z.string().min(1).max(200),
  platform: z.enum(["hackerone", "bugcrowd", "intigriti", "other"]),
  url: z.string().max(2048).optional().or(z.literal("")),
  description: z.string().optional(),
  policy_source_url: z.string().max(2048).optional().or(z.literal("")),
});

type FormValues = z.infer<typeof schema>;

export default function ProgramsPage() {
  const router = useRouter();
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const { data, isLoading } = usePrograms();

  const create = useMutation({
    mutationFn: (values: FormValues) =>
      apiFetch<Program>("/api/v1/programs", {
        method: "POST",
        body: JSON.stringify({
          ...values,
          url: values.url || null,
          policy_source_url: values.policy_source_url || null,
        }),
        csrf,
      }),
    onSuccess: (program) => {
      queryClient.invalidateQueries({ queryKey: ["programs"] });
      setOpen(false);
      form.reset();
      router.push(`/programs/${program.id}`);
    },
  });

  const [open, setOpen] = useState(false);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", platform: "other", url: "", description: "", policy_source_url: "" },
  });

  const programs = (data?.items ?? []).filter((p) => !p.archived_at);

  return (
    <>
      <PageHeader
        title="Programs"
        description="Bug bounty programs and their authorized scopes."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="h-4 w-4" /> New program
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New program</DialogTitle>
              </DialogHeader>
              <form
                className="space-y-3"
                onSubmit={form.handleSubmit((v) => create.mutate(v))}
              >
                <div className="space-y-1.5">
                  <Label htmlFor="p-name">Name</Label>
                  <Input id="p-name" {...form.register("name")} placeholder="ACME Corp" />
                  {form.formState.errors.name && (
                    <p className="text-xs text-danger">{form.formState.errors.name.message}</p>
                  )}
                </div>
                <div className="space-y-1.5">
                  <Label>Platform</Label>
                  <Select
                    value={form.watch("platform")}
                    onValueChange={(v) => form.setValue("platform", v as FormValues["platform"])}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select platform" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="hackerone">HackerOne</SelectItem>
                      <SelectItem value="bugcrowd">Bugcrowd</SelectItem>
                      <SelectItem value="intigriti">Intigriti</SelectItem>
                      <SelectItem value="other">Other / custom</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="p-url">Program URL</Label>
                  <Input id="p-url" {...form.register("url")} placeholder="https://hackerone.com/acme" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="p-src">Policy source URL</Label>
                  <Input id="p-src" {...form.register("policy_source_url")} placeholder="https://hackerone.com/acme/policy" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="p-desc">Description</Label>
                  <Textarea id="p-desc" {...form.register("description")} rows={3} />
                </div>
                <div className="flex justify-end gap-2 pt-1">
                  <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={create.isPending}>
                    {create.isPending ? "Creating…" : "Create program"}
                  </Button>
                </div>
                {create.error && (
                  <p className="text-xs text-danger">{create.error.message}</p>
                )}
              </form>
            </DialogContent>
          </Dialog>
        }
      />

      {!isLoading && programs.length === 0 ? (
        <EmptyState
          title="No programs"
          description="Create a program to define its scope rules. Every scan and active test is gated by the program's policy."
        />
      ) : (
        <div className="space-y-2">
          {programs.map((p) => (
            <Card key={p.id} className="p-0">
              <button
                className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left"
                onClick={() => router.push(`/programs/${p.id}`)}
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-text-primary">{p.name}</p>
                  <p className="mt-0.5 text-xs text-text-muted">
                    {p.platform} · policy v{p.current_policy_version} · updated {formatTime(p.updated_at)}
                  </p>
                </div>
                <StatusBadge status={p.current_policy_version > 0 ? "in_scope" : "not_started"} />
              </button>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
