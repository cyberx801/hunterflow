"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, FlaskConical } from "lucide-react";
import { useAsset } from "@/lib/api/hooks";
import { Badge, Button, Card, CardContent, CardHeader, Skeleton } from "@/components/ui/primitives";
import { MonoValue, PageHeader, ScopeBadge } from "@/components/domain/shared";
import { formatTime } from "@/lib/utils";

export default function AssetDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: asset, isLoading } = useAsset(params.id);

  if (isLoading || !asset) return <Skeleton className="h-40 w-full" />;

  return (
    <>
      <PageHeader
        title={<MonoValue value={asset.value_normalized} />}
        description={`${asset.type} · first seen ${formatTime(asset.first_seen)} · last seen ${formatTime(asset.last_seen)}`}
        actions={
          <>
            <ScopeBadge status={asset.scope_status} />
            <Button variant="ghost" size="sm" onClick={() => router.back()}>
              <ArrowLeft className="h-4 w-4" /> Back
            </Button>
          </>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Metadata</h2>
          </CardHeader>
          <CardContent className="space-y-2 text-[13px]">
            <p className="text-text-secondary">
              Original value: <span className="mono text-text-primary">{asset.value_original}</span>
            </p>
            <p className="text-text-secondary">
              HTTP status: <span className="mono text-text-primary">{asset.http_status ?? "—"}</span>
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(asset.tech ?? []).map((t) => (
                <Badge key={t} tone="info">{t}</Badge>
              ))}
            </div>
            {asset.notes && <p className="text-text-primary">{asset.notes}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text-primary">Research</h2>
            <Button
              size="sm"
              onClick={() => router.push(`/research?asset_id=${asset.id}`)}
            >
              <FlaskConical className="h-3.5 w-3.5" /> Open cards
            </Button>
          </CardHeader>
          <CardContent className="space-y-2 text-[13px]">
            <p className="text-text-secondary">
              Endpoints discovered: <span className="mono text-text-primary">{asset.endpoint_count}</span>
            </p>
            <p className="text-text-secondary">
              Research cards: <span className="mono text-text-primary">{asset.card_count}</span>
            </p>
            <p className="text-text-secondary">
              Priority score: <span className="mono text-text-primary">{asset.priority_score}</span>
            </p>
            <div className="flex gap-2 pt-1">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => router.push(`/endpoints?program_id=${asset.program_id}`)}
              >
                View endpoints
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => router.push(`/research?program_id=${asset.program_id}&asset_id=${asset.id}`)}
              >
                New research card
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {asset.screenshot_path && (
        <Card className="mt-4">
          <CardHeader>
            <h2 className="text-sm font-semibold text-text-primary">Screenshot</h2>
          </CardHeader>
          <CardContent>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/api/v1/assets/${asset.id}/screenshot`}
              alt={`Screenshot of ${asset.value_normalized}`}
              className="max-h-[520px] w-auto rounded border border-border"
            />
          </CardContent>
        </Card>
      )}
    </>
  );
}
