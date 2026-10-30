import { expect, test } from "@playwright/test";
import { E2E_PASSWORD, E2E_USER, createProgramViaApi, csrf, ensureUser, loginViaUi } from "./helpers";

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";
const RUN = Date.now().toString(36);
const PROG = `ACME ${RUN}`;

async function programFor(request: import("@playwright/test").APIRequestContext, name: string) {
  const programs = await (await request.get(`${BASE}/api/v1/programs?page_size=100`)).json();
  return programs.items.find((p: { name: string }) => p.name === name) ?? null;
}

test.describe("HunterFlow critical workflows", () => {
  test("F1-F2: onboarding, program creation, scope, policy version", async ({ page, request }) => {
    await ensureUser(request);
    await page.goto("/login");
    const bootstrap = await (await request.get(`${BASE}/api/v1/auth/bootstrap`)).json();
    if (bootstrap.setup_required) {
      await page.reload();
      await expect(page.getByRole("button", { name: /create account/i })).toBeVisible();
      await page.getByLabel("Username").fill(E2E_USER);
      await page.getByLabel("Password", { exact: true }).fill(E2E_PASSWORD);
      await page.getByLabel("Confirm password").fill(E2E_PASSWORD);
      await page.getByRole("button", { name: /create account/i }).click();
      await expect(page).toHaveURL(/\/overview/);
    } else {
      await loginViaUi(page);
    }

    await page.goto("/programs");
    await page.getByRole("button", { name: /new program/i }).click();
    await page.getByPlaceholder("ACME Corp").fill(PROG);
    await page.getByRole("button", { name: /create program/i }).click();

    await expect(page).toHaveURL(/\/programs\//);
    await expect(page.getByText("Scope rules").first()).toBeVisible();
    await page.getByPlaceholder("*.example.com").fill("*.example.com");
    await page.getByRole("button", { name: /add rule/i }).click();

    await page.getByPlaceholder(/https:\/\/api\.example\.com\/v1/).fill(
      "https://api.example.com/v1\nhttps://evil.net/x"
    );
    await page.getByRole("button", { name: /evaluate targets/i }).click();
    await expect(page.getByText("allowed").first()).toBeVisible();
    await expect(page.getByText("needs confirmation").first()).toBeVisible();

    await page.getByRole("button", { name: /publish policy version/i }).click();
    await expect(page.getByText(/policy v1/).first()).toBeVisible();
  });

  test("F3: recon dry-run and job history", async ({ page, request }) => {
    await ensureUser(request);
    await createProgramViaApi(request, `Recon ${RUN}`);
    await loginViaUi(page);

    await page.goto("/recon");
    await page.getByRole("button", { name: /new scan/i }).click();
    await page.getByText("Dry run — plan steps without executing tools").click();
    await page.getByRole("button", { name: /start scan/i }).click();
    await expect(page.getByText("dry run").first()).toBeVisible();

    await page.locator("[data-job-id]").filter({ hasText: "dry run" }).first().click();
    await expect(page.getByText(/no tools were executed/i)).toBeVisible();
  });

  test("F4: research card from template with checklist", async ({ page, request }) => {
    await ensureUser(request);
    const program = await createProgramViaApi(request, `Research ${RUN}`);
    await loginViaUi(page);

    await page.goto(`/research?program_id=${program.id}`);
    await page.getByRole("button", { name: /new research card/i }).click();
    await page.getByRole("combobox").first().click();
    const bolaOption = page.getByRole("option", { name: /BOLA/ });
    await expect(bolaOption).toBeVisible();
    await bolaOption.click();
    await page.getByPlaceholder(/e\.g\. BOLA check/).fill(`BOLA orders ${RUN}`);
    await page.getByRole("button", { name: /create card/i }).click();

    await expect(page.getByText(`BOLA orders ${RUN}`).first()).toBeVisible();
    await page.getByText(`BOLA orders ${RUN}`).first().click();
    await expect(page.getByText(/object-level authorization/i, { exact: false }).first()).toBeVisible();
    await expect(page.getByText("Identify resource identifiers")).toBeVisible();

    await page.getByRole("combobox").click();
    await page.getByText("in progress", { exact: true }).click();
    await expect(page.getByText("in progress", { exact: true }).first()).toBeVisible();

    await page
      .locator("label")
      .filter({ hasText: "Identify resource identifiers" })
      .locator("button")
      .click();
  });

  test("F5: traffic import and comparison review notice", async ({ page, request }) => {
    await ensureUser(request);
    const program = await createProgramViaApi(request, `Traffic ${RUN}`);
    const token = await csrf(request);
    const url = `https://api.example.com/orders/${RUN}`;

    for (const [tag, status] of [
      [`acct-a-${RUN}`, 200],
      [`acct-b-${RUN}`, 403],
    ] as const) {
      await request.post(`${BASE}/api/v1/traffic/transactions`, {
        headers: { "X-CSRF-Token": token },
        data: {
          program_id: program.id,
          account_tag: tag,
          method: "GET",
          url,
          response_status: status,
          response_headers: { "Content-Type": "application/json" },
          response_body: '{"id": 1}',
        },
      });
    }

    await loginViaUi(page);
    await page.goto(`/traffic?program_id=${program.id}`);
    await expect(page.getByText(url).first()).toBeVisible();

    const txs = await (
      await request.get(`${BASE}/api/v1/traffic/transactions?program_id=${program.id}`)
    ).json();
    const ids = txs.items.map((t: { id: string }) => t.id);
    const set = await request.post(`${BASE}/api/v1/comparisons`, {
      headers: { "X-CSRF-Token": token },
      data: { program_id: program.id, name: `status-only-${RUN}`, transaction_ids: ids },
    });
    const comparison = await set.json();

    await page.goto(`/traffic/compare/${comparison.id}`);
    await expect(page.getByText(/review required/i).first()).toBeVisible();
    await expect(page.getByText(/does not indicate a vulnerability/i)).toBeVisible();
  });

  test("F6-F7: finding verification honesty and report generation", async ({ page, request }) => {
    await ensureUser(request);
    const program = await createProgramViaApi(request, `Findings ${RUN}`);
    const token = await csrf(request);
    const title = `BOLA on orders ${RUN}`;

    const finding = await request.post(`${BASE}/api/v1/findings`, {
      headers: { "X-CSRF-Token": token },
      data: {
        program_id: program.id,
        title,
        category: "object_access",
        severity: "high",
        impact: "Account data disclosure",
        reproduction_steps: "1. Login as alice\n2. Fetch order of bob",
      },
    });
    const f = await finding.json();

    await request.post(`${BASE}/api/v1/findings/${f.id}/transition`, {
      headers: { "X-CSRF-Token": token },
      data: { to: "under_investigation" },
    });
    const noConfirm = await request.post(`${BASE}/api/v1/findings/${f.id}/transition`, {
      headers: { "X-CSRF-Token": token },
      data: { to: "verified", verified_human_confirmation: false },
    });
    expect(noConfirm.status()).toBe(403);

    await loginViaUi(page);
    await page.goto(`/findings/${f.id}`);
    await expect(page.getByText(title).first()).toBeVisible();
    await expect(page.getByText("unverified").first()).toBeVisible();

    await page.getByRole("button", { name: /markdown/i }).click();
    await expect(page.getByText(/view generated markdown report/i)).toBeVisible();

    const reports = await (await request.get(`${BASE}/api/v1/reports`)).json();
    const mine = reports.filter((r: { finding_id: string }) => r.finding_id === f.id);
    expect(mine.length).toBeGreaterThanOrEqual(1);
    const reportContent = await (
      await request.get(`${BASE}/api/v1/reports/${mine[mine.length - 1].id}`)
    ).json();
    expect(reportContent.content).toContain("UNVERIFIED");
  });

  test("Keyboard accessibility: core navigation without mouse", async ({ page, request }) => {
    await ensureUser(request);
    await createProgramViaApi(request, `Keyboard ${RUN}`);
    await loginViaUi(page);

    await page.goto("/overview");
    // Focus must reach a real control via the keyboard.
    let focused = "";
    for (let i = 0; i < 6; i++) {
      await page.keyboard.press("Tab");
      focused = await page.evaluate(() => document.activeElement?.tagName ?? "");
      if (["BUTTON", "A", "INPUT", "SELECT"].includes(focused)) break;
    }
    expect(["BUTTON", "A", "INPUT", "SELECT"]).toContain(focused);
  });
});

