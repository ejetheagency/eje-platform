# PLAN — the anchor (read this first, update it last)

> **THE GOAL:** a factory that turns mined companies into a small number of real, ready-to-contact decisor cards,
> and raises the **mine→finished (quality) ratio** by itself. We don't do leads, we do conversations yet to be had:
> every card is intentional or dies with cause. **Docs must equal the live machine.** Clean code: every line has a
> purpose and an effect. (Full anchor + hard rules in `CLAUDE.md`.)

**Current truth lives in `docs/SESSION_STATE.md` — read that first, then this queue.** Doctrine (depth):
`docs/FACTORY-VISION.md` (THE CIRCLE), `docs/CRM-PROJECT.md` (product spine). **THE NORTH:** an Innovations↔Miners
feedback loop that finds + repeats the high-yield routes per ICP. Everything below serves that.

**Discipline (non-negotiable):** ONE change per session; golden checks before/after with auto-restore; backup before
any client-report write; staging first. At the END of every session, update `SESSION_STATE.md` (current truth) and
this queue (move/retire items). No session ends without it.

---

## DEADLINE
**The factory produces 2uplatam's daily reports on its own by Wed Oct 14 night.** (Buffer ends Oct 16; serper is
refilled; the gap is the decisor-name + email walls, not plumbing. This is the one dated commitment.)

## ORDERED QUEUE (one change per session, in this order)
Reordered 2026-10-08: the Oct 14 deadline rides on **decisor NAME + discovery**, not on finance or refactors, so
those move up and finance/intelligence/endpoint/compartments move down.
1. **Name-step rule.** A decisor name counts ONLY if it sits next to a role word (dueño/fundador/director/CEO/owner)
   on the company's OWN site or its LinkedIn — never from testimonials/client lists (the "Tim Park" bug). This is
   the real bottleneck that must be tight before the factory self-produces.
2. **4x discovery for SMB ICPs.** `scheduler.pool_floor` discovers ~4x the daily target for small-business ICPs (low
   mine→finished ratio: 20 READY/day needs ~80 discovered).
3. **Finance view.** Billing compartment: per-charge paid/pending + Stripe links + cost-vs-revenue per client
   (`cost_ledger` has client_id; contract has charge dates). Today it's charge-dates-only.
4. **Intelligence compartment.** Capture what the client sent / edits / replies by channel. The response-intelligence
   loop (who converts, which channel). **Trace finding (2026-10-08): for 2uplatam, SENDS are recorded (email,
   dual-logged in `messages_sent` + `sent_actuals`) but REPLIES are not yet captured in-platform** (no inbox reconcile
   for Fernando's mailbox; only 1 manual status flip exists). Replies are NOT lost — they sit in his mailbox and can
   be imported later. Two concrete builds for this item:
   - **Import replies from Fernando's mailbox** (extend `reply_reconcile` beyond EJE-only to 2uplatam's inbox) →
     `engagement_events` + status, so the response-intelligence loop has real reply data.
   - **Fix the `EJE_USER='scarlett'` hard-code at [app.html:1042](public/app.html#L1042)** so every write
     (sent_actuals, messages_sent, status_history, notes, actions, seguimiento) is stamped with the REAL logged-in
     user, not the retired-cockpit leftover. Until then, sender identity on every row is wrong.
5. **App reads client counts from a server endpoint backed by `client_deliveries`** (service_role, **no anon policy**).
   Replaces the current app-side dedup-derive with a literal read of the ledger via a backend route.
6. **Client-file compartments.** Split the `icp_config` blob into the 7 clean compartments (Contract, Billing,
   Identity, ICP, Delivered, Intelligence, Spend) — the approved map. Schema per the map.

---

## 2uplatam ACCOUNT-CLEANUP TRACK (separate from the queue above)
Done: **#1** Vercel git auto-deploy fixed (Ignored Build Step now watches `public api vercel.json`; proven via git push). **#2** ONE `clientCounts()` source + one-person-one-card (deployed `1e247ec`, golden r15 PASS, badge=41).
Open (each ONE change, golden before/after, staging first): **#3** Hoy reads DB not legacy manifest · **#4** release exactly 20 shippable/day, refill shortfalls with passing leads (no low-fit/unshippable padding) [golden r10] · **#5** fit-score<60 gate at approve/schedule [golden r11] · **#6** non-university company caps enforced at release [golden r12] · **#7** (dropped — universities in-ICP, no cap) · **#8** harden admin count labels.
New: **PURGE UNABASE** (former client) — Step 1 inventory done (see SESSION_STATE); Step 2 (archive/remove/rename) awaits operator OK. **VERCEL COST** — switch build machine turbo→standard + batch pushes (~$24.78 Build-CPU-Minutes from turbo×volume).

## RETIRED THIS SESSION (done, do not redo)
**Spend rules + Altavia off + sends trace (old item 1), 2026-10-08:**
- Spend rules ENFORCED IN CODE: serper **≤1000 searches/night** (`budget.provider_nightly_call_caps`, gated in
  `budget.can_spend`); miner now does **paid search only on ICP-passed companies** (`icp_filters.is_chain_text`/
  `officp_by_name_domain` gate the per-company serper lanes) and **never re-searches a domain already in the pool**
  (`mine_vein(known=...)`); funnel email now shows **serper searches used + cost per shipped lead** per client.
- CLAUDE.md: new **SPEND RULES** block — manual Claude sessions are **web-fetch only, never a paid API**.
- **Altavia OFF** (archived, not deleted): `icp_config.archived=true`, honored in `scheduler.pool_floor`/`tick`,
  `reports.build_all`, `release.schedule_all`, and `api/me.js` (dropped from the switcher/login). Spend tonight = **$0**.
- Golden grew to **9/9** (added r8 serper cap, r9 archived-off). Sends trace = read-only, see item 4 above.

**Prior sessions:** Nightly honest-gate + crash-emails + budget reserve + preflight + miner timeout; Night-1 bug fixes;
serper crash guard; provider health probe + hunter/prospeo/apollo disabled; per-client business-day calendar (holidays);
golden checks (`golden_2uplatam.py`); `report_guard` backup/dedup + change protocol in CLAUDE.md; `2uplatam_staging`
clone; **`client_deliveries` delivered ledger** (backfilled 41, release-dedup, nightly sync, Decisores=41). ICP-v2 for 2uplatam.
