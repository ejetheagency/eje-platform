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
1. **Spend rules + Altavia off + where Fernando's sends land (read-only trace).** Encode the spend doctrine (manual
   sessions = web-fetch only / no paid APIs; paid search only on ICP-passed companies; per-client spend caps). Disable
   Altavia (FD stop). Trace, read-only, where Fernando's outbound actually lands (`sent_actuals` = email-only today).
2. **Finance view.** Billing compartment: per-charge paid/pending + Stripe links + cost-vs-revenue per client
   (`cost_ledger` has client_id; contract has charge dates). Today it's charge-dates-only.
3. **Intelligence compartment.** Capture what the client sent / edits / replies by channel (today `sent_actuals` =
   email-only, no replies). The response-intelligence loop (who converts, which channel).
4. **Client-file compartments.** Split the `icp_config` blob into the 7 clean compartments (Contract, Billing,
   Identity, ICP, Delivered, Intelligence, Spend) — the approved map. Schema per the map.
5. **App reads client counts from a server endpoint backed by `client_deliveries`** (service_role, **no anon policy**).
   Replaces the current app-side dedup-derive with a literal read of the ledger via a backend route.
6. **Name-step rule.** A decisor name counts ONLY if it sits next to a role word (dueño/fundador/director/CEO/owner)
   on the company's OWN site or its LinkedIn — never from testimonials/client lists (this session: "Tim Park" bug).
7. **4x discovery for SMB ICPs.** `scheduler.pool_floor` discovers ~4x the daily target for small-business ICPs (low
   mine→finished ratio: 20 READY/day needs ~80 discovered).

---

## RETIRED THIS SESSION (done, do not redo)
Nightly honest-gate + crash-emails + budget reserve + preflight + miner timeout; Night-1 bug fixes; serper crash
guard; provider health probe + hunter/prospeo/apollo disabled; per-client business-day calendar (holidays); golden
checks (`golden_2uplatam.py`); `report_guard` backup/dedup + change protocol in CLAUDE.md; `2uplatam_staging` clone;
**`client_deliveries` delivered ledger** (backfilled 41, release-dedup, nightly sync, Decisores=41). ICP-v2 for 2uplatam.
