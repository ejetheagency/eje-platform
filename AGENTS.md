# EJE Platform: read this first

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

**The authoritative EJE mechanic, real metrics, and voice live in `~/Codex/eje-brand/BRAND.md` §1b. Read it before touching EJE copy or positioning.** Full pipeline state + ops in `~/Codex/eje-leads/PIPELINE-CHECKPOINT.md`.

## Handy
- Draft into a Gmail without the flaky Codex.ai connector: `~/Codex/eje-leads/scripts/eje-work-draft.py <batch.json>` (contact@ejetheagency.com) or `--personal`. Creds in `eje-leads/.env` (gitignored).
- Company email is **contact@ejetheagency.com** (no second "o").
- No em dashes, ever. Client-facing Spanish = neutral LATAM tú, grammatically correct.
