# 001 · Global Data Model (Phase 1 backbone)

Date: 2026-10-01. Design only, **not yet applied**. DDL: `db/002-factory-schema.sql`.
Implements `ENRICHMENT_MASTER_PLAN.md` §9 (data model) + §4 (lead state machine), plus the dream-team
stack's needs (signals, email cost-cascade, findings board). Decision confirmed: design now, migrate in Phase 1.

## The one idea that drives the whole shape: two zones
1. **Global pool** (`companies`, `contacts`, `enrichment_findings`, `signals`, `assets`): shared across all
   clients, enriched **once**, reused many times. This is the #1 cost lever (a company 40 clients target is
   enriched once). **Clients never see the pool directly** (the library model) — access is only through the
   service-role `/api`. RLS on these tables = admin-only; workers use the service key (bypasses RLS).
2. **Per-client** (`client_leads`, `gate_results`, `engagement_events`, `reports`, owned `templates`): a client's
   pipeline + results. RLS = tenant-scoped, reusing `auth_is_admin()` / `auth_client_ids()` from the isolation step.

`client_leads` is the hinge: it links a client to a company with a **lifecycle state** and the chosen decision-maker.
It replaces the per-client meaning of today's flat `leads` table.

## The lead state machine (the backbone to build/test first)
States live on `client_leads.state` (CHECK-guarded in the DB, enforced in a `lead_state` code module):
`DISCOVERED → T1_ENRICHING → SCORED → (DISCARDED | GATE_CHECK | T2_ENRICHING) → GATE_CHECK → (READY | back to
T1 with missing-fields | T3_REASONING) → READY → DELIVERED`, with `PARKED` at max cycles. Gate failures record
**which fields are missing** (`gate_results.missing_fields`) so the next pass only re-does the gap, never the whole lead.

## Cost governance is in the schema, not bolted on
`cost_ledger` logs every external call; `provider_accounts` holds balances/caps. `can_spend(client, provider, est)`
reads both + the plan budget before any paid call. The email cost-cascade (free → pattern → Reacher → Icypeas →
Prospeo → Hunter → Apollo) is just `contacts.email_status`/`email_source` advancing, each paid step gated by `can_spend`.

## The north-star metric is wired in
`engagement_events` (viewed/contacted/replied/positive_reply/meeting/won) feeds "positive replies per 100 delivered."
`strategy_runs.reply_outcome` is backfilled from it, so strategies are scored by replies-per-dollar, not data-found.
`signals` (Signal Spotter) is the "why-now" layer that lifts those replies.

## Mapping from the current `leads` table (1,091 rows)
Today: one flat `leads` row per (client, company), keyed by domain, with a `lead_data` JSONB blob. Migration splits each row:
- → **`companies`** (dedup by `dedupe_key`: `domain`, else `ig:<handle>`, else `name:<norm>|<country>`). Pulls
  company/country/industry/website/instagram/linkedin + `lead_data.logo`→`assets`. The dedupe_key is what lets
  domain-less IG-only pymes exist (fixes the "no domain ⇒ dropped" bug the audit flagged).
- → **`contacts`** (contact_name/email/phone + `lead_data.additionalContacts[]`), with `email_status` seeded from
  how it was sourced.
- → **`client_leads`** (one per original row): `client_id`, `company_id`, chosen `contact_id`, `state` mapped from
  the old `status` (none→DISCOVERED… contacted/replied/meeting→DELIVERED-ish), `score`, `ready`/`hold_reason` from
  `lead_data` flags, and **`legacy_lead_id` = the old `leads.id`**.
- **Outreach history stays intact:** `messages_sent` / `status_history` / `actions` / `notes` currently key by
  `lead_id` (= old `leads.id`). They keep pointing at `legacy_lead_id` (no rewrite needed); a view joins them to
  `client_leads`. `tracked_leads` / `tracked_lead_notes` (manual Seguimiento) are **left untouched** (they're
  hand-entered relationships, not discovered pool companies).

Migration is a one-time backfill script (service key), idempotent, run in Phase 1 after the schema is applied on a
branch/test first. The old `leads` table is kept read-only until the app's reads are cut over, then retired.

## ICPs
Staying in `clients.icp_config` (JSON) for now rather than a separate `icps` table — the Python engine is already
config-per-client. Add an `icps` table only when a client needs multiple ICPs. `client_leads.icp_id` is reserved for that.

## RLS summary
- Per-client tables: `tenant_*` policies (admin all, member own) — same pattern as the isolation step.
- Global pool + treasury + jobs: `admin_*` policies only → members get nothing; workers use service_role.
- Templates: owner sees own, everyone sees `shared=true`; `template_stats` readable (min-sample gated in the app).

## Phase-1 CORE subset (what we actually stand up first)
Enough to satisfy the plan's Phase-1 "done when a test job moves a lead through states and logs a cost":
`companies`, `contacts`, `client_leads` (+ state machine), `enrichment_findings`, `cost_ledger`, `provider_accounts`,
`gate_results`, `job_log` (+ pgmq queues). **Later phases:** `signals` (Phase 2 w/ Signal Spotter), `strategies`/
`strategy_runs` + `engagement_events` (Phase 4 learning), `templates`/`template_stats` (Phase 6), `reports` (Phase 5).
The DDL defines them all now so the schema is coherent; we only populate what each phase needs.

## Open questions for the founder (not blocking the design)
1. **Confirm pgmq** as the queue (vs a plain `jobs` table we poll). Recommendation: pgmq (native, durable, you're on Supabase).
2. **Dedupe collisions:** two real companies sharing a domain (rare) or domain-less near-duplicates. Recommendation:
   domain wins; domain-less dedup by IG handle first, then fuzzy name+country with a manual-merge admin tool later.
3. **Keep the old `leads` table** as a frozen archive after cutover, or migrate-then-drop? Recommendation: freeze, don't drop.
