# EJE Platform: read this first

## THE GOAL (the anchor — hold this before anything else, every session)
**We build a factory that turns mined companies into a small number of real, ready-to-contact decisor cards,
and raises the mine→finished (quality) ratio by itself.** That one honest number is the job.
- **We don't do leads. We do conversations yet to be had.** Every card the factory produces is INTENTIONAL —
  the right ICP, a named decisor, a reachable email — or it dies with a recorded cause. Nothing floats.
- **Docs must equal the live machine.** A doc/line that claims "works" without being shown running in code is a
  lie we trip over next week. Label reality honestly: WIRED (in the live run path) vs MEASUREMENT (read-only,
  not yet acting) vs WORDS (not built). Never celebrate volume or vision over the finished-ratio.
- **Clean code: every line has a purpose and an effect.** A line that doesn't change what the factory does is the
  code version of a floating doc. Build so tomorrow is easier.
- **The north:** an Innovations↔Miners feedback loop where departments reverse-engineer hard info, find new
  routes, and REPEAT the high-yield ones per ICP — optimizing even when no one is watching.
- When the operator says **"the plan"**, read **`docs/PLAN.md`** (the anchor) + this block, and work toward it.
  Doctrine = `docs/FACTORY-VISION.md` (THE CIRCLE). Honest current truth: TSA is not yet tight (junk still slips,
  ICP drifts, mine→finished ratio is ~2%) — that gap IS the work.

## ⛔ HARD RULE — writing to a paying client's report (operator 2026-10-08, non-negotiable)
A paying client's report (e.g. **2uplatam / Fernando**) is **PRODUCTION, not a workspace.** Before ANY insert/update
to a client's `leads`:
1. **BACKUP first** — `python3 -m factory.workers.report_guard <client>` snapshots all their leads to
   `~/claude/eje-leads/report-backups/` so every write is reversible.
2. **DEDUP check** — `report_guard.dedup(client, candidates)` against the client's existing pool (domain + email +
   company name); write ONLY `dedup['new']`. Never re-add or clobber an existing lead.
3. **Never during a mixed session** — don't edit a production report in the same session that's also doing other
   work (nightly, EJE, sourcing). One pipe at a time. (This rule exists because skipping it clobbered 5 records.)

## ⛔ SPEND RULES (operator 2026-10-08, non-negotiable)
Paid-API spend must stay a small fraction of a client's fee. Two layers, both real:
1. **Manual Claude sessions (this agent) use WEB FETCH ONLY — never a paid API.** Do NOT call Serper, Hunter,
   Prospeo, Apollo, MillionVerifier, Places-Details or any metered endpoint by hand. Enrich with WebFetch/WebSearch
   and reasoning; the paid providers belong to the autonomous nightly, which is budget-gated. (This keeps per-lead
   cost at the factory, where the caps live, and stops ad-hoc credit burn.)
2. **The nightly factory is enforced in code** (`factory/packages/budget.py`, `config/budgets.json`): a kill switch,
   a $3/night + $30/month USD cap, a per-provider nightly COUNT cap (**serper ≤ 1000 searches/night**), and in the
   miner: **paid search runs ONLY on ICP-passed companies** and **never re-searches a company already in the pool**.
   Never RAISE a cap to make a run fit — make the run cheaper. The funnel email shows serper searches + cost/shipped lead.

## ⛔ CHANGE PROTOCOL — 2uplatam (paying client), enforced (operator 2026-10-08)
For ANY change touching 2uplatam, in this exact order:
1. **BEFORE:** run `python3 -m factory.checks.golden_2uplatam` (record PASS/FAIL) **and** `python3 -m factory.workers.report_guard 2uplatam` (backup).
2. Make **exactly ONE change** (test it on the hidden **`2uplatam_staging`** clone first).
3. **AFTER:** re-run the golden checks.
4. **Any rule that NEWLY fails => automatically restore from the report_guard backup** and tell the operator which rule broke. Never leave a new FAIL standing.
5. **Every fix ADDS its rule** to `factory/checks/golden_2uplatam.py` (the net only grows).

This repo (GitHub `eje-platform`) hosts **two things that share one codebase + one Supabase project**
(`ogdsuztzhmnnjolilsuo`, `leads` table): the legacy productora cockpit (built for a former client) AND EJE's own product.
Deploy = commit the changed file(s) by name + `git push origin main` (Vercel auto-deploys; live at `app.ejetheagency.com`).
Do NOT `git add public/*.json` (~40 untracked historical lead files).
PostgREST hard-caps every response at 1000 rows — always paginate reads.

## Frontends
- **`public/app.html`** = the LIVE app ("EJE / Plataforma"). This is what everyone uses. Fix bugs here.
- **`public/index.html`** = the retired classic cockpit. It now just redirects to app.html (kept for history). Don't build on it.

## Workspaces (app.html switches on `client_id`, from `localStorage.eje_ws`)
- `unabase_default` : the legacy productora pipeline (Scarlett's cockpit, from the former client).
- `eje` — **EJE's OWN outreach + product** (owner-gated to Emiliano's accounts). The "EJE Outreach" switcher entry.
- `eje_web` — retired.

## THE EJE OUTREACH WORKSPACE **is EJE's product** (client_id=eje)
The `eje` workspace IS the system EJE sells. Its parts map to EJE's mechanic:
- **Hoy** = the daily decision-card report (leads whose email is due that day; source_date == today).
- **Tareas** = the guided lifecycle / next-steps queue — **follow-ups only** for already-contacted leads (first-touches live in Hoy on their send day).
- **Send button** = "siguiente tarea": one click copies the message, opens the right channel (IG/LinkedIn/mailto/wa), and marks it.
- **Cadence** = the "ciclo de vida": 1er email → IG (if handle) → LinkedIn (if profile) → email. `ISEJE` scopes all EJE-only behavior so the productora (`unabase_default`) workspace is untouched.
- EJE does **NOT auto-send** — the client's team sends via the guided one-click steps.

**The authoritative EJE mechanic, real metrics, and voice live in `~/claude/eje-brand/BRAND.md` §1b. Read it before touching EJE copy or positioning.** Full pipeline state + ops in `~/claude/eje-leads/PIPELINE-CHECKPOINT.md`.

## Prospect demos and account research
**Any prospect demo or account research: use `.claude/skills/account-demo`; its targets are the definition of done.**
(Hard targets: >=2 personal emails per company, >=20 total, 10/10 companies with >=1, >=1 named manager-level door.
Only personal emails tied to a named non-contexto person count; area/program inboxes, sister-company inboxes and
sales inboxes never do. Sources older than 2023 need newer confirmation; undated ones are "sin fecha, verificar
vigencia" and a client report counts only confirmed.) Build with `python3 demos/_template/build.py <prospecto>`.

## Handy
- Draft into a Gmail without the flaky claude.ai connector: `~/claude/eje-leads/scripts/eje-work-draft.py <batch.json>` (contact@ejetheagency.com) or `--personal`. Creds in `eje-leads/.env` (gitignored).
- Company email is **contact@ejetheagency.com** (no second "o").
- No em dashes, ever. Client-facing Spanish = neutral LATAM tú, grammatically correct.
