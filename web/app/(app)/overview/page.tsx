"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, Bug, Boxes, FlaskConical, Globe, Network } from "lucide-react";
import { useOverview, usePrograms } from "@/lib/api/hooks";
import { Button, Card, CardContent, CardHeader, Skeleton } from "@/components/ui/primitives";
import { EmptyState, PageHeader, SeverityBadge, StatusBadge } from "@/components/domain/shared";
import { timeAgo } from "@/lib/utils";

export default function OverviewPage() {
  const router = useRouter();
  const { data, isLoading } = useOverview();
  const { data: programs } = usePrograms();

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 md:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      </div>
    );
  }

  const noData =
    data.program_count === 0;

  return (
    <>
      <PageHeader
        title="Overview"
        description="Your research workspace at a glance."
      />
      {noData ? (
        <EmptyState
          title="No programs yet"
          description="Create your first bug bounty program to define its authorized scope and start reconnaissance."
          action={
            <Button onClick={() => router.push("/programs")}>
              Create your first program
            </Button>
          }
        />
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <MetricCard icon={Globe} label="Programs" value={data.program_count} href="/programs" />
            <MetricCard icon={Boxes} label="Assets" value={data.asset_count} href="/assets" />
            <MetricCard icon={Network} label="Endpoints" value={data.endpoint_count} href="/endpoints" />
            <MetricCard icon={Bug} label="Findings" value={data.finding_count} href="/findings" />
            <MetricCard icon={FlaskConical} label="Active scans" value={data.active_scan_count} href="/recon" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-text-primary">Research queue</h2>
                <Button variant="ghost" size="sm" onClick={() => router.push("/research")}>
                  Open workspace <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.research_queue.length === 0 && (
                  <p className="text-[13px] text-text-muted">No cards in progress.</p>
                )}
                {data.research_queue.map((card) => (
                  <button
                    key={card.id}
                    className="flex w-full items-center justify-between rounded border border-border bg-app px-3 py-2 text-left hover:border-border-strong"
                    onClick={() => router.push(`/research/${card.id}`)}
                  >
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-medium text-text-primary">{card.title}</p>
                      <p className="text-xs text-text-muted">
                        {card.factors
                          ? Object.entries(card.factors)
                              .filter(([, on]) => on)
                              .map(([k]) => k.replace(/_/g, " "))
                              .join(" · ")
                          : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-text-muted">score {card.priority_score}</span>
                      <StatusBadge status={card.status} />
                    </div>
                  </button>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-text-primary">Findings needing verification</h2>
                <Button variant="ghost" size="sm" onClick={() => router.push("/findings?unverified_only=true")}>
                  View all <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.findings_needing_verification.length === 0 && (
                  <p className="text-[13px] text-text-muted">Nothing awaiting verification.</p>
                )}
                {data.findings_needing_verification.map((f) => (
                  <button
                    key={f.id}
                    className="flex w-full items-center justify-between rounded border border-border bg-app px-3 py-2 text-left hover:border-border-strong"
                    onClick={() => router.push(`/findings/${f.id}`)}
                  >
                    <span className="truncate text-[13px] font-medium text-text-primary">{f.title}</span>
                    <SeverityBadge severity={f.severity} />
                  </button>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <h2 className="text-sm font-semibold text-text-primary">Recent changes</h2>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {data.recent_changes.length === 0 && (
                  <p className="text-[13px] text-text-muted">No new assets in the last 24 hours.</p>
                )}
                {data.recent_changes.map((c, i) => (
                  <p key={i} className="flex items-center justify-between text-[13px]">
                    <span className="mono truncate text-text-primary">{c.value}</span>
                    <span className="shrink-0 text-xs text-text-muted">{timeAgo(c.at)}</span>
                  </p>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <h2 className="text-sm font-semibold text-text-primary">Recent activity</h2>
              </CardHeader>
              <CardContent className="space-y-1.5">
                {data.recent_activity.length === 0 && (
                  <p className="text-[13px] text-text-muted">No activity recorded.</p>
                )}
                {data.recent_activity.map((a, i) => (
                  <p key={i} className="flex items-center justify-between text-[13px]">
                    <span className="mono truncate text-text-secondary">{a.action}</span>
                    <span className="shrink-0 text-xs text-text-muted">{timeAgo(a.at)}</span>
                  </p>
                ))}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  href: string;
}) {
  const router = useRouter();
  return (
    <button
      onClick={() => router.push(href)}
      className="rounded-panel border border-border bg-surface p-4 text-left transition-colors hover:border-border-strong"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text-secondary">{label}</span>
        <Icon className="h-4 w-4 text-text-muted" />
      </div>
      <p className="mt-2 text-2xl font-semibold text-text-primary">{value}</p>
    </button>
  );
}
