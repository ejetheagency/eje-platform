# Altavia factory challenge: gate outcomes + honest self-assessment
Date 2026-10-04. Scope: the 74 JSON records across the three exports. Run 4's 13 records are NOT combined (no JSON export). No outreach. Measurement limits from the handoff are honored: three rates kept separate; no "fastest route" claim from retrieval time; MX is not treated as deliverability.

## Part 1 — Backend gate outcomes (74 records)
Policy applied: 3 mandatory channels (person-specific email + Instagram + PERSONAL LinkedIn), deliverable mailbox (MillionVerifier, reused from today's runs), eligible industry + US/CA, and the handoff rule "unknown company size/office/ownership = REVIEW, not pass." Deduped within the three files + against our production DB.

**Counts: PASS 6 · REVIEW 33 · REJECT 7 · DUPLICATE 28** (= 74).

Reason drivers (a record can have several):
- 28 — email not deliverable (catch-all / undeliverable / unverified) -> recheck mailbox before any send.
- 28 — duplicate: already in our DB or a prior batch (we ingested run-1's 3 accepts + run-2's 21 into `leads`, so they correctly flag as dups now).
- 22 — company size unknown -> review (policy).
- 7 — reject: industry not in ICP. HONESTY FLAG: 6 are genuinely adjacent (mental-health/therapy from run-2: Livis, Persechini, Irazabal, Buck, Broocks, Logan); 1 is a classifier miss (Erik Pelton = trademark LAW, eligible -> should be REVIEW not reject). So 6 true rejects + 1 mis-classification.
- 6 — missing Instagram. 4 — missing personal LinkedIn. 1 — possible 3+ locations.

**The 6 PASS** (deliverable + 3 channels + eligible + size known + not dup): Aaron Minc (Minc Law), Ariana Tadler (Tadler Law), Francesca Witzburg (ESCA Legal), Jordana Goldlist (JHG Criminal Law), Sonia Lakhany (Lakhany Law), Marcella Giuffrida (Forte Vita). Even these need a buyer-authority + current-office recheck before send.

**Records needing recheck:** all 28 catch-all (mailbox), all 22 size-unknown (headcount + office count), and the Pelton mis-classification. Per-record evidence preserved in the source JSONs (source URLs, aliases, hold states).

## Part 2 — The factory challenge, answered with artifacts
Each artifact marked: PLANNED / IMPLEMENTED / EXECUTED / MEASURED. Missing = unknown.

### Q1. Qualified new contacts (all mandatory fields + ICP) per end-to-end minute, factory vs research
**UNKNOWN as a matched comparison.** I have NOT instrumented the factory's end-to-end time to the handoff's standard (distinct public-ICP decision-makers per end-to-end minute, including analysis/failures/human effort). The factory's "READY" uses a looser gate than this strict 3-channel+size policy, and its nightly wall-time isn't broken out per qualified contact. So I will not state a factory qualified/min and cannot claim faster.
What IS measured, directionally: the factory's autonomous discovery named a decision-maker on **6/40 US companies pre-fix, 15/40 post-fix** (see Q2). The research runs produced **74 named, mostly multi-field candidates** across three runs (run-3: 24 in 24.45 min retrieval-checkpoint). On completeness of named candidates, the manual runs are ahead. The factory adds the deliverability + dedup the manual runs explicitly skipped (0 mailboxes verified in all runs). Not apples-to-apples. Verdict: **unknown; define the experiment in Part 3.**

### Q2. Did the factory apply a high-yield lesson, with a route change and measured downstream result?
**YES — one proven case. IMPLEMENTED + EXECUTED + MEASURED.**
- Lesson: handoff practice #4 (on official sites extract visible text + mailto + JSON-LD + public email-display data together).
- Receiving component: `factory/providers/site_decisor.py` (Pivot 1, the free contact-finder), commit `4aed4d5` (2026-10-04).
- Route change: added JSON-LD Person/Organization parsing + `mailto:` extraction + Cloudflare `data-cfemail` decoding on RAW html BEFORE the LLM. Root cause it fixed: the old extractor stripped `<script>` (killing JSON-LD) and ran email regex on stripped text (missing obfuscated emails).
- Next call changed: `tier2.find_contact` -> `site_decisor` now returns a name+email on sites it previously returned nothing for.
- Measured downstream result: named-decisor rate on the same 40 Altavia companies went **6/40 -> 15/40 (2.5x)** (scratchpad measure.log); Altavia READY **5 -> 12** after re-processing (`client_leads`).
- **Honesty:** this was ORCHESTRATOR-mediated. I (the operator's AI) read the lesson and edited the code. It was not one autonomous factory agent handing a finding to another.
- Lessons RECORDED but NOT yet changing work: the RSS/WordPress archive route = PLANNED only (`docs/specs/archive-discovery-provider.md`, not built, not running); the interview-block route = not built; "qualify company size/office before social recovery" = not coded as a gate (hence the 22 size-unknown reviews above).

### Q3. Is the human outperforming the factory, though new to this?
**On this task, yes — on named-candidate yield/completeness.** The manual runs produced 74 named, mostly-multi-field ICP candidates; the factory's autonomous discovery named a decisor on a fraction per company and required my manual code change to improve. **Diagnosis of where the gap is:**
- DISCOVERY (primary): the factory's Google-Places lane names few decisors on US sites; the manual interview/archive routes + homepage-first extraction name many more. 
- FAILURE TO AUTONOMOUSLY REUSE FINDINGS (primary): see Q4/Q5 — the learning loop is human-mediated, so a good route doesn't propagate without me.
- NOT the gap: enrichment-gate + dedup + deliverability. Those are the factory's edge (it verified mailboxes and deduped across 3 batches; the manual runs did neither).
- Latency/measurement: unknown (not instrumented).

### Q4. Proof that factory agents exchange findings, update shared state, and change each other's actions
**CANNOT be proven. It did not happen.** The factory is a FIXED PIPELINE (`enrich_t1 -> scoring -> tier2 -> verify -> gates -> compose`) coordinated by a `job_log` queue. These are stages, not agents that read each other's findings, reverse-engineer routes, update a shared knowledge store, and change later assignments. The subagents I spawned tonight (e.g. the provisioning-map agent, the lessons-analysis agents) returned reports to ME; they did not autonomously update shared factory state or redirect another agent. Per the handoff's own rule, parallel agents and self-reported coordination are not proof — so this is **UNPROVEN / absent.**

### Q5. Does cross-agent learning work today? Plainly.
**No. Autonomous cross-agent learning does not work today. This is a verified, serious system gap** — the factory's stated central value (agents learn from one another and improve together) is not implemented. Learning is operator-mediated: a human/AI reads a lesson, edits code, writes a memory file. There is no shared-knowledge store that agents read+write, and no mechanism for one agent's evidence to change another agent's route. I am not softening this into an aspiration; it is an absent capability.

## Part 3 — Repair procedure + experiment (owners, measures, rollback)
**Gap: no autonomous learning loop.** Repair (phased):
1. **Shared knowledge store** (IMPLEMENT): a `route_findings` table — (route, lesson, evidence_url, yield metric, by_agent, ts). Owner: factory/backend. Success: agents write findings after each run.
2. **Route registry + selector** (IMPLEMENT): discovery/enrichment become named routes (places, homepage-first, archive, interview-block); a selector reads `route_findings` and picks/weights routes per client. Owner: factory. Success: a route's weight changes from another run's logged yield without human edits. Rollback: pin to the current fixed pipeline via a flag.
3. **Instrument the three rates** (IMPLEMENT): raw records/retrieval-sec, distinct public-ICP decisor/end-to-end-min, deliverable/processing-min — logged per route per run. Owner: factory. Success: Q1 becomes answerable.
4. **Measured rerun** (EXECUTE+MEASURE): a fresh US cohort (new cities, no overlap) through the factory with the homepage-first route live, vs a manual run on a matched cohort; compare deliverable-ICP/min. Success criterion: factory >= manual on deliverable-ICP contacts/end-to-end-min, OR a documented reason. Timing: next nightly + one scored rerun.

**Fresh-cohort reproduction already done (EXECUTED+MEASURED) for ONE route:** the homepage-first route was reproduced on the 40-company Altavia cohort (6->15 named). That is evidence the route transfers, not evidence of autonomous collaboration.

## Route recipe (reproducible)
Homepage-first pivot-1: fetch raw HTML of home + team/about/contact/attorneys/staff pages; extract emails from plaintext + `mailto:` + decoded `data-cfemail`; parse JSON-LD Person/Organization for name+role+email; if a JSON-LD Person carries an email, use it (no LLM); else cheap-LLM picks the decisor grounded against the full decoded email set; capture `tel:` phone. Measured 2.5x named-decisor lift. Next: domain-match the chosen email; add the archive-discovery route as a second lane and log its yield to `route_findings`.
