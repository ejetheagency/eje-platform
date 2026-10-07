# Daily release + micro-routes (the norm for every client and demo)

Locked 2026-10-07 from the Data Insights premium-week build. This is how we store a client's leads once and
release them 20/day without polluting their interface, plus the micro-routes + discipline that let a slower,
cheaper model (Haiku) reproduce today's premium result with less power.

## 1. The daily-release mechanism (WIRED, in app.html)
One batch is stored once; the client only ever sees what has been delivered.

- **Store**: every lead is a `leads` row (`client_id`, `id`=domain, `lead_data`), with `source_date` = the day it
  should be delivered, and `approved=true`. Future days are stored ahead of time (e.g. Oct 8/9/12/13).
- **Release gate** (`loadUniverse`): for any client (non-admin, `CLIENTCLEAN()`), leads with `source_date > today`
  are dropped from `UNIVERSE` entirely, so Decisores and Tareas never show undelivered leads. Admin sees the full queue.
- **Hoy**: narrows further to exactly `source_date === today` (the fresh 20). No carry-forward pile. Rolls over at
  **08:00 America/Santiago** (`ejeTodayET`), so the next 20 appear each morning automatically.
- **Delivered-cumulative**: Decisores/Tareas show `source_date <= today` (everything released so far = the client's
  working CRM); future stays invisible until its day.
- **Admin pool**: the whole queue is visible to admin for management. `leads.id` is a GLOBAL primary key (a domain
  can exist once), so a reusable library copy must use a prefixed id (`lib_<domain>`), see section 3.

This is identical for demos and paying clients: store the week, release 20/day, zero pollution.

## 2. Micro-routes + discipline (what helps the cheap factory models)
The win is not a smarter model; it is deterministic routes + mechanical gates. Spend the expensive reasoning once
to lay these rails; Haiku follows them.

**Micro-routes (deterministic discovery/enrichment, little reasoning needed):**
- Search via the factory's own `serper` key (uncapped, ~$0.001/search), NOT a model's capped WebSearch tool.
  Query templates that worked: `"<empresa>" <ciudad> gerente general`, `"<empresa>" (fundador OR dueño OR CEO)`,
  `<nombre> <empresa> linkedin`, `<empresa> whatsapp contacto`.
- Decisor fallback: **TheOrg org-charts** are directly fetchable by URL (`theorg.com/org/<slug>`) when the company
  site names no executive. Always verify entity + country (wrong-entity traps are common).
- Channels by regex on the company site/footer (no LLM): `wa.me/ | api.whatsapp.com/send?phone=` for WhatsApp,
  `instagram.com/<handle>`, `linkedin.com/company/<slug>` for company LinkedIn. WhatsApp ONLY from a wa.me/mobile
  link, never a landline.
- Email: prefer the decisor box, else a published company box; verify with MillionVerifier; never ship `invalid`.

**Discipline (the gates, applied mechanically, already in agent_miner.mine_report):**
- Named decisor (owner/GM/CFO) is mandatory; skip the company if unconfirmable. Enforced again at publish.
- >= 2 real channels beyond email (WhatsApp / Instagram / LinkedIn / 2nd decisor). Thin cards do not ship.
- ICP-fit gate + non-biz/aggregator domain reject + real-website gate.
- Per-query variety cap (spread the batch across sectors, not one vein).
- 4-part intel brief as a FILL-IN TEMPLATE (Modelo / Clientes-socios / Reciente / Ángulo), grounded in fetched
  text, so a weak model produces insider depth without free-form reasoning.
- Pitch grounded in the brief's why-now/ángulo (one hook, one ask), not a generic blast.
- No fabrication: empty beats invented. Honest gaps recorded.

**Gaps to wire next (the nightly runs `discovery -> micro_routes -> publish`, NOT `agent_miner`):**
- Port the above routes/discipline into `factory/workers/micro_routes.py` + `publish.py` (company LinkedIn capture,
  2nd decisor, 4-part brief, grounded pitch, richness score), then validate a cheap-model run end to end.
- `agent_miner.py` is the clean reference implementation (serper lanes + all gates) but is not yet in the nightly path.

## 3. The reusable lead library (stored 2026-10-07)
94 enriched Guayaquil distributor/manufacturer leads (75 premium) stored under `client_id='eje_library'` with
prefixed ids (`lib_<domain>`), carrying the full enrichment (brief, pitch, channels, 2nd decisor, sector, score).
Provision for an overlapping future client by copying the relevant rows into that client's workspace with the real
domain id and the target `source_date`s. This makes a future demo cost ~$0 and no time.
