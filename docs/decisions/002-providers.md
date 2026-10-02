# 002 · Provider Adapters (the dream-team stack, mapped)

Date: 2026-10-01. Maps the dream-team tool stack onto the factory's provider-adapter pattern
(`factory/providers/*.py`, one file per external API). Every paid call goes through `budget.can_spend()`
first and logs to `cost_ledger`. Cheapest-first; tools are downgraded if they don't lift replies
(the north-star metric = positive replies per 100 delivered).

## Built now (no new key, usable today)
| Adapter | Dept | Cost | Notes |
|---|---|---|---|
| `site_enrich.py` | D2 Tier-1 | $0 | Fetches the company's own site + contact subpages, regex-extracts email/IG/LinkedIn/phone → findings board. |
| `gemini.py` | D2 Tier-1 | ~$0.0002 | Cheap-LLM factual brief. Uses the EXISTING `GEMINI_API_KEY`. (See caution #3.) |
| `logo.py` | D7 Asset | $0 | Logo via unavatar (free) → `assets` + `companies.logo_url`. Monogram stays the render-time fallback. |

## Ready to add (same contract, ONE file each) — need a key or a decision from you
| Adapter | Dept | Rough cost | Status / what I need |
|---|---|---|---|
| `groq.py`, `cerebras.py` | D2 | free tier | Add as cheap-LLM providers next to Gemini (auto-switch on rate limit). Need: Groq + Cerebras API keys. |
| `serper.py` | D1/D2 | ~$0.001/search | Google search. Need: Serper key. |
| `crawl4ai.py` | D2 | $0 (self-host) | Open-source page reader. Need: confirm we self-host (a small worker host). |
| `google_places.py` | D1 Discovery | free basic | Find businesses per ICP (great for local/sector). Need: Google Maps/Places key. |
| `instagram_api.py` | D2/signals | free | Official IG API. CAUTION: only reads business/creator accounts you're connected to — limited for cold prospecting; we likely keep a careful IG-verify fallback. Decision needed. |
| `brandfetch.py` | D7 Asset | free tier | Better logos than unavatar. Need: Brandfetch key. |
| Email cascade: `reacher.py` → `icypeas.py` → `prospeo.py` → `hunter.py` → `apollo.py` | D4 | free → ~$0.005–0.02 | `contacts.email_status` advances free→pattern→verified; each PAID step gated by `can_spend`. Hunter/Apollo keys likely already in `eje-leads/.env`. Need: Icypeas + Prospeo keys; confirm Reacher hosting (AGPL + needs port 25). |
| `signal_spotter.py` | D1.5 | ~$0 (search) | "Why-now" signals (hiring/new location/posting spike) → `signals`. The reply-lifter. Builds on serper/places. |

## What I need from you (the queue)
1. **API keys:** Groq, Cerebras, Serper, Google Places, Brandfetch, Icypeas, Prospeo. (Hunter/Apollo: confirm the ones in `eje-leads/.env` are current.) Always send the direct "get a key" link if handy.
2. **The dream-team files** (`DREAM_TEAM_STACK.md`, `capacity_model.py`, `capacity.yaml`) — I reconstructed a capacity model (`factory/capacity_model.py`, reproduces your $320/$2,570/$19,300), but your real numbers should replace it.
3. **Three decisions:** (a) Instagram official API vs keep IG-verify fallback for cold prospecting; (b) pay for Gemini before real client data flows through it (free tier trains on prompts — real privacy item); (c) Reacher self-host (AGPL + port 25) vs a hosted email verifier instead.
4. **Confirm the queue** = `job_log` + atomic `claim_job()` (built + tested) vs pgmq. I went with `job_log` because it works over the service key with no extension and is proven today.

## Cautions carried from the stack (all respected in the design)
- No LinkedIn scraping (Proxycurl was shut down after LinkedIn sued). We read LinkedIn URLs only, never scrape.
- No multi-account free-tier rotation (bans). One account per provider.
- Pay for Gemini before real client data (see decision 3b).
- Reacher: AGPL license + needs outbound port 25 (blocked on most clouds) — see decision 3c.
