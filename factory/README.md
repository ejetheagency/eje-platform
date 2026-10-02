# EJE Enrichment Factory

The backend factory (supply side) that feeds the client app. North star: `docs/ENRICHMENT_MASTER_PLAN.md`.
Decisions: `docs/decisions/`. Schema: `db/002-factory-schema.sql` (applied). EJE-only, built on the Python
cost-governor engine. Workers use the **service key** (bypass RLS); clients never see the global pool.

## Layout
```
factory/
  packages/
    db.py          service-key Supabase access (retries, Conflict, rpc)
    lead_state.py  THE lead state machine (single source of transition rules)
    budget.py      Treasury: can_spend() + log_cost()  (reads config/budgets.json)
    queue.py       durable job queue on job_log + atomic claim_job()
  providers/        one file per external API (can_spend -> work -> finding -> log_cost)
    site_enrich.py  free site scrape (email/IG/LinkedIn/phone)
    gemini.py       cheap-LLM brief (existing GEMINI_API_KEY)
    logo.py         logo via unavatar (free)
    [todo]          groq, cerebras, serper, google_places, brandfetch, icypeas/prospeo/hunter/apollo, signal_spotter
  workers/
    gates.py        quality gates -> gate_results -> route state (READY / re-enrich / PARKED)
    runner.py       claim -> dispatch -> complete/fail (retry + dead-letter). HANDLERS map per department.
  config/
    budgets.json    plan budgets + caps (kill switch, global cap)
    capacity.json   cost-model assumptions
  capacity_model.py cost/capacity calculator
  migrate_leads.py  one-time backfill: old leads -> global pool + client_leads
  test_phase1.py / test_queue.py / test_providers.py / test_gates.py   acceptance tests (all PASS)
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
and `-> PARKED` at max cycles. Every paid call is gated by `budget.can_spend` and logged to `cost_ledger`.

## Status: Phase 1 foundations DONE + proven. Next: real providers (need keys, see docs/decisions/002-providers.md),
the scheduler (D0) to enqueue nightly jobs per active client, and the learning loop (D3).
