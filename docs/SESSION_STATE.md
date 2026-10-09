# SESSION_STATE — one page, start here (updated 2026-10-09, after queue item 1)

The single current-truth page. Read this + `docs/PLAN.md` queue, then work. Doctrine = `CLAUDE.md` GOAL block.

## Live now (current truth, deployed + working)
- **RELEASE GATE = just-in-time report assembly** (`factory/workers/release.py`, WIRED in the nightly). Two states,
  one date field: **POOL** = `source_date` NULL (enriched, gate-passed, invisible to the client, re-ranked every
  night, nothing expires) / **REPORT** = one business day / **DELIVERED** = `source_date <= today`, frozen forever.
  Every night, per client: every undelivered dated card goes **back to the pool**, the whole pool is ranked against
  the current ICP, and **only the next business day** is built from the **top 20**. Rules enforced in code:
  **fit >= 60** (never lowered to fill a day), **one person = one card**, **non-university company max 1/report +
  2 overall** (universities exempt), **never padded** (a short report ships short and the funnel email says so).
  Rank = `fit + 4*channels + 2*completeness + freshness`; **fit = the card's own `lead_data.score`** (the one number
  the card shows, golden r11 reads and the ranker sorts by). `publish.py` no longer dates new cards (that leak put
  cards on Hoy the night they were published, which is how a report landed on the Oct 9 holiday).
  **Operator veto:** `python3 -m factory.workers.release 2uplatam --veto <lead_id> "reason"` pulls a card out of the
  report and the pool for good; the next assembly backfills with the next best. A delivered card cannot be vetoed.
  (No veto button in the app yet, CLI only.)
- **Monday 2026-10-12 rebuilt by the gate:** 20 cards, **fit 84-96** (was 20 cards, fit 8-96 with **14 below 60**),
  **12 universities** (was 5). Pool after the rebuild: **76 approved undated**, of which **44 eligible now = 2.2 more
  report days**. Oct 13-15's pre-scheduled cards are back in the pool. **No delivered card moved** (ledger = 51).
- **One source for client counts:** `clientCounts()` in `public/app.html` feeds every Decisores/Hoy/Reporte badge, page header and greeting; recomputes on every view change. **Decisores = 41.** **One person = one card** (dedup by `contactEmail` = ledger key; WA/IG/LinkedIn merged as attributes on the one card). Counts labeled **cliente ve** vs **pipeline**. (deployed `1e247ec`)
- **Vercel git auto-deploy FIXED.** Ignore step is now `git diff --quiet HEAD^ HEAD -- public api vercel.json`; a `git push` to main builds → promotes to **app.ejetheagency.com** on its own (no CLI). Commits that don't touch `public/`/`api/`/`vercel.json` (docs, factory) correctly skip Vercel.
- **Spend rules LIVE** (Railway VERSION `2026-10-09-spend-rules-altavia-off`): serper **≤1000 searches/night**, paid search **only on ICP-passed companies**, **never re-search a pooled domain**, funnel email shows serper count + cost/shipped-lead. Manual Claude sessions = **web-fetch only, no paid APIs**.
- **Altavia OFF** (archived, not deleted; 57 leads kept): no discovery/enrichment/spend/reports/login. Spend = **$0**.
- **Golden 16/17** (`python3 -m factory.checks.golden_2uplatam`; grew by 2 rules this session). r10 (report size),
  r11 (fit<60) and the new r16/r17 now PASS. The 1 FAIL is **r5: 10 cards were delivered on Thu Oct 9, an Ecuador
  holiday** (Independencia de Guayaquil) by the old publish leak. They are in the client's hands + the ledger, so
  the history stands; the root cause is fixed (only the gate dates cards, and only on business days), so r5 cannot
  recur. **r10/r11 are scoped to cards that have not shipped yet** and report the legacy delivered counts honestly
  (22 delivered cards sit below fit 60) — a delivered card cannot be re-scored into the past or recalled.
- **`client_deliveries` ledger** = source of truth for client-facing counts (2uplatam = 41). **Nightly** on Railway `eje-factory` at **06:00 UTC**. **Staging** `2uplatam_staging` = hidden 167-lead clone; changes go there first.

## Known (not yet fixed)
- **`fit.fit_score` understates fit, so the ranker leans on the hand/hybrid scores.** Three real defects found while
  building the gate: (a) geo reads `companies.country`, which is empty for most pooled rows, so a correct Ecuador
  lead loses 20 points; (b) the seniority regex misses real decisor titles (**Decano, Rector, Vicerrector**) and
  gives them the generic +12; (c) an empty `contactTitle` scores 0 seniority even on owner-operated one-person
  businesses. Recomputing from the cards today would drop 38 of 64 eligible cards below 60 and gut the university
  segment, so **fit stays the card's stored `lead_data.score`** and the scorer repair is queued (PLAN item 2b).
- **Monday is 12/20 universities** (allowed: universities are in-ICP with no cap), because the university cards carry
  the highest hand-assigned fit. If that mix is wrong, veto per card or add a per-segment cap (a decision, not a bug).
- **Factory not yet proven to self-produce 20/day** — the deadline. The gate makes the shortfall visible: the funnel
  email now prints the next report's size + fit range + how many days the pool covers, and says SHORT when it is.
- **Replies to 2uplatam not captured in-platform** — they sit in Fernando's inbox (not lost); import = queue item 7.
- **`EJE_USER='scarlett'` hard-coded** (`app.html:1044`) stamps every write; sender identity wrong until queue item 5.

## Vercel cost
Builds are already ~6s and install-free (no package.json/lockfile/node_modules). The $24.78 Build-CPU-Minutes = **`turbo` build machine × ~100 deploys** in 3 days. **Operator will switch turbo → standard manually.** Batch frontend pushes (non-Vercel commits already skip).

## Decisions (standing)
- **Universities IN ICP, no cap / no %.** Company caps apply **only to non-universities**: max 1 per report, max 2 overall.
- **Fit floor = 60.** **20 per business day.** Never pad with low-fit/unshippable; a short day refills to 20 with passing leads.
- **No report is ever pre-scheduled.** A report is assembled the night it ships, from the pool, by the release gate.
  A card with no date is pooled, not lost; a card the client has seen never moves and never vanishes.
- **One person = one card**; channels are attributes on the card, never separate cards.
- **Unabase / Scarlett are FORMER clients and must be purged** (inventory below; purge = queue item 6, only after item 5).

## Unabase/Scarlett footprint (inventory 2026-10-09, for queue item 6)
- **DB:** `eje_productoras` = **931** legacy productora leads. `user_name='scarlett'` stamped on messages_sent 2173/2319, actions 1586/1644, status_history 119/124, sent_actuals 40/40 (from the hard-code — depends on item 5).
- **Static:** 141 `public/*.json` + `reports-manifest.json` (106 batches, client_id=None) + `public/campana-altcanal.html`.
- **Active code:** app.html greeting + Scarlett templates (1219/1224/1235) + `scripts/reset-bounced-status.js`, `apply-bounced-recovery.js`.
- **External names:** Vercel project `unabase-app` (+ `unabase-app.vercel.app`) and local dir `~/claude/unabase-app`. GitHub `eje-platform`, Railway `eje-factory`, Supabase (opaque) already clean.

## Hard rules (non-negotiable; enforced in CLAUDE.md)
1. **One change per session.**
2. **Golden before AND after; any NEW fail → auto-restore from backup + name the broken rule.**
3. **Backup first** (`report_guard <client>`) before any write to a client report.
4. **Staging first** — test on `2uplatam_staging` before production.
5. **Manual Claude sessions: web fetch only, no paid APIs.**
6. **Paid search only on ICP-passed companies; never re-search a pooled company; serper ≤1000/night** (enforced in code).
7. **Client-facing counts come from `client_deliveries` via `clientCounts()`.**
8. **No anon read policies on client data** (ledger stays service_role; app → server endpoint = queue item 9).
9. **No em dashes, ever.**
