# EJE Platform — Product Brief (for someone with zero context)

_Last updated: 2026-10-05. This lives in the repo (not memory/cloud). Refresh it when the state changes._

---

## 1. What this is, in one paragraph

**EJE is an appointment-setting / lead-generation agency.** Its product is a **system that turns a client's "ideal customer profile" (ICP) into a daily, disciplined outreach routine.** Every day it hands the client a short list of the right decision-makers to contact (verified name + email + social channels + a ready first message), and walks them step-by-step through a multi-touch sequence across email, Instagram, and LinkedIn. **EJE does not auto-send** — the client's team sends with one click per step. The promise is not "a CRM" and not "more leads"; it's **"the most actionable conversation generator"**: the right contacts, the right channel, the right message, and the discipline to actually execute, so conversations (and sales) happen.

The same codebase also carries **EJE's OWN outreach** (EJE selling itself to new agency/studio clients) and a **retained 931-lead productora database** from a former client (UnaBase), kept as an asset.

---

## 2. The north-star goal (what we are building toward)

- **Be the most ACTIONABLE conversation generator**, not a CRM and not a lead dump. Quality of the next action is the product.
- **The real moat is data + results, not enrichment.** Enrichment (finding emails) is now a ~$0.001 commodity. The defensible edge is **earned response-intelligence** — learning *who converts, on which channel, with which message* — plus **booked results**. 
- **Built for 1000 clients, operator-run (not founder-run), fast and cheap.** Bound every read, isolate every tenant, tier the automation, default to cheap LLMs, and spend the expensive model once to *create a standard* that cheap models replicate.
- **Long-term shape:** the system as **agent-run departments** (sourcing, enrichment, cost-governor, composing, client-admin, lead-library) that a small team operates for hundreds of clients.
- **Premium bar:** output must be better than an operator doing it ad-hoc with Claude on their phone. Having tools isn't the moat; *using them well* (verified grounding + compounding results-intelligence + scale) is.

---

## 3. How it works (plain architecture)

```
  THE FACTORY (backend)                      THE APP (what clients use)
  factory/ — Python, runs nightly on         public/app.html — the live CRM shell
  Railway at 09:00 UTC. Cost-governed.        (app.ejetheagency.com). Login-gated,
                                              one workspace per client.
  discovery -> enrich (free pivots first,
  paid providers last) -> score -> GATE      Reads the legacy `leads` table, keyed
  (deliverable email + real ICP) ->          by company DOMAIN. Shows a daily "Hoy"
  compose a pitch -> READY                   card list + a guided "Tareas" queue +
         |                                   a one-click Send that copies the message,
         v                                   opens the channel, and marks it done.
  client_leads / companies / contacts
  (the factory's own tables)                 Supabase (Postgres) is the shared DB.
         |                                   PostgREST hard-caps reads at 1000 rows.
         v                                   RLS isolates each tenant.
  publish -> writes READY leads into the
  `leads` table so the app can show them  <--- THIS BRIDGE was missing until 2026-10-05
```

Key doctrine: **free fact-graph enrichment first, paid providers only when justified; global + per-provider + per-client spend caps; a nightly credit cap; never auto-send; verify from source.**

---

## 4. The clients today

| Workspace | Who | Status | Pipeline (factory) | On the app |
|---|---|---|---|---|
| **eje** | EJE's OWN outreach (Emiliano) | Active, daily | 20 READY / 59 parked / 160 delivered | 170 leads |
| **2uplatam** | Fernando (Ecuador) | **First PAYING client, go-live ~Oct 7** | 32 READY / 109 parked | 19 (legacy surface) |
| **altavia** | US staffing, sells to law firms | Full access, time-limited to Oct 11 | 36 READY / 90 parked | 36 |
| **somoshobby** | Felipe (branding studio) | **Demo** (just re-activated) | 10 delivered | 11 (no pitches yet) |
| **nanovideos** | Ross | **Demo** | 8 delivered | 22 |
| **eje_productoras** | Retained UnaBase DB | Asset / library (not a live client) | — | 931 |

---

## 5. Strengths (what genuinely works)

- **A real, self-running factory.** It sources, enriches, scores, gates, composes, and reports nightly on Railway without a human, under hard cost caps. Phase-0/1 shipped.
- **A polished, dead-simple client app.** Daily cards, a guided one-click multi-channel sequence, swipe UI, Seguimiento tracker. Clients operate it without training.
- **Verified grounding.** Deliverability is a hard gate (MillionVerifier); source-verified ≠ deliverable is enforced; ICP exclusions filter out global brands / schools / chambers / government.
- **Real traction.** One paying client (2uplatam), two warm demos (Hobby, Nanovideos), EJE's own outreach running, and a 931-lead proprietary database.
- **The operator's real voice and sales motion are captured** (verbatim first-touch templates, the IG re-engagement, the loom funnel) so the system speaks like him, not like generic AI.

---

## 6. Weaknesses / where we are underdeveloped vs the goal

- **The moat itself (results-intelligence + lead library) is largely UNBUILT.** We have the plumbing to source and send; we do NOT yet systematically learn who converts and feed it back. The thing that's supposed to be defensible is the least built.
- **Autonomous cross-agent learning does NOT exist (verified).** The factory is a *fixed pipeline*, not collaborating agents that teach each other. Lessons are applied only when the human wires them in. We must not claim otherwise.
- **The factory→app bridge was missing** until this session (fixed for full-access clients). It revealed that "the factory produces, but clients don't see it" was a structural gap, not a one-off.
- **Task-queue accuracy is fragile.** The platform only knew about sends made *inside* the app; anything sent from a mailbox drifted, and the one reconcile script was silently RLS-broken. Being fixed, but it shows the "accurate queue = the service" promise wasn't yet guaranteed.
- **Composer quality is uneven.** Some clients' leads reach the app with *no pitch message* (somoshobby), which makes a demo look empty. Per-lead dossier + pitch quality is not uniformly enforced.
- **Data gaps weaken the multi-channel promise.** LinkedIn URLs exist for only ~28 of 170 EJE leads; countries and signals are often missing — so "LinkedIn touch" or "send at 8am local" silently degrade.
- **No self-serve onboarding.** Activating a client is still manual. The `activate_client()` primitive and structured `icps` table exist but aren't a product flow.
- **Lots of parked inventory.** 2uplatam has 109 parked, altavia 90 — leads that stalled for a missing name/email/channel and have no automatic path back to READY.

---

## 7. Recurring problems (patterns, not one-offs)

1. **Drift between reality and the platform.** Work done outside the app (mailbox sends, manual LinkedIn) isn't recorded, so the queue lies. Root of "my tasks keep unsyncing."
2. **ICP precision slips.** The factory has repeatedly let off-ICP leads (global brands, schools, chambers) reach READY; each time it needs a tightened, *precise* filter (not blunt rules that also kill real small agencies).
3. **Produced-but-not-surfaced.** The factory computes a result (reports table, READY leads) that no client view actually consumes until a bridge is built.
4. **Off-by-one / counting assumptions.** The cadence miscounted touches because the first email is never logged — small modeling gaps cause wrong, sometimes domain-risking, actions.
5. **Silent breakage under RLS.** Scripts written pre-RLS (anon key) silently return nothing after RLS is enabled — no error, just a quiet no-op.

---

## 8. Recently touched (this session, 2026-10-05)

- **EJE cadence rebuilt to the operator's real doctrine:** 4 main touches (email → IG/WA → email → LinkedIn/alt) + a 5th IG re-engagement; fixed a 3-touch "stop" that had frozen ~95 leads.
- **Fixed a cadence off-by-one** (count the unlogged first email) and made EJE's non-email touches **never fall back to email** — cut redundant-email exposure from ~106 to 1 (domain-burn protection).
- **Built the factory→app publish bridge** (Altavia: 16 stranded leads now visible; auto-runs nightly for full-access clients).
- **Built + wired an outbound reconcile** (Sent folder → platform, by recipient) so mailbox sends stop drifting; backfilling 20 un-logged sends.
- **EJE's own outreach:** 10 A/B first-touch drafts created, wired into the app + Gmail; voice + templates captured.
- **Altavia Codex gate:** 3 of 10 contacts approved to standard (deliverable + small-local ICP), the other 7 documented with reasons.
- **somoshobby demo re-activated** (account was banned to 2126 as the "lock"); timezone/working-hours awareness added to task cards.

---

## 9. To do / where to go next

**Immediate (tied to a client deadline):**
- **Email-pattern pivot** — infer email addresses for 2uplatam's named-but-no-email leads **before Fernando's ~Oct 7 go-live** (unlocks ~20 parked leads).
- **Compose pitches for somoshobby** (and any demo) so the demo isn't empty.

**Near-term (reliability = the service):**
- **Tiered reconcile cron:** the EJE outbound reconcile is done; add a **DB-only task-check** for every client so "today" is always correct on open (no mailbox needed). Clients never drift because they stay in-app; this is the universal safety net.
- **Un-park path:** automatically re-enrich parked leads (find the missing channel) and return them to READY.

**The actual moat (strategic):**
- **Results-intelligence loop + Lead Library:** capture replies/meetings per lead → learn who/which-channel/which-message converts → feed it back into sourcing, composing, and cadence. This is the defensible edge and is the least built.
- **Self-serve activation** (structured ICP → `activate_client()` as a real flow) toward the 1000-client, operator-run target.

---

## 10. What is being left behind (built or planned, now dormant)

- **Outreach playbook engine + learning rollup** — built on prod, reproduces the cadence, but **not wired to the live app** (the app still uses the simpler in-file cadence).
- **The full factory 10-department plan** — partially built; the "agent departments" vision is aspirational, not implemented.
- **Plan A (second-chance campaign), Plan B (quality sourcing), Plan C (WhatsApp/alt-channel)** — specced, on hold.
- **Paid-ads motion to sell UnaBase's SaaS** and the **EJE self-hunt repos** — separate tracks, parked.
- **Fresh sourcing** — the curated productora pool has been dry since ~June; net-new mining in priority markets (ES/MX/CO) is owed.

---

### The one-line read
We have a **working sourcing-and-sending machine with real clients**, and we spent this session making its **task queue trustworthy** and **actually visible to clients**. What still separates us from the north star is the **results-intelligence loop and lead library** — the part that was always supposed to be the moat, and is the part we've built least.
