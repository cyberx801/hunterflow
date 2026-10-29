# Running a local recon demo (no third-party targets)

This is the safe way to see a real scan end to end: HunterFlow scans the synthetic
demo application in this repository, not anything on the internet.

The demo app is deliberately flawed (see `demo/README.md`) and reachable inside the
Docker network as `demo.local:8080`.

## 1. Start the stack with the demo target

```bash
docker compose --profile demo up -d
docker compose ps
```

You should see `hunterflow-demo-1` running.

## 2. Create a program and allow the demo host

In the UI:

1. **Programs → New program** (e.g. "Local Demo").
2. Open the **Scope** tab and add a rule:
   - Kind: **Exact domain**
   - Value: `demo.local`
   - Effect: **Allow**
3. Click **Publish policy version**.

Optional check: paste `http://demo.local:8080/` into **Scope preview** and confirm it is
*allowed*.

## 3. Run the scan

**Recon → New scan**:

- Profile: **Web Inventory** (`subfinder` → `httpx` → `katana`)
- Targets: `http://demo.local:8080`
- Dry run: off

Start the scan. The job detail shows each tool run, its arguments, exit code, and output.
`subfinder` receives the bare host `demo.local` (it cannot take a URL), while `httpx` and
`katana` receive the full URL.

## 4. Look at the results

- **Assets** should contain `http://demo.local:8080`.
- **Endpoints** should contain paths found by the crawler, such as `/`, `/api/v1/version`,
  and `/api/orders`.

From there, open an endpoint and create a research card. The demo's `/api/orders/{id}`
endpoint is intentionally missing an ownership check, so a BOLA research card is a
sensible thing to practise with. Remember: the demo is synthetic; nothing here is a real
vulnerability report.

## If the scan fails

- `TOOL_NOT_FOUND`: the image did not build with the pinned binaries; rebuild with
  `docker compose build worker`.
- The job fails on `subfinder` with a network error: DNS/passive sources are unavailable in
  your environment. Use the **Dry run** option, or run only against hosts you control.

## Dry run instead (no Docker required)

If you only want to see the workflow, tick **Dry run**. It completes immediately, executes
no tools, and shows "Dry run — no tools were executed." in the job detail.
