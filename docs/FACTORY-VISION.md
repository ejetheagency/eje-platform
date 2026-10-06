# THE FACTORY — vision → architecture (non-negotiable north star)

> **Status + current position live in `docs/PLAN.md` (the anchor). This doc = the detailed spec for CRM Project slices S3+S4 (`docs/CRM-PROJECT.md`).**


This is the operator's vision for EJE's factory, translated from human language into the system it has to become.
It is not aspirational copy. It is the spec. Every build decision is measured against it. Written 2026-10-05.

---

## 0. The thesis (never compromise these)

- **EJE initiates conversations with the client's ideal customer and leaves the channel open for the owner to close.** It does not "generate leads" and it does not close for them.
- **A contact card is a conversation yet to be had — not a lead.** Each carries a probability of becoming a sale that rises with how fully the operator works the tasks the system hands them.
- **The life cycle exists to make it as low-effort as possible for the prospect to respond.** Each step fits some decision-makers better than others; persistence is the point; **a NO is more valuable than silence — a rejection is closer to a sale than an empty chat.**
- **There is no master template.** Each *channel* communicates differently, and each *company* has its own soul. In a world of one-template-for-100-people, EJE rows the other way: it **promotes human imperfection, and the efficiency comes from learning each client's imperfections and replicating them.**
- **The factory is what makes this real.** Without it, the above is just words. It is a continuously-running, multi-agent operation optimizing for the highest-yield contact card, under strict economic discipline, that **learns and improves itself in real time without a developer in the loop.**

The visual: ~100 of the most capable people, each at full potential, collaborating — finding contacts, learning high-yield processes, exchanging clues, innovating, starting from different theses and reverse-engineering new paths — to produce the deadliest enrichment + outreach-intelligence factory in the industry.

---

## 0b. THE CIRCLE (the governing shape — every mechanism serves this)

The factory is a **closed loop, not a pipeline.** A lead enters the circle and keeps moving around it,
accumulating evidence, until it earns one of exactly **two sanctioned exits — and no other way out exists:**

1. **Fully enriched → READY/DELIVERED** (out the "win" door).
2. **Proven useless → DISCARDED, WITH recorded cause** (out the "proven" door).

Everything in between **re-circulates.** A lead that fails a gate is not dropped — it loops back for another
enrichment pass down a *different* route. **"Leaks only where they are needed"** means the only places a lead
leaves the circle are those two doors; any other exit is a bug, not a design.

**The two laws that make this real:**

- **No premature death.** A lead may not be proclaimed useless on thin evidence. Discard requires BOTH (a) a
  genuine TSA failure after honest attempts (no real website AND no findable email AND no decisor, per the
  client's ICP), AND (b) a recorded cause (`hold_reason` / `quality_flags`). **A cycle-0, score-below-floor,
  no-reason discard is forbidden** — that lead has no evidence yet; it must loop, not leave.
- **Evidence density = priority.** The more evidence we already hold on a lead (findings count, cycles survived,
  signals), the **higher** its priority to finish — it is closest to READY and carries the most sunk work. The
  queue pulls high-evidence leads first; it never scores a lead *down* for data we simply have not mined yet.

**Why this is also the yield fix (not just philosophy):** 20-READY/client/night is gated by *conversion*, not
sourcing. Every premature leak (terminal cycle-0 discard, a parked lead that can't loop back, a found email never
promoted) is conversion thrown away. Sealing the circle's illegitimate leaks raises conversion directly; the
route-yield brain then optimizes *which* route each re-circulation should take. Brain-over-leaky-pipe only
optimizes the leak.

**Evidence snapshot (2026-10-06, the leaks found):** reenrich_parked was 400-erroring every night (parked leads
couldn't loop — FIXED); 116/183 2uplatam discards were cycle-0 terminal with no cause (illegitimate leaks);
195/395 leads never cycled once. The factory was linear-with-early-exit. Making it circular is the active build.

---

## 1. Departments → what each one IS in the system

Legend: **[exists]** today · **[partial]** some pieces exist · **[to build]** the real work ahead.

### Miners — the execution fleet
Cheap worker-agents that execute *proven* playbooks (sourcing + enrichment routes) at the lowest possible cost, non-stop. They don't decide strategy; they read the current playbook/route registry (what works) and replicate it deterministically or with the cheapest model that clears the bar.
- Maps to: `discovery.py` lanes + the enrichment workers (`gate_a`, `site_decisor`, `tier2`) draining the job queue. **[partial]** — the workers exist; they are not yet a scalable, self-directed fleet reading a shared playbook.

### Innovations — the meta-learning brain
Keeps the miners from ever getting comfortable. It (a) maintains the **playbook/route registry** (the shared "what works"), (b) runs the **hand-off pipeline** — a clue found by one miner (a LinkedIn profile, a name fragment) is routed to the miner/source best able to advance it, so the *riddle* (ICP-matching decisor + company with every channel enriched) gets solved collaboratively instead of one miner chasing it forever, (c) **detects improvement and writes new rules/routes in real time — no developer**, so miners apply the better method immediately, and (d) *proposes* scaling (more worker instances) to the FD, which approves it within budget. **Correction to the vision:** "hire more employees without increasing expense" is not physically possible — a new employee = a parallel agent call = more tokens. So scaling is an FD-approved budget decision, never one Innovations makes alone, or the financial guard has a hole.
- The riddle it optimizes: **ICP-matching decision-maker + company, fully channel-enriched** = verified personal email + Instagram + LinkedIn + (utopia) WhatsApp.
- Maps to: today this is **orchestrator-mediated only** — a human wires lessons in. **[to build]** Genuine cross-agent learning (a shared route registry + a route selector that updates from measured yield, and agents that hand clues to each other) is the single hardest and most important build. We do not claim it exists. Building it is the job.

### Financial Department (FD) — the governor
Grounds Innovations and the miners. Tracks subscriptions/credits/tokens so they **last the whole month, for every client**, and always keeps a **month of runway in reserve**. Every new idea or action passes three gates before miners may apply it:
1. Does it **increase our margin**?
2. If not margin, does it **increase client results without lowering our margin**?
3. **Will it still work when EJE has 100 clients?**
4. **Does it degrade the contact card?** (QUALITY VETO — added 2026-10-05.) The first three gates are all margin + scale, so a cheaper path that produces *worse* cards passes them. TSA catches it later, but the incentive is then born crooked — the governor would be actively pushing toward junk. The quality veto makes "cheaper but worse" fail at the source. This directly protects the operator's non-negotiable: never taint a client with a bad card to save money.

If an idea fails ANY gate, FD tells Innovations and the miners never apply it. Spend discipline is paramount.
- Maps to: `budget.can_spend` + the treasury caps (global $200, per-provider, per-client, per-day verify cap). **[partial]** — the spend ceilings exist; the **economic policy engine** (the 3-gate vetting that approves/denies *new methods*, not just dollars) is **[to build]**.

### Committee — the premium-enrichment router
With FD, decides **which leads deserve the expensive tools** (usually premium clients) — Hunter.io, Apollo, even expensive-model Claude calls. FD approves the budget per decision and guarantees a month stays available. Nothing expensive fires without this gate.
- Maps to: `tier2.py` + Gate selection. **[partial]** — tier2 exists; the **value-based selector** ("is this lead worth the expensive call, given the client tier and remaining runway?") is **[to build]**.

### TSA — quality + inspection (the hard gate)
Every lead undergoes exams before it may pass:
1. **ICP conformity + drift detection.** Compare to the client's ICP; if miners are drifting (fetching cheap/fast instead of *right*), **report to Innovations** so the target is corrected.
2. **Channel completeness.** Does the card have Instagram (preferably with follower count), personal email, LinkedIn, and ideally WhatsApp? **If the first three aren't present, it does NOT pass** — it bounces to Innovations with the question "how did a lead reach TSA without essentials?", and Innovations makes miners close the gap by reverse-engineering.
- Maps to: `gates.py` + `icp_filters.py`. **[partial]** — deliverability + ICP-exclusion gates exist; the **≥3-channel completeness gate + the drift→Innovations feedback loop** are **[to build]**.

### Design — presentation + template health
Only runs after TSA fully qualifies a lead. It makes each card look right: cheap-LLM/brandfetch call to **find + render the company logo** onto the card. It pulls the per-channel templates (from the Writers / template library), runs the **anti-AI-slop check**, and confirms each is tailored to the client's ICP. It **watches template performance**: a template with a low reply rate after ~10 days triggers an alert to Innovations and a recommendation to the operator to change it.
- Maps to: `brandfetch.py` + the composer's presentation layer. **[partial]** — logo fetch exists; the **anti-slop gate + the 10-day template-performance monitor/alert** are **[to build]**.

### Writers — composition + voice intelligence
Work constantly with Innovations to learn **the best single facts** to drop into a message and **how to communicate on each channel** (no master template — per channel, per client soul). They research response-prone phrasings, run anti-AI-slop filters, and stay in **close contact with CEO Emiliano** to learn his voice and moves. They have the **most client contact**: they leave performance-based recommendation notes. When a client's template performs, they **recommend it again and hand it to Innovations to tweak for other ICP-matching clients** so everyone benefits.
- Maps to: `composer.py` + the exemplar/voice library + the hook-fact rule + `EJE_FUNNEL.md`/`sector-templates.md`. **[partial]** — composition + per-client voice grounding + sector templates exist; the **single-fact research loop, the anti-slop gate, and the cross-client high-performer propagation** are **[to build]**.

---

## 2. The nervous system (what makes them ONE factory, not seven scripts)

- **A feedback bus + findings board** so departments actually talk: TSA→Innovations (drift, under-enrichment), Design→Innovations (template fatigue), Writers→Innovations (a high-performer to propagate), FD→Innovations (veto). **[to build]**
- **The Library (institutional memory)** — the shared brain every department reads and writes: playbooks/routes, per-client voice profiles, exemplars, response-intelligence, template performance. **This is what makes learning compound instead of resetting.** Without it, "Innovations teaches miners" has nowhere to live. **[to build — and it is foundational; nothing else compounds without it.]**
- **Continuous operation.** The factory runs as persistent workers draining the queue + department cycles on timers — **not a once-a-day batch** — because the thesis (self-improving, serving many clients) can't live in a nightly cron. The FD caps are the governor; continuous running hits the same ceilings, just sooner, then idles. **[to build — this is the "run all day" change.]**

---

## 3. Departments / roles I think you're missing

1. **The Library / Institutional Memory** (named above) — not optional. It is the single most important missing piece: the store where everything learned is kept and compounded. Build this first or nothing else learns.
2. **Reception / Response Intelligence** — captures and classifies *every* reply (positive / soft-no / no / silence) per channel and per decisor type. Operationalizes "a NO beats silence" and produces the moat: knowing *who converts, on which channel, with which words*. **Critical correction: optimize for CLOSES, not replies.** Reply rate alone is the cheap-conversations trap already lived — a factory that optimizes for *responses* produces chatty dead-ends. This department must take an **outcome signal from the operator** (became a client / meeting booked / dead) so the whole factory optimizes toward *sales*, not toward getting answered. Today replies are only partially captured and outcomes not at all.
3. **Scouts** (can live inside Innovations) — when a source pool dries up, go find **new structured pools** (funding registries, award rosters, co-pro markets, fresh geos). Miners work known lanes; Scouts open new ones so volume never silently declines (it's declining for 2uplatam right now).
4. **The Adversary / Verifier** (inside TSA) — adversarially confirm a finding is *real* before it ships: is this truly the decisor? is this email truly theirs? Grounding as a discipline, so we never hand a client a confident-but-wrong card.
5. **Dispatch / Operator Success** — delivers the daily 10–25 cards + the guided task queue, and **captures what the operator actually did** (sent / reply / meeting) to feed Reception. **And it supervises the operator:** the whole thesis depends on the client completing daily tasks, and nothing watches whether they do. It must detect when a client stops operating and alert — *before* they blame the product and churn. (The operator's own inbox is exactly where this dies today.)
6. **Security / Deliverability** — **the sender is the CLIENT, so a burned domain / restricted Instagram / LinkedIn jail / WhatsApp ban is the CLIENT's account, not ours.** A restriction caused by the system ends the contract AND the referral — existential, not cosmetic. Owns: one account per provider, per-channel rate + volume discipline, and protecting the client's sending reputation (never redundant or wrong-channel sends).
7. **Aduana / Do-not-contact + collision control** — nobody owns the "never contact" set: the client's EXISTING customers, open conversations, those who already said no, and competitors. And the thesis-breaking case: **if two EJE clients share an ICP, the same decisor gets two "personalized" messages both generated by us** — the whole promise collapses the instant that happens. Owns a global do-not-contact list + **cross-client dedup** so a decisor is never double-touched across clients.
8. **Caducidad / Freshness** — a verified email from January is wrong by June; cards go stale. Nobody owns re-verification or expiry. Owns: re-verify contacts on a decay schedule and expire/refresh stale cards so the factory never ships rot. (Partly overlaps TSA, but it's a distinct lifecycle owner.)

---

## 4. The mandate

This gets built, whatever it takes. The bar is not "it runs and produces something." The bar is the vision above, honored in full: self-improving, economically disciplined, grounded, anti-slop, per-client-soul, and built so it still works at 100 clients. Where something isn't built yet, this doc says so plainly — because the first act of making it real is refusing to pretend it already is.
