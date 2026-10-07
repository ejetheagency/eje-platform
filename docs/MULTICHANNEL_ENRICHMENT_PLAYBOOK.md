# MULTI-CHANNEL ENRICHMENT — the proven method + how the factory does it autonomously
**Written 2026-10-07, from the manual "act-as-the-factory" run. This is the STANDARD (expensive-once → cheap-replicates).**
The job: turn a company into a COMPLETE contact card — named decisor + a verified email + every reachable channel
(Instagram, LinkedIn, WhatsApp) — at the operator's quality bar, with zero fabrication.

---

## What this run PROVED
In one operator-directed session, parallel subagent "miners" + a verification gate produced **30 real, multi-channel,
MillionVerifier-verified, deduped, country-clean, zero-fabrication leads** (20 Ecuador small-biz + 10 MX/CO/Chile studios).
The automated factory produced **1** lead overnight the same day. The entire gap = **routes + gates the factory does not
run yet**. Everything below is cheap and deterministic enough to encode.

---

## THE 5 PUSHES = THE 5 CAPABILITIES (the operator's insight — this is the product)
The value was the refinement loop: the operator's brain FILTERING/PUSHING + the factory EXECUTING. Each push was a
quality dimension the factory must own as DEFAULT, so the 5 pushes collapse into ONE autonomous pass + operator review.

| # | What happened in the manual run | The capability the factory must encode |
|---|---|---|
| 1 | "Find the cards" → came back half-done, **no ICP clarity** | **ICP CONTRACT, locked FIRST**: geo + vertical + decisor definition + REQUIRED channels + best veins + exclusions. No mining without it. |
| 2 | Second sweep better but **missing Instagram** | **MULTI-CHANNEL GATE**: a card isn't done until it has ≥2 channels; IG mandatory where the ICP says so. |
| 3 | Third sweep **cleaner** | **QUALITY GATES**: MV-verify + catch-all REJECT + dedup vs pool + per-lead country check. |
| 4 | Fourth push → **found LinkedIn** | **LINKEDIN route**: press/site link → confirm name+company → empty if unconfirmable. |
| 5 | Fifth push → **15 WhatsApp numbers** | **WHATSAPP route**: `wa.me`/`tel:` regex on HTML (~100% precision) → site phone → Maps. |

**Operating model:** operator's brain = DIRECTOR (defines ICP, sets the bar, filters, corrects). Factory = EXECUTES the
5-dimensional extraction at scale. The human does judgment; the machine does the mechanical deep-digging.

---

## THE METHOD, PER CHANNEL (the encodable routes)

### EMAIL (the gated, verified core)
- **Winner routes (ranked by clean-yield):** (1) found **business gmail/hotmail** ≈ 100% clean — Google/MS reject
  nonexistent inboxes, so a found gmail CANNOT be catch-all; (2) **directory co-source** (owner+email+address in one
  listing, e.g. Guía Artesanal del Ecuador) ≈ 100%; (3) **press feature → founder name + brand's own site → email**;
  (4) **affiliate/registry pages** (CrossFit.com, business registries) print owner+email together; (5) **product/
  e-commerce brands** publish email on-site + founders named in press.
- **Loser routes:** own-domain SERVICE emails = ~50% **catch-all** (reject); **pattern-guessing** ≈ 12-15% for small
  biz (fallback only; works on design-studio non-catch-all domains); IG/WhatsApp-only businesses = no verifiable email.
- **Gate:** MillionVerifier. Accept `valid` only. **REJECT `accept_all` (catch-all)** — deliverable-but-maybe-wrong.

### INSTAGRAM (mandatory where ICP requires; the 2nd channel for most)
- Route: on the business's own site / press / their linked socials. Raw IG fetches are useless (login wall) — get the
  handle from the site or a press article, not by scraping IG.

### LINKEDIN (3rd channel; high for founders, sparse for tiny local biz)
- Route: link from the studio/brand's own team page → OR WebSearch "name + company" and CONFIRM name+company+city match.
- Personal profile preferred; company page is a sanctioned fallback. **Empty if unconfirmable — never guess.**
- Reality: ~50% for founders (EJE), ~20% for tiny Ecuadorian businesses (they aren't on LinkedIn — that's fine).

### WHATSAPP (the deep channel; often the PRIMARY one for LatAm small biz)
- **THE deterministic route:** fetch raw HTML, regex `wa.me/` | `api.whatsapp.com/send?phone=` | `whatsapp://send?phone=`
  | `wa.link/`. The number behind the floating WhatsApp button IS the WhatsApp — ~100% precision, pure code, no LLM.
- **Secondary:** `tel:` href (a published small-biz phone is almost always the WhatsApp line).
- **DO NOT** loose-regex phone numbers from page text — it catches analytics IDs / prices (false positives). Structured
  links only. Fallback for IG-only businesses: Google Maps / Facebook listing.
- **Validate** country mobile format (EC +593 9########, MX +52 1##########, CL +56 9########, CO +57 3#########).

---

## THE NON-NEGOTIABLE GATES (every card passes ALL)
1. **MV-verify + catch-all reject** (killed ~40% of "found" emails).
2. **Dedup vs the existing pool** (caught ~30% already-known — KALOS, Stratto, Novum…). Global, by domain + normalized name.
3. **Per-lead country check** (caught México/Perú/Spain false positives — e.g. "Esencia Yoga" was México, not Ecuador).
4. **Multi-channel completeness** = the READY gate: decisor + verified email + ≥2 channels (ideally 3-4). A clean email
   with NO second channel is a WEAK lead, not a done one.
5. **Zero fabrication** — every fact cites a real fetched page; unconfirmable → empty, not guessed.

---

## THE ICP CONTRACT (push #1 — nothing mines without this)
Per client, LOCKED before mining: **geo** (exact countries/cities) · **vertical** (and whether it's a hard gate or broad)
· **decisor definition** (owner/founder; gender preference) · **REQUIRED channels** (e.g. EJE: email+IG mandatory) ·
**best veins** (the sub-segments that reliably have findable channels — e.g. EC product brands, fitness/CrossFit, press-
covered founders) · **exclusions** (already-contacted, wrong geo). Provisional ICPs are flagged `provisional_unvalidated`
so the factory never learns an unvalidated ICP as settled (see the EJE "branding studios" correction).

---

## HOW THE FACTORY DOES THIS AUTONOMOUSLY (the build)
The manual subagent miners ARE the factory's miners — wire them as real workers on the queue/cron:
1. **Discovery lanes** that target the ICP's BEST VEINS and prefer businesses with findable channels (directories,
   press rosters, product-brand indices), not broad keyword scraping.
2. **Per-channel extractor workers** (each a cheap, mostly-deterministic micro-route):
   - `email_find` (gmail/site/directory/press → MV-verify → catch-all reject)
   - `ig_find` (site/press handle)
   - `linkedin_find` (confirm name+company)
   - `whatsapp_find` (**`wa.me`/`tel:` regex** → Maps fallback) ← the proven deterministic win
3. **Gate pipeline** = the 5 gates above as hard requirements; completeness (≥2-3 channels) is the READY bar.
4. **Operator-as-filter UI**: the operator sets the ICP + bar, reviews the finished multi-channel cards, tunes the ICP.
   The 5 pushes become 1 pass + a review. His brain directs; the factory deep-digs.

**Cost:** all four channel-routes are cheap (regex + a few fetches + $0.0005 MV). This is encodable now — it's the
highest-leverage factory build, because it turns "1 lead overnight" into "a full multi-channel report on demand."
