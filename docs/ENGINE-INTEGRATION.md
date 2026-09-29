# EJE, Engine ↔ Phases Integration Map

_Re-anchor doc (2026-09-29). We built a modular ENGINE (standalone scripts) ahead of the CHASSIS (the
multi-tenant app). This maps each engine piece to WHERE it plugs in and WHICH phase gates its real
deployment, so wiring later is a known, clean step, not a rewrite._

## The engine we built (all committed, all run on the free/cheap lane)
| Tool | What it does | Plug-in point | Gated by |
|---|---|---|---|
| `config/eje.json` + `icp_config` | per-client settings (ICP, geos, gate, signals) | the client record | Phase 1 (moves to `clients.icp_config` on prod) |
| `orchestrator.py` | daily per-client loop: gate → reconcile → draft | a scheduler (Railway/cron) | Railway deploy |
| `enrichment-gate.py` | blocks un-actionable leads (readyToSend) | inside orchestrator + pre-load | none (runs today) |
| `reconcile-sends.py` | Gmail Sent → platform (no manual reconcile) | inside orchestrator | none (runs today) |
| `enrich-deterministic.py` | email/IG/LinkedIn by parsing ($0) | inside enrichment stage | none |
| `llm_router.py` | cheapest-model routing + cache + cost ledger | every LLM call in the system | none (Gemini live) |
| `deepen-briefs.py` | cheap-lane brief writing | inside enrichment stage | none |
| `seguimiento-assistant.py` | paste/voice → structured lead → filed | **serverless fn + Seguimiento UI** | Phase 1 prod (multi-tenant) |
| `classify-response.py` | reply → typed response + next move (flywheel seed) | **serverless fn + Seguimiento UI** | Phase 1 prod |

## What each still needs to become a real product feature
- **Backend tools** (orchestrator, gate, reconcile, enrich, router): need a **home that runs them on a
  schedule** = a Railway (or cron) deploy. Then the daily pipeline self-runs. Needs operator's Railway access.
- **Client-facing tools** (assistant, classifier): need **(a) a serverless function** that holds the LLM key
  server-side and exposes the brains as an API the browser can call, **(b) a Seguimiento UI** ("just tell me
  what happened" box). These attach to the multi-tenant app, so they follow **Phase 1 landing on prod**.
- **Per-sector intelligence** (aggregate `response_type` → recommend action buttons/playbook per sector):
  needs response data to accumulate first (comes from usage once the assistant is wired).

## The spine, in order (what actually gates the engine going live)
1. **Phase 1 → prod** (auth + RLS + the `clients`/`memberships`/`icp_config` tables on the live DB). Do this
   when the first real external client is near, not before (no reason to lock down a single-operator app early).
2. **Serverless API layer** (Vercel functions) exposing the engine brains, so the app UI can call them safely.
3. **Wire the app UI** (Seguimiento assistant box; sector-aware action buttons).
4. **Railway deploy** of the autonomous orchestrator (daily self-run).
5. Then Phase 3 finish (multi-contact, note-analyzer) + Phase 3B (lead library / control room).

## Principle
The engine is done and modular; it is NOT wasted by waiting. Wiring it is a step, not a rebuild. Build the
chassis (Phase 1 on prod + the serverless layer) when a real client makes it worth it, then the engine snaps in.
