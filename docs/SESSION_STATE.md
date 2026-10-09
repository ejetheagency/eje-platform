# SESSION_STATE — one page, start here (updated 2026-10-08)

The single current-truth page. Read this + `docs/PLAN.md` queue, then work. Doctrine = `CLAUDE.md` GOAL block.

## Current truth (live + working)
- **Nightly** (Railway `eje-factory`, runs **06:00 UTC** = 2 AM Miami): honest net-new gate (`auto-approved tonight`, not the buffer), crash-still-emails (`RUN DIED at <step>`), budget reserve ($1.50 miner slice of the $3/day cap) + per-step spend trace, miner 90-min hard stop. Last deploy `dbd722c`.
- **Preflight**: real live probe of every provider; the funnel email's first line lists each OK/DOWN/OUT_OF_CREDITS/DISABLED. Current: **serper OK (refilled), places OK, MV OK (~9.4k), cheap-LLM OK; hunter/prospeo/apollo DISABLED** (out of credits / deprecated endpoints).
- **Business-day calendar** (`config/holidays.json` + `calendar_bd.py`): release.py + reports skip weekends/holidays per client country (`icp_config.geo`). 2uplatam: **no report Oct 9-11, next report Mon Oct 12**.
- **Golden checks** `factory/checks/golden_2uplatam.py`: **7/7 PASS** (client-parameterized, re-runnable).
- **Staging** `2uplatam_staging`: hidden clone (profile + 167 leads + ledger), not visible to the client. Changes go here first.
- **`client_deliveries` ledger** (new table, RLS on, service_role only): the source of truth for client-facing counts. A contact is delivered to a client **once, ever** (unique client_id+contact_key). 2uplatam backfilled = **41** (13 duplicates collapsed to first date). release.py never re-schedules a delivered contact; nightly `deliveries.sync_all()` records new ones; Decisores shows 41.

## Clients
- **2uplatam (Fernando)** — LIVE, paying. ICP-v2 (B2B scale-hub). Buffer ends **Oct 16**; **next report Mon Oct 12**. Decisores = 41.
- **Hobby** — PAUSED, no contact.
- **Chatmuyo** — proposal sent, awaiting response.
- **Altavia** — OFF, to be disabled (queue item 1).

## Hard rules (non-negotiable; enforced in CLAUDE.md)
1. **One change per session.**
2. **Golden checks before AND after; any new FAIL → auto-restore from backup + name the broken rule.**
3. **Backup first** (`report_guard <client>`) before any write to a client report.
4. **Staging first** — test on `2uplatam_staging` before production.
5. **Manual Claude sessions: web fetch only, no paid APIs.**
6. **Paid search only on ICP-passed companies.**
7. **Client-facing counts come from `client_deliveries`.**
8. **No anon read policies on client data** (ledger stays service_role; app reads counts via a server endpoint — queue item 5).
9. **No em dashes, ever.**

## Open problems (with evidence)
- **Factory can't self-produce leads yet.** Evidence: Fernando's 40-mine returned 0 (serper was out; hunter/prospeo/apollo dead). Serper now refilled, but unproven end-to-end. Deadline: self-producing 2uplatam reports by **Wed Oct 14 night**.
- **Decisor-NAME wall** (the real bottleneck, not email). Evidence: auto-extractor pulled "Tim Park"/"Jane Carten" from testimonials, not founders. Fix = queue item 6 (name only counts next to a role word on the company's own site/LinkedIn).
- **Email deliverability wall on SMBs.** Evidence: AGREGO, Bioxnet, Human, David Cárdenas all catch-all/invalid in MV.
- **Buffer runs out Oct 16.** Evidence: delivery schedule shows Oct 16 = 0 cards. No reports after unless the factory produces.
- **App can't read `client_deliveries` (RLS).** Evidence: table is service_role-only; Decisores currently *derives* 41 by deduping delivered leads, kept in lockstep by release-dedup. Literal read needs queue item 5 (server endpoint, no anon policy).
- **Where Fernando's sends land is unverified.** Evidence: `sent_actuals` logs 40 rows, email-only, user "scarlett". Trace in queue item 1 (read-only).
