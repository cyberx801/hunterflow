"use client";

import { usePathname, useRouter } from "next/navigation";
import {
  Activity,
  Boxes,
  Bug,
  Crosshair,
  FileText,
  FlaskConical,
  Globe,
  LayoutDashboard,
  Network,
  Settings,
  TrafficCone,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/programs", label: "Programs", icon: Globe },
  { href: "/recon", label: "Recon", icon: Network },
  { href: "/assets", label: "Assets", icon: Boxes },
  { href: "/endpoints", label: "Endpoints", icon: Activity },
  { href: "/research", label: "Research", icon: FlaskConical },
  { href: "/traffic", label: "HTTP Traffic", icon: TrafficCone },
  { href: "/findings", label: "Findings", icon: Bug },
  { href: "/reports", label: "Reports", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="flex w-14 shrink-0 flex-col border-r border-border bg-surface md:w-56">
      <button
        className="flex h-14 items-center gap-2.5 border-b border-border px-3 md:px-4"
        onClick={() => router.push("/overview")}
        aria-label="HunterFlow home"
      >
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent/15 text-accent">
          <Crosshair className="h-4 w-4" />
        </span>
        <span className="hidden text-sm font-semibold text-text-primary md:block">HunterFlow</span>
      </button>
      <nav className="flex-1 space-y-0.5 overflow-y-auto p-2" aria-label="Main navigation">
        {NAV.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/overview" && pathname.startsWith(item.href + "/"));
          const Icon = item.icon;
          return (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium transition-colors",
                active
                  ? "bg-raised text-text-primary"
                  : "text-text-secondary hover:bg-raised/60 hover:text-text-primary"
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className={cn("h-4 w-4 shrink-0", active ? "text-accent" : "text-text-muted")} />
              <span className="hidden md:block">{item.label}</span>
            </button>
          );
        })}
      </nav>
      <div className="border-t border-border p-2">
        <button
          onClick={() => router.push("/settings")}
          className={cn(
            "flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium transition-colors",
            pathname.startsWith("/settings")
              ? "bg-raised text-text-primary"
              : "text-text-secondary hover:bg-raised/60 hover:text-text-primary"
          )}
        >
          <Settings className="h-4 w-4 shrink-0 text-text-muted" />
          <span className="hidden md:block">Settings</span>
        </button>
      </div>
    </aside>
  );
}
