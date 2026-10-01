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
- **Per-seat pricing (idea, 2026-10-01 operator, NOT now):** base subscription includes the owner; each ADDITIONAL
  user invited into a client's org = **+$10/mo/seat**. Natural upsell, memberships already model multi-seat; just
  needs seat-count metering + Stripe line item. Park until billing is built.
- **Table stakes:** multi-seat per client (memberships already support it; add assignment + per-rep activity),
  and a MOBILE-FIRST surface (clients act from their phone via IG/WhatsApp).

## UI v2 direction + gamified rewards (2026-09-30, operator)
Reference bar = **Attio + Folk**, but IDENTITY = a **PROSPECTION SYSTEM obsessed with INITIATING conversations
effectively**, NOT a pipeline tracker (it has CRM qualities, that is not its identity). Elevate-on-hover /
"worth clicking" feel throughout. Per section:
- **Hoy = grid of small SQUARE premium contact cards** (logo + little profile), whole report on ONE screen (no
  scroll); a card **FLIPS on open** to reveal all info + the **Contactar** action. Premium color. Framed "X conversaciones por iniciar".
- **Tareas = horizontal + sectioned** (by origin/stage/urgency), whole picture at once, no vertical scroll; buckets + drill-in.
- **Decisores** = leave strong; it is the "go update states" menu, fine as-is.
- **Seguimiento + Vera** (assistant name = placeholder) good; add **proactive update-nudges per card**
  ("lo último que nos contaste fue X, ¿pasó algo? dile a Vera o actualízalo").
- **Plantillas must CALL to action** = the **social-media part**: a browsable feed of the most effective templates
  (yours + other clients', with response rates); **add WhatsApp** channel.
- **GAMIFIED REWARDS (coins):** earn coins for action, **WEIGHTED TO OUTCOMES** (response > send, meeting > response,
  close highest; daily-goal + streak bonuses) so it rewards EFFECTIVENESS not spam. Redeem monthly for **extra
  leads/decisores** (self-reinforcing fuel), a free gadget/perk, or a premium unlock. Persistent coin balance +
  earn micro-animation + a **Recompensas** surface. Drives daily action, excitement, retention = renewal lever.

## Design direction + current-CRM audit (2026-09-30, operator-set)
**Direction:** white/light, modern (like mockup B / Atlas), EVOLVED from the current `app.html` (familiar, not a
reskin shock). **Rule: every section earns its place with ONE clear purpose; simple by default, complex only
where it must be.** Build so a stranger can self-serve, so it converts without the operator selling.

**Current `app.html` sections (1490 lines, views: home/hoy/tareas/decisores/seguimiento/historial/ajustes):**
- **Inicio (Home)** KEEP + wire to real data. Already a proof+nudge dashboard (KPI tiles, streaks, goals, autopilot
  line). Feed it `/api/metrics` instead of static numbers. This IS the S5 Results layer. Purpose: "tus números + qué hacer hoy."
- **Hoy** KEEP. Daily decisores to contact, one click. The heartbeat.
- **Tareas** KEEP. Follow-ups due.
- **Decisores** KEEP + add activity timeline (`/api/activity`) to the card. Searchable decisor database.
- **Seguimiento** KEEP + elevate. Manual leads + home of the LIVE assistant (`/api/assistant`, now wired).
- **Historial** MERGE -> CUT. Report-era framing; move who-responded/results-over-time into Inicio/Resultados; drop the batch list.
- **Ajustes** EXPAND HARD. Today just account/theme/logout. Becomes the SELF-SERVE hub: sector/ICP, geos, channels,
  team seats, plan/billing. This is what lets it convert without sales.

**ADD (new sections, each one purpose):**
- **Plantillas** (operator's flagship idea): templates per channel (IG/email/LinkedIn), TUNED BY THE ASSISTANT on
  request ("hazlo más humano"); each template accrues its OWN response rate; and CROSS-CLIENT INTELLIGENCE, suggest
  templates other same-sector clients use with their response % ("estudios como el tuyo usan esta, 31%"). Moat + renewal reason.
- **Agenda** (near-future, simple v1): one timeline of the whole operation, meetings booked, scheduled sends,
  follow-up dates, so the CRM is aware of the client's operation. Park it; not now.

**Target = 7 sections:** Inicio/Resultados · Hoy · Tareas · Decisores · Seguimiento · Plantillas · Ajustes (+ Agenda later).

## Demo-as-product: self-expiring demo workspaces (the SALES mechanism) — 2026-10-01, operator
**Problem:** sending demo PDFs is confusing. An unqualified prospect can think "the product = a guy who emails me
PDFs of leads daily," which undersells the system and can kill the sale (operator may not always be there to explain).
**Fix: the demo IS the product.** Give each prospect a LIVE, time-boxed demo workspace inside the real UI, seeded
with THEIR OWN enriched decisores (the premium per-prospect cards we already prove we can build).

**Mechanic (reuses the whole tenancy spine — a demo is just a role + an expiry):**
- **Self-expiring demo tenant.** A real `client_id` + a `demo` membership carrying `expires_at` (~24-72h). After
  expiry, login shows "demo terminada, suscríbete" (enforced at `/api/me` + every endpoint: reject/limit if expired).
- **Lives inside the real system** (same `app.html`, same `/api`), NOT a separate HTML. It looks legit because it IS the product.
- **Hoy unlocked** = they see their daily decision cards (their real enriched leads). The "aha."
- **Other sections = glimpse + paywall.** Clicking Tareas/Decisores/Seguimiento/Plantillas shows an attractive
  BLURRED preview + "Disponible con tu suscripción" (FOMO: they see how much more there is).
- **Limited assistant.** The agent is visible and answerable ~2 questions (capped by role), so they feel the "an agent works for you" layer.
- **Pay-to-unlock.** Banner/CTA → (future) Stripe link → on payment, role flips `demo`→`member`, everything unlocks.
- **Burner provisioning.** One command spins up a demo for a prospect: create client + `demo` membership (expires_at)
  + load their enriched leads + issue a login (Google/password). Operator-run, seconds.

**Role model (one UI, role-driven):** `admin` (you)=see-all + spin up demos · `member` (Fernando, paid)=full workspace ·
`demo` (prospect)=Hoy + blurred teasers + capped assistant + countdown + unlock CTA. The SAME cutover built for
Fernando powers demos — build once. Replaces the PDF as the primary demo; PDF = optional leave-behind.
Ties to [[project-eje-crm-lead-library-model]], S5 monetization (Stripe), and the proven per-prospect enrichment.

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
- **ENRICHMENT = self-escalating PARALLEL waterfall (the "beast").** Never a straight line that stops at the first
  miss. Each contact escalates through avenues that FAN OUT in parallel and get cheaper-LLM help on messy pages:
  Apollo people/match (verified + personal-email reveal) -> Hunter domain-search (pattern + named people, cracks
  SMEs) -> site/subpage parse (/contacto /nosotros /equipo) -> **cheap-LLM extraction of fetched page text** ->
  IG/FB bio -> LinkedIn -> NEW SOURCE POOLS (chambers, sector directories, press, job boards). Proven 2026-09-30
  on the 3 client demos: Apollo cracked big corporates (Nano 7/8), was thin on MX pymes (GrupoDúo 2/9) exactly as
  briefed, and the deep Hunter+site pass recovers the pyme gaps. **Bottlenecks are the roadmap:** each avenue that
  keeps failing for a segment tells us the next tool/source to add. This is the enrichment "department"
  ([[project-eje-operating-model-agent-departments]], [[feedback-exhaustive-enrichment-loop]], [[feedback-reverse-engineer-new-source-pools]]).
- **ALREADY DOING (the video validates us):** no Apollo / no saturated lists (precise WebSearch + structured
  pools); per-prospect LLM personalization from their own site (the cheap-lane brief writer).
- **DO NOT adopt as core: volume spray from burner domains.** His numbers = ~1.4% reply / ~0.4% meeting = the
  commodity game. Our edge is the opposite: decisor-level, multi-channel (IG/LinkedIn/WA/email), meeting-first
  (IG voice-memo close ~33% reply in Apr 2026, ~10x his rate). We optimize the rate, not the volume. See
  [[project-reply-rate-sender-email]], [[reference-ig-voicememo-close]].
- **OPTIONAL later (client add-on, not core): a sequencer integration** (Smartlead / Instantly / Plusvibe /
  Email Bison) for a client who explicitly wants a volume-email channel, gated behind the deliverability layer.
  Cost: $40-100/mo + domains/inboxes (~$1-3 each) + warm-up. Only if that client's model is volume.

## Card / enrichment display STANDARDS (locked 2026-10-01, operator QA on the 2upLatam beta)
Non-negotiables for every lead card in-product (and in any demo). A card that fails these is not shippable:
- **LOGO IS A HARD GATE (operator, 2026-10-01).** A lead does not enter any client's system without a resolvable
  logo. Source order: stored `lead_data.logo` (resolved at enrich) -> **unavatar.io/<website-domain>** (works for any
  site; this is why the enrich gate must require a website/logo source) -> premium brand-gradient monogram ONLY as the
  explicit last resort for genuinely logo-less leads (e.g. IG-only pymes with no site). Never a blank/empty tile.
  Regression caught 2026-10-01: switching avImg to stored-only dropped the unavatar runtime source and blanked all
  160 EJE leads' logos -> restored. Enforce logo-presence in `enrichment-gate.py` as a blocker.
- **No dead links, ever.** Every clickable link (website + Instagram) must resolve LIVE. Link-liveness is an
  in-product standard, not just a report gate: validate on enrich, drop/null anything that 404s or won't connect
  (caught on beta: blossomspaibarra.com dead -> website nulled). Soft-404/parking pages count as dead.
- **Links never overlap or wrap mid-word.** Don't render the full URL/email as wrapping text; truncate to one line
  with ellipsis (clickable, title on hover). Fixed 2026-10-01: `.c-rail/.tab-panel .v .link` now nowrap+ellipsis.

## Reliability crons — TIERED (grounded 2026-10-01, operator) — the core of the service
The product's promise is an ACCURATE daily task queue. That only holds if a scheduled job keeps it true;
doing it by hand drifts (proven: EJE's own `eje` workspace stopped logging 09-30 while sends continued, so
Tareas looked empty though 10 IG DMs were actually due). Two tiers:
- **Premium (EJE's own account + premium clients): email + task cron.** Reads the client's mailbox (IMAP),
  reconciles real sends -> platform (first-touch AND follow-ups), advances the cadence, flags double-send
  risk, recomputes due tasks. This is the full `reconcile-sends.py` loop, extended + scheduled.
- **Normal clients: task-check cron (DB-only).** No mailbox access needed. Recomputes the cadence/due tasks
  from existing data, advances stages, fires daily nudges. Lighter, universal, cheap. **This IS the service**
  for the base tier — the client always opens the app to a correct "what to do today."
- **Build:** extend `scripts/reconcile-sends.py` (also match follow-up subjects "feedback"/"no recibí tu
  feedback"; widen scope beyond status=none so a lead advances touch-by-touch; write clean `sent_at`), then
  SCHEDULE it. Home for the Python reconcile = the existing Railway daily automation ([[project-automation-deployed]]);
  the DB-only task-check can be a Vercel Cron -> `/api/cron/task-check`. Per-client config in `clients.icp_config`
  (which tier, whether email creds exist). This is S3 made concrete.

## Cadence gap to fix (grounded 2026-10-01): ISEJE has NO re-touch, 57% of pipeline dead-ends
`cadNext`/`cadOf` in app.html: EJE cadence = 1er email -> IG DM (+2d) -> 2º email (+5d), then `if(ISEJE &&
touches>=3) return {kind:'stop'}`. So after ~1 week every lead that didn't reply STOPS forever. Live check on
`eje` (2026-10-01): due 0 · soon 10 · upcoming 42 · **stop 91** · first 2 · replied 11 · loom 3 · meeting 1.
91/160 (57%) are permanently stopped. Fix: add a monthly re-touch (touch 5+, 30d) for ISEJE too (the cadence
already defines "Mensual" for n>=5; the stop-at-3 short-circuits it) OR a sanctioned Plan A revival sweep. This
is the biggest lever on EJE's own pipeline volume and applies to clients. See [[project-second-chance-top-tier-campaign]].

## Hoy must look DIFFERENT from Decisores — dumb-proof (operator, 2026-10-01, CONFIRMED next build)
Today both render the same list, so a new user can't tell the tabs apart = red flag / not dumb-proof. Fix: Hoy becomes
a **grid of premium square cards** ("X conversaciones por iniciar hoy", logo + decisor + channel + prominent
**Contactar** action, action-first, one screen). Decisores stays a compact searchable **list** (browse/update the
whole database). The visual split alone teaches "Hoy = what I do today" vs "Decisores = my contact database". This is
the approved flip-card Hoy (see UI v2 direction) and is the NEXT build toward a working beta.

## Immediate UI fixes queued (grounded 2026-10-01)
- **Admin workspace switcher must list ALL /api/me workspaces** (currently only the hardcoded `eje` ws-opt shows,
  so an admin can't reach 2uplatam/eje_productoras from the dropdown).
- **Tareas must surface "today/soon" tasks, not hide them behind an empty "Urgentes" (overdue) panel** — the queue
  reads as empty when 10 IG DMs are due today. "Due today" != "overdue".

## Status
- **S1 backend spine: DONE + verified on prod (2026-10-01).**
  - API layer BUILT + DEPLOYED (`/api/health` live, service key in Vercel). Endpoints: me, leads, metrics,
    activity, mark-sent, notes, status, tracked-leads, assistant, classify. Tenant isolation enforced in
    API code (token -> memberships -> scope to clientIds), works pre-RLS.
  - `clients` live: eje, eje_productoras, 2uplatam. `icp_config` is a COLUMN on `clients` (not a table).
  - **2upLatam beta provisioned:** 19 Ecuador seed leads loaded (client_id=2uplatam, status:new, approved,
    score 8-9, owner/IG/WhatsApp/hook in lead_data). Fernando auth user `2ea2c849...` (contactar@2uplatam.com,
    email_confirm) + membership (2uplatam, member).
  - **Membership model cleaned (was a trap):** the only admin membership was `admin@eje.test`, NOT the real
    operator emails. Fixed: ejofreeyzaguirre@gmail.com + contact@ejetheagency.com + emilianoeyzaguirre1@gmail.com
    all now `eje` admin (see-all). Scarlett excluded (UnaBase = former client).
  - **Auth DECISION (2026-10-01, revised): Google sign-in + email/password** — the real-CRM pattern (HubSpot/
    Pipedrive/Attio), NOT magic-link-only (that was overstated; passwordless-only is a consumer pattern). Google =
    one-click primary (button ALREADY in app.html ~line 666, just enable the Supabase provider + a Google OAuth app);
    password = universal fallback (already proven in crm.html). Email provider ON, `site_url=.../app.html`,
    `uri_allow_list` set. FULL cutover (no browser secrets, reads via /api) executed INCREMENTALLY view-by-view.
- **UI cutover increment 1 SHIPPED to prod (2026-10-01):** email/password + Google login; membership-driven
  auth via `/api/me` (hardcoded allowlist removed); per-tenant cache + purge-on-account-switch; real logos
  (stored lead_data.logo) + premium monogram fallback; contact-link truncation. Operator login set
  (contact@ejetheagency.com, admin). **Live at https://app.ejetheagency.com** (custom domain + SSL, Supabase
  auth re-pointed; unabase-app.vercel.app 307-redirects). Reconcile run once (10 today-sends logged).
- **Cutover remaining:** (a) admin workspace switcher from `/api/me` (only hardcoded `eje` shows now);
  (b) route CLIENT reads through `/api/leads` with the token (no RLS yet, so direct anon reads don't isolate);
  (c) role-driven demo gating (Hoy + blurred teasers + capped assistant + expiry). RLS = defense-in-depth after.
- S2: current `app.html` is the evolve-from baseline (auth gate + Seguimiento CRM + decision cards already exist).
  S3: engine scripts exist, not scheduled; deliverability layer to add. S4: brains exist (scripts), not wired.
