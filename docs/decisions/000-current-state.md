# 000 · Current-State Map (Phase 0 of the Enrichment Master Plan)

Date: 2026-10-01. North star: `ENRICHMENT_MASTER_PLAN.md` (founder's canonical vision). This is the
Phase 0 deliverable: map what already exists onto the target departments before building. Confirmed by the founder.

## The core reality: two engines exist, we grow ONE
- **Live UnaBase Node engine** (`unabasi-leads/automation/`, Railway, approval-gated). Proven, but UnaBase is a
  FORMER client. **PAUSED 2026-10-01** (`config.paused=true` + `PAUSE.flag`). Reference it, do not extend it.
- **Newer Python "cost-governor" engine** (`unabase-app/scripts/*.py`, Sep 29). Already written department-style,
  config-per-client, EJE-scoped, $0-LLM deterministic orchestrator. **DECISION: this is the go-forward factory, EJE-only.**

## Department status (target → what exists today)
| Dept | Status | Where / note |
|---|---|---|
| D0 Scheduler | EXISTS (UnaBase only, paused) | `unabasi-leads/automation/approval-service.js` self-schedules; EJE has none yet. Factory needs its own. |
| D1 Discovery | PARTIAL / fragmented | `nightly-farm.js` (web_search), `batch-builder.js` (Apollo, keyword-discovery deprecated). No per-ICP config engine. |
| D2 Tier-1 cheap + LLM router | ROUTER EXISTS | `scripts/llm_router.py` (cheapest-first Groq→Gemini→DeepSeek→Sonnet, fallback, cache, meter). Cheap enrichers exist. **Findings board MISSING.** |
| D3 Learning | SEED only | `scripts/classify-response.py` (reply taxonomy). No results-per-dollar strategy scoring; ledger unused for learning. |
| D4 Tier-2 paid APIs | APIS EXIST | Apollo (`enrichment/apollo.js`), Hunter (`enrichment/contactHunter.js`). **Global contact cache MISSING.** |
| D5 Quality Gates | EXISTS (strongest) | `scripts/link-liveness.js`, `dedup-guard.js`, `audit-drafts.js`, `enrichment-gate.py`, IG-verify family. Deterministic; no LLM-for-ambiguous. |
| D6 Tier-3 reasoning | PARTIAL | Premium tier in `llm_router.py`; `daily-run.js` one Anthropic call. **No cap/budget enforcement.** |
| D7 Asset / Logo | PARTIAL | Render-time fallback in `app.html` (stored logo → unavatar → monogram). No standalone fetch/clean/store worker. |
| D8 Treasury | MOSTLY MISSING | Only `cache/llm_ledger.jsonl` (LLM-only). **No `can_spend()`, no credit balances, no burn forecast, no Apollo/Hunter ledger.** |
| D9 Report worker | EXISTS (UnaBase) | `daily-run.js` + `approval-service.js` + `RUN-REPORT-V1.md`. No per-client loop. |
| Lead state machine | MISSING | Flat Supabase `status` string + label map in `app.html`. No FSM module. |
| Job queue | MISSING | "Queue" = pool files + farm-seeds backlog. Candidate: Supabase pgmq. |
| Template library | PARTIAL | One locked first-touch skeleton. Not a selectable multi-template library. |

## Data model gap (the #1 scale lever)
Today: a single flat `leads` table (1,091 rows: company, contact fields, score, status, `lead_data` JSONB, `client_id`),
per-client, keyed by domain. Target (§9): **global** `companies` + `contacts` deduped across clients + `client_leads`
link, plus `enrichment_findings`, `strategies`, `gate_results`, `jobs`, `cost_ledger`, `provider_accounts`, `assets`,
`engagement_events`, `reports`, `templates`. **DECISION: design the global model now, migrate in Phase 1.** Next doc: `001-data-model.md`.

## Hosting / security
- App = Vercel (no crons: `vercel.json` has no `crons` block, no `api/cron/`). Factory workers → Supabase pgmq +
  scheduled runner (Railway pattern already proven).
- **RLS tenant isolation ENFORCED 2026-10-01** (`db/rls-2026-10-01-tenant-isolation.sql`). Consequence: **server-side
  scripts must use the SERVICE key, not the anon key.** The Python engine + a couple of UnaBase ops scripts still inline
  the anon key → they now read 0 rows. Live report pipeline is file-based so it was unaffected; fix = swap to service key
  as we build on the Python engine. (This is a Phase-1 "provider/key" item.)

## Locked decisions (founder, 2026-10-01)
1. Build the factory on the **Python cost-governor engine, EJE-only**. Reference UnaBase Node engine, don't extend.
2. **Design the global data model now, migrate in Phase 1.**
3. **Pause the UnaBase automation.** (Done.)

## Phase 1 entry point (next step)
Per the master plan Phase 1: data model + lead state machine + job queue + provider-adapter pattern + `cost_ledger` +
`can_spend()` + config files. Start with **the data model + state machine** (the backbone the plan says to build/test first),
informed by the "dream team" stack (adds providers + a Signal Spotter + an email cost-cascade; see `DREAM_TEAM_STACK.md`).
Service-key swap folds in here. Done when a test job moves a lead through states and logs a cost.
