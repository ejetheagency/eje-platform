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
- **Phase 1 — The Library / Memory (the brain)** ⬜ the #1 missing department. A consultable store of what-source-yielded / what-template-replied / what-signal-worked + per-client voice. Without it every improvement is oral tradition lost on restart. Build first; everything else compounds on it. (= CRM S4 foundation.)
- **Phase 2 — Continuous running + feedback bus** ⬜ flip `run_nightly` (cron) → persistent workers draining the queue all day + department cycles on timers, FD caps as the governor. Plus the bus so departments talk (TSA→Innovations, Design→Innovations, Writers→Innovations). (= CRM S3 deepened.)
- **Phase 3 — Self-improving departments** ⬜ FD **quality veto** (4th gate) + FD-approved scaling; TSA ≥3-channel completeness gate + drift→Innovations loop; Committee value-based premium selector; Innovations real cross-agent learning (the hardest build). (= CRM S3/S4.)
- **Phase 4 — Intelligence + safety** ⬜ Response Intelligence (**optimize for CLOSES not replies** — needs operator outcome signal); Aduana (do-not-contact + cross-client collision); Caducidad (re-verify + expire stale cards); Deliverability (protect the CLIENT's account). (= CRM S4.)
- **Phase 5 — Value / proof / monetization** ⬜ ROI dashboard (conversations→replies→meetings→closes), meeting booking + outcome tracking, operator-engagement supervision/churn alert. This is what makes $200/mo renew. (= CRM S5.)

---

## RIGHT NOW (the single most current truth)
- **Just finished:** the factory vision doc + external-review integration; mapped Factory ↔ CRM Project; built this anchor.
- **The open decisions that unblock the next move** (operator's call):
  1. **Email-pattern pivot for Fernando?** (guess+verify emails — the real 20/day lever; a quality tradeoff you've guarded).
  2. **Flip the factory to continuous running?** (run all day; caps stay as governor).
  3. **Build order for Track B:** start with **the Library (brain)** or **continuous running (work all day while we build the brain)**?
- **Immediate next action (proposed):** decide #1 (Fernando can't hit 20/day without it), then start Phase 1 (Library) as the first Track-B brick.

---

## SESSION LOG (one line per session; newest first)
- 2026-10-05: Cadence overhaul (5-touch, off-by-one fix, no-email-fallback, LinkedIn=5th, 1-msg gendered re-toque, client roster). Publish bridge (factory→app) for full-access + 2uplatam. Outbound send reconcile wired. Template floor + sector templates (Hobby/NanoVideos/2uplatam). 2uplatam offer grounded + pitches flagged. somoshobby demo unbanned. Factory re-enrich-parked deployed. FACTORY-VISION.md + PLAN.md written. Open: email-pivot decision, continuous-running decision, Library build.

---

## HOW DRIFT WORKS (so we never lose the anchor)
Daily tasks (a Fernando fire, a template, a bug) are TRACK A. Do them, log them in TRACK A, then return here.
The strategic build is TRACK B. Whenever a session has spare capacity, it advances the lowest-numbered unblocked
Track-B phase. "Where do we stand" is always answerable from TRACK A status + the current Track-B phase + RIGHT NOW.
