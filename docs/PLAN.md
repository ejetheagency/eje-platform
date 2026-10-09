# PLAN — the anchor (read this first, update it last)

> **THE GOAL:** a factory that turns mined companies into a small number of real, ready-to-contact decisor cards,
> and raises the **mine→finished (quality) ratio** by itself. We don't do leads, we do conversations yet to be had:
> every card is intentional or dies with cause. **Docs must equal the live machine.** (Full anchor + hard rules in `CLAUDE.md`.)

**Current truth lives in `docs/SESSION_STATE.md` — read that first, then this queue.** Doctrine (depth):
`docs/FACTORY-VISION.md` (THE CIRCLE), `docs/CRM-PROJECT.md` (product spine). **THE NORTH:** an Innovations↔Miners
feedback loop that finds + repeats the high-yield routes per ICP. Everything below serves that.

**Discipline (non-negotiable):** ONE change per session; golden before/after with auto-restore; backup before any
client-report write; staging first. END every session by updating `SESSION_STATE.md` + this queue. No session ends without it.

---

## DEADLINE
**The factory produces 2uplatam's 20/day on its own by Wed Oct 14 night.** (Buffer ends Oct 16.)

## ORDERED QUEUE (one change per session, in this order)
1. **Hoy reads the DB,** not the legacy `reports-manifest` static files.
2. **Repair `fit.fit_score`** (uncovered by the release gate, which now depends on fit being true): read geo from the
   card/`lead_data` instead of the usually-empty `companies.country`; add the missing decisor titles (Decano, Rector,
   Vicerrector, Decana); stop scoring an empty title as 0 seniority on a one-person business. Then **re-score the pool
   and compare against the hand/hybrid scores** before letting the computed score drive the gate. Golden: the ranker's
   top 20 does not change character when fit is recomputed.
3. **Name-step rule.** A decisor name counts ONLY if a role word (dueño/fundador/director/CEO/owner) sits next to it on
   the company's OWN site or its LinkedIn — never from testimonials/client lists.
4. **4x discovery for SMB ICPs.** `scheduler.pool_floor` keeps the pool at **2-3 days of reports** for small-business ICPs.
5. **Identity fix.** `EJE_USER='scarlett'` is hard-coded at `app.html:1044`; stamp every write with the REAL logged-in user.
6. **Unabase purge, step 2** (ONLY after item 5): archive legacy data, remove code refs, rename the Vercel project
   `unabase-app`, **keep the `app.ejetheagency.com` alias**. (Inventory in SESSION_STATE.) Golden: zero "unabase"/"scarlett"
   in active code and in anything a client sees.
7. **Replies import** from Fernando's inbox → `engagement_events` + status (Intelligence / response loop).
8. **Finance view.** Cost-vs-revenue per client, including **Vercel + Railway + Supabase** as costs; per-charge paid/pending + Stripe links.
9. **Server endpoint for client counts** (service_role, no anon policy) + **client-file compartments** (split `icp_config` into the 7 clean compartments).

---

## DONE (do not redo)
- **Oct 9 holiday leak TAKEN BACK (2026-10-09):** read-only audit first (none of the 10 cards had any action from
  Fernando), then all 10 un-delivered: pooled (`source_date` NULL, invisible), ledger rows revoked with the reason
  logged, `approved` kept so the gate re-ships them only if they rank (1 eligible now, 9 below the fit floor).
  **Decisores 51 → 41.** New primitives: `release.undeliver` / `undeliver_date` (both REFUSE a card the client acted
  on) + `deliveries.touched` / `is_actioned` / `backup_ledger` / `revoke`. Fixed in the same change: the
  `"" <= today` bug that made the whole pool read as delivered and would have added 55 ledger rows that night.
  Golden **18/18** (r5 PASS with a named-exception path; new r18). `test_gates` FAIL is pre-existing (lead_state).
- **Release gate = just-in-time assembly (2026-10-09, queue item 1):** `release.py` rewritten from the pre-scheduling
  drip into the gate (pool / report / delivered; next business day only; top 20 of the ranked pool; fit floor 60;
  one person one card; non-uni company caps; never padded; operator veto + automatic backfill). `publish.py` now
  pools new cards instead of dating them (that leak is what delivered a report on the Oct 9 holiday). Funnel email
  prints the next report + a SHORT flag. Monday Oct 12 rebuilt: fit 84-96, zero cards under 60 (was 14 under 60);
  Oct 13-15 back to the pool. Golden grew to 17 (r16 next-report-is-top-of-pool, r17 screen-level report tabs);
  16/17 PASS. Details + the fit-score defects it uncovered: `docs/SESSION_STATE.md`.
- **Cleanup #2 (2026-10-09):** ONE `clientCounts()` source + one-person-one-card, counts labeled cliente-ve/pipeline (deployed `1e247ec`; golden r15 PASS; Decisores badge = 41).
- **Cleanup #1 (2026-10-09):** Vercel git auto-deploy fixed (Ignore step `public api vercel.json`); proven via git push. Vercel build-cost analysis (turbo × volume; operator switches turbo→standard).
- **Spend rules + Altavia off + sends trace (2026-10-08):** serper ≤1000/night, paid search only on ICP-passed, no re-search of pooled domains, funnel shows serper+cost/lead (all in code, live); CLAUDE.md SPEND RULES (manual = web-fetch only); Altavia archived OFF ($0 spend); golden grew (serper cap, archived-off, screen-level r2/r14/r15, university-exempt r12). Sends traced: recorded in `messages_sent`+`sent_actuals` (email); replies not yet captured (item 7); identity hard-coded (item 5).
- **Prior:** nightly honest-gate + crash-emails + budget reserve + preflight + miner timeout; provider health probe (hunter/prospeo/apollo disabled); business-day calendar; `golden_2uplatam.py`; `report_guard` + change protocol; `2uplatam_staging` clone; **`client_deliveries` ledger** (Decisores=41); ICP-v2 for 2uplatam.
