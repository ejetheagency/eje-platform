# Session state (single source of current truth)
Updated: 2026-10-04. Read this first. Update it when you change state. Keep it one page. Rules: `docs/WORKING_RULES.md`.

## What this is
EJE's enrichment factory: an autonomous, cost-governed backend that runs nightly on Railway (09:00 UTC) and turns a client ICP into verified, pitch-ready leads with no human in the loop. North star: `docs/ENRICHMENT_MASTER_PLAN.md`. Pivot/verification spec: `docs/PIVOT_ENGINE.md` (§4b = two-gate verification).

## Clients (discovery reads `clients.icp_config` only)
- `2uplatam` — first paying client, go-live ~Oct 7. Stays on the LEGACY surface; do not migrate it. 21 READY as of 2026-10-03 (audit: `docs/audits/2uplatam-ready-2026-10-03.csv`).
- `eje` — EJE's own outreach + product.
- `altavia` — DEMO, one week, no payment. Bilingual LatAm VAs for US/CA small service businesses. Profile: `docs/clients/CLIENT_ALTAVIA.md`, brief: `docs/clients/ALTAVIA_BRIEF.md`. Demo setup call Sun 10:00 Santiago, starts Mon. Caps: $10 USD (per-client), demo. language=en. **Status 2026-10-04: 12 READY** (was 5; the homepage-first pivot-1 upgrade promoted 7 more) = 2 factory-found (RC Dental, Hill Heals Chiro) + 3 seeded from Codex's 10 contacts (Romy Jurado, Tristan Jagroop, Louis Berk; all deliverable + English pitch). 40 discovered, 36 PARKED (34 no-named-decisor: US sites rarely name the owner, which is the Gate-A / seed gap). Codex's other 7 contacts: 4 catch-all email + 3 ICP caveats, in the enrichment queue (see Codex analysis). Seed file: `seeds/altavia.csv`.

## Live on prod (origin/main @ 1b2b604; Railway auto-deployed, next run 09:00 UTC)
- Verification is a pipeline step (`verify` worker): MillionVerifier primary, Hunter secondary. Only this step sets `email_verified_at`. SMTP ~82% unknown on small LatAm domains; reliable on US domains.
- Treasury: `budget.can_spend` gates every paid call (kill switch, global monthly cap $200, per-provider cap + credits, and NOW a per-client cap from `icp_config.spend_cap_usd`). `night_credit_cap=100` is a HARD per-UTC-day stop in the verify worker.
- Pool-floor: nightly sizes discovery to `ready_leads_per_day x ready_pool_days(7)`, logs per client, alerts under 50% two nights.
- Seed import (item 6): drop `seeds/<client>.csv` -> nightly pushes each row through the normal chain (facts `source_type=operator_seed`, each field tagged with the pivot that would have found it). Nothing skips a gate. LIVE.
- Composer: Spanish by default; English path when `icp_config.language=="en"`.
- Pivot 1 (`site_decisor`) is now homepage-first: JSON-LD Person/Org + mailto + Cloudflare cfemail decode on RAW html before the LLM, + phone capture. Measured 2.5x lift in named decisors on US sites (6->15 of 40). Next refinement: prefer a domain-matched email (one stray off-domain pick observed).
- Gates now include: email_verified with VERIFIED_SOFT (catch-all whose identity is corroborated by Gate A or operator_seed passes, flagged) + a channel-bar gate (`icp_config.channels={min,required}`; default min 2 + instagram required for IG-native sectors; altavia = min 2, required []). Per-client USD cap via `icp_config.spend_cap_usd`. night_credit_cap=100 is a hard per-UTC-day stop.

## Gate A (free corroboration, PIVOT_ENGINE §4b) — BUILT, DOMAIN-SCOPED, NOT WIRED
- `factory/workers/gate_a.py`: find a name (pivot 1 first-party site; else pivot 4 domain-scoped forward search), corroborate by domain/locale (pivot 19/20), brand-name guard (global/single-word names need a first-party source), small-company relaxation. Handler registered; NOT enqueued in the live chain yet.
- Pending operator review: 12-lead scoped hand check (incl. re-run of the two purged test names LEDVANCE and Aura). Only after OK: wire `gate_a` IN FRONT of tier2 (free loop first; tier2 paid only when gate_a yields no name/email and score justifies), then run the PARKED backlog.

## Known gaps (what the factory does NOT do yet)
- No ICP company gates enforced in code: geography (US/CA), industry allowlist, locations <=2, employees 1-50, franchise/chain/DSO/ACA exclusions. Geography is query-text only. Only 6 data-presence gates run (company_name, web_presence, decision_maker, email_deliverable, email_verified, contact_channel).
- Per-client USD cap exists; MillionVerifier CREDITS are still a global pool (not capped per client). night_credit_cap bounds the nightly total.
- Email-pattern pivot (7/16/8) NOT built: named leads without an email are the next bottleneck (next build after Gate A wiring).

## 48-hour order (operator, 2026-10-04)
1. 12-lead scoped Gate A hand-check -> operator reviews TODAY. (Done: `gate_a.run(.., dry_run=True)` added so the hand-check mutates nothing. A dry-run already caught + fixed a bug: the company select referenced a non-existent `companies.city` column, which would have broken Gate A for every client.)
2. ON OPERATOR OK: wire `gate_a` in front of `tier2` before tomorrow's 09:00 UTC run. FREE LOOP FIRST; tier2 only when Gate A ends with no name OR no email candidate. Run the **2upLatam PARKED backlog first**.
3. Email-pattern pivot (infer from a known domain email / MX provider, generate candidates, Gate B only when report-bound) so named-no-email leads reach READY. TARGET: live before **Tuesday night's run**, so Wednesday's launch has two nights of both Gate A + the pivot.
4. Learning repair: WAITS until after Oct 7 (needs reply data, none exists yet). Plan below.
5. (later) ICP-aware scoring; backend expiry-enforcement cron for Altavia (membership revocation on `demo_expires`).

### Wednesday-morning deliverable (Fernando's first report)
2upLatam READY count, named-via-Gate-A count, and channels per lead.

### Learning-repair plan (post-Oct-7; do not lose) — fixes the verified autonomous-learning gap
The factory's cross-agent learning is NOT implemented (see `docs/audits/altavia-factory-challenge-2026-10-04.md`, `[[feedback-factory-autonomous-learning-gap]]`). Repair, phased:
1. **Shared store** `route_findings` (route, lesson, evidence_url, yield_metric, by_agent, ts) agents write after each run.
2. **Route registry + selector**: discovery/enrichment become named routes (places, homepage-first, archive, interview-block); a selector reweights routes from logged yield WITHOUT human edits. Rollback: a flag pins the current fixed pipeline.
3. **Instrument the 3 rates** per route per run: raw records/retrieval-sec, distinct public-ICP decisor/end-to-end-min, deliverable/processing-min. Makes the factory-vs-manual comparison answerable.
4. **Measured rerun**: a fresh US cohort through the factory vs a matched manual run; success = factory >= manual on deliverable-ICP/end-to-end-min, or a documented reason. Needs the reply data that starts accumulating after Oct 7.

## Daily report format owed each morning
Pool-floor line per client, 2uplatam READY, credits used, verified/soft/unknown, alerts, named-via-gate_a count, and the 12-lead hand check when run.
