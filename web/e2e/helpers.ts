import { APIRequestContext, Page, expect } from "@playwright/test";

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

// HunterFlow v0.1.0 is single-user: one shared account for the whole E2E suite.
export const E2E_USER = "e2e";
export const E2E_PASSWORD = "e2e-password-123";

export async function ensureUser(request: APIRequestContext): Promise<string> {
  // Register if first-run; otherwise log in as the shared account.
  const bootstrap = await request.get(`${BASE}/api/v1/auth/bootstrap`);
  const { setup_required } = await bootstrap.json();
  if (setup_required) {
    const resp = await request.post(`${BASE}/api/v1/auth/register`, {
      data: { username: E2E_USER, password: E2E_PASSWORD },
    });
    if (resp.status() !== 200) {
      throw new Error(`register failed: ${resp.status()} ${await resp.text()}`);
    }
    return E2E_USER;
  }
  const login = await request.post(`${BASE}/api/v1/auth/login`, {
    data: { username: E2E_USER, password: E2E_PASSWORD },
  });
  if (login.status() !== 200) {
    throw new Error(`login failed: ${login.status()} ${await login.text()}`);
  }
  return E2E_USER;
}

export async function createProgramViaApi(request: APIRequestContext, name = "ACME E2E") {
  const me = await request.get(`${BASE}/api/v1/auth/me`);
  const { csrf_token } = await me.json();
  const resp = await request.post(`${BASE}/api/v1/programs`, {
    headers: { "X-CSRF-Token": csrf_token },
    data: { name, platform: "other" },
  });
  const program = await resp.json();
  await request.post(`${BASE}/api/v1/programs/${program.id}/scope/rules`, {
    headers: { "X-CSRF-Token": csrf_token },
    data: { kind: "domain_wildcard", value: "*.example.com", effect: "allow", priority: 10 },
  });
  await request.post(`${BASE}/api/v1/programs/${program.id}/scope/versions`, {
    headers: { "X-CSRF-Token": csrf_token },
    data: { change_summary: "e2e" },
  });
  return program;
}

export async function loginViaUi(page: Page, username: string = E2E_USER) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(E2E_PASSWORD);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/\/overview/);
}

export async function csrf(request: APIRequestContext): Promise<string> {
  const me = await request.get(`${BASE}/api/v1/auth/me`);
  return (await me.json()).csrf_token;
}
