# Nightly automation: make the night factory do today's manual demon-run by itself

**Why this doc exists.** On 2026-10-07 the brain (Claude, directed by the operator) produced BY HAND a 6-day
buffer of 20 fully-enriched premium leads/day for 2uplatam. The autonomous nightly factory, running the same
nights, produced **~0 net-new shippable leads**. This doc is the bridge: (1) the exact micro-routes we used and how
to apply them, (2) how to turn the operator's quality JUDGMENT into context the cheap factory can replicate, and
(3) the honest analysis of what the nightly does NOT run today + the plan to make it run. Hold this against
`docs/PLAN.md` (the anchor) and `docs/manual-run/README.md` (the recipe).

The doctrine that governs all of this (from memory + CLAUDE.md): **expensive once -> cheap replicates.** We spend
the expensive model ONCE to write the standard (rubric + exemplars + gates + routes); the cheap nightly model
replicates it because of the grounding and the gates, not because of a clever prompt. **Never fabricate** (empty
beats invented, no blind email guessing). **Docs = the live machine** (label WIRED vs MEASUREMENT vs WORDS).

---

## PART 1 - The micro-routes we learned today (and how to apply each)

A "micro-route" is one small, learned way to turn what we know (a company name, a site, a decisor name) into one
more real, verified channel. The factory's reason to exist is to RUN lanes, measure per-ICP yield, and double down
on winners (`factory/workers/micro_routes.py` already instruments this: each attempt logs `route:<lane>`, each hit
logs an `enrichment_finding` by source, so `route_yield` ranks lanes per ICP). Today we ran these lanes by hand via
`serper.py` (uncapped Google) + WebFetch. Each one below maps to a lane the nightly must run autonomously.

### A. DISCOVERY lanes (find NET-NEW companies that fit the ICP)
The nightly's only net-new source today is Google Places (`discovery.py`, needs a key). These serper lanes are what
the brain used instead, and what the factory must gain. Try free lanes first; stop when the pool floor is met.

| Lane | serper query pattern | Yields | Notes |
|---|---|---|---|
| sector+geo | `"{sector}" {city} {country}` | company sites | the backbone; rotate cities to avoid repeats |
| directory | `mejores {sector} en {city}` / `directorio {sector} {country}` | listing pages -> many companies at once | association member lists are gold |
| instagram-first | `site:instagram.com {sector} {city}` | IG business profiles -> bio -> site + WhatsApp | best for consumer pymes (IG-native) |
| registry/edge | funding registries, award rosters, co-pro markets, chamber directories | structured pools | the "reverse-engineer a new pool" rule: when a lane dries, open a NEW structured pool, do not re-search the same way |

Discipline: **dedup on domain BEFORE paying** for anything (the global `id`/`dedupe_key` is the guard). **Exclude
chains/franchises** before enriching (`icp_filters.is_chain`). A company with no real website is not a lead by
default (TSA real-website gate), except per-client exceptions (2uplatam) which are declared, never fabricated.

### B. ENRICHMENT lanes (fill every real channel on a company that passed discovery)
Run ALL of these on every surviving company. **No empty core channels** = a card ships only with >=2 (ideally 3-4)
real channels. Exhaust free routes before paid.

| Channel | How we found it (route) | Gate / honesty rule |
|---|---|---|
| named decisor | site about/"equipo"/"nosotros", IG bio, LinkedIn, press | owner/GM/CFO/partner, PERSONAL, not a role inbox; **no name = no card** (hard gate) |
| email | site contact-page scrape -> serper `"{name}" {domain} (email OR correo OR contacto)` -> MV-verify | accept valid/accept_all/unknown, never `invalid`; no blind pattern guessing (locked) |
| WhatsApp | site `wa.me`/`tel:` scrape -> serper `"{company}" whatsapp` -> IG bio link -> footer phone | ONLY `wa.me`/mobile; NEVER a landline shown as WhatsApp, NEVER a group-invite (`chat.whatsapp.com`) as a DM. ~53% yield on 2uplatam pool |
| Instagram | `site:instagram.com {brand}` -> site footer IG icon -> serper `"{company}" instagram` | real business profile only |
| LinkedIn (person) | `site:linkedin.com/in {decisor} {company}` -> company page "people" | the decisor's own profile |
| LinkedIn (company) | `site:linkedin.com/company {company}` | lights the company LinkedIn rail |
| 2nd decisor | site team page -> LinkedIn company people -> a second named role | real second person, else leave empty (hide the tab) |
| logo | scrape site `apple-touch-icon` -> `google.com/s2/favicons?domain=X&sz=128` fallback | Clearbit is DEAD (DNS fails). Every lead needs a logo |

### C. COMPOSITION lanes (what the brain WROTE per lead)
These are generative, cheap-LLM (Haiku via `cheap_llm.generate(..., judge=True)`), grounded on the scraped facts.
`cheap_llm.generate` returns a DICT `{provider, text}` - extract `res["text"]` (we lost a whole run to passing the
dict through once).

| Field (stored in `lead_data`) | What it is | Rule |
|---|---|---|
| `ofrecen` phrase | one line: what THIS company offers, for the networking email's first sentence ("vi que ofrecen {X}") | from site hero / IG bio; specific, not generic |
| 4-part intel brief (`Nota`/Inteligencia) | what they do, a recent first-party signal (why-now), a size/traction cue, the hook | the hook-fact rule: a fact may OPEN only if offer-relevant + recent (<=90d) first-party + phrased as an observed moment, never a compliment |
| `pitchEmailES` | the first-touch email, networking or sales by `purpose` | 2uplatam networking template (Fernando's spirit) with `{ofrecen}` filled; keep it SHORT |
| `whatsappMessage`, `instagramDM`, `linkedinDM` | the per-channel first touch | channel-appropriate length/tone |
| `followupEmail` | the +7d touch | |
| `purpose` | `networking` or `sales` | drives which template the app renders; today all 2uplatam = networking |

### D. FINALIZE lanes
- **Score** with the floor formula (never ship a raw 0-100 factory score; an "8" is nonsense and sorts wrong):
  `60 + email8 + whatsapp10 + instagram6 + linkedin8 + additionalContacts8 + brief4`, cap 99, floor 60.
- **Stage** with a future `source_date` + `approved=true` -> the app auto-releases 20/day at 8 AM Santiago (no cron
  "sends"). Keep **>=3 business days** staged forward as insurance.

### Honest structural limit to encode (do not fight reality)
- **Consumer pymes** = IG + WhatsApp ~100% reachable.
- **Academics / universities / B2B institutions** = no personal IG, rarely a direct WhatsApp (admisiones group
  links only). Their channel floor is **LinkedIn + email + faculty/role line**. The gate must be sector-aware, not
  one-size: demanding IG+WhatsApp on a university lead would kill good leads for a channel they structurally lack.

---

## PART 2 - Making the operator's BRAIN the factory's context (quality sense, encoded)

The gap is not tools. The factory already has serper, MV, a cheap-LLM lane, scoring, gates. The gap is **judgment**:
the brain knows what a premium ready-to-contact card looks like, which decisor is the RIGHT decisor, what counts as
"demon enrichment", and what is instant junk. Autonomy means encoding that judgment as **committed artifacts +
deterministic gates + a cheap judge**, so the nightly reaches the operator's own bar with no one watching.

Five layers, in priority order:

1. **The QUALITY RUBRIC (committed doc, per concern).** Write down, explicitly:
   - ICP-fit per client (what 2uplatam's right company looks like; signals that make a lead "best" per
     `icp_config.signals` - IG followers for productoras, funding/traction for tech, etc.).
   - Right-decisor definition (owner/founder/CEO/partner, personal reachability; NOT creative director, NOT a role
     inbox).
   - "Demon enrichment" definition (the Part 1.B/1.C channel + composition checklist that must be attempted on
     every lead).
   - Instant-kill list (no name, no real website unless declared exception, fabricated anything, invalid email,
     landline-as-WhatsApp, group-link-as-DM, chain/franchise, ICP drift).

2. **GOLD EXEMPLARS (committed).** Save 3-5 of today's real premium cards verbatim as the standard the cheap model
   imitates. "Expensive once -> cheap replicates" only works if the exemplars are committed artifacts, not a memory
   of a good run. Pair each with a one-line "why this is premium".

3. **HARD GATES (deterministic, in code - already partly there).** Judgment is fallible; gates are not. Enforce in
   the pipeline: named decisor (`agent_miner.publish_batch` no-name gate), >=2 channels, MV-verify, real website
   (TSA), logo present, floor-score, no-fabrication. These catch what the LLM's judgment misses. `tsa.py` already
   enforces "no READY card without a verified email".

4. **A JUDGE PASS (cheap LLM, grounded on the rubric + exemplars).** After assembly, before publish, score each
   card against the rubric: ICP-fit? right decisor? channels real and >=2? brief offer-relevant and not a
   compliment? If below bar -> back to enrich or kill, **never ship**. This is the "no-slop overnight quality bar":
   validate the department's JUDGMENT before trusting the cron. The judge is where the brain's taste lives at
   nightly scale.

5. **THE LEARNING LOOP (the moat).** Write back what actually converts: which lane found the winning channel
   (`route_yield` already), which message/channel got the reply (`reply_reconcile`), which decisor type closed.
   Feed that back so the factory REPEATS high-yield routes per ICP and the rubric sharpens itself. This is THE NORTH
   (Innovations<->Miners feedback loop) and the edge (data + results, not enrichment - enrichment is a commodity now).

The operator's design notes are STANDARDS, not one-offs: every "this is how a good lead/card/message should be"
becomes a rubric line or a gate applied system-wide, for all clients, as if we already run 1000.

---

## PART 3 - What the nightly does NOT run today, and the plan to make it run

Traced from the live code (2026-10-07). This is the real machine, with file:line evidence, not a guess.

### 3.1 What the nightly actually runs (the real path)
`run_nightly.run()` = `scheduler.pool_floor` (sizes a discovery gap) -> `scheduler.tick` (enqueues `enrich_t1` for
`DISCOVERED` leads) -> recovery sweeps (`reverify`, `promote_candidates`, `micro_routes`, `reenrich_parked`) ->
`runner.drain_concurrent` (threads process the queue: `enrich_t1`/`gate_a`/`tier2`/`verify`/`gates`/`compose`/`logo`)
-> `tsa.enforce_ready_invariant` -> `reports.build_all` -> `whatsapp_find` -> `publish.publish_full_access` ->
`release.schedule_all` -> `sla_check`. State machine: `DISCOVERED -> T1_ENRICHING -> SCORED ->` (routes to)
`GATE_CHECK`/`T2_ENRICHING` `-> gate_a -> verify -> gates -> READY (-> compose)` or `PARKED`.

### 3.2 Why it yields ~0 net-new shippable leads (ranked, with evidence)
1. **No working net-new SOURCE.** Discovery is **Google Places only** (`discovery.py:33`), which hard-fails without
   `GOOGLE_PLACES_API_KEY` (`google_places.py:34-36`; header says "UNTESTED until a key is present"). No key -> 0
   jobs enqueued -> drain processes nothing -> 0 net-new. **The serper+judgment miner that produced today's premium
   leads (`agent_miner.mine_report` / `mine_and_publish`, `agent_miner.py:179,311`) has ZERO call sites in the
   nightly.** It is a manual-only script. The whole brain-grade discovery+enrich+compose path is simply not wired.
2. **The nightly never sets `approved=true`.** `publish` and `release` leave leads unapproved (`publish.py:88-102`,
   `release.py:48` set only `source_date`). But `sla_check` counts ONLY approved leads as shippable on Hoy
   (`sla_check.py:45-46`). The only code that sets `approved=true` is `agent_miner.publish_batch`
   (`agent_miner.py:294`) - manual. So even a lead that reaches READY and publishes is **not shippable** and the
   client's Hoy stays empty while the SLA alert fires.
3. **The channel gate starves on the 2nd channel.** Gates default to **Instagram required + >=2 channels**
   (`gates.py:42,76`). The nightly sets Instagram only opportunistically from homepage HTML (`site_enrich.py:74-75`)
   and **never writes LinkedIn to the company** (`site_enrich.py` promotes IG but not LI). `whatsapp_find` runs only
   AFTER READY (`whatsapp_find.py:61`), too late to satisfy the gate. Result: named+email leads PARK at `channels`.
4. **Verification ceiling.** `night_credit_cap=100`/day (`thresholds.json:22`, `runner.py:84`): past the cap, leads
   route to gates without `email_verified_at` -> fail `email_verified` -> PARKED.

### 3.3 Capability matrix - demon standard vs what the nightly actually produces
| Capability | Wired in nightly? | Where / gap |
|---|---|---|
| Net-new discovery (serper + judgment) | **NO** | `agent_miner.py` exists but has no call site; nightly = Places only |
| Net-new discovery (Google Places) | YES (key-gated) | `discovery.py:33`; dies without `GOOGLE_PLACES_API_KEY` |
| Email find + verify | YES (capped) | `micro_routes`/`promote_candidates`/`runner.py:87`; 100/day cap parks the rest |
| WhatsApp | YES but POST-READY | `whatsapp_find.py:76-82`; runs after gates, can't satisfy the channel gate |
| Instagram | PARTIAL | `site_enrich.py:74-75`, only if on homepage HTML |
| LinkedIn (person + company) | **NO** | `site_enrich` never writes `companies.linkedin`; `agent_miner.lane_linkedin` unwired |
| 2nd decisor | **NO** | `additionalContacts=[]` hard-coded (`publish.py:101`) |
| 4-part intel brief / Nota | **NO** | `gemini.brief` is 1-2 sentences (`gemini.py:33`); no 4-part generator |
| "ofrecen {X}" phrase | **NO** | no generator exists |
| Per-channel scripts | PARTIAL | `composer` emits 1 pitch; IG/LI/followup are TEMPLATE merges (`publish.py:96-97`); no `whatsappMessage` at all |
| Logo | YES (unavatar) | `logo.py:35`; NOT apple-touch-icon/favicon scrape |
| Score floor-60 formula | **NO** | `scoring.py`/`fit.py` use different weighted models; neither is `60+email8+wa10+ig6+li8+addl8+brief4` |
| Publish to app | YES | `publish.py:123-129` (clients with `icp_config.access=="full"`) |
| Release drip (N/day) | YES | `release.py` sets `source_date` only |
| `approved=true` | **NO** | manual-only (`agent_miner.py:294`); SLA needs it |

### 3.4 The plan to make it run (ordered; keystone first)

> **STATUS 2026-10-07 (cont.15) - WIRED, pending the 3-night proof.** Operator froze all new providers/docs/features
> until the nightly shows approved leads 3 nights running. Shipped this session: (1) **funnel email** per client per
> night via `funnel.py`+`notify` (counts only: discovered->enriched->named->email->verified->channels->READY->
> published->approved + card-valid %); (2) **Places key CONFIRMED in Railway** (trace #1 was a local artifact - prod
> discovery works); (3) **miner wired** - `agent_miner.mine_and_publish("2uplatam",20,approved=False,source=agent_miner)`
> in `run_nightly` for side-by-side vs a manual run; (4) **3 wiring bugs fixed** - LinkedIn now promoted to
> `companies.linkedin` (`site_enrich.py`), WhatsApp runs BEFORE gates (inline in `gates._run_one` + pre-drain sweep),
> channel gate uses client config (`2uplatam.icp_config.channels={min:2,required:[]}`); (5) **auto-approval** - new
> gate-passing cards get `approved=true, approvedBy=auto` in `publish.py` (existing cards preserve the operator's
> decision); (6) **quality standard as code** - `card_validator.py` (named, email, 2+ channels, logo, hook fact,
> per-channel scripts) reported as a nightly %. KNOWN remaining depth gap the validator exposes: `hook_fact` +
> `whatsappMessage` not generated yet (deferred behind the 3-night gate). NEXT: watch 3 funnel emails; if miner
> quality matches the manual run, make it the main lane.

**Keystone - WIRE the miner that already works.** `agent_miner` already does serper discovery + raw-fetch + cheap-LLM
judgment + compose + `publish_batch(approved=True)`. The single highest-leverage move is to **call
`agent_miner.mine_and_publish` from `run_nightly` as the net-new SOURCE** (per client, sized by the same
`pool_floor` gap), keeping the existing Places path as a secondary lane and the recovery sweeps for parked leads.
That one wire turns the nightly from "0 net-new" to "produces approved, enriched cards" in the same shape as today's
manual run. Everything below raises that output to the full demon bar.

1. **Source:** wire `agent_miner.mine_and_publish` into `run_nightly` (keystone). Confirm `GOOGLE_PLACES_API_KEY`
   in the Railway env OR drop Places as primary in favor of serper lanes. Add the discovery lanes from Part 1.A
   (directory, instagram-first, registry/edge) as instrumented lanes so `route_yield` picks winners per ICP.
2. **Approval:** have the nightly set `approved=true` on leads that pass ALL hard gates (named + real-site-or-exempt
   + verified email + >=2 real channels + logo + floor-score), so published leads are actually shippable on Hoy.
   Keep it gated behind the gates, never a blanket approve.
3. **Channels before the gate:** promote **LinkedIn** to `companies.linkedin` (the one-line `site_enrich` fix +
   wire `agent_miner.lane_linkedin`); run **WhatsApp find BEFORE gates**, not after; make the **channel gate
   sector-aware** (pymes require IG+WhatsApp; academics/B2B require LinkedIn+email+role-line, no IG demand).
4. **Enrichment depth:** add the missing lanes/generators - **2nd decisor**, **4-part intel brief (Nota)**,
   **"ofrecen {X}"**, and per-channel **`whatsappMessage`/`instagramDM`/`linkedinDM`/`followupEmail`** composed per
   lead by `purpose` (networking|sales), not template-merged. Switch logo to **apple-touch-icon + google-favicon**.
5. **Score:** replace the published score with the **floor-60 formula** so clients never see a raw single-digit.
6. **Verify cap:** raise/schedule `night_credit_cap` to cover the daily intake (MV is cheap; the bottleneck is
   upstream finding, not verifying), or spread verification so named leads are not parked for lack of a check.
7. **The judge (Part 2.4):** before publish, run the cheap judge against the committed rubric + exemplars; below
   bar -> re-enrich or kill. This is what keeps autonomy honest (no slop at 8 AM).

Sequencing: **1 + 2 first** (that alone restores a real daily output), then **3** (multi-channel so cards clear the
gate), then **4-7** (raise to the full demon standard + the quality judge). Each step maps to a Part-1 lane or a
Part-2 layer, so the nightly converges on exactly what the brain did by hand today.
