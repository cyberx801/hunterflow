"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Bug, Link2 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, useResearchCard } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Checkbox, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton, Textarea } from "@/components/ui/primitives";
import { PageHeader, StatusBadge } from "@/components/domain/shared";
import { AiAssistCard } from "@/components/domain/ai-assist";
import { formatTime } from "@/lib/utils";
import type { ResearchCard } from "@/lib/api/types";

const CARD_STATUSES = ["not_started", "in_progress", "needs_verification", "confirmed", "rejected", "blocked", "archived"];

const NEXT_STATUS: Record<string, string[]> = {
  not_started: ["in_progress", "blocked", "archived"],
  in_progress: ["needs_verification", "confirmed", "rejected", "blocked", "not_started"],
  needs_verification: ["confirmed", "rejected", "in_progress"],
  confirmed: ["archived", "in_progress"],
  rejected: ["in_progress", "archived"],
  blocked: ["in_progress", "archived"],
  archived: ["not_started", "in_progress"],
};

export default function ResearchCardPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const { data: card, isLoading } = useResearchCard(params.id);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["research"] });

  const transition = useMutation({
    mutationFn: (to: string) =>
      apiFetch<ResearchCard>(`/api/v1/research/${params.id}/transition`, {
        method: "POST",
        body: JSON.stringify({ to }),
        csrf,
      }),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: (patch: Record<string, string | null>) =>
      apiFetch<ResearchCard>(`/api/v1/research/${params.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
        csrf,
      }),
    onSuccess: invalidate,
  });

  const toggleItem = useMutation({
    mutationFn: ({ itemId, checked }: { itemId: string; checked: boolean }) =>
      apiFetch(`/api/v1/research/${params.id}/checklist/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify({ checked }),
        csrf,
      }),
    onSuccess: invalidate,
  });

  const addItem = useMutation({
    mutationFn: (label: string) =>
      apiFetch(`/api/v1/research/${params.id}/checklist`, {
        method: "POST",
        body: JSON.stringify({ label }),
        csrf,
      }),
    onSuccess: invalidate,
  });

  if (isLoading || !card) return <Skeleton className="h-96 w-full" />;

  const next = NEXT_STATUS[card.status] ?? [];

  return (
    <>
      <PageHeader
        title={card.title}
        description={`Created ${formatTime(card.created_at)} · score ${card.priority_score}`}
        actions={
          <>
            <StatusBadge status={card.status} />
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </>
        }
      />

      {card.priority_factors && (
        <div className="mb-4 flex flex-wrap gap-1.5">
          {Object.entries(card.priority_factors)
            .filter(([, on]) => on)
            .map(([key]) => (
              <Badge key={key} tone="info">{key.replace(/_/g, " ")}</Badge>
            ))}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Hypothesis</h2>
            </CardHeader>
            <CardContent>
              <EditableText value={card.hypothesis} onSave={(v) => update.mutate({ hypothesis: v })} placeholder="What do you expect to find or disprove?" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Methodology</h2>
            </CardHeader>
            <CardContent>
              <EditableText value={card.methodology} onSave={(v) => update.mutate({ methodology: v })} placeholder="Steps you plan to follow…" multiline />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Observations</h2>
            </CardHeader>
            <CardContent>
              <EditableText value={card.observations_md} onSave={(v) => update.mutate({ observations_md: v })} placeholder="Record what you observe during testing…" multiline />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Notes & next action</h2>
            </CardHeader>
            <CardContent className="space-y-4">
              <EditableText value={card.notes_md} onSave={(v) => update.mutate({ notes_md: v })} placeholder="Notes…" multiline />
              <EditableText value={card.next_action} onSave={(v) => update.mutate({ next_action: v })} placeholder="Next action…" />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Checklist</h2>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {card.checklist.map((item) => (
                <label key={item.id} className="flex cursor-pointer items-center gap-2.5 rounded border border-border bg-app px-3 py-2 text-[13px] text-text-primary">
                  <Checkbox
                    checked={item.checked}
                    onCheckedChange={(v) => toggleItem.mutate({ itemId: item.id, checked: !!v })}
                  />
                  <span className={item.checked ? "line-through opacity-60" : ""}>{item.label}</span>
                </label>
              ))}
              <QuickAdd onAdd={(label) => addItem.mutate(label)} />
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Status</h2>
            </CardHeader>
            <CardContent className="space-y-3">
              <Select
                value={card.status}
                onValueChange={(to) => transition.mutate(to)}
                disabled={transition.isPending}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CARD_STATUSES.map((s) => (
                    <SelectItem key={s} value={s} disabled={!next.includes(s) && s !== card.status}>
                      {s.replace(/_/g, " ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-text-muted">
                Valid next: {next.map((s) => s.replace(/_/g, " ")).join(", ")}
              </p>
              {transition.error && <p className="text-xs text-danger">{transition.error.message}</p>}
              {card.status === "confirmed" && (
                <Button
                  className="w-full"
                  onClick={() =>
                    router.push(
                      `/findings?program_id=${card.program_id}&endpoint_id=${card.endpoint_id ?? ""}`
                    )
                  }
                >
                  <Bug className="h-4 w-4" /> Record a finding
                </Button>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <h2 className="text-sm font-semibold text-text-primary">Linked context</h2>
            </CardHeader>
            <CardContent className="space-y-2 text-[13px]">
              <p className="text-text-secondary">
                Program:{" "}
                <button className="text-info hover:underline" onClick={() => router.push(`/programs/${card.program_id}`)}>
                  {card.program_id.slice(0, 8)}
                </button>
              </p>
              {card.asset_id && (
                <p className="text-text-secondary">
                  Asset:{" "}
                  <button className="mono text-info hover:underline" onClick={() => router.push(`/assets/${card.asset_id}`)}>
                    view
                  </button>
                </p>
              )}
              {card.endpoint_id && (
                <p className="text-text-secondary">
                  Endpoint:{" "}
                  <button className="mono text-info hover:underline" onClick={() => router.push(`/endpoints/${card.endpoint_id}`)}>
                    view
                  </button>
                </p>
              )}
              <p className="text-text-secondary">
                Required authorization: <span className="text-text-primary">{card.required_authorization ?? "—"}</span>
              </p>
              <p className="text-text-secondary">
                Required accounts: <span className="text-text-primary">{card.required_accounts ?? "—"}</span>
              </p>
              <Button
                variant="secondary"
                size="sm"
                className="mt-2 w-full"
                onClick={() =>
                  router.push(`/traffic?program_id=${card.program_id}&endpoint_id=${card.endpoint_id ?? ""}`)
                }
              >
                <Link2 className="h-3.5 w-3.5" /> Compare traffic for this endpoint
              </Button>
            </CardContent>
          </Card>

          <AiAssistCard kind="research_card" id={card.id} />
        </div>
      </div>
    </>
  );
}

function EditableText({
  value,
  onSave,
  placeholder,
  multiline,
}: {
  value: string | null;
  onSave: (v: string | null) => void;
  placeholder?: string;
  multiline?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? "");
  const [hover, setHover] = useState(false);

  if (!editing) {
    return (
      <button
        className="block w-full rounded border border-transparent px-2 py-1.5 text-left text-[13px] text-text-primary hover:border-border hover:bg-raised/50"
        onClick={() => {
          setDraft(value ?? "");
          setEditing(true);
        }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
      >
        {value ? (
          <span className="whitespace-pre-wrap">{value}</span>
        ) : (
          <span className="text-text-muted">{placeholder}</span>
        )}
      </button>
    );
  }

  return (
    <div className="space-y-1.5">
      {multiline ? (
        <Textarea
          autoFocus
          rows={4}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      ) : (
        <input
          autoFocus
          className="w-full rounded border border-border bg-surface px-2 py-1.5 text-[13px] text-text-primary focus-visible:border-border-strong focus-visible:outline-none"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      )}
      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => {
            onSave(draft.trim() ? draft : null);
            setEditing(false);
          }}
        >
          Save
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
          Cancel
        </Button>
      </div>
    </div>
  );
}

function QuickAdd({ onAdd }: { onAdd: (label: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <div className="flex gap-2 pt-1">
      <input
        className="h-8 flex-1 rounded border border-border bg-surface px-2 text-[13px] text-text-primary placeholder:text-text-muted focus-visible:border-border-strong focus-visible:outline-none"
        placeholder="Add checklist item…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim()) {
            onAdd(value.trim());
            setValue("");
          }
        }}
      />
      <Button
        size="sm"
        variant="secondary"
        onClick={() => {
          if (value.trim()) {
            onAdd(value.trim());
            setValue("");
          }
        }}
      >
        <ArrowRight className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
