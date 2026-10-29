"use client";

import { useQuery } from "@tanstack/react-query";
import { ChevronsUpDown, Loader2, LogOut } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthContext } from "@/lib/api/auth-context";
import { apiFetch } from "@/lib/api/client";
import { Badge, Button, Dropdown, DropdownContent, DropdownItem, DropdownTrigger } from "@/components/ui/primitives";

interface Program {
  id: string;
  name: string;
  platform: string;
  archived_at: string | null;
}

interface ScanJob {
  id: string;
  status: string;
  progress: { current_tool?: string; step?: number; total_steps?: number } | null;
}

export function Topbar() {
  const { me, logout } = useAuthContext();
  const router = useRouter();
  const searchParams = useSearchParams();
  const programId = searchParams.get("program_id");

  const { data: programs } = useQuery({
    queryKey: ["programs", "list"],
    queryFn: () => apiFetch<{ items: Program[] }>("/api/v1/programs?page_size=100"),
  });

  const { data: activeJobs } = useQuery({
    queryKey: ["jobs", "active"],
    queryFn: async () => {
      const data = await apiFetch<{ items: ScanJob[] }>("/api/v1/scans?page_size=10&status=running");
      return data.items.filter((j) => j.status === "running");
    },
    refetchInterval: 3000,
  });

  const activeProgram = programs?.items.find((p) => p.id === programId);

  function selectProgram(id: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (id) params.set("program_id", id);
    else params.delete("program_id");
    router.push(`/overview?${params.toString()}`);
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
      <Dropdown>
        <DropdownTrigger asChild>
          <Button variant="secondary" size="sm" className="max-w-64">
            <span className="truncate">{activeProgram?.name ?? "All programs"}</span>
            <ChevronsUpDown className="h-3.5 w-3.5 text-text-muted" />
          </Button>
        </DropdownTrigger>
        <DropdownContent align="start">
          <DropdownItem onClick={() => selectProgram(null)}>All programs</DropdownItem>
          {(programs?.items ?? [])
            .filter((p) => !p.archived_at)
            .map((p) => (
              <DropdownItem key={p.id} onClick={() => selectProgram(p.id)}>
                {p.name}
              </DropdownItem>
            ))}
        </DropdownContent>
      </Dropdown>

      {activeJobs && activeJobs.length > 0 && (
        <button
          onClick={() => router.push("/recon")}
          className="flex items-center gap-2 rounded-md border border-info/30 bg-info/10 px-2.5 py-1 text-xs text-info"
          aria-label={`${activeJobs.length} active scans`}
        >
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
          <span>
            {activeJobs[0].progress?.current_tool ?? "scanning"}
            {activeJobs[0].progress?.total_steps
              ? ` (${activeJobs[0].progress.step}/${activeJobs[0].progress.total_steps})`
              : ""}
          </span>
        </button>
      )}

      <div className="ml-auto flex items-center gap-2">
        <Badge tone="muted" className="hidden md:inline-flex">
          v0.2.0
        </Badge>
        <Dropdown>
          <DropdownTrigger asChild>
            <Button variant="ghost" size="sm" aria-label="User menu">
              {me?.username}
            </Button>
          </DropdownTrigger>
          <DropdownContent align="end">
            <DropdownItem onClick={() => router.push("/settings")}>Settings</DropdownItem>
            <DropdownItem
              onClick={async () => {
                await logout();
                router.push("/login");
              }}
            >
              <LogOut className="mr-1.5 h-3.5 w-3.5" /> Sign out
            </DropdownItem>
          </DropdownContent>
        </Dropdown>
      </div>
    </header>
  );
}
