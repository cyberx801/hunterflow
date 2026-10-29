# Monitoring playbook

How to use continuous monitoring as a bug bounty hunter without drowning in noise.

## Cadence

| Profile | Suggested interval | Why |
|---|---|---|
| `passive` | 6–12 hours | cheapest; finds new subdomains from passive sources |
| `light_recon` | daily | adds live host/tech changes |
| `web_inventory` | daily or every 3 days | adds endpoints from crawling |
| `vuln_checks` | weekly, curated templates only | low-noise checks you explicitly chose |

Start with passive. Add profiles when you actually read the results. A schedule you ignore is
worse than no schedule.

## What actually matters

- **New subdomain** — staging builds, forgotten environments, takeover candidates. Highest
  value, lowest volume.
- **New endpoint** — new API routes and admin paths; often shipped without the old guardrails.
- **Tech change** — a host moving to a new stack or WAF; adjust your approach.
- **Removal** — treat as information, not truth. Services flap. HunterFlow only says
  "removed" after two consecutive misses, and even then it is a signal to re-check.

## Triage loop (15 minutes)

1. Open **Monitoring → Changes**, filter to the last day.
2. For each new asset, check scope status. Anything `needs_confirmation` is not yours to test
   until the program's rules cover it.
3. For each interesting endpoint, create a research card from a template and log the next
   action. Do not start testing from the change feed.
4. Mark low-value changes by archiving the card, not by ignoring it silently.

## Noise control

- Notifications are per schedule; turn them off for chatty programs.
- Keep intervals at or above the program's expectations and your own reading speed.
- Don't schedule `web_inventory` on large scopes until you have seen one run's volume. A
  crawl can add thousands of endpoints the first time.
- The first run of a schedule on an existing program will report every asset as new. Expect
  that; the second run is the interesting one.

## Scope hygiene

- When a program updates its policy, edit the scope rules and **publish a new policy
  version**. Scheduled scans snapshot the policy version at creation time.
- If a target is excluded, add a deny rule; deny wins over allow.
- Never widen scope just to make a scan "work". If the target is not authorized, it is not a
  target.

## Safety

- Active profiles make real requests. Only enable them where the program allows automated
  testing and within its rate limits.
- HunterFlow never scans anything outside the effective policy, but third-party tools have
  limits; read `specs/architecture/security.md` §9 before scheduling aggressive scans.
- Notifications are a convenience. Never treat a webhook message as a confirmed finding.
