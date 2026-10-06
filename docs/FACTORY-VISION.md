# THE FACTORY — vision → architecture (non-negotiable north star)

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

## 1. Departments → what each one IS in the system

Legend: **[exists]** today · **[partial]** some pieces exist · **[to build]** the real work ahead.

### Miners — the execution fleet
Cheap worker-agents that execute *proven* playbooks (sourcing + enrichment routes) at the lowest possible cost, non-stop. They don't decide strategy; they read the current playbook/route registry (what works) and replicate it deterministically or with the cheapest model that clears the bar.
- Maps to: `discovery.py` lanes + the enrichment workers (`gate_a`, `site_decisor`, `tier2`) draining the job queue. **[partial]** — the workers exist; they are not yet a scalable, self-directed fleet reading a shared playbook.

### Innovations — the meta-learning brain
Keeps the miners from ever getting comfortable. It (a) maintains the **playbook/route registry** (the shared "what works"), (b) runs the **hand-off pipeline** — a clue found by one miner (a LinkedIn profile, a name fragment) is routed to the miner/source best able to advance it, so the *riddle* (ICP-matching decisor + company with every channel enriched) gets solved collaboratively instead of one miner chasing it forever, (c) **detects improvement and writes new rules/routes in real time — no developer**, so miners apply the better method immediately, and (d) spawns more worker instances when it helps, without raising spend.
- The riddle it optimizes: **ICP-matching decision-maker + company, fully channel-enriched** = verified personal email + Instagram + LinkedIn + (utopia) WhatsApp.
- Maps to: today this is **orchestrator-mediated only** — a human wires lessons in. **[to build]** Genuine cross-agent learning (a shared route registry + a route selector that updates from measured yield, and agents that hand clues to each other) is the single hardest and most important build. We do not claim it exists. Building it is the job.

### Financial Department (FD) — the governor
Grounds Innovations and the miners. Tracks subscriptions/credits/tokens so they **last the whole month, for every client**, and always keeps a **month of runway in reserve**. Every new idea or action passes three gates before miners may apply it:
1. Does it **increase our margin**?
2. If not margin, does it **increase client results without lowering our margin**?
3. **Will it still work when EJE has 100 clients?**

If an idea fails the gates, FD tells Innovations and the miners never apply it. Spend discipline is paramount.
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
2. **Reception / Response Intelligence** — captures and classifies *every* reply (positive / soft-no / no / silence) per channel and per decisor type. This is the department that operationalizes "a NO beats silence" and produces the real moat: knowing *who converts, on which channel, with which words*. Today replies are only partially captured.
3. **Scouts** (can live inside Innovations) — when a source pool dries up, go find **new structured pools** (funding registries, award rosters, co-pro markets, fresh geos). Miners work known lanes; Scouts open new ones so volume never silently declines (it's declining for 2uplatam right now).
4. **The Adversary / Verifier** (inside TSA) — adversarially confirm a finding is *real* before it ships: is this truly the decisor? is this email truly theirs? Grounding as a discipline, so we never hand a client a confident-but-wrong card.
5. **Dispatch / Operator Success** — delivers the daily 10–25 cards + the guided task queue, and **captures what the operator actually did** (sent / reply / meeting) to feed Reception. The factory's contact with ground truth. (We just fixed part of this: the send-reconcile.)
6. **Security / Deliverability** — one account per provider, rate-limit discipline, and **protect the sending domain** (never burn it with redundant or wrong-channel sends). Protects the entire operation's ability to reach anyone at all.

---

## 4. The mandate

This gets built, whatever it takes. The bar is not "it runs and produces something." The bar is the vision above, honored in full: self-improving, economically disciplined, grounded, anti-slop, per-client-soul, and built so it still works at 100 clients. Where something isn't built yet, this doc says so plainly — because the first act of making it real is refusing to pretend it already is.
