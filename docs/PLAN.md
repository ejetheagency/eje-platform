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
1. **Release gate = just-in-time report assembly.** Build only the NEXT business day's report from the **top 20 of the
   ranked pool**; send Oct 13-15's pre-scheduled cards **back to the pool**; Monday's report is rebuilt fresh. (Fixes
   the padded / low-fit future tabs = golden r10 + r11.)
2. **Hoy reads the DB,** not the legacy `reports-manifest` static files.
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
- **Cleanup #2 (2026-10-09):** ONE `clientCounts()` source + one-person-one-card, counts labeled cliente-ve/pipeline (deployed `1e247ec`; golden r15 PASS; Decisores badge = 41).
- **Cleanup #1 (2026-10-09):** Vercel git auto-deploy fixed (Ignore step `public api vercel.json`); proven via git push. Vercel build-cost analysis (turbo × volume; operator switches turbo→standard).
- **Spend rules + Altavia off + sends trace (2026-10-08):** serper ≤1000/night, paid search only on ICP-passed, no re-search of pooled domains, funnel shows serper+cost/lead (all in code, live); CLAUDE.md SPEND RULES (manual = web-fetch only); Altavia archived OFF ($0 spend); golden grew (serper cap, archived-off, screen-level r2/r14/r15, university-exempt r12). Sends traced: recorded in `messages_sent`+`sent_actuals` (email); replies not yet captured (item 7); identity hard-coded (item 5).
- **Prior:** nightly honest-gate + crash-emails + budget reserve + preflight + miner timeout; provider health probe (hunter/prospeo/apollo disabled); business-day calendar; `golden_2uplatam.py`; `report_guard` + change protocol; `2uplatam_staging` clone; **`client_deliveries` ledger** (Decisores=41); ICP-v2 for 2uplatam.
