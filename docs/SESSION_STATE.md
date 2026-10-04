# Session state (single source of current truth)
Updated: 2026-10-04. Read this first. Update it when you change state. Keep it one page. Rules: `docs/WORKING_RULES.md`.

## What this is
EJE's enrichment factory: an autonomous, cost-governed backend that runs nightly on Railway (09:00 UTC) and turns a client ICP into verified, pitch-ready leads with no human in the loop. North star: `docs/ENRICHMENT_MASTER_PLAN.md`. Pivot/verification spec: `docs/PIVOT_ENGINE.md` (§4b = two-gate verification).

## Clients (discovery reads `clients.icp_config` only)
- `2uplatam` — first paying client, go-live ~Oct 7. Stays on the LEGACY surface; do not migrate it. 21 READY as of 2026-10-03 (audit: `docs/audits/2uplatam-ready-2026-10-03.csv`).
- `eje` — EJE's own outreach + product.
- `altavia` — DEMO, one week, no payment. Bilingual LatAm VAs for US/CA small service businesses. Profile: `docs/clients/CLIENT_ALTAVIA.md`, brief: `docs/clients/ALTAVIA_BRIEF.md`. Demo setup call Sun 10:00 Santiago, starts Mon. Caps: $10 USD (per-client), demo. language=en.

## Live on prod (origin/main @ 1b2b604; Railway auto-deployed, next run 09:00 UTC)
- Verification is a pipeline step (`verify` worker): MillionVerifier primary, Hunter secondary. Only this step sets `email_verified_at`. SMTP ~82% unknown on small LatAm domains; reliable on US domains.
- Treasury: `budget.can_spend` gates every paid call (kill switch, global monthly cap $200, per-provider cap + credits, and NOW a per-client cap from `icp_config.spend_cap_usd`). `night_credit_cap=100` is a HARD per-UTC-day stop in the verify worker.
- Pool-floor: nightly sizes discovery to `ready_leads_per_day x ready_pool_days(7)`, logs per client, alerts under 50% two nights.
- Seed import (item 6): drop `seeds/<client>.csv` -> nightly pushes each row through the normal chain (facts `source_type=operator_seed`, each field tagged with the pivot that would have found it). Nothing skips a gate. LIVE.
- Composer: Spanish by default; English path when `icp_config.language=="en"`.

## Gate A (free corroboration, PIVOT_ENGINE §4b) — BUILT, DOMAIN-SCOPED, NOT WIRED
- `factory/workers/gate_a.py`: find a name (pivot 1 first-party site; else pivot 4 domain-scoped forward search), corroborate by domain/locale (pivot 19/20), brand-name guard (global/single-word names need a first-party source), small-company relaxation. Handler registered; NOT enqueued in the live chain yet.
- Pending operator review: 12-lead scoped hand check (incl. re-run of the two purged test names LEDVANCE and Aura). Only after OK: wire `gate_a` IN FRONT of tier2 (free loop first; tier2 paid only when gate_a yields no name/email and score justifies), then run the PARKED backlog.

## Known gaps (what the factory does NOT do yet)
- No ICP company gates enforced in code: geography (US/CA), industry allowlist, locations <=2, employees 1-50, franchise/chain/DSO/ACA exclusions. Geography is query-text only. Only 6 data-presence gates run (company_name, web_presence, decision_maker, email_deliverable, email_verified, contact_channel).
- Per-client USD cap exists; MillionVerifier CREDITS are still a global pool (not capped per client). night_credit_cap bounds the nightly total.
- Email-pattern pivot (7/16/8) NOT built: named leads without an email are the next bottleneck (next build after Gate A wiring).

## Pending build queue (operator-approved order)
1. 12-lead scoped Gate A hand check -> operator review.
2. Wire gate_a in front of tier2 -> run 2uplatam PARKED backlog -> other clients.
3. Email-pattern pivot (infer from known domain email / MX; Gate B only when report-bound).
4. ICP company gates for altavia-type ICPs (geo/size/location/exclusions).

## Daily report format owed each morning
Pool-floor line per client, 2uplatam READY, credits used, verified/soft/unknown, alerts, named-via-gate_a count, and the 12-lead hand check when run.
