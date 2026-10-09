# SESSION_STATE — one page, start here (updated 2026-10-09)

The single current-truth page. Read this + `docs/PLAN.md` queue, then work. Doctrine = `CLAUDE.md` GOAL block.

## Live now (current truth, deployed + working)
- **One source for client counts:** `clientCounts()` in `public/app.html` feeds every Decisores/Hoy/Reporte badge, page header and greeting; recomputes on every view change. **Decisores = 41.** **One person = one card** (dedup by `contactEmail` = ledger key; WA/IG/LinkedIn merged as attributes on the one card). Counts labeled **cliente ve** vs **pipeline**. (deployed `1e247ec`)
- **Vercel git auto-deploy FIXED.** Ignore step is now `git diff --quiet HEAD^ HEAD -- public api vercel.json`; a `git push` to main builds → promotes to **app.ejetheagency.com** on its own (no CLI). Commits that don't touch `public/`/`api/`/`vercel.json` (docs, factory) correctly skip Vercel.
- **Spend rules LIVE** (Railway VERSION `2026-10-09-spend-rules-altavia-off`): serper **≤1000 searches/night**, paid search **only on ICP-passed companies**, **never re-search a pooled domain**, funnel email shows serper count + cost/shipped-lead. Manual Claude sessions = **web-fetch only, no paid APIs**.
- **Altavia OFF** (archived, not deleted; 57 leads kept): no discovery/enrichment/spend/reports/login. Spend = **$0**.
- **Golden 13/15** (`python3 -m factory.checks.golden_2uplatam`). The 2 FAILs are known data issues below (r10 report size, r11 fit<60), fixed by **queue item 1**.
- **`client_deliveries` ledger** = source of truth for client-facing counts (2uplatam = 41). **Nightly** on Railway `eje-factory` at **06:00 UTC**. **Staging** `2uplatam_staging` = hidden 167-lead clone; changes go there first.

## Known (not yet fixed)
- **Future report tabs Oct 12-15 are OLD pre-scheduled batches (≈25/22/23/23)** carrying padding and low-fit (<60) cards — this is golden r10 (size ≠ 20) + r11 (fit<60, 27 cards). **Fixed by queue item 1** (just-in-time assembly: build only the next business day from the top 20 of the ranked pool; Oct 13-15 back to pool; Monday rebuilt).
- **Factory not yet proven to self-produce 20/day** — the deadline.
- **Replies to 2uplatam not captured in-platform** — they sit in Fernando's inbox (not lost); import = queue item 7.
- **`EJE_USER='scarlett'` hard-coded** (`app.html:1044`) stamps every write; sender identity wrong until queue item 5.

## Vercel cost
Builds are already ~6s and install-free (no package.json/lockfile/node_modules). The $24.78 Build-CPU-Minutes = **`turbo` build machine × ~100 deploys** in 3 days. **Operator will switch turbo → standard manually.** Batch frontend pushes (non-Vercel commits already skip).

## Decisions (standing)
- **Universities IN ICP, no cap / no %.** Company caps apply **only to non-universities**: max 1 per report, max 2 overall.
- **Fit floor = 60.** **20 per business day.** Never pad with low-fit/unshippable; a short day refills to 20 with passing leads.
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
