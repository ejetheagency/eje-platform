# Factory Deployment

The factory is plain Python (stdlib only) + Supabase. Two processes:

## 1. The night shift (deploy this)
**`factory/service.py`** is the always-on service (self-schedules `run_nightly` daily, exposes `/` health +
`/run` manual trigger). `factory/railway.json` has the deploy config. Start command: `python3 -m factory.service`.
- **Railway (recommended, matches our existing pattern):** new service pointing at the `unabase-app` repo,
  Nixpacks, start `python3 -m factory.service`, healthcheck `/`. Set `FACTORY_RUN_HOUR_UTC` (default 9 ≈ 06:00 Chile).
- Run `python3 -m factory.run_nightly` directly for a one-off (idempotent, safe anytime).
- `GET /run` on the deployed service triggers a run on demand (to test the deploy).

## 2. The worker (optional, for throughput)
`python3 -m factory.workers.runner` drains the queue once; `runner.loop()` runs continuously. For low volume,
the night-shift `drain()` is enough. For scale, run N always-on workers (they claim jobs concurrently via
`claim_job()` FOR UPDATE SKIP LOCKED).

## Environment (set in the host, NEVER commit)
Required now: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`.
Lights up more departments when present: `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `SERPER_API_KEY`,
`GOOGLE_PLACES_API_KEY`, `BRANDFETCH_API_KEY`, `ICYPEAS_API_KEY`, `PROSPEO_API_KEY`, `HUNTER_API_KEY`, `APOLLO_API_KEY`.

## Safety
- Workers use the **service key** (bypass RLS) — host-only, never shipped to the browser.
- Kill switch: `config/budgets.json` `kill_switch_paid_spend: true` pauses all PAID calls instantly.
- Spend caps: `monthly_global_spend_cap_usd` + per-provider `monthly_cap_usd` in `provider_accounts`.
- `budget.forecast(provider)` alerts before credits run out (wire to ntfy/email on the cron).

## What I need from you to deploy
1. **Railway access** (or confirm Vercel Cron) to schedule `run_nightly`.
2. The **provider API keys** above (see `docs/decisions/002-providers.md`).
3. Seed `provider_accounts` with real balances/caps so the Treasury forecast + guards are live.
