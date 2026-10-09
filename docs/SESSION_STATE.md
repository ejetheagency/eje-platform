# SESSION_STATE — one page, start here (updated 2026-10-09, after the Oct 9 leak take-back)

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
  **12 universities** (was 5). Oct 13-15's pre-scheduled cards are back in the pool. Monday's 20 did **not** change
  when the Oct 9 cards returned (r16 PASS: it is still the top 20 of the ranked pool, no re-assembly needed).
  Pool now: **86 approved undated**, of which **65 eligible = 3.2 more report days**.
- **The Oct 9 holiday report is TAKEN BACK (2026-10-09).** All **10** cards the leak published on the Ecuador holiday
  were **never actioned** by Fernando (zero rows in `messages_sent` / `sent_actuals` / `actions` / `status_history` /
  `engagement_events` / `tracked_leads`, all `status=none`; there is **no card-open log**, so "did he open it" is
  **not knowable** and was not counted either way). All 10 were un-delivered: `source_date` → NULL (**pool, invisible
  to the client**), ledger rows deleted, reason logged to `report-backups/undelivered.jsonl`, `approved` kept so the
  gate can re-ship them on a real business day **if they rank**. **1 of the 10 (nadiavaro.com, fit 81) is eligible now;
  9 sit pooled below the fit floor.** **Decisores 51 → 41.** Golden **18/18, r5 PASS** (new rule r18).
  `release.undeliver` / `undeliver_date` **refuse** to take back a card the client acted on, whatever dated it.
- **Ledger bug fixed in the same change:** `deliveries.delivered_leads` tested `(source_date or "") <= today`, and
  `"" <= today` is TRUE in string order, so the **whole invisible pool read as delivered**. Tonight's
  `sync_all()` would have written **55 pooled cards** into the ledger (Decisores 41 → ~96) and frozen the pool as
  "delivered". Now it requires a non-empty date. Without this the take-back would have been undone at 06:00 UTC.
- **One source for client counts:** `clientCounts()` in `public/app.html` feeds every Decisores/Hoy/Reporte badge, page header and greeting; recomputes on every view change. **Decisores = 41.** **One person = one card** (dedup by `contactEmail` = ledger key; WA/IG/LinkedIn merged as attributes on the one card). Counts labeled **cliente ve** vs **pipeline**. (deployed `1e247ec`)
- **Vercel git auto-deploy FIXED.** Ignore step is now `git diff --quiet HEAD^ HEAD -- public api vercel.json`; a `git push` to main builds → promotes to **app.ejetheagency.com** on its own (no CLI). Commits that don't touch `public/`/`api/`/`vercel.json` (docs, factory) correctly skip Vercel.
- **Spend rules LIVE** (Railway VERSION `2026-10-09-spend-rules-altavia-off`): serper **≤1000 searches/night**, paid search **only on ICP-passed companies**, **never re-search a pooled domain**, funnel email shows serper count + cost/shipped-lead. Manual Claude sessions = **web-fetch only, no paid APIs**.
- **Altavia OFF** (archived, not deleted; 57 leads kept): no discovery/enrichment/spend/reports/login. Spend = **$0**.
- **Golden 18/18 PASS** (`python3 -m factory.checks.golden_2uplatam`; grew to 18 rules). **r5 now PASSES** (zero cards
  dated a non-business day; its one accepted exception, a card the client ACTED on, is listed by name when it exists).
  New **r18** = no un-actioned card stays delivered on a non-business day, so the leak cannot silently re-stand; it
  also counts out loud the **4 un-approved rows that still carry the Oct 9 date** (invisible to the client, not
  delivered, left alone — flagged, not acted on). **r10/r11 are scoped to cards that have not shipped yet** and
  report the legacy delivered counts honestly (13 delivered cards sit below fit 60, was 22 before the take-back) —
  a delivered card the client acted on cannot be re-scored into the past or recalled.
- **`client_deliveries` ledger** = source of truth for client-facing counts (2uplatam = 41). A delivery is removed
  ONLY via `deliveries.revoke` (ledger snapshotted first, reason appended to `undelivered.jsonl`), and only for a
  card the client never acted on. **Staging carries one planted `messages_sent` row** (`cea-expertos.com`,
  `user_name='staging_test'`) as the fixture that keeps the r5 actioned-exception branch covered. **Nightly** on Railway `eje-factory` at **06:00 UTC**. **Staging** `2uplatam_staging` = hidden 167-lead clone; changes go there first.

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
