# PLAN — the anchor (read this first, update it last)

**Purpose:** the single place that answers "where do we stand right now?" at all times, even when we drift into
daily tasks. If this doc is current, a new session spends zero tokens re-deriving context.

**The discipline (non-negotiable):** at the END of every session, update this file — move items between
status buckets, refresh "RIGHT NOW," and append one line to the SESSION LOG. No session ends without it.
Repo-only (never the Claude memory folder). Specs live in their own docs; this file holds **status + position**, not detail.

**The specs this anchors to:**
- `docs/FACTORY-VISION.md` — the factory doctrine (departments → architecture). = CRM slices S3+S4, in depth.
- `docs/CRM-PROJECT.md` — the product build spine (S1 infra → S2 UI → S3 engine → S4 intelligence → S5 proof).
- `docs/PRODUCT-BRIEF.md` — zero-context overview (strengths / gaps / clients).
- `docs/ENRICHMENT_MASTER_PLAN.md` — earlier backend plan (reconcile into FACTORY-VISION over time).

Status legend: ✅ done · 🔄 in progress · ⛔ blocked (on a decision/dep) · ⬜ not started

---

## TWO TRACKS (we are always on one; never let A starve)

### TRACK A — Fernando / daily revenue (the only paying client; protect it)
The drift track. Daily ops to keep 2uplatam producing + served. Timeline: live ~Oct 7.
- ✅ 2uplatam templates wired on the REAL offer (consultoría→acompañamiento+capital), composer grounded, 29 off-offer AI pitches cleared + flagged for recompose, 45 cards backfilled.
- ✅ Factory re-enrich of parked leads deployed (runs nightly).
- ⛔ **20 READY/day** — blocked. Root cause: yield (~10%). Homepage extractor barely helps 2uplatam (sites expose no emails: 0 personal, 1 JSON-LD of 109). The real lever = **email-pattern pivot** (guess+verify) — **operator decision pending** (quality call). Second lever = **discovery refill** (queries drying up).
- ⬜ Recompose the 29 2uplatam pitches on the corrected offer (after composer grounding confirmed).
- ⬜ Follow-up templates (IG / LinkedIn / email-followup) per client — currently fall back to EJE/Scarlett voice (wrong). Drafts pending operator review.

### TRACK B — the Factory + CRM (the compounding product)
The strategic build. Order chosen so each phase makes the next compound.
- **Phase 0 — S1 infrastructure** ⛔ *prerequisite for everything multi-tenant.* Backend API (keys server-side), auth + RLS multi-tenant on PROD, provision clients. Needs the prod DB connection string from the operator. Without this: no Aduana (cross-client dedup), browser still holds the anon key, can't scale. **This gates the full vision.**
- **Phase 1 — The Library / Memory (the brain)** 🔄 STARTED. **Finding (2026-10-05): ~70% already built + dormant.** `enrichment_findings` (2,755 rows: field/value/source/strategy_id/confidence/cost), `engagement_events` (431), `playbook_runs` (157), `icps` (5), `signals`/`corroborations` populated. **The gap is the BRAIN, not the tables:** `strategies` is EMPTY (no route registry, though findings reference strategy_id), and NOTHING reads the 2,755 findings to rank routes ("which route finds emails best, for which ICP, at what cost"). Work = ACTIVATE, not construct. Bricks: (1) route-yield read layer over `enrichment_findings`; (2) populate/define `strategies` as the route registry; (3) route-selector miners consult; (4) 3-rate instrumentation (named/emailed/replied per route+ICP). (= CRM S4 foundation.)
- **Phase 2 — Continuous running + feedback bus** ⬜ flip `run_nightly` (cron) → persistent workers draining the queue all day + department cycles on timers, FD caps as the governor. Plus the bus so departments talk (TSA→Innovations, Design→Innovations, Writers→Innovations). (= CRM S3 deepened.)
- **Phase 3 — Self-improving departments** ⬜ FD **quality veto** (4th gate) + FD-approved scaling; TSA ≥3-channel completeness gate + drift→Innovations loop; Committee value-based premium selector; Innovations real cross-agent learning (the hardest build). (= CRM S3/S4.)
- **Phase 4 — Intelligence + safety** ⬜ Response Intelligence (**optimize for CLOSES not replies** — needs operator outcome signal); Aduana (do-not-contact + cross-client collision); Caducidad (re-verify + expire stale cards); Deliverability (protect the CLIENT's account). (= CRM S4.)
- **Phase 5 — Value / proof / monetization** ⬜ ROI dashboard (conversations→replies→meetings→closes), meeting booking + outcome tracking, operator-engagement supervision/churn alert. This is what makes $200/mo renew. (= CRM S5.)

---

## RIGHT NOW (the single most current truth)
- **Decisions LOCKED (2026-10-05):**
  1. **NO email guessing.** Email is MANDATORY — no lead ships without a verified one. The factory must FIND the real email; Instagram is a *clue to find it*, NOT a substitute channel. (I had misproposed an IG-only gate — rejected.)
  2. **Continuous running: NOT YET.** It amplifies weak work; sequence it after the brain + yield fix.
  3. **Build order: THE LIBRARY FIRST.**
- **In progress:** Library Phase 1. Found it ~70% built + dormant (see Phase 1). **Next brick = the route-yield read layer** over `enrichment_findings` (2,755 rows): rank which routes/sources find emails + decisors best, per ICP, at what cost. Then populate `strategies` (the route registry), then the selector the miners consult, then 3-rate instrumentation.
- **Fernando bridge (Track A, honest — no guessing):** the durable fix is the Library teaching the factory to FIND the 59 IG-having leads' real verified emails (IG handle as the path + tier2 Hunter/Apollo, FD-approved premium spend). Not gate-lowering, not guessing.
- **LIBRARY FINDING #1 (2026-10-05, the leak):** `enrichment_findings` has **366 real `email_candidates` (scraped from company sites — NOT guesses) but only 50 verified `email`s.** The factory FINDS emails then drops them — no step verifies candidates + promotes them to the contact. **49 of Fernando's 109 parked leads already have a found candidate on file.** Also: Hunter/Apollo produce ZERO findings (not running / not logged). **NEXT BRICK = a `promote_candidates` factory step: verify a lead's found candidates (MillionVerifier) → promote the deliverable one → READY.** Honest (completes the factory's own work), recovers ~49 for Fernando, fixes the leak system-wide.

---

## SESSION LOG (one line per session; newest first)
- 2026-10-05: Cadence overhaul (5-touch, off-by-one fix, no-email-fallback, LinkedIn=5th, 1-msg gendered re-toque, client roster). Publish bridge (factory→app) for full-access + 2uplatam. Outbound send reconcile wired. Template floor + sector templates (Hobby/NanoVideos/2uplatam). 2uplatam offer grounded + pitches flagged. somoshobby demo unbanned. Factory re-enrich-parked deployed. FACTORY-VISION.md + PLAN.md written. DECISIONS LOCKED: no email-guessing (email mandatory, factory must FIND it; IG = clue not substitute), continuous-running NOT yet, Library FIRST. Library assessed = ~70% built + dormant (enrichment_findings 2755, brain/route-registry is the gap). Saved 2 Seguimiento leads (Diego Palermo/Academia SomoS demo Oct 12; Daniel Cárdenas/Data Insights demo Oct 7 3:30). NEXT: route-yield read layer over enrichment_findings.

---

## HOW DRIFT WORKS (so we never lose the anchor)
Daily tasks (a Fernando fire, a template, a bug) are TRACK A. Do them, log them in TRACK A, then return here.
The strategic build is TRACK B. Whenever a session has spare capacity, it advances the lowest-numbered unblocked
Track-B phase. "Where do we stand" is always answerable from TRACK A status + the current Track-B phase + RIGHT NOW.
