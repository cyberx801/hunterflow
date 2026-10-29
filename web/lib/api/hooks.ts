"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { apiFetch } from "./client";
import type {
  Asset,
  Comparison,
  ComparisonDetail,
  Endpoint,
  Evidence,
  Finding,
  JobDetail,
  Overview,
  Page,
  PolicyVersion,
  Program,
  ResearchCard,
  ResearchTemplate,
  ScanJob,
  ScanProfile,
  ScopeRule,
  SettingsView,
  Transaction,
  TransactionDetail,
} from "./types";

export function useCsrfToken(): string {
  const { useAuthContext } = require("./auth-context");
  return useAuthContext().me?.csrf_token ?? "";
}

export function useProgramId(): string | undefined {
  const params = useSearchParams();
  const raw = params.get("program_id");
  return raw ?? undefined;
}

export function usePrograms() {
  return useQuery({
    queryKey: ["programs"],
    queryFn: () => apiFetch<Page<Program>>("/api/v1/programs?page_size=100"),
  });
}

export function useProgram(id: string | undefined) {
  return useQuery({
    queryKey: ["programs", id],
    queryFn: () => apiFetch<Program>(`/api/v1/programs/${id}`),
    enabled: !!id,
  });
}

export function useScopeRules(programId: string | undefined) {
  return useQuery({
    queryKey: ["scope", programId],
    queryFn: () => apiFetch<ScopeRule[]>(`/api/v1/programs/${programId}/scope`),
    enabled: !!programId,
  });
}

export function usePolicyVersions(programId: string | undefined) {
  return useQuery({
    queryKey: ["scope", programId, "versions"],
    queryFn: () => apiFetch<PolicyVersion[]>(`/api/v1/programs/${programId}/scope/versions`),
    enabled: !!programId,
  });
}

export function useAssets(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["assets", qs.toString()],
    queryFn: () => apiFetch<Page<Asset>>(`/api/v1/assets?page_size=50&${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
}

export function useAsset(id: string | undefined) {
  return useQuery({
    queryKey: ["assets", id],
    queryFn: () => apiFetch<Asset>(`/api/v1/assets/${id}`),
    enabled: !!id,
  });
}

export function useEndpoints(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["endpoints", qs.toString()],
    queryFn: () => apiFetch<Page<Endpoint>>(`/api/v1/endpoints?page_size=50&${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
}

export function useEndpoint(id: string | undefined) {
  return useQuery({
    queryKey: ["endpoints", id],
    queryFn: () => apiFetch<Endpoint>(`/api/v1/endpoints/${id}`),
    enabled: !!id,
  });
}

export function useResearchCards(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["research", qs.toString()],
    queryFn: () => apiFetch<Page<ResearchCard>>(`/api/v1/research?page_size=100&${qs.toString()}`),
  });
}

export function useResearchCard(id: string | undefined) {
  return useQuery({
    queryKey: ["research", id],
    queryFn: () => apiFetch<ResearchCard>(`/api/v1/research/${id}`),
    enabled: !!id,
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: ["research-templates"],
    queryFn: () => apiFetch<ResearchTemplate[]>("/api/v1/research-templates"),
  });
}

export function useTransactions(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["transactions", qs.toString()],
    queryFn: () => apiFetch<Page<Transaction>>(`/api/v1/traffic/transactions?page_size=50&${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
}

export function useTransaction(id: string | undefined) {
  return useQuery({
    queryKey: ["transactions", id],
    queryFn: () => apiFetch<TransactionDetail>(`/api/v1/traffic/transactions/${id}`),
    enabled: !!id,
  });
}

export function useComparisons(programId?: string) {
  return useQuery({
    queryKey: ["comparisons", programId],
    queryFn: () => apiFetch<Comparison[]>(`/api/v1/comparisons${programId ? `?program_id=${programId}` : ""}`),
  });
}

export function useComparison(id: string | undefined) {
  return useQuery({
    queryKey: ["comparisons", id],
    queryFn: () => apiFetch<ComparisonDetail>(`/api/v1/comparisons/${id}`),
    enabled: !!id,
  });
}

export function useFindings(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["findings", qs.toString()],
    queryFn: () => apiFetch<Page<Finding>>(`/api/v1/findings?page_size=50&${qs.toString()}`),
    placeholderData: keepPreviousData,
  });
}

export function useFinding(id: string | undefined) {
  return useQuery({
    queryKey: ["findings", id],
    queryFn: () => apiFetch<Finding>(`/api/v1/findings/${id}`),
    enabled: !!id,
  });
}

export function useFindingDuplicates(id: string | undefined) {
  return useQuery({
    queryKey: ["findings", id, "duplicates"],
    queryFn: () =>
      apiFetch<{ finding_id: string; title: string; score: number; reasons: string[]; status: string }[]>(
        `/api/v1/findings/${id}/duplicates`
      ),
    enabled: !!id,
  });
}

export function useEvidence(programId?: string) {
  return useQuery({
    queryKey: ["evidence", programId],
    queryFn: () => apiFetch<Evidence[]>(`/api/v1/evidence${programId ? `?program_id=${programId}` : ""}`),
  });
}

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: () => apiFetch<import("./types").Report[]>("/api/v1/reports"),
  });
}

export function useScans(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["scans", qs.toString()],
    queryFn: () => apiFetch<Page<ScanJob>>(`/api/v1/scans?page_size=50&${qs.toString()}`),
    refetchInterval: (q) =>
      q.state.data?.items.some((j) => j.status === "queued" || j.status === "running") ? 2000 : false,
  });
}

export function useJob(id: string | undefined) {
  return useQuery({
    queryKey: ["jobs", id],
    queryFn: () => apiFetch<JobDetail>(`/api/v1/jobs/${id}`),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data?.status === "queued" || q.state.data?.status === "running" ? 2000 : false,
  });
}

export function useProfiles() {
  return useQuery({
    queryKey: ["profiles"],
    queryFn: () => apiFetch<ScanProfile[]>("/api/v1/profiles"),
  });
}

export function useCuratedTemplates() {
  return useQuery({
    queryKey: ["profiles", "templates"],
    queryFn: () => apiFetch<{ id: string; name: string; severity: string; category: string }[]>(
      "/api/v1/profiles/curated-templates"
    ),
  });
}

export function useOverview() {
  return useQuery({
    queryKey: ["overview"],
    queryFn: () => apiFetch<Overview>("/api/v1/overview"),
  });
}

export function useSettings() {
  return useQuery({
    queryKey: ["settings"],
    queryFn: () => apiFetch<SettingsView>("/api/v1/settings"),
  });
}

export function useAudit(page: number) {
  return useQuery({
    queryKey: ["audit", page],
    queryFn: () =>
      apiFetch<{ total: number; items: import("./types").AuditEvent[] }>(
        `/api/v1/audit?page=${page}&page_size=50`
      ),
  });
}

export function useSchedules(programId?: string) {
  return useQuery({
    queryKey: ["schedules", programId],
    queryFn: () =>
      apiFetch<import("./types").Schedule[]>(
        `/api/v1/schedules${programId ? `?program_id=${programId}` : ""}`
      ),
  });
}

export function useMonitoringEvents(filters: Record<string, string | undefined>) {
  const qs = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => v && qs.set(k, v));
  return useQuery({
    queryKey: ["monitoring-events", qs.toString()],
    queryFn: () =>
      apiFetch<import("./types").MonitoringEvent[]>(
        `/api/v1/monitoring/events?limit=200&${qs.toString()}`
      ),
    refetchInterval: 15000,
  });
}

export function useMonitoringStatus() {
  return useQuery({
    queryKey: ["monitoring-status"],
    queryFn: () => apiFetch<import("./types").MonitoringStatus>("/api/v1/monitoring/status"),
  });
}

export function useAiStatus() {
  return useQuery({
    queryKey: ["ai-status"],
    queryFn: () => apiFetch<import("./types").AiStatus>("/api/v1/ai/status"),
  });
}

export function useUsers(enabled: boolean) {
  return useQuery({
    queryKey: ["users"],
    queryFn: () => apiFetch<import("./types").UserAccount[]>("/api/v1/users"),
    enabled,
  });
}
