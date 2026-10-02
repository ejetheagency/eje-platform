# 002 · Provider Adapters (the dream-team stack, mapped)

Date: 2026-10-01. Maps the dream-team tool stack onto the factory's provider-adapter pattern
(`factory/providers/*.py`, one file per external API). Every paid call goes through `budget.can_spend()`
first and logs to `cost_ledger`. Cheapest-first; tools are downgraded if they don't lift replies
(the north-star metric = positive replies per 100 delivered).

## Built + working now (no new key)
| Adapter | Dept | Cost | Notes |
|---|---|---|---|
| `site_enrich.py` | D2 Tier-1 | $0 | Site scrape → email/IG/LinkedIn/phone → findings board. |
| `gemini.py` | D2 Tier-1 | ~$0.0002 | Cheap-LLM factual brief. Existing `GEMINI_API_KEY`. (Caution #3.) |
| `cheap_llm.py` | D2 router | varies | Cheapest-first LLM router w/ fallback. Uses Gemini now; auto-lights Groq/Cerebras on key. |
| `signal_spotter.py` | D1.5 | $0 | Free "why-now" signals (hiring/expansion) from the site → `signals`. The reply-lifter. v2 adds search. |
| `logo.py` | D7 Asset | $0 | Logo via unavatar → `assets`. Monogram stays the render-time fallback. |

## Built + READY, just add the key (code written, graceful no-op without; UNTESTED pending key)
| Adapter | Dept | Rough cost | Key needed |
|---|---|---|---|
| `cheap_llm.py` Groq + Cerebras lanes | D2 | free tier | `GROQ_API_KEY`, `CEREBRAS_API_KEY` |
| `serper.py` | D1/D2 | ~$0.001/search | `SERPER_API_KEY` |
| `google_places.py` | D1 Discovery | free basic | `GOOGLE_PLACES_API_KEY` |
| `brandfetch.py` | D7 Asset | free tier | `BRANDFETCH_API_KEY` (falls back to unavatar without) |

## Still to write (need a key AND/or a decision)
| Adapter | Dept | Note |
|---|---|---|
| `crawl4ai.py` | D2 | Open-source page reader; confirm self-host. |
| `instagram_api.py` | D2/signals | Official IG API limited for cold prospecting — decision: API vs keep IG-verify fallback. |
| Email cascade: `reacher` → `icypeas` → `prospeo` → `hunter` → `apollo` | D4 | `contacts.email_status` advances free→verified, each PAID step gated by `can_spend`. Need Icypeas/Prospeo keys; confirm Hunter/Apollo; Reacher hosting (AGPL + port 25). |

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
