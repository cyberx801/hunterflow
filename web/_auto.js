const { request } = require("@playwright/test");
const BASE = "http://localhost:3000";
(async () => {
  const ctx = await request.newContext({ baseURL: BASE });
  await ctx.post("/api/v1/auth/login", { data: { username: "researcher", password: "a-strong-passphrase" } });
  const me = await (await ctx.get("/api/v1/auth/me")).json();
  const h = { "X-CSRF-Token": me.csrf_token };
  const programs = await (await ctx.get("/api/v1/programs")).json();
  const program = programs.items[0];

  const s = await ctx.post("/api/v1/schedules", {
    headers: h,
    data: {
      program_id: program.id,
      profile: "web_inventory",
      interval_minutes: 60,
      targets: ["http://demo.local:8080"],
      notify: false,
      auto_cards: true,
    },
  });
  const schedule = await s.json();
  console.log("schedule:", s.status(), "auto_cards:", schedule.auto_cards);

  const run = await ctx.post(`/api/v1/schedules/${schedule.id}/run-now`, { headers: h });
  const job = await run.json();
  console.log("run-now:", run.status(), job.job_id?.slice(0, 8));

  let status = "queued";
  for (let i = 0; i < 45; i++) {
    await new Promise((r) => setTimeout(r, 5000));
    const d = await (await ctx.get(`/api/v1/jobs/${job.job_id}`)).json();
    status = d.status;
    if (["completed", "failed", "cancelled"].includes(status)) {
      console.log("job:", status, d.error_code ?? "");
      console.log("runs:", (d.tool_runs || []).map((t) => `${t.tool}=${t.status}`).join(" "));
      break;
    }
  }

  const cards = await (await ctx.get(`/api/v1/research?program_id=${program.id}&page_size=100`)).json();
  const auto = cards.items.filter((c) => (c.title || "").includes("new endpoint") || (c.title || "").includes("new JS"));
  console.log("auto cards:", auto.length, auto.slice(0, 5).map((c) => c.title));
  const events = await (await ctx.get(`/api/v1/monitoring/events?program_id=${program.id}&kind=new_endpoint`)).json();
  console.log("new_endpoint events:", events.length, events.slice(0, 5).map((e) => e.entity_value));
  await ctx.dispose();
})();
