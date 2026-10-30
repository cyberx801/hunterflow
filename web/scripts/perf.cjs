const { chromium } = require("@playwright/test");

const BASE = "http://localhost:3000";
const PATHS = ["/login", "/overview", "/assets", "/findings", "/research", "/monitoring", "/recon"];

(async () => {
  const browser = await chromium.launch();

  // Log in once and reuse the session, but measure each page in a fresh context
  // (cold cache) so the JS transfer numbers are meaningful.
  const loginCtx = await browser.newContext();
  const loginPage = await loginCtx.newPage();
  await loginPage.goto(`${BASE}/login`);
  await loginPage.getByLabel("Username").fill("researcher");
  await loginPage.getByLabel("Password").fill("a-strong-passphrase");
  await loginPage.getByRole("button", { name: /sign in/i }).click();
  await loginPage.waitForURL(/\/overview/);
  const state = await loginCtx.storageState();
  await loginCtx.close();

  console.log("page            TTFB   DCL   load   JS reqs   JS KB   total KB");
  for (const path of PATHS) {
    const ctx = await browser.newContext({ storageState: path === "/login" ? undefined : state });
    const page = await ctx.newPage();
    await page.goto(`${BASE}${path}`, { waitUntil: "load" });
    await page.waitForLoadState("networkidle");
    const m = await page.evaluate(() => {
      const nav = performance.getEntriesByType("navigation")[0];
      const res = performance.getEntriesByType("resource");
      const scripts = res.filter((r) => r.initiatorType === "script" || r.name.includes(".js"));
      const sum = (arr) => arr.reduce((a, r) => a + (r.transferSize || 0), 0);
      return {
        ttfb: Math.round(nav.responseStart - nav.startTime),
        dcl: Math.round(nav.domContentLoadedEventEnd - nav.startTime),
        load: Math.round(nav.loadEventEnd - nav.startTime),
        jsCount: scripts.length,
        jsKB: Math.round(sum(scripts) / 1024),
        totalKB: Math.round(sum(res) / 1024),
      };
    });
    console.log(
      `${path.padEnd(14)} ${String(m.ttfb).padStart(6)} ${String(m.dcl).padStart(5)} ${String(m.load).padStart(5)} ${String(m.jsCount).padStart(8)} ${String(m.jsKB).padStart(7)} ${String(m.totalKB).padStart(9)}`
    );
    await ctx.close();
  }
  await browser.close();
})();
