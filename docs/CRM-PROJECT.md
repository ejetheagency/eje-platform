# CRM Project, Build Spec

**Official project name: the CRM Project.** The execution spine for rebuilding the EJE Outreach tool into
**the scalable multi-tenant CRM product**.
Grounded in `ARCHITECTURE.md` (current state), `ENGINE-INTEGRATION.md` (the engine we already built),
and the locked redesign plan. Approach decided 2026-09-30: **additive clean rebuild that EVOLVES the
current `app.html` into a proper CRM**, not a from-scratch framework rewrite (fastest to a real product,
lowest risk to the Fernando / 2upLatam timeline).

## The gap we are closing
Current: one monolithic `public/app.html`, browser holds the Supabase anon key, direct table access, no
real auth, cadence computed at render, sourcing/enrichment run by hand. Works for one operator, not a product.

Target: **proper infrastructure + proper CRM**.
- **Infrastructure:** a backend API layer (keys server-side), real auth + per-client data walls (RLS),
  and the sourcing -> enrichment -> gate -> compose pipeline running AUTOMATICALLY behind the scenes.
- **CRM:** a modern CRM surface (records, pipeline, activity timeline, the daily decision cards, Seguimiento,
  a live assistant), with an admin Lead Library separate from what each client sees.

## Principles
- **Additive + clean:** build the new alongside the working app; cut over per slice; never break the live tool.
- **Behind-the-scenes automation:** sourcing/enrichment is a scheduled system job, not a human running agents.
- **Server holds secrets:** the browser never carries the service key; all writes go through the API layer.
- **Multi-tenant by default:** every path is client-scoped; a client sees only their own data (RLS-enforced).
- **The engine already exists** (`scripts/`): this build WIRES it in, it does not rewrite it.

## Build slices (sequenced; each independently shippable)
**S1, Infrastructure spine.**
  - Backend API layer (Vercel serverless functions under `/api`) that holds the service key and exposes
    scoped endpoints the UI calls (leads, messages, notes, tracked_leads, assistant, classifier).
  - Auth + RLS multi-tenant on PROD (the `clients`/`memberships`/`icp_config` tables + security-definer
    functions + tenant policies, proven on staging). Needs the prod DB connection string (operator providing).
  - Provision the 2upLatam client + Fernando's membership (weekend task).

**S2, CRM core UI (the "proper CRM").**
  - Modern shell: workspace switcher (from membership, not localStorage), left nav, command surface.
  - Records: company/decisor detail view with the full channel row + activity timeline (messages/actions/notes).
  - Pipeline/board view over stages; the daily **decision cards (Hoy)** as the default "today" surface.
  - Seguimiento folded in as first-class (not a bolt-on tab).

**S3, Automated engine (behind the scenes).**
  - Deploy the orchestrator (sourcing -> deterministic enrich -> cheap-lane brief -> **stricter multi-channel
    gate** -> compose) on a scheduler (Railway/cron), per-client via `icp_config`.
  - Cost Governor + ledger in the loop; reconcile-sends as a scheduled job.
  - Output lands in each client's workspace automatically; the operator approves, does not assemble.

**S4, Intelligence + live assistant.**
  - The "just tell me what happened" assistant (paste/voice -> structured lead + next move), server-side LLM.
  - Response classifier -> per-sector intelligence -> action buttons/playbook that adapt by sector.
  - Admin Lead Library + intelligence write-back (who converts, which channel) = the moat.

## Gap analysis: what makes it a $200/mo MONSTER (2026-09-30)
S1-S4 make the MACHINE work. A client renews at $200/mo when they FEEL + can PROVE the value. The missing
layer is client value, proof & the business model. Added as S5.

**S5, Client value, proof & monetization.**
- **Results / ROI dashboard (the renewal engine):** per client + period, conversations generated, replies,
  MEETINGS booked, closes, conversion by channel + sector, pipeline value. Justifies $200 + wins the 15-day
  review. Highest-value gap. (API groundwork: `/api/metrics`, `/api/activity` built in S1.)
- **Meeting booking + outcome tracking:** meetings are the KPI, so first-class: insert a booking link, log the
  meeting, track meeting -> outcome. Ties the variable fee ($20 meeting / $80 close) to real data.
- **Proactive notifications / daily nudges:** "5 leads due today", follow-up + meeting reminders via
  push / email / WhatsApp, so the client acts daily (the "does work for you" feel). Seguimiento reminders exist; extend.
- **Templates + playbook as a living, in-product asset:** client-facing templates with per-template
  performance, plus the conversion coaching (IG voice-memo close, the human close) surfaced inline. "My brain in a system."
- **Billing + plan tiers + Pro add-on:** in-app subscription (Stripe), base vs Pro, usage/credits, so it scales
  as a product (the Phase-5 monetization, now first-class).
- **Table stakes:** multi-seat per client (memberships already support it; add assignment + per-rep activity),
  and a MOBILE-FIRST surface (clients act from their phone via IG/WhatsApp).

## Fernando / 2upLatam beta (the near-term proof, ~Oct 7)
Runs on S1 + a first cut of S2: his own login (auth/RLS), his workspace with seeded Ecuador leads as daily
decision cards, Seguimiento, and a taste of the live assistant. His auth/profile provisioning = this weekend.

## Deliverability & channel discipline (filtered from a cold-email playbook, 2026-09-30)
Reviewed a volume-cold-email playbook (scrape -> verify -> LLM icebreaker -> sequencer). Kept what fits; rejected what dilutes the model.
- **ADOPT (cheap, high value): an email-deliverability layer in S3.** Before any email send, verify the address
  (deterministic MX/syntax = $0 first; optional MillionVerifier/Bouncer API, ~$0.0004/email, for the ones that
  matter). Track bounces; keep the sender domain warm (EJE already runs MailReach). Protects the client's domain and ours.
- **ADOPT (S3 enrichment): waterfall email + mobile finding.** Chain cheap finder APIs (Findymail / Prospeo /
  Dropcontact, on top of our Hunter/Apollo) until one hits, to raise decisor direct-email coverage AND capture
  MOBILE numbers (feeds WhatsApp + the get-on-a-call motion, our best channel). Build into `enrich-deterministic.py`;
  ~pennies/lead; own it, do NOT buy Clay/leads.io as platforms.
- **ALREADY DOING (the video validates us):** no Apollo / no saturated lists (precise WebSearch + structured
  pools); per-prospect LLM personalization from their own site (the cheap-lane brief writer).
- **DO NOT adopt as core: volume spray from burner domains.** His numbers = ~1.4% reply / ~0.4% meeting = the
  commodity game. Our edge is the opposite: decisor-level, multi-channel (IG/LinkedIn/WA/email), meeting-first
  (IG voice-memo close ~33% reply in Apr 2026, ~10x his rate). We optimize the rate, not the volume. See
  [[project-reply-rate-sender-email]], [[reference-ig-voicememo-close]].
- **OPTIONAL later (client add-on, not core): a sequencer integration** (Smartlead / Instantly / Plusvibe /
  Email Bison) for a client who explicitly wants a volume-email channel, gated behind the deliverability layer.
  Cost: $40-100/mo + domains/inboxes (~$1-3 each) + warm-up. Only if that client's model is volume.

## Status
- S1: tenant tables + clients LIVE on prod; prod DDL access secured (PAT). API layer scaffolded (`api/`). RLS + auth cutover = weekend.
- S2: current `app.html` is the evolve-from baseline (Seguimiento CRM + decision cards shipped). S3: engine scripts exist, not scheduled; deliverability layer to add. S4: brains exist (scripts), not wired.
