"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useAiStatus, useCsrfToken } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Button, Card, CardContent, CardHeader } from "@/components/ui/primitives";
import type { AiSummary } from "@/lib/api/types";

export function AiAssistCard({
  kind,
  id,
}: {
  kind: "research_card" | "finding";
  id: string;
}) {
  const csrf = useCsrfToken();
  const { data: status } = useAiStatus();
  const [text, setText] = useState<string | null>(null);
  const [disclaimer, setDisclaimer] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () =>
      apiFetch<AiSummary>("/api/v1/ai/summarize", {
        method: "POST",
        body: JSON.stringify({ kind, id }),
        csrf,
      }),
    onSuccess: (data) => {
      setText(data.text);
      setDisclaimer(data.disclaimer);
    },
  });

  if (!status?.enabled) return null;

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold text-text-primary">
          <Sparkles className="h-3.5 w-3.5 text-accent" /> AI assist
        </h2>
        <Button size="sm" variant="secondary" onClick={() => run.mutate()} disabled={run.isPending}>
          {run.isPending ? "Thinking…" : "Summarize"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {!text && !run.error && (
          <p className="text-[13px] text-text-muted">
            Summarizes this page with {status.model}. It has no tool access and cannot scan or
            verify anything.
          </p>
        )}
        {run.error && <p className="text-xs text-danger">{run.error.message}</p>}
        {text && (
          <>
            <pre className="whitespace-pre-wrap rounded border border-border bg-app p-2 text-[13px] text-text-primary">
              {text}
            </pre>
            <p className="text-xs text-warning">{disclaimer}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
