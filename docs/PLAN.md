# PLAN, the anchor (read this first, update it last)

> **THE GOAL:** a factory that turns mined companies into a small number of real, ready-to-contact decisor cards,
> and raises the **mine→finished (quality) ratio** by itself. We don't do leads, we do conversations yet to be had:
> every card is intentional or dies with cause. **Docs must equal the live machine.** (Full anchor + hard rules in `CLAUDE.md`.)

**Current truth lives in `docs/SESSION_STATE.md`, read that first, then this queue.** Doctrine (depth):
`docs/FACTORY-VISION.md` (THE CIRCLE), `docs/CRM-PROJECT.md` (product spine). **THE NORTH:** an Innovations↔Miners
feedback loop that finds + repeats the high-yield routes per ICP. Everything below serves that.

---

## PRINCIPLES (the test every change has to pass, before the queue)
1. **Every feature must save the client time or raise their return, without raising our cost.** Three things to
   name before building: the minutes saved or the return raised, and the cost delta. If a feature does neither,
   it does not get built.
2. **Data is the product.** Every outcome is captured, **including rejections and no-replies**: a "no encaja" and a
   silence are findings, not waste. Two steps, in this order: **first** make sure we can STORE and USE the outcome
   (schema, one event shape, queryable), **second** make it EFFORTLESS for the client to give it (one button, one
   step, pre-filled). Storage without an easy way to give it collects nothing; an easy button with nowhere to put
   the answer loses it.
3. **Finish line per client:** **5 business days in a row of 20 cards at fit >= 60, zero manual work, cost < 10% of
   the fee, all golden green.** **Nothing new gets built for a client until this holds for that client.** The finish
   line is per client, not global: a second client does not get features while the first is not finished.
4. **Weekly rhythm:** **Mon-Thu, one change per day.** **Friday is review only:** the numbers, the client's actual
   activity, and next week's 3-4 changes. **No builds on Friday.**
5. **Speed:** read-only tasks **skip backup and staging** (nothing is being written). During the work, run **only
   the golden rules related to the change**; run the **full suite once before and once after**. **Reports under
   300 words.**
6. **The operator's morning check, 10 minutes, every day.** Read the golden + health lines at the top of the funnel
   email (queue item 0b puts them there); **open 5 cards** of the next report; **veto anything not worth sending**.
   **If everything is green, no dev session that day for that client. If something is red, that one thing is the
   day's only job.** The machine reports itself so the operator decides in minutes, not by digging.

---

## FINISH LINE / DEADLINE
**The factory produces 2uplatam's 20/day on its own by Wed Oct 14 night.** (Buffer ends Oct 16.) Done = principle 3
for 2uplatam: 5 business days in a row, 20 cards, fit >= 60, no manual work, cost < 10% of fee, golden green.

## DISCIPLINE (non-negotiable)
ONE change per day (Mon-Thu); golden before/after with auto-restore; backup before any client-report write;
staging first for anything that WRITES. END every session by updating `SESSION_STATE.md` + this queue.
No session ends without it.

---

## ORDERED QUEUE (one change per day, in this order)
0. **Housekeeping (small).** Pool the **4 `approved:false` rows still dated Oct 9** (siglobpo, ecuador.unir.net,
   outsourcing-ec, wearedrew): invisible to the client today, but they hold a holiday date. **Fix or document the
   pre-existing `test_gates` failure** (it routes a complete lead to PARKED on `email_verified`); if it is a stale
   test rather than a real defect, say so in the test itself.
0b. **Nightly review, automatic (the machine reports itself).** At the end of every nightly run, **the full golden
   suite runs per client** and its result goes in the **first lines of the funnel email**: run status
   (**OK / RUN DIED at step**), providers status, and per client: **cards shipped for the next business day, lowest
   fit, pool days left, cost tonight vs the daily ceiling, golden X/Y with the NAME of any FAIL**. **Any FAIL or
   RUN DIED also sends a separate alert email.** This is what principle 6 reads each morning, so it comes before
   the feature work.
1. **Fit repair** (the gate now depends on fit being true). **Geo:** fall back to the **domain / phone / address
   country** when `companies.country` is empty. **Seniority:** recognize **Decano, Rector, Vicerrector, Director/a,
   Gerente, Dueño/a, Fundador/a, CEO, Socio/a**. **Empty title on a one-person business:** use **owner signals from
   the site** instead of scoring 0. **Recompute fit for the UNDELIVERED POOL ONLY** (a delivered card is never
   re-scored into the past). **One score** used by the card, the ranker and golden r11. No second opinion computed
   in the dark.
2. **Name-step rule.** A decisor name counts **only next to a role word** on the company's **own site or LinkedIn**.
   Never from testimonials or client lists.
3. **4x discovery for SMB ICPs.** Pool target = **2-3 report days** for small-business ICPs.
4. **BCC send logging.** The **Contactar** action adds BCC **contact+<client_id>@ejetheagency.com**; the nightly
   inbox job matches recipients against **`client_deliveries`** and logs the send with **full text**, stamped with
   the **real client**. The "what I sent" box becomes **optional, pre-filled from the BCC copy**.
   **Golden:** every logged send's recipient is a delivered contact **of that client**.
5. **Respondió, automatic Seguimiento card.** One **Respondió** button on any delivered card **creates the
   Seguimiento card automatically with all the lead's data** (no manual creation) and asks in **one step**: what did
   they say (**interesado, reunión agendada, no por ahora, no encaja, persona equivocada, me refirió a otra persona,
   cerrado ganado, cerrado perdido**) + an **optional note**. Every later update **adds a timestamped entry**, stored
   as an **`engagement_event`** (client, contact, channel, template, outcome, note, date). **Home nudge:** "X personas
   respondieron sin estado, cuéntanos qué dijeron." **The Seguimiento tab is INACTIVE in the client view today:
   turn it on only with this item**, as the client's **conversations board**, visible **once the first Respondió
   exists**, with an **empty-state line** explaining it. **No purposeless tab.**
5b. **Hoy reads the DB,** not the legacy `reports-manifest` static files. **Must land BEFORE item 6:** the Unabase
   purge **archives those static files**, so Hoy cannot still depend on them when that happens (purge first = a
   client-facing Hoy reading files that are gone). **Golden: the Hoy count == the next-business-day report in the DB.**
6. **Identity fix, then Unabase purge step 2.** `EJE_USER='scarlett'` is hard-coded at `app.html:1044`: stamp every
   write with the **real logged-in user**. Then the purge: archive legacy data, remove code refs, **rename the Vercel
   project `unabase-app`**, **keep the `app.ejetheagency.com` alias**. (Inventory in `SESSION_STATE.md`.)
   Golden: zero "unabase"/"scarlett" in active code and in anything a client sees.
7. **Replies import** via a **Gmail/Outlook connection, read-only**, **filtered to delivered contacts only**.
   Consent line, verbatim: **"solo leemos conversaciones con los contactos que te entregamos"**.
8. **Finance view.** Cost vs revenue **per client**, including **Vercel + Railway + Supabase** as costs; per-charge
   **paid/pending**. The **morning email adds pool days left and cost vs fee, per client**.
9. **Intelligence use.** **Weekly, per client:** which **roles, industries, channels and templates** get replies and
   conversations; **the ranker prioritizes similar leads**. **Across clients, aggregate patterns ONLY: one client's
   conversation data is never shown to another.**
10. **Card-open logging (`lead_views`)** so **"opened" becomes knowable** (today it is not: there is no open log, so
    "did he open it" cannot be answered). Plus the **operator veto button in the app** (today CLI only).

> **PARKED, not queued:** "server endpoint for client counts (service_role, no anon policy) + client-file
> compartments (split `icp_config` into the 7 clean compartments)". Not recorded as DONE, just not scheduled.
> Hard rule 8 (no anon read policies on client data) stands without it. Re-add deliberately if it matters.

---

## FUTURE / INNOVATION TRACK (reviewed Fridays, NOT scheduled)
Each idea gets a **one-line hypothesis and a cheap test before any build**. Nothing here is committed work.

- **Clara as the intel collector.** The client tells Clara **by text or voice note**: "esta persona respondió esto,
  el estado es X". Clara **transcribes**, **identifies the contact from the delivered list**, **proposes** the update
  and **saves it to the Seguimiento card only after the client confirms**. **Same `engagement_event` structure as
  queue item 5** (one event shape, not a second parallel store).
- **New ways to create conversations beyond cold outreach:** a **referral loop** (ask every responder "¿a quién más
  debería conocer?"), **warm intros through partners**, **events and communities where the ICP gathers**, **inbound
  from content**, and **meeting-booking offers** for clients who want it done for them.
- **Weekly client note:** what improved in their reports, what they did, conversations count, and what we changed
  **because of their feedback**.

(The nightly review is no longer future work: part (a) is **queue item 0b**, part (b) is **principle 6**.)

---

## DONE (do not redo)
- **Oct 9 holiday leak TAKEN BACK (2026-10-09):** read-only audit first (none of the 10 cards had any action from
  Fernando), then all 10 un-delivered: pooled (`source_date` NULL, invisible), ledger rows revoked with the reason
  logged, `approved` kept so the gate re-ships them only if they rank (1 eligible now, 9 below the fit floor).
  **Decisores 51 -> 41.** New primitives: `release.undeliver` / `undeliver_date` (both REFUSE a card the client
  acted on) + `deliveries.touched` / `is_actioned` / `backup_ledger` / `revoke`. Fixed in the same change: the
  `"" <= today` bug that made the whole pool read as delivered and would have added 55 ledger rows that night.
  Golden **18/18** (r5 PASS with a named-exception path; new r18). `test_gates` FAIL is pre-existing (lead_state),
  now queue item 0.
- **Release gate = just-in-time assembly (2026-10-09):** `release.py` rewritten from the pre-scheduling
  drip into the gate (pool / report / delivered; next business day only; top 20 of the ranked pool; fit floor 60;
  one person one card; non-uni company caps; never padded; operator veto + automatic backfill). `publish.py` now
  pools new cards instead of dating them (that leak is what delivered a report on the Oct 9 holiday). Funnel email
  prints the next report + a SHORT flag. Monday Oct 12 rebuilt: fit 84-96, zero cards under 60 (was 14 under 60);
  Oct 13-15 back to the pool. Golden grew to 17 (r16 next-report-is-top-of-pool, r17 screen-level report tabs);
  16/17 PASS. Details + the fit-score defects it uncovered: `docs/SESSION_STATE.md`.
- **Cleanup #2 (2026-10-09):** ONE `clientCounts()` source + one-person-one-card, counts labeled cliente-ve/pipeline (deployed `1e247ec`; golden r15 PASS).
- **Cleanup #1 (2026-10-09):** Vercel git auto-deploy fixed (Ignore step `public api vercel.json`); proven via git push. Vercel build-cost analysis (turbo x volume); **operator has switched the build machine turbo -> standard.**
- **Spend rules + Altavia off + sends trace (2026-10-08):** serper <=1000/night, paid search only on ICP-passed, no re-search of pooled domains, funnel shows serper+cost/lead (all in code, live); CLAUDE.md SPEND RULES (manual = web-fetch only); Altavia archived OFF ($0 spend); golden grew (serper cap, archived-off, screen-level r2/r14/r15, university-exempt r12). Sends traced: recorded in `messages_sent`+`sent_actuals` (email); replies not yet captured (items 4/7); identity hard-coded (item 6).
- **Prior:** nightly honest-gate + crash-emails + budget reserve + preflight + miner timeout; provider health probe (hunter/prospeo/apollo disabled); business-day calendar; `golden_2uplatam.py`; `report_guard` + change protocol; `2uplatam_staging` clone; **`client_deliveries` ledger**; ICP-v2 for 2uplatam.
