"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Crosshair } from "lucide-react";
import { useAuthContext } from "@/lib/api/auth-context";
import { apiFetch } from "@/lib/api/client";
import { Button, Card, Input, Label } from "@/components/ui/primitives";

export default function LoginPage() {
  const auth = useAuthContext();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (auth.me) {
      router.replace("/overview");
      return;
    }
    apiFetch<{ setup_required: boolean }>("/api/v1/auth/bootstrap")
      .then((r) => setMode(r.setup_required ? "register" : "login"))
      .catch(() => {});
  }, [auth.me, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "register") {
      if (password.length < 12) {
        setError("Password must be at least 12 characters.");
        return;
      }
      if (password !== confirm) {
        setError("Passwords do not match.");
        return;
      }
    }
    setBusy(true);
    try {
      if (mode === "register") {
        await auth.register(username, password);
      } else {
        await auth.login(username, password);
      }
      router.replace("/overview");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <Card className="w-full max-w-sm p-6">
        <div className="mb-6 flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-md bg-accent/15 text-accent">
            <Crosshair className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-base font-semibold text-text-primary">HunterFlow</h1>
            <p className="text-xs text-text-muted">From recon to research. One intelligent workspace.</p>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
              minLength={3}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              required
              minLength={mode === "register" ? 12 : 1}
            />
            {mode === "register" && (
              <p className="text-xs text-text-muted">Minimum 12 characters.</p>
            )}
          </div>
          {mode === "register" && (
            <div className="space-y-1.5">
              <Label htmlFor="confirm">Confirm password</Label>
              <Input
                id="confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                required
              />
            </div>
          )}
          {error && <p className="text-[13px] text-danger">{error}</p>}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Please wait…" : mode === "register" ? "Create account" : "Sign in"}
          </Button>
        </form>

        <p className="mt-5 text-center text-xs text-text-muted">
          Self-hosted · Your data stays on this machine · Authorized testing only
        </p>
      </Card>
    </main>
  );
}
