# Dream Team Stack & Capacity Plan

> **For the AI assistant reading this in the repo:** This extends `docs/ENRICHMENT_MASTER_PLAN.md`. It names the specific tools for each department, the agents that run in parallel, how they talk to each other, and how many calls and dollars the system needs at 10, 100 and 1,000 clients. Prices and free tiers were checked on 2026-10-01 and change often: verify each one on the vendor's own pricing page before writing its adapter, and put every number in `/config`, never in code.

---

## 1. The Thesis, as a Metric

**More replies means more clients.** So the system is not optimized for "most data found." It is optimized for:

> **North-star metric: positive replies per 100 delivered leads** (per client, per ICP, per channel).

Every agent, strategy and tool is ultimately scored on whether the leads it touched got replies, not just on whether it filled a field. A tool that fills 30% more fields but produces no lift in replies gets downgraded by the Learning agent automatically.

Supporting metrics (all computed nightly, stored in `metrics_daily`):

| Metric | Why it matters |
|---|---|
| Ready leads delivered per client per day | The product promise (the 8 a.m. report) |
| Contact found rate (decision-maker email or DM handle) | No contact = no reply possible |
| Email bounce rate | Bounces kill sender reputation and therefore replies |
| Cost per ready lead | Must stay under the plan's cost target |
| Cost per positive reply | The real unit economics |

---

## 2. What We Have Today vs. What We Add

| Layer | Today | Add (cheap or free) |
|---|---|---|
| Database + queues + cron | Supabase | **Supabase Queues (pgmq) + pg_cron** (already in Supabase, no new vendor) |
| Web app | Vercel | Stays read-only; no workers on Vercel |
| Heavy workers | (none) | **One small always-on container** (Railway, Fly or Render) for the browser scraper and email verifier |
| Cheap LLMs | Gemini | **Groq, Cerebras, OpenRouter free models** behind one router |
| Web search | (none) | **Serper** (Google results, cheapest per query) |
| Page reading | (none) | **Crawl4AI** self-hosted (open source); **Jina Reader** as backup |
| Local business discovery | (none) | **Google Places API (New)** using its free tiers; **OpenStreetMap Overpass** (open data, free) |
| Instagram | (none) | **Instagram Graph API, Business Discovery** (official) |
| Email finding | Hunter, Apollo | **Pattern guesser + self-hosted verifier (Reacher)** first, then **Icypeas -> Prospeo -> Hunter -> Apollo** waterfall |
| Logos | (none) | **Brandfetch Logo API** (free), **logo.dev** backup, **rembg** (open source background removal) |
| Premium reasoning | Claude | Keep, capped (Tier 3 only) |

Why these and not others is explained per agent below.

---

## 3. The Dream Team (agents and their tools)

Each "agent" is a worker type: a small program that pulls jobs from its own queue, does one thing, writes results to the findings board, and enqueues the next job. Many copies of each can run at once.

### A1. Scout: discovery
**Job:** find candidate companies that match each client's ICP.
**Tools, in order of cost:**
1. **Google Places API (New), Text Search "IDs only"**. Google lists this SKU at $0 with an unlimited free cap, so discovering *which* businesses exist costs nothing. Detail lookups are a separate SKU: Essentials SKUs get 10,000 free calls a month, Pro 5,000, Enterprise 1,000, and the old $200 monthly credit is gone. Request only the fields you need (field masks), because the most expensive field requested decides the price.
2. **OpenStreetMap Overpass API**: free, open data for local businesses by category and area. Good second source to cross-check names.
3. **Serper** (Google search results): for "category + city" queries and for finding websites. It gives 2,500 free queries, then about $0.30-$1.00 per 1,000 depending on plan.

**Dedupe rule:** before creating a company, normalize the domain and check `companies`. Already known, link to this client, do not re-discover.

### A2. Reader: page fetching
**Job:** turn a company website into clean text for the LLMs.
**Tools:**
1. **Crawl4AI**, self-hosted (Apache-2.0, built on Playwright). No per-page fee; you pay for the container, your own proxies if needed, and maintenance. Runs in the always-on container, not in Supabase Edge Functions (it needs a real browser).
2. **Jina Reader** as backup: prefix a URL and get markdown. Its free key is limited to non-commercial use, so use a paid key in production (about $0.02 per million output tokens).

**Rule:** read only the pages that matter (home, about, contact, team). Cache every fetched page by URL + date so no agent fetches the same page twice in 30 days.

### A3. Analyst pool: cheap LLM labor (the "cheap labor house")
**Job:** extract structured facts from page text (services, size signals, owner names, socials, emails on page), score ICP fit, write findings.
**Tools (all behind `packages/llm_router`):**

| Provider | Free tier (verify live) | Role |
|---|---|---|
| **Gemini Flash-Lite** | Only Flash and Flash-Lite remain free since April 2026; developers report roughly 5-15 requests/minute and up to ~1,000/day, adjusted without notice | Default extractor |
| **Groq** | No card; per model, 30 requests/minute and about 1,000/day on chat models | Fast fallback |
| **Cerebras** | About 1M tokens/day free, no card; the free tier is described as for development/testing, so plan to pay at production volume | Bulk fallback |
| **OpenRouter free models** | 50 requests/day, 1,000/day after buying $10 of credits | Last-resort fallback |

**Router rules:**
- Pick the cheapest available provider that meets the task's quality level (`config/providers.yaml`).
- On a 429 (rate limit), mark that provider cold for N minutes and fall to the next.
- Limits are per organization or project, not per key. Groq and OpenRouter both say extra keys or accounts don't add capacity. **Never create multiple accounts or keys to multiply free quota**; it violates terms and gets accounts banned.
- **Privacy:** on Gemini's free tier, prompts can be used to improve Google's products. Before real client data flows through it, move to the paid tier (Flash-Lite is about $0.10 per million input tokens) or keep free tiers for public web text only.
- Keep prompts short and structured (JSON output schema). Token budget per call lives in config.

### A4. Socials Inspector: Instagram and LinkedIn
**Job:** confirm the business is real and active, and capture follower count, bio, website, recent activity.

- **Instagram:** use the official **Business Discovery** endpoint of the Instagram Graph API. From your own connected Business account you can read another public Business or Creator account's followers count, media count, bio and website. It does not work for personal or private accounts, and gives no follower lists. Personal accounts: mark "IG unverifiable," don't scrape.
- **LinkedIn:** **do not scrape.** Proxycurl, the most popular LinkedIn data API, shut down in July 2025 after LinkedIn sued it. For now, only confirm a company page exists by searching for it through Serper (cheap, public search results). When revenue allows, add a licensed data provider (People Data Labs or Coresignal) behind the same adapter interface.

### A5. Signal Spotter: why-now signals
**Job:** find reasons a lead would reply *today*. This is the biggest lever on replies.
**Signals, all from tools already in the stack:**
- Hiring (job posts found via Serper)
- New location or opening (Places + news search)
- Recent reviews spike or complaints (Places details, Pro SKU, within free cap)
- Active Instagram in last 14 days (Business Discovery)
- Website missing booking, outdated, or no clear call to action (Analyst reads it)

Each signal is a finding with `signal_type`, `evidence_url`, `detected_at`. The Writer uses these for personalization; the Learning agent learns which signals predict replies per ICP.

### A6. Contact Hunter: Tier 2 waterfall
**Job:** find the decision-maker and a deliverable email (or DM handle). Runs only for leads that passed ICP scoring.

**Waterfall, cheapest first. Stop at the first verified hit:**
1. **Already in `contacts` cache** (free).
2. **Emails printed on the website** (already extracted by the Analyst, free).
3. **Pattern guess + self-hosted verification:** generate `first@`, `first.last@`, `info@` etc., verify each with **Reacher** (open-source SMTP verifier, checks if a mailbox exists without sending). Two cautions:
   - It needs outbound port 25, which many cloud hosts block. Pick a host that allows it, or use Reacher's hosted API.
   - Its license is AGPL-3.0. Proprietary commercial use needs Reacher's commercial license. Confirm which applies before building on it.
4. **Icypeas**: pay only for found, verified emails; credits roll over. About $0.019 per email on the $19 plan, down to about $0.005 at volume. Independent benchmarks show a lower find rate (~26-32%), so it's the cheap first paid try, not the only one.
5. **Prospeo**: about $0.01 per email, 75 free per month.
6. **Hunter** (existing account).
7. **Apollo** (existing account): last, for the highest-value leads only.

Every step logs cost and result to `strategy_runs`, so the Learning agent can reorder the waterfall per ICP (for example, if Prospeo wins for dental clinics, it moves up for dental clinics).

### A7. Gatekeeper: quality gates (TSA)
Mostly free code checks: DNS/MX records exist, website resolves, name matches across 2+ sources, IG Business Discovery succeeds, email verified and not a catch-all (or catch-all flagged). One cheap LLM call only when sources disagree.

### A8. Brand Stylist: logos
1. **Brandfetch Logo API**: free with fair-use limits (~500K/month), no attribution required.
2. **logo.dev**: 500K/month free but requires visible attribution; use only as backup or on a paid plan.
3. Website favicon / `og:image` / IG profile picture.
4. **rembg** (open-source background removal) + resize to WebP, upload to Supabase Storage. Store URL only.
5. Monogram fallback.

(Clearbit's free logo API is gone; it was sunset in December 2025.)

### A9. Writer: personalized first message
**Job:** draft the outreach message per lead, per channel, using the chosen template approach + that lead's findings and signals.
- Cheap LLM by default; Tier 3 (Claude) only for the top 5% of leads by score.
- Blocks generation if required personalization fields are missing (see master plan, Section 11).
- Every message stores which signals and template it used, so replies can be credited back.

### A10. Strategist: learning
**Job:** nightly, rank every strategy (source x ICP x waterfall order x signal type x template) by **positive replies per dollar** once reply data exists, and by verified fields per dollar before that. Allocate ~80% of tomorrow's jobs to winners, ~20% to exploration (config). Pure SQL + code, no external cost.

### A11. Treasurer
Unchanged from the master plan: `can_spend()`, ledger, 10-day forecast, kill switch. Add one thing: **free-tier meters**. Track daily usage per provider against its free quota so the router uses free capacity first and the forecast knows when free tiers will run out.

---

## 4. How the Agents Talk to Each Other

No agent calls another agent directly. They communicate through two things in Supabase:

1. **Queues (Supabase Queues / pgmq):** one queue per agent (`q_scout`, `q_reader`, `q_analyst`, `q_contact`, `q_gate`, `q_logo`, `q_writer`). A job finishing enqueues the next agent's job. pgmq keeps messages until a worker removes them and gives exactly-once delivery within a visibility timeout, so a crashed worker's job reappears.
2. **Findings board (`enrichment_findings` table):** every fact any agent learns is written here with source and confidence. Before working on a company, an agent reads all findings for it. That is how "this agent found something unusual, so the next one goes deeper" works:
   - Rule example: if the Analyst finds an owner name on the About page, it enqueues the Contact Hunter with `hint: owner_name`, which skips straight to pattern guessing for that name.
   - Rule example: if Socials finds IG followers above the ICP's threshold, the lead's priority rises and it jumps the Tier 2 queue.

These "if finding X, then do Y" rules live in `config/escalation_rules.yaml` so they can be changed without code.

**Scheduling:** `pg_cron` (on by default in Supabase) wakes the workers and runs nightly jobs. Caveat: if the database is unhealthy or a free project is paused, cron silently stops. Add a heartbeat: each worker writes `last_seen` every minute, and a check alerts the founder if any worker is silent for 15 minutes.

**Where each agent runs:**

| Agent | Runs on | Why |
|---|---|---|
| Scout, Analyst, Socials, Contact (API calls), Gatekeeper, Writer, Logo fetch | Supabase Edge Functions triggered by pg_cron reading pgmq | Light HTTP work; no extra server |
| Reader (Crawl4AI), Reacher, rembg | One always-on container (Railway, Fly or Render) | Need a real browser, port 25, or image processing |
| Strategist, Treasurer, Reports | SQL + Edge Functions on pg_cron | Database-heavy, nightly |
| Web app | Vercel | Read-only views, nothing heavy |

---

## 5. Capacity and Cost Model

### Assumptions (all go in `config/capacity.yaml`)

```yaml
ready_leads_per_client_per_day: 25
candidates_per_ready_lead: 4        # discover 4 to deliver 1
icp_fit_rate: 0.5                   # share of candidates that pass ICP scoring
need_paid_contact_rate: 0.6         # share of fit leads where free contact methods fail
tier3_rate: 0.03                    # share of fit leads escalated to premium LLM
dedupe_rate: { 10: 0.0, 100: 0.2, 1000: 0.4 }  # share already enriched for another client
per_candidate:
  searches: 2
  pages_read: 3
  llm_calls: 3
per_fit_lead:
  gate_llm_calls: 1
unit_cost_usd:
  search: 0.001          # Serper, starter rate
  page: 0.0002           # self-hosted compute or Jina paid
  llm_call: 0.0005       # Flash-Lite class, ~3k in / 500 out tokens, paid rate
  discovery: 0.002       # Places detail fields per candidate, after free cap
  paid_email: 0.012      # blended waterfall (Icypeas -> Prospeo -> Hunter/Apollo)
  tier3_call: 0.05
```

### Results (computed by `scripts/capacity_model.py`, paid rates, before free tiers)

| | 10 clients | 100 clients | 1,000 clients |
|---|---|---|---|
| Candidates processed / day | 1,000 | 8,000 | 60,000 |
| Cheap LLM calls / day | 3,500 | 28,000 | 210,000 |
| Search queries / day | 2,000 | 16,000 | 120,000 |
| Pages read / day | 3,000 | 24,000 | 180,000 |
| Paid email lookups / day | 300 | 2,400 | 18,000 |
| Tier 3 calls / day | 15 | 120 | 900 |
| LLM requests / minute (20h shift) | ~3 | ~23 | ~175 |
| Tier 1 cost / month | $183 | $1,464 | $10,980 |
| Gates cost / month | $8 | $60 | $450 |
| Tier 2 cost / month | $108 | $864 | $6,480 |
| Tier 3 cost / month | $22 | $180 | $1,350 |
| **Total / month** | **~$321** | **~$2,568** | **~$19,260** |
| **Cost per client / month** | **~$32** | **~$26** | **~$19** |

What this means:
- **Cost per client falls as you grow** because of global dedupe. This is the "smarter and cheaper with every client" effect in numbers.
- **Price check:** if the target is enrichment <= 20% of revenue, the plan needs to cost at least ~$160/month per client at 10 clients, falling to ~$100 at 1,000. If prices will be lower, cut `ready_leads_per_client_per_day` or `candidates_per_ready_lead` in config.
- **Biggest cost lines:** discovery details and search at scale, then paid emails. So the highest-value engineering work is (1) better ICP pre-filtering so fewer candidates are processed (lower `candidates_per_ready_lead`), and (2) better free contact finding (pattern + verify) so fewer leads hit paid tools.
- **Workers needed:** at 20 jobs/minute per worker over a 20-hour shift, 2-3 Tier 1 workers cover even 1,000 clients for throughput. The real limit is **provider rate limits**, which is why the router spreads load across providers and paid tiers are needed past ~100 clients.

### Bootstrap mode (now, before revenue)

At 10 clients, free tiers absorb most of Tier 1:
- LLM calls (~3,500/day): spread across Gemini, Groq and Cerebras free tiers, roughly covered if prompts stay small.
- Pages: self-hosted Crawl4AI, only the container cost.
- Discovery: Places "IDs only" search is free; detail calls mostly within free caps at this volume.
- Search: Serper's 2,500 free queries last about a day at this volume, then ~$50 for 50K.
- Paid emails: ~9,000/month at the assumption above, roughly $50-110/month with Icypeas first.

**Realistic bootstrap total: about $150-250/month** for 10 clients at 25 ready leads/day each, plus one small container. To spend less, start at 10 ready leads per client per day and raise it as revenue arrives (one config number).

---

## 6. Build Order (adds to master plan phases)

| Step | Add | Done when |
|---|---|---|
| 1 | `llm_router` with Gemini + Groq + Cerebras adapters, 429 fallback, free-tier meters | 1,000 test extractions run with zero failed jobs |
| 2 | Supabase Queues per agent + pg_cron wake-ups + heartbeat alert | Killing a worker mid-job causes no lost jobs |
| 3 | Scout (Places IDs-only + Overpass + Serper) with global dedupe | Two clients with overlapping ICPs share companies |
| 4 | Always-on container with Crawl4AI + page cache | Same URL never fetched twice in 30 days |
| 5 | Contact waterfall with pattern + verifier + Icypeas, logging per step | Waterfall step stats visible in admin page |
| 6 | Socials (IG Business Discovery) + Signal Spotter | Each ready lead shows at least one "why now" signal or is flagged |
| 7 | Brand Stylist (Brandfetch -> favicon -> monogram) | No broken logos in reports |
| 8 | Writer + reply tracking + Strategist scoring on replies | Strategy rankings use reply data |
| 9 | `scripts/capacity_model.py` reads `config/capacity.yaml`, Treasurer compares forecast vs. actual | Weekly forecast error under 20% |

---

## 7. Rules for This Stack

1. Free capacity first, then cheapest paid, then premium. The router and waterfall decide; agents never call a vendor directly.
2. One account per provider. No multiple accounts or keys to stretch free tiers.
3. No LinkedIn or Instagram scraping. Official APIs, public search results, or licensed data providers only.
4. Client data never goes through a provider tier that trains on prompts.
5. Every vendor sits behind an adapter with the same interface, so swapping one (prices change monthly in this market) is a one-file change.
6. Check every license before shipping open-source code in a commercial product (Reacher is AGPL-3.0; Crawl4AI is Apache-2.0).
7. Before adding any new paid vendor, ask the founder.

---

## 8. Open Decisions for the Founder

- Plan prices (they set how many ready leads per day each plan can afford).
- Starting value for `ready_leads_per_client_per_day` in bootstrap mode (suggest 10).
- Reacher: commercial license, hosted API, or a different verifier.
- Which always-on host (must allow outbound port 25 if self-hosting the verifier).
- When to move Gemini to the paid tier (recommended before real client data flows).
- When revenue allows a licensed company data provider for LinkedIn-type firmographics.

---

## Sources (checked 2026-10-01)

- Gemini free tier changes: https://www.cloudzero.com/blog/gemini-pricing/ · https://geotoolbox.ai/blog/gemini-api-pricing
- Groq free tier: https://itsfree.ai/provider/groq/ · https://www.cloudzero.com/blog/groq-pricing/ · https://github.com/xyzs996/free-llm-api/discussions/3
- Cerebras free tier: https://getfreeai.net/en/services/api/cerebras/
- Search APIs: https://parallel.ai/articles/best-free-web-search-api · https://openbenchmarks.com/multi-turn-company-search/serp-rapidapi-for-research-agents
- Crawl4AI / Jina / Firecrawl: https://crawlbase.com/blog/firecrawl-alternatives/ · https://dev.to/josejux/firecrawl-vs-jina-reader-vs-tavily-picking-the-right-web-to-llm-tool-and-when-you-need-none-of-21ck · https://spider.cloud/blog/best-web-scraping-apis-for-ai-2026/
- Google Places pricing: https://developers.google.com/maps/billing-and-pricing/pricing · https://bizcollect.dev/blog/google-places-api-pricing
- Instagram Business Discovery: https://www.keyapi.ai/blog/which-instagram-api-should-you-use/ · https://elfsight.com/blog/instagram-graph-api-complete-developer-guide-for-2026/
- Proxycurl shutdown: https://connectsafely.ai/articles/best-proxycurl-alternative-linkedin-inbound-2026 · https://linkedapi.io/guides/proxycurl-alternatives
- Reacher: https://github.com/amaurymartiny/check-if-email-exists · https://www.blog.brightcoding.dev/2026/09/24/reacherhqcheck-if-email-exists-rust-based-email-verification-without-sending-mail
- Email finders: https://www.icypeas.com/pricing · https://reply.io/blog/best-email-enrichment-apis/ · https://www.findymail.com/blog/best-email-finder-api/ · https://prospeo.io/s/icypeas-alternatives
- Logos: https://www.context.dev/blog/company-logo-api-comparison · https://getquikturn.io/blog/clearbit-logo-api-alternative/
- Supabase Queues and cron: https://supabase.com/docs/guides/queues/pgmq · https://crontap.com/guides/supabase-cron-jobs
