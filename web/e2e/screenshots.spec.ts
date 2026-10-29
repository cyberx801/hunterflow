import { test } from "@playwright/test";
import { E2E_USER, createProgramViaApi, csrf, ensureUser, loginViaUi } from "./helpers";

const BASE = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

/**
 * README screenshots: run only when SCREENSHOTS=1 is set (locally).
 * Outputs real captures to docs/screenshots/ — never fabricated.
 */
const capture = process.env.SCREENSHOTS === "1" ? test : test.skip;

capture.describe("screenshots", () => {
  capture("capture app screens", async ({ page, request }) => {
    await ensureUser(request);
    const program = await createProgramViaApi(request, "ACME Corp");
    const token = await csrf(request);

    for (const [tag, status] of [
      ["acct-a", 200],
      ["acct-b", 403],
    ] as const) {
      await request.post(`${BASE}/api/v1/traffic/transactions`, {
        headers: { "X-CSRF-Token": token },
        data: {
          program_id: program.id,
          account_tag: tag,
          method: "GET",
          url: "https://api.example.com/orders/1",
          response_status: status,
          response_headers: { "Content-Type": "application/json" },
          response_body: '{"id": 1, "status": "shipped"}',
        },
      });
    }
    await request.post(`${BASE}/api/v1/research`, {
      headers: { "X-CSRF-Token": token },
      data: {
        program_id: program.id,
        title: "BOLA check: orders endpoint",
        hypothesis: "Verify whether object-level authorization is enforced between two authorized test accounts.",
        test_category: "object_access",
        methodology: "Access as account A, repeat as account B, compare.",
      },
    });
    await request.post(`${BASE}/api/v1/findings`, {
      headers: { "X-CSRF-Token": token },
      data: {
        program_id: program.id,
        title: "BOLA on orders endpoint",
        category: "object_access",
        severity: "high",
        impact: "Account data disclosure",
        reproduction_steps: "1. Login as account A\n2. Fetch order belonging to account B",
      },
    });

    await loginViaUi(page, E2E_USER);

    const shots: [string, string][] = [
      ["overview", "/overview"],
      ["programs", "/programs"],
      ["scope", `/programs/${program.id}`],
      ["research", "/research"],
      ["findings", "/findings"],
      ["traffic", "/traffic"],
      ["endpoints", "/endpoints"],
      ["recon", "/recon"],
    ];

    for (const [name, path] of shots) {
      await page.goto(path);
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `../docs/screenshots/${name}.png` });
    }
  });
});
