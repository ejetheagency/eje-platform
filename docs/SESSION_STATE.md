# SESSION_STATE — one page, start here (updated 2026-10-08)

The single current-truth page. Read this + `docs/PLAN.md` queue, then work. Doctrine = `CLAUDE.md` GOAL block.

## Current truth (live + working)
- **Nightly** (Railway `eje-factory`, runs **06:00 UTC** = 2 AM Miami): honest net-new gate (`auto-approved tonight`, not the buffer), crash-still-emails (`RUN DIED at <step>`), budget reserve ($1.50 miner slice of the $3/day cap) + per-step spend trace, miner 90-min hard stop. Last deploy `dbd722c`.
- **Spend rules (code written + tested 2026-10-08, NOT yet pushed → not live on Railway until deploy):** serper **≤1000 searches/night** (`config/budgets.json` → `provider_nightly_call_caps`, gated in `budget.can_spend`); the miner does **paid search ONLY on ICP-passed companies** and **never re-searches a domain already in the pool**; funnel email now shows **serper searches + cost per shipped lead** per client. Manual Claude sessions = **web-fetch only, no paid APIs** (CLAUDE.md SPEND RULES). **Deploy = commit + `git push origin main` to make it live** (not done this session, per instruction).
- **Preflight**: real live probe of every provider; the funnel email's first line lists each OK/DOWN/OUT_OF_CREDITS/DISABLED. Current: **serper OK (refilled), places OK, MV OK (~9.4k), cheap-LLM OK; hunter/prospeo/apollo DISABLED** (out of credits / deprecated endpoints).
- **Business-day calendar** (`config/holidays.json` + `calendar_bd.py`): release.py + reports skip weekends/holidays per client country (`icp_config.geo`). 2uplatam: **no report Oct 9-11, next report Mon Oct 12**.
- **Golden checks** `factory/checks/golden_2uplatam.py`: **7/7 PASS** (client-parameterized, re-runnable).
- **Staging** `2uplatam_staging`: hidden clone (profile + 167 leads + ledger), not visible to the client. Changes go here first.
- **`client_deliveries` ledger** (new table, RLS on, service_role only): the source of truth for client-facing counts. A contact is delivered to a client **once, ever** (unique client_id+contact_key). 2uplatam backfilled = **41** (13 duplicates collapsed to first date). release.py never re-schedules a delivered contact; nightly `deliveries.sync_all()` records new ones; Decisores shows 41.

## Clients
- **2uplatam (Fernando)** — LIVE, paying. ICP-v2 (B2B scale-hub). Buffer ends **Oct 16**; **next report Mon Oct 12**. Decisores = 41.
- **Hobby** — PAUSED, no contact.
- **Chatmuyo** — proposal sent, awaiting response.
- **Altavia** — **OFF (archived 2026-10-08)**. `icp_config.archived=true` + `spend_policy=paused` (kept, not deleted; 57 leads retained). **Spend tonight = $0 is already guaranteed** by the deployed pause logic (`pool_floor` + `can_spend` skip paused non-paying clients) — verified $0, 0 rows today. The new archived skips in `reports.build_all`/`release.schedule_all`/`scheduler.tick`/`api/me.js` (no reports, no login/switcher) are **written but go live on deploy**. Reversible by clearing the flag.

## Hard rules (non-negotiable; enforced in CLAUDE.md)
1. **One change per session.**
2. **Golden checks before AND after; any new FAIL → auto-restore from backup + name the broken rule.**
3. **Backup first** (`report_guard <client>`) before any write to a client report.
4. **Staging first** — test on `2uplatam_staging` before production.
5. **Manual Claude sessions: web fetch only, no paid APIs.** (CLAUDE.md SPEND RULES.)
6. **Paid search only on ICP-passed companies**, **never re-search a company already in the pool**, **serper ≤1000/night** — all enforced in code (`budget.py` + miner).
7. **Client-facing counts come from `client_deliveries`.**
8. **No anon read policies on client data** (ledger stays service_role; app reads counts via a server endpoint — queue item 5).
9. **No em dashes, ever.**

## Open problems (with evidence)
- **Factory can't self-produce leads yet.** Evidence: Fernando's 40-mine returned 0 (serper was out; hunter/prospeo/apollo dead). Serper now refilled, but unproven end-to-end. Deadline: self-producing 2uplatam reports by **Wed Oct 14 night**.
- **Decisor-NAME wall** (the real bottleneck, not email). Evidence: auto-extractor pulled "Tim Park"/"Jane Carten" from testimonials, not founders. Fix = queue item 6 (name only counts next to a role word on the company's own site/LinkedIn).
- **Email deliverability wall on SMBs.** Evidence: AGREGO, Bioxnet, Human, David Cárdenas all catch-all/invalid in MV.
- **Buffer runs out Oct 16.** Evidence: delivery schedule shows Oct 16 = 0 cards. No reports after unless the factory produces.
- **App can't read `client_deliveries` (RLS).** Evidence: table is service_role-only; Decisores currently *derives* 41 by deduping delivered leads, kept in lockstep by release-dedup. Literal read needs queue item 5 (server endpoint, no anon policy).
- **Where Fernando's sends land — TRACED 2026-10-08 (read-only).** His sends ARE recorded, in **two** tables, both `client_id=2uplatam`, both email-only so far:
  - `messages_sent` (Send-button / cadence log, templated text): **36 rows** — Oct 7: 1, Oct 8: 35.
  - `sent_actuals` (the "what you actually sent" editable textarea, the EDITED text): **40 rows** — Oct 7: 4, Oct 8: 36. Captures channel, company, situation (first 36 / upcoming 4), message_text (40/40 non-empty).
  - **Why all "scarlett":** `EJE_USER` is **hard-coded** to `'scarlett'` at `public/app.html:1042` (leftover from the retired productora cockpit). EVERY workspace write (sent_actuals, messages_sent, status_history, notes, actions, seguimiento) is stamped `scarlett` regardless of who is logged in — so **sender identity is not captured** (not recoverable per-row).
  - **NOT recorded at all = lost forever (flag):** (1) **Replies** to 2uplatam outreach — `reply_reconcile` runs EJE-only (agency inbox), not Fernando's mailbox; `engagement_events` replied for 2uplatam = **0**; only **1** reply was ever manually marked (`status_history`). (2) **Non-email sends** (WhatsApp/Instagram/LinkedIn) done outside the app — the in-app Send button would log them by channel, but all 40 rows are email, so anything sent directly in WhatsApp/IG/LinkedIn is uncaptured. (3) **Edits vs the template** are kept in `sent_actuals` but not diffed/analyzed.
  - **Exception check:** the operator's reorder exception triggers only if SENDS are not recorded — they ARE (email, dual-logged), so item 2 stays the name-step rule. The real data-loss is REPLIES (lost daily); folded into queue item 4 (Intelligence). If the operator considers replies the "data that can't be recovered," elevate item 4.
