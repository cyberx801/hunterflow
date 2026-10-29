"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRightLeft, FlaskConical } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useCsrfToken, useEndpoint } from "@/lib/api/hooks";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Card, CardContent, CardHeader, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Skeleton } from "@/components/ui/primitives";
import { MethodBadge, MonoValue, PageHeader } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";

const CATEGORIES = ["auth", "account", "profile", "admin", "file", "payment", "object_access", "resource_mgmt", "api_versioning", "other"];

export default function EndpointDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const csrf = useCsrfToken();
  const queryClient = useQueryClient();
  const { data: ep, isLoading } = useEndpoint(params.id);

  const updateCategory = useMutation({
    mutationFn: (category: string) =>
      apiFetch(`/api/v1/endpoints/${params.id}`, { method: "PATCH", body: JSON.stringify({ category }), csrf }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["endpoints"] }),
  });

  if (isLoading || !ep) return <Skeleton className="h-40 w-full" />;

  const statusDist = Object.entries(ep.status_distribution ?? {});
  const maxStatus = Math.max(1, ...statusDist.map(([, n]) => n as number));

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-2">
            <MethodBadge method={ep.method} />
            <MonoValue value={ep.path} />
          </span>
        }
        description={`Discovered on ${formatTime(ep.first_seen)}`}
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => router.push(`/traffic?program_id=${ep.program_id}`)}
            >
              <ArrowRightLeft className="h-3.5 w-3.5" /> Compare traffic
            </Button>
            <Button
              size="sm"
              onClick={() =>
                router.push(`/research?program_id=${ep.program_id}&endpoint_id=${ep.id}`)
              }
            >
              <FlaskConical className="h-3.5 w-3.5" /> Research card
            </Button>
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Classification</h2>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-xs text-text-secondary">Category {ep.category_manual ? "(manual)" : "(auto)"}</label>
              <Select value={ep.category} onValueChange={(v) => updateCategory.mutate(v)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>{c.replace(/_/g, " ")}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-text-muted">
                Classification is informational — it never implies a vulnerability.
              </p>
            </div>
            <p className="text-[13px] text-text-secondary">
              Auth challenge observed:{" "}
              <span className="text-text-primary">
                {(ep.auth_indicators as { auth_challenge?: boolean } | null)?.auth_challenge ? "yes" : "no"}
              </span>
            </p>
            <p className="text-[13px] text-text-secondary">
              Priority score: <span className="mono text-text-primary">{ep.priority_score}</span>
            </p>
            <p className="text-[13px] text-text-secondary">
              Research cards: <span className="mono text-text-primary">{ep.card_count}</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Status distribution</h2>
          </CardHeader>
          <CardContent>
            {statusDist.length === 0 ? (
              <p className="text-[13px] text-text-muted">No responses observed.</p>
            ) : (
              <div className="space-y-2">
                {statusDist.map(([status, count]) => (
                  <div key={status} className="flex items-center gap-2 text-[13px]">
                    <span className="mono w-10 text-text-primary">{status}</span>
                    <div className="h-3 flex-1 rounded bg-raised">
                      <div
                        className="h-3 rounded bg-info/60"
                        style={{ width: `${((count as number) / maxStatus) * 100}%` }}
                      />
                    </div>
                    <span className="mono w-6 text-right text-text-muted">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Content</h2>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-[13px] text-text-secondary">Content types</p>
            <div className="flex flex-wrap gap-1.5">
              {(ep.content_types ?? []).length === 0 && <span className="text-xs text-text-muted">—</span>}
              {(ep.content_types ?? []).map((ct) => (
                <Badge key={ct} tone="muted">{ct}</Badge>
              ))}
            </div>
            <p className="pt-2 text-[13px] text-text-secondary">Asset</p>
            <MonoValue value={ep.asset_value ?? "—"} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}
