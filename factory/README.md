# EJE Enrichment Factory

The backend factory (supply side) that feeds the client app. North star: `docs/ENRICHMENT_MASTER_PLAN.md`.
Decisions: `docs/decisions/`. Schema: `db/002-factory-schema.sql` (applied). EJE-only, built on the Python
cost-governor engine. Workers use the **service key** (bypass RLS); clients never see the global pool.

## Layout
```
factory/
  packages/
    db.py          service-key Supabase access (retries, Conflict, rpc, count, select_all)
    lead_state.py  THE lead state machine (single source of transition rules)
    budget.py      Treasury: can_spend() + log_cost() + forecast()  (config/budgets.json)
    queue.py       durable job queue on job_log + atomic claim_job()
  providers/        one file per external API (can_spend -> work -> finding -> log_cost)
    site_enrich.py  free site scrape (email/IG/LinkedIn/phone)
    gemini.py       cheap-LLM brief (existing GEMINI_API_KEY)
    logo.py         logo via unavatar (free)
    signal_spotter.py  free "why-now" signals (hiring/expansion) -> signals table
    [need keys]     groq, cerebras, serper, google_places, brandfetch, icypeas/prospeo/hunter/apollo
  workers/
    runner.py       claim -> dispatch -> complete/fail (retry + dead-letter). HANDLERS per department.
    scheduler.py    D0: enqueues the next job per lead state (cron-agnostic tick)
    scoring.py      completeness + signals + ICP fit -> score -> route (DISCARD / GATE_CHECK)
    gates.py        quality gates -> gate_results -> route (READY / re-enrich / PARKED)
    reports.py      D9: precompute per-client READY report -> reports table (app-reads-only)
    learning.py     D3: replies-per-100 (north star) + strategy results-per-dollar
    admin.py        ops snapshot (queue, states, spend, gate pass rates, replies-per-100)
  config/
    budgets.json    plan budgets + caps (kill switch, global cap)
    thresholds.json scoring weights + discard/tier2 thresholds
    capacity.json   cost-model assumptions
  capacity_model.py cost/capacity calculator
  migrate_leads.py  one-time backfill: old leads -> global pool + client_leads (idempotent)
  test_*.py         acceptance tests: phase1, queue, providers, gates, e2e (all PASS)
```

## Run (from the repo root)
```
python3 -m factory.test_phase1       # state machine + budget + ledger
python3 -m factory.test_queue        # queue claim/dispatch/complete
python3 -m factory.test_providers    # real site_enrich + gemini + logo (isolated, cleans up)
python3 -m factory.test_gates        # gate routing
python3 factory/capacity_model.py    # cost table
python3 -m factory.migrate_leads             # migration dry-run
python3 -m factory.migrate_leads --apply     # migration execute
python3 -m factory.workers.runner    # drain the job queue once
```

## How a lead flows
`DISCOVERED -> T1_ENRICHING (site_enrich + gemini) -> SCORED -> GATE_CHECK (gates.py)
-> READY -> DELIVERED`, with `GATE_CHECK -> T1_ENRICHING` re-enriching only the missing fields,
and `-> PARKED` at max cycles. Every paid provider call is gated by `budget.can_spend` before spending
(free adapters log at $0); costs go to `cost_ledger`, and per-call price estimates live in `config/prices.json`.

## Status
Phase 1 DONE + proven. Departments standing: scheduler (D0), Tier-1 enrich (D2: site+gemini+signals+logo),
scoring, gates (D5), reports (D9), learning (D3), Treasury (D8: can_spend + forecast), admin observability.
A lead flows DISCOVERED->READY autonomously through the queue (test_e2e PASS). 1,128 companies + 2,004 contacts
migrated; the old `leads` table is kept frozen for reversibility.

Next (needs keys, see docs/decisions/002-providers.md): real Discovery (Google Places/Serper), the email
cost-cascade (Icypeas/Prospeo/Hunter/Apollo) + Tier-2 escalation, extra cheap-LLM providers (Groq/Cerebras),
Brandfetch logos, and deploying the scheduler on a cron. Then wiring the app to read the precomputed `reports`.

## Safety note for whoever runs SQL here
In Postgres `LIKE`, `_` is a single-char wildcard. `client_id LIKE '__%'` matches EVERYTHING. Scope deletes by
exact match or `dedupe_key LIKE 'TEST:%'` (literal), and prefer the service-key REST layer (which filters by eq.)
over raw SQL for row deletes.
