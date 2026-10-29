"use client";

import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { useProgram } from "@/lib/api/hooks";
import { ScopePanel } from "@/features/scope/scope-panel";
import { Badge, Button, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/primitives";
import { PageHeader, StatusBadge } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";

export default function ProgramWorkspace({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: program, isLoading } = useProgram(params.id);

  if (isLoading || !program) {
    return <Skeleton className="h-40 w-full" />;
  }

  const tabs: { id: string; label: string }[] = [
    { id: "scope", label: "Scope" },
    { id: "assets", label: "Assets" },
    { id: "endpoints", label: "Endpoints" },
    { id: "research", label: "Research" },
    { id: "scans", label: "Scans" },
    { id: "findings", label: "Findings" },
    { id: "details", label: "Details" },
  ];

  return (
    <>
      <PageHeader
        title={program.name}
        description={program.description || undefined}
        actions={
          <div className="flex items-center gap-2">
            <Badge tone="muted">{program.platform}</Badge>
            <StatusBadge status={program.current_policy_version > 0 ? "in_scope" : "not_started"} />
          </div>
        }
      />
      <Tabs defaultValue="scope">
        <TabsList>
          {tabs.map((t) => (
            <TabsTrigger key={t.id} value={t.id}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="scope" className="pt-4">
          <ScopePanel programId={program.id} />
        </TabsContent>

        {[
          ["assets", "/assets"],
          ["endpoints", "/endpoints"],
          ["research", "/research"],
          ["scans", "/recon"],
          ["findings", "/findings"],
        ].map(([id, href]) => (
          <TabsContent key={id} value={id} className="pt-4">
            <div className="rounded-panel border border-dashed border-border p-8 text-center">
              <p className="text-sm text-text-primary">
                {id[0].toUpperCase() + id.slice(1)} for this program live in the {id} workspace.
              </p>
              <Button
                variant="secondary"
                className="mt-3"
                onClick={() => router.push(`${href}?program_id=${program.id}`)}
              >
                Open {id} <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </TabsContent>
        ))}

        <TabsContent value="details" className="pt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1 text-[13px]">
              <p className="text-text-secondary">Program URL</p>
              {program.url ? (
                <a href={program.url} target="_blank" rel="noreferrer" className="mono text-info hover:underline">
                  {program.url}
                </a>
              ) : (
                <p className="text-text-muted">—</p>
              )}
            </div>
            <div className="space-y-1 text-[13px]">
              <p className="text-text-secondary">Policy source</p>
              {program.policy_source_url ? (
                <a href={program.policy_source_url} target="_blank" rel="noreferrer" className="mono text-info hover:underline">
                  {program.policy_source_url}
                </a>
              ) : (
                <p className="text-text-muted">—</p>
              )}
            </div>
            <div className="space-y-1 text-[13px]">
              <p className="text-text-secondary">Created</p>
              <p className="text-text-primary">{formatTime(program.created_at)}</p>
            </div>
            <div className="space-y-1 text-[13px]">
              <p className="text-text-secondary">Last policy review</p>
              <p className="text-text-primary">{program.last_policy_review ? formatTime(program.last_policy_review) : "—"}</p>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </>
  );
}
