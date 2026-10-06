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
- ✅ Follow-up templates (IG / LinkedIn / email-followup) now **per-client** (app uses `lead_data.instagramDM/linkedinDM/followupEmail` for non-EJE; publish merges from `icp_config.outreach_ig/_linkedin/_email_followup`). **2uplatam done in Fernando's consulting voice** + 45 cards backfilled. Demos (somoshobby/nanovideos) can get theirs the same way when wanted.
- 🔄 **Factory run triggered manually (~01:30 UTC Oct 6) for 2uplatam** — 8h early so recovery + data land tonight. Awaiting results (candidates_promoted / reenriched / new READY / spend).

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
- **LIBRARY FINDING #1 (2026-10-05, the leak):** `enrichment_findings` has **366 real `email_candidates` (scraped from sites — NOT guesses) but only 50 verified `email`s.** The factory finds emails then drops them. Also: Hunter/Apollo produce ZERO findings (not running / not logged).
- ✅ **FIX SHIPPED — `promote_candidates`** (commit 6425cc4, wired into nightly BEFORE re-enrich): verifies a lead's found candidates + attaches the deliverable one to the decisor → READY. Honest, no guessing. **Recovers 12 of Fernando's parked leads** (those with decisor + candidate) autonomously tonight, and stops new leads dropping their found email.
- **REMAINING for Fernando's 20/day (honest gap):** **72 no-decisor** (decisor-finding) + **~25 decisor-but-no-candidate**. The re-enrich (site_decisor) swings at the 72 tonight; `promote_candidates` at the candidates. Measure after the nightly.
- **LIBRARY FINDING #2 (2026-10-05, route yield is ICP-specific):** Hunter/Apollo/Prospeo are all WIRED (not broken) but barely spend (apollo $0, hunter $0.64) because they **don't cover tiny Ecuadorian businesses** (they index bigger/US firms) and the chain is free-first. **Conclusion: paying them more will NOT find Fernando's emails** — his emails are on the leads' own sites (site path wins). For Altavia (US) the paid finders ARE the right tool. So the route-registry/selector must learn **route yield PER ICP** (ES-small-biz → site candidates; US → Hunter/Apollo). This is the first concrete entry for the Library's route-intelligence.

---

## NEXT BUILD — profile-aware FIT score (the "best-lead signals" doctrine)
The "fit" number is a dumb binary checklist: it clumps (28 leads at 72 = same boxes checked), caps ~72, and
PENALIZES un-mined/ICP-irrelevant data (no LinkedIn/phone = -points, even though we never looked / a tiny Ecuador
biz isn't expected to have them). Operator rule: **never score a lead down for data we didn't mine.** Fix = BOTH:
1. **Profile-weighted fit** (config-driven from `icp_config`): weight what THIS client cares about — e.g. 2uplatam = decisoras mujeres (gender) + owner seniority + geo. Tested scorer already spreads 2uplatam 12→72 across 10 distinct values (vs 28 clumped at 72); female owners rank top.
2. **Per-profile NORMALIZATION:** denominator = criteria that matter for the profile AND are evaluable; exclude un-mined/irrelevant channels so a strong lead reads ~90, not 72 ("72 should read ~8.5/10").
3. **Mine the missing signal:** IG follower count (we have handles, 0 counts) — differentiates + legitimately raises strong leads. Add as an enrichment step.
4. Wire the fit score into publish (replacing the checklist for the "fit" display); keep enrichment-completeness as the READY gate, separate from fit.

## STILL OPEN (pending builds, newest first)
- **Note + note-analyzer:** add a free-text NOTE on the lead card (notes table exists + sbNoteWrite); then the system smartly READS it (cheap LLM) to understand the lead's situation + recommend next actions. (Memory had this as "note-analyzer pending".) Note-UI = quick; analyzer = real LLM build.
- **Profile-aware FIT** (see NEXT BUILD above): profile-weighted + per-profile normalization + follower mining.
- **Factory run (bli1hkyud)** finishing for 2uplatam → when done: re-run `release.schedule('2uplatam')` to drip new leads + measure recovery (promote_candidates / reenriched / new READY / spend).
- **Demos' follow-ups** (somoshobby/nanovideos IG/LinkedIn/email) — replicate the 2uplatam pattern when wanted.

## SESSION LOG (one line per session; newest first)
- 2026-10-06 (cont. 3): Report SLA = exactly today's 20 (client Hoy ==today; recorded in CLIENT_2UPLATAM.md). Profile-aware FIT shipped (fit.py, wired into publish): 2uplatam re-scored 20-93 (was clumped 72). 2uplatam set access=full (nightly publishes+drips it). CONTINUOUS factory loop RUNNING for 2uplatam (bg task b8vdp2jey, every 20m, FD caps govern) for evidence — temporary evidence-gather, NOT the permanent Phase-2 architecture; deactivate via TaskStop on operator word. First manual run: 23 discovered, ~8 new READY, $0.55 (old code, pre-recovery-steps).
- 2026-10-06 (cont. 2): TSA enforced as the HARD surface gate — no client sees a lead without named decisor + verified email (guarded at publish+drip+display; tsa.py). Cleaned 2uplatam surface (4 junk deleted, 11 incomplete held); released-missing-data now 0. Note feature requested (pending). Fit calibration decided (profile-aware = next build).
- 2026-10-06 (cont.): Per-client follow-ups (IG/LinkedIn/email) wired for non-EJE + 2uplatam in Fernando's voice. Fit STALE-SCORE fixed (re-score at publish: 2uplatam 7-9 -> 32-72). Daily-report DRIP shipped (release.py: 20/day dated releases from go-live + app gate holds future; 2uplatam dated Oct7=20/Oct8=6). Email-bounced button shipped. UI render verified (WebFetch: shell clean). Triggered factory run for 2uplatam (bli1hkyud, running). NEXT BUILD logged = profile-aware FIT (profile-weighted + normalize + follower mining). PENDING: re-run release.schedule('2uplatam') after the factory run finishes (to drip new leads) + measure recovery.
- 2026-10-05: Cadence overhaul (5-touch, off-by-one fix, no-email-fallback, LinkedIn=5th, 1-msg gendered re-toque, client roster). Publish bridge (factory→app) for full-access + 2uplatam. Outbound send reconcile wired. Template floor + sector templates (Hobby/NanoVideos/2uplatam). 2uplatam offer grounded + pitches flagged. somoshobby demo unbanned. Factory re-enrich-parked deployed. FACTORY-VISION.md + PLAN.md written. DECISIONS LOCKED: no email-guessing (email mandatory, factory must FIND it; IG = clue not substitute), continuous-running NOT yet, Library FIRST. Library assessed = ~70% built + dormant (enrichment_findings 2755, brain/route-registry is the gap). Saved 2 Seguimiento leads (Diego Palermo/Academia SomoS demo Oct 12; Daniel Cárdenas/Data Insights demo Oct 7 3:30). NEXT: route-yield read layer over enrichment_findings.

---

## HOW DRIFT WORKS (so we never lose the anchor)
Daily tasks (a Fernando fire, a template, a bug) are TRACK A. Do them, log them in TRACK A, then return here.
The strategic build is TRACK B. Whenever a session has spare capacity, it advances the lowest-numbered unblocked
Track-B phase. "Where do we stand" is always answerable from TRACK A status + the current Track-B phase + RIGHT NOW.
