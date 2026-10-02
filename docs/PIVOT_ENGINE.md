# The Pivot Engine: Addendum to the Master Plan

> **For the AI assistant reading this in the repo:** This replaces the one-line description of the "Shared Findings Board" in `docs/ENRICHMENT_MASTER_PLAN.md` (§5, D2) with a full design. It is the core of Tier 1 and the thing that makes the product hard to copy. Build it exactly as a graph of facts and a library of pivot operators, not as a chain of prompts. Everything here runs on cheap LLM calls and free lookups, overnight, inside the cost rules of the master plan.

---

## 1. The Idea in One Paragraph

Anyone can send a company name to an AI and get a summary. That is not enrichment, it is a search result. Real enrichment is **pivoting**: every fact you find is the input to the next lookup. A phone number on a website becomes a search that finds the same number on a marketplace listing, which names the owner, which finds a LinkedIn profile, which gives the email pattern, which the verifier confirms. Each hop is cheap. The chain is what nobody else has, because nobody else runs the chain at scale, overnight, for every company. The agents "talk to each other" by reading and writing the same graph of facts, and the system learns which hops produce the contacts that get replies.

---

## 2. Core Model: Facts and Pivots

### A fact
Every piece of information is a row in `facts` (this renames `enrichment_findings`):

```
fact {
  id, company_id,
  type,            # from a fixed enum: domain, phone, email, email_pattern, ig_handle,
                   #   li_company, li_person, person_name, role, address, gbp_id,
                   #   review_reply_name, whois_registrant, mx_provider, job_post,
                   #   news_mention, marketplace_listing, youtube_channel, ...
  value,
  confidence,      # 0-1
  source_type,     # which pivot produced it
  source_fact_id,  # the fact it was derived from (the edge of the graph)
  evidence_url,
  cost_usd,
  created_at,
  verified_at      # null until a gate or verifier confirms it
}
```

`source_fact_id` is what turns the table into a graph. From any verified contact you can walk back to the first thing that was found, and from any first find you can walk forward to see what it eventually produced.

### A pivot
A pivot is a pure function: **one fact type in, zero or more facts out, with a known cost.**

```
pivot {
  name,
  input_type,              # which fact type it accepts
  output_types,            # which fact types it can produce
  cost_class,              # free | cheap_llm | search | paid
  tool,                    # which provider adapter it calls
  rate_limit_key,
  run(fact) -> [fact]      # the only thing it does
}
```

Pivots never call each other. They never know about the lead, the client, or the ICP. They take a fact and return facts. That is what keeps them small, testable, and swappable.

### The loop
One worker, `pivot_worker`, does this forever:

```
pop next (fact, pivot) pair from the pivot queue
if budget.can_spend(client, pivot.cost_class): run it
write new facts (dedupe on company_id + type + value)
for each new fact:
    for each pivot where pivot.input_type == fact.type:
        if not already run for this fact and scheduler.allows(fact, pivot):
            enqueue (fact, pivot)
```

That is the entire "agents talking to each other." No chat. No orchestration prompt. A queue, a graph, and a library of small functions.

---

## 3. Starter Pivot Library

These are the hops that produce decision-maker contacts for SMBs and mid-size companies in LATAM. Start with these; the learning loop (Section 5) decides which ones get more runs.

| # | Input fact | Pivot | Output facts | Cost |
|---|---|---|---|---|
| 1 | domain | fetch home/about/contact/team pages | phone, email, person_name, role, ig_handle, li_company, address | free (self-hosted crawler) |
| 2 | domain | DNS / MX lookup | mx_provider (Google Workspace, Microsoft 365, other) | free |
| 3 | domain | WHOIS | whois_registrant (often the owner on small companies) | free |
| 4 | domain | `site:domain` + "equipo" / "fundador" / "director" search | person_name, role | search |
| 5 | phone | reverse search of the number in quotes | marketplace_listing, gbp_id, other domains, person_name | search |
| 6 | email | search the email in quotes | person_name, li_person, other listings | search |
| 7 | email | infer pattern from any verified email on the domain (`first.last@`, `first@`) | email_pattern | free |
| 8 | email_pattern + person_name | generate candidate addresses, verify via SMTP | email (verified) | free (self-hosted verifier) |
| 9 | ig_handle | Business Discovery API: bio, website, follower count | domain, phone, email (from bio), ig_followers, ig_last_post | free (official API) |
| 10 | ig_handle | cheap LLM reads the bio and last captions for names and roles | person_name, role | cheap_llm |
| 11 | gbp_id | Places details: owner replies to reviews, website, phone | review_reply_name, domain, phone | free within cap |
| 12 | review_reply_name | search name + company | li_person, role | search |
| 13 | person_name + company | LinkedIn search via public search results | li_person, role | search |
| 14 | li_company | search for recent job posts | job_post (hiring signal), role | search |
| 15 | company name | news search last 90 days | news_mention (expansion, opening, award) | search |
| 16 | mx_provider = Google Workspace | pattern is very likely `first@` or `first.last@`; raise confidence of pivot 8 | email_pattern | free |
| 17 | any person_name | cheap LLM disambiguates: is this the same person across facts? | merged person | cheap_llm |
| 18 | any 3+ facts on one company | cheap LLM writes the "why now" signal summary for the message writer | signal_summary | cheap_llm |

Paid pivots (Icypeas, Prospeo, Hunter, Apollo) are also pivots in this library, with `cost_class: paid`. They sit at the end of the order, and the scheduler only enqueues them when the free chain ran out and the lead's score justifies it. This is how Tier 2 plugs into the same engine instead of being a separate system.

---

## 4. Scheduler Rules (what stops it from running forever)

`scheduler.allows(fact, pivot)` returns true only if all hold:

- **Depth cap:** the fact is at most `max_pivot_depth` hops from the seed (config, default 6).
- **Per-company cap:** fewer than `max_pivots_per_company_per_night` already run (config, default 40).
- **No repeats:** this (fact, pivot) pair has not run in the last `pivot_ttl_days` (config, default 30).
- **Confidence floor:** the input fact's confidence is above `min_confidence_to_pivot` (config, default 0.5). Weak facts don't spawn work.
- **Budget:** `can_spend()` says yes for the pivot's cost class and the client's plan.
- **Priority:** the pivot's current score (Section 5) is above the exploration floor, or it was picked as one of tonight's exploration runs.
- **Stop on success:** once a company has a verified contact for the ICP's target role, contact-finding pivots stop; only signal pivots (14, 15, 18) continue. In `account_based` mode the stop is `contacts_per_company` verified contacts, not one.

Every blocked enqueue is logged with the reason, so the admin page can show *why* a company stopped getting enriched.

---

## 5. Learning: Which Pivots Earn More Runs

Every pivot run writes a `pivot_runs` row: pivot, input fact, facts produced, cost, time. Nightly, the Strategist joins that with downstream outcomes:

```
score(pivot, icp_type) =
    verified_contacts_traceable_to_this_pivot
    weighted by reply_rate_of_those_contacts (once reply data exists)
    divided by cost
```

"Traceable" uses `source_fact_id` to walk the graph: if pivot 5 (reverse phone search) found the listing that led to the owner's name that led to the verified email that got a reply, pivot 5 gets credit. This is the reverse engineering, made measurable.

Allocation: 80% of tomorrow's pivot capacity goes in score order; 20% goes to pivots with few runs (so new ones get a chance). Both numbers in config. Scores are kept per ICP type, because "reverse phone search" might be gold for restaurants and useless for banks.

Nothing in this section needs an LLM. It is SQL over the graph.

---

## 6. Why This Is Hard to Copy

- A competitor with an LLM gets one hop per prompt and no memory between leads. This engine gets up to six hops, remembers every fact for every company it has ever seen, and reuses them across clients (global `companies`).
- The pivot library grows with every client. A hop discovered while serving a dental clinic is available to the next dental clinic that night.
- The scores are proprietary data: which hops, in which order, for which industries, produce people who reply. That table does not exist anywhere else and cannot be bought.
- It runs at the price of free lookups and Flash-Lite calls, so the moat gets deeper every night at a cost that rounds to zero per company.

---

## 7. Build Order (slots into master plan §12)

| Phase | Build | Done when |
|---|---|---|
| 1 | `facts` table with `source_fact_id`; `pivots` registry; `pivot_runs` table | A fact can be inserted and its ancestry walked |
| 2 | `pivot_worker` loop; scheduler rules; pivots 1, 2, 7, 8, 9, 11 (all free) | A seed domain produces a verified email overnight with zero paid calls on at least 3 of 10 test companies |
| 2b | pivots 4, 5, 6, 12, 13 (search class) with Serper budget | Verified-contact rate on the same 10 rises; cost logged per hop |
| 3 | Paid providers registered as pivots with `cost_class: paid` | Paid calls appear only after free chain is exhausted, visible in `pivot_runs` |
| 4 | Scoring query, 80/20 allocation, per-ICP-type scores | Pivot order differs between two ICP types after one week of data |
| 7 | Admin page: graph view of one company's facts, blocked-enqueue reasons, top pivots per ICP | Founder can explain, for any contact, how it was found |

---

## 8. Coding Rules Added

1. A pivot is a pure function with one input type and a declared cost class. No pivot calls another pivot or reads the queue.
2. Every fact records `source_fact_id`. A fact with no source is a seed, and only Discovery creates seeds.
3. Dedupe on `(company_id, type, value)` before insert. Duplicates raise confidence, they don't create rows.
4. All caps and thresholds in `config/pivots.yaml`. Adding a pivot is adding a file in `/packages/pivots/` and a line in the registry; nothing else changes.
5. Cheap LLM pivots return structured JSON validated against the fact enum. A fact of an unknown type is rejected, not stored.
6. Never pivot on a fact about a private individual beyond their business role. Facts are about companies and the people who run them, in their public professional capacity.
