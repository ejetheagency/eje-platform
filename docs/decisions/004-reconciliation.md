# 004 · Reconciliation: the four new addendum docs vs. existing code

Date: 2026-10-02. Scope: where `DREAM_TEAM_STACK.md`, `PIVOT_ENGINE.md`, `TREASURY.md`,
`SELF_SERVE_ONBOARDING.md` conflict with code that already exists. **No code changed in this step.**
This cites `docs/decisions/002-grounding-2026-10-02.md` and only adds what 002 does not already cover.
Default resolution (operator): **keep the code's names, update the docs to match**, unless the doc's name
is clearer. The last section says which (none, with one noted caveat).

## 1. Naming conflicts

| # | Doc name | Code name (path) | Keep | Reason |
|---|---|---|---|---|
| N1 | `jobs` (DREAM_TEAM §4, master plan §9) | `job_log` (`db/002-factory-schema.sql:235`, `factory/packages/queue.py`) | **code** | Already in 002. Live table; rename buys nothing. |
| N2 | `touches` (OUTREACH_PLAYBOOKS §2) | `engagement_events` (`db/002:145`, extended `db/007`) | **code** | Already in 002 + decision 003 F2 (folded). One event log, not two. |
| N3 | `facts`, `source_fact_id` (PIVOT_ENGINE §2, says it "renames enrichment_findings") | `enrichment_findings` (`db/002:62`); lineage col will be `source_finding_id` (STEP 3) | **code** | NEW. Renaming a live 302-row table + every writer/reader for zero functional gain; "finding" already fits. STEP 3 adds `source_finding_id`, not `source_fact_id`. |
| N4 | `pivot_runs` (PIVOT_ENGINE §5) | `strategy_runs` (`db/002:175`) | **code** | NEW. STEP 4 persists to `strategy_runs` with `strategy = provider or pivot_name`. One "what a run produced" table generalizes both. |
| N5 | `/packages/pivots/`, `/packages/providers`, `packages/llm_router` (PIVOT_ENGINE §8, DREAM_TEAM §3) | `factory/providers/`, `factory/packages/` (repo root is `factory/`, not `packages/`) | **code** | NEW. Repo layout is `factory/*`. Update the docs' `/packages/...` to `factory/...`. |
| N6 | `cost_ledger` cols `ts, units, unit_cost_usd, cost_usd, was_free_tier, result_status, pivot_name, lead_id` (TREASURY §2) | `cost_ledger` cols `provider, client_id, company_id, job_type, credits_used, usd_cost, estimated, created_at` (`db/002:211`) | **code** | NEW. Keep `created_at`/`usd_cost`/`credits_used`. `was_free_tier`/`result_status`/`pivot_name` are net-new columns to ADD only if a step needs them, not renames. |
| N7 | `budgets` table (TREASURY §2) | `config/budgets.json` file (`factory/config/budgets.json`) | **code (file)** | NEW. Caps live in config per master plan §13. A live-editable mirror table is optional future work, not a rename. |
| N8 | `metrics_daily` / `metrics_finance_daily` (DREAM_TEAM §1, TREASURY §2) | (none exist) | n/a | NEW. Pure gap, not a conflict; net-new tables if those metrics are built. |
| N9 | `provider_accounts` rich schema (quota_free/paid, used_free/paid, rate_limit_rpm/rpd, cooldown_until, …) (TREASURY §2) | `provider_accounts` = `provider, credits_remaining, monthly_cap_usd, meta, updated_at` (`db/002:225`) | **code** | NEW. Expansion, not rename. The richer columns are the allocator's future need (not this sprint). |

## 2. Structural conflicts (design, not naming)

- **S1 · `budget.can_spend`/`log_cost` vs `treasury.acquire`/`settle` (TREASURY §3).** Code (`factory/packages/budget.py:36,56`) is a pre-check + post-log where the **caller picks the provider** (the `cheap_llm.py` ladder, or a single-provider paid adapter with worker-level cascade in `tier2.py`). The doc wants a capability-based **allocator that chooses the provider by live headroom** (free-before-paid across providers) with reservations/Grants/settle. **Decision: keep `can_spend`/`log_cost` for this sprint** (STEP 1b only adds the two missing gates per 002 §3). `acquire/settle` is the TREASURY target state, additive (it can wrap `can_spend` + provider selection) and belongs to a later phase, not a rename to make now. This is the one the operator flagged; I would **not** rename, I would **defer** the allocator.
- **S2 · Deployment model.** Docs assume Supabase Queues (pgmq) + pg_cron + Edge Functions (DREAM_TEAM §4, TREASURY §7). Code uses `job_log` + `factory/packages/queue.py` (custom `claim_job`, `db/004`) + a Railway always-on container self-scheduling (`factory/service.py:11`), per 002. **Decision: keep `job_log` + Railway** (built, deployed, working); treat pgmq/pg_cron/Edge as an unmade alternative. Update docs to describe the Railway+job_log reality or mark it an open decision.
- **S3 · Pivot architecture.** PIVOT_ENGINE models pure pivot operators over a fact graph; code is tiered **workers** (`factory/workers/*`) calling **provider adapters** (`factory/providers/*`), with no fact-to-fact edges (002 §2a: no lineage field). **Decision: not resolvable by renaming.** STEP 3 (lineage columns) is the first brick toward the graph; the full `pivot_worker` loop + pivots registry is net-new and a later phase.
- **S4 · `activate_client` signature.** Doc: `onboarding.activate_client(client_id)` reads an existing ICP, enqueues discovery, schedules the report (SELF_SERVE §2/§7). Code: `factory/workers/onboarding.py activate_client(client_id, name, brief, …, apply)` dual-writes `clients` + `icps`. **Decision: keep the one name `activate_client`** (matches); converge behavior so it also enqueues first discovery + schedules the report (today the `provision_client` worker does the discovery, `runner.py _h_provision_client`). Minor.
- **S5 · `icps` structure.** Doc: nested schema (`company`/`contact`/`signals`/`volume`/`channels`/`offer`, SELF_SERVE §3). Code: flatter `icps` (`brief, voice, decisor_role, geos, sectors, signals, discovery_queries, playbook_id, config`, `db/009`). **Decision: keep the code table**; the nested fields map into it (+ the `config` jsonb catch-all). Structured refinement is SELF_SERVE phase 1/5, not this sprint.
- **S6 · Stripe subscriptions / customer IDs.** Doc assumes Stripe customer + subscription IDs stored on `clients` (SELF_SERVE §2). Code stores neither (002 §4: customer creation + subscriptions MISSING); only the webhook + `provision_client` exist. **Decision: out of scope by the operator's own instruction** ("Stripe subscriptions and self-serve are NOT in this sprint… webhook + provision_client are enough for the next ten clients paid by link"). Agreement on the rule that matters: code never self-computes "has paid" (002 §4 confirms it reads webhook-written state only).

## 3. The seven pre-existing docs

| Doc | Status | Action |
|---|---|---|
| `ARCHITECTURE.md` | Describes the **legacy surface** (app.html, workspaces, ISEJE, cadence-at-render) accurately; silent on the factory. | Keep; add a header note that it covers the legacy client surface only. |
| `CRM-PROJECT.md` | **Superseded** build-spec (2026-09-30 "rebuild into multi-tenant CRM"); its vision is now carried by the master plan + the four sprint docs. | **Archive** under `docs/archive/` (STEP 5). |
| `DATA-ASSETS.md` | **Accurate**: inventory of the retained productora data asset (932 leads, `unabase_default`). | Keep. |
| `DATA-CONTRACT.md` | Describes the **legacy surface** data contract (the `leads` table, 1000-row cap, anon key in app.html). Accurate for what runs today. | Keep; scope-note as legacy surface. |
| `ENGINE-INTEGRATION.md` | **Superseded**: maps the older standalone engine scripts (`orchestrator.py`, `enrichment-gate.py`, `reconcile-sends.py`) that predate `factory/`; replaced by DREAM_TEAM_STACK + the factory build. | **Archive** under `docs/archive/` (STEP 5). |
| `SEGUIMIENTO-PLAN.md` | Describes a **shipped legacy feature** (Seguimiento, `tracked_leads`/`tracked_lead_notes`, 12/28 rows live). Accurate; not touched by the sprint docs. | Keep. |
| `STAGING-SETUP.md` | **Accurate as a guide** (one-time staging setup checklist). Whether staging was actually created is unverified. | Keep. |

## 4. What I would change (operator's addition 2)

**Adopt the operator default everywhere: keep every code name, update the four new docs to match**, specifically: `job_log` (not jobs), `engagement_events` (not touches), `enrichment_findings`/`source_finding_id` (not facts/source_fact_id), `strategy_runs` (not pivot_runs), `factory/providers` + `factory/packages` (not `/packages/*`), `cost_ledger.(created_at|usd_cost|credits_used)` (not ts/cost_usd/units), `config/budgets.json` (not a `budgets` table).

**Doc names I would adopt over code: none.** One caveat worth recording: `facts` + a pivot abstraction is conceptually cleaner than `enrichment_findings` + provider/worker, but only on a greenfield; it does not justify renaming a live table and rewriting every writer. If the pivot engine is built, add it as a thin layer over the existing tables (lineage columns on `enrichment_findings`, strategy/pivot name on `strategy_runs`), not as a rename.

**Net:** the only true blockers for the sprint are the two STEP-1b gates (S1, already code-change work in STEP 1) and the lineage columns (STEP 3). Everything else here is a doc-text update (keep-code-name) or a later-phase delta, not a change to make now.
