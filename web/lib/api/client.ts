"use client";

import { useCallback, useEffect, useState } from "react";

export interface Me {
  id: string;
  username: string;
  is_admin: boolean;
  csrf_token: string;
}

interface ApiErrorBody {
  error?: { code?: string; message?: string; correlation_id?: string };
}

export class ApiClientError extends Error {
  status: number;
  code?: string;
  correlationId?: string;

  constructor(status: number, message: string, code?: string, correlationId?: string) {
    super(message);
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit & { csrf?: string } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init.headers as Record<string, string>),
  };
  if (init.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] ?? "application/json";
  }
  if (init.method && !["GET", "HEAD", "OPTIONS"].includes(init.method)) {
    headers["X-CSRF-Token"] = init.csrf ?? "";
  }
  const resp = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
  });
  let body: unknown = null;
  try {
    body = await resp.json();
  } catch {
    body = null;
  }
  if (!resp.ok) {
    const err = (body as ApiErrorBody | null)?.error;
    throw new ApiClientError(
      resp.status,
      err?.message ?? `Request failed (${resp.status})`,
      err?.code,
      err?.correlation_id
    );
  }
  return body as T;
}

export function useAuth() {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetch<Me>("/api/v1/auth/me");
      setMe(data);
      setError(null);
      return data;
    } catch {
      setMe(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (username: string, password: string) => {
      setError(null);
      try {
        const data = await apiFetch<Me>("/api/v1/auth/login", {
          method: "POST",
          body: JSON.stringify({ username, password }),
        });
        setMe(data);
        return data;
      } catch (e) {
        const msg = e instanceof ApiClientError ? e.message : "Login failed";
        setError(msg);
        throw e;
      }
    },
    []
  );

  const register = useCallback(async (username: string, password: string) => {
    setError(null);
    try {
      const data = await apiFetch<Me>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setMe(data);
      return data;
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : "Registration failed";
      setError(msg);
      throw e;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiFetch("/api/v1/auth/logout", { method: "POST", csrf: me?.csrf_token });
    } finally {
      setMe(null);
    }
  }, [me]);

  return { me, loading, error, refresh, login, register, logout };
}

export type AuthContextValue = ReturnType<typeof useAuth>;
