# Brief for Codex — 2026-10-04 (relay as-is)

## 0. Framing correction (most important)
Your RSS / WordPress archive route is NOT "opportunistic, not the backbone." That was single-pipeline thinking. This is a **factory**: it runs many discovery lanes at once. Places->site-enrich is one lane; your archive miner is another lane; tomorrow someone tries directories, funding/award registries, chamber rosters. A new lane never has to replace the main structure. Each lane is a small team that proves its yield to the board and earns its place. The compounding of many self-proving lanes is the moat. So: keep running the archive lane, and report its **qualified yield**, not its retrieval speed.

## 1. We ran your run-2 (40 contacts) through our real backend gates
Independent checks our side adds: MillionVerifier mailbox deliverability + dedup. ICP eligibility applied from your evidence. No outreach.
- **Deliverability: 25 deliverable, 12 catch-all/risky, 3 undeliverable** (Leslee Cohen + Erin Quiggle @ allriselawyers.com, Eric Proos @ ejplawoffice.com). Those 3 were source-verified but bounce. **Source-verified is necessary, not sufficient. Always mark deliverability as untested and let our verifier decide.**
- **Dedup: 0 collisions** (all 40 net-new vs our DB, including run-1).
- **Eligibility: 32 eligible-industry, 6 adjacent (5 mental-health/therapy + 1 autism/preschool) = out of ICP, held for approval; 2 physical-therapy = borderline.** Do not include adjacent industries without approval; they came in because the wellness-podcast archive is full of them.
- **20 clean accept-candidates** (deliverable + eligible industry + US + >=2 channels). Available to seed into the demo on your word.

## 2. Per-industry channel yield (the reusable asset for the first paying US client)
Outreach channels only (website is not a channel). Email + personal LinkedIn were ~universal.

| industry | n | email | IG | LinkedIn | phone |
|---|---|---|---|---|---|
| law | 18 | 18/18 | 5/18 (28%) | 18/18 | 0/18 |
| real estate | 5 | 5/5 | 5/5 | 5/5 | 0/5 |
| chiropractic | 3 | 3/3 | 3/3 | 3/3 | 0/3 |
| medical clinic | 3 | 3/3 | 2/3 | 3/3 | 0/3 |
| mental health/therapy (adjacent) | 5 | 5/5 | 3/5 | 5/5 | 0/5 |
| dental / gym / landscaping / PT | 1 each | 1/1 | 1/1 | 1/1 | 0/1 |
| home services / cleaning | 1 | 1/1 | 0/1 | 1/1 | 0/1 |

Reads: **LinkedIn + email are the reliable 2-channel floor for US B2B. IG is reliable for consumer-facing verticals (chiro, dental, gym, real estate) but NOT law (28%).** So IG is bonus, not a hard gate, for a law-heavy US pool.

## 3. What we need from you next (standards + the gaps this run exposed)
1. **Capture phone (`tel:` links + contact blocks).** You returned 0/40 structured phones. Phone is often the 2nd channel for US SMBs; our factory extractor already grabs it. Add it.
2. **Classify Instagram firmly as personal vs business vs founder-brand.** You left `instagram_scope: "personal_or_business_as_linked_by_source"` (ambiguous). Our channel-type rule needs a firm call; a business handle is not a personal channel.
3. **Stay in ICP.** Exclude mental-health/therapy, autism/preschool, and other adjacents unless we approve the vertical first.
4. **Keep doing what you did well:** mailto-vs-visible-text reconciliation (prefer corroborated visible), accept published cross-domain emails (don't rewrite domains), reconcile brand/domain changes before promotion, store former domains/emails/handles as aliases, and your location holds (GFF 3 offices, Chris Travis 7 gyms, Mila 2 clinics) were exactly right.

## 4. What is now NATIVE in our factory (so you know what you no longer need to carry)
- Pivot 1 (`site_decisor`) is homepage-first: JSON-LD Person/Org + mailto + Cloudflare cfemail decode on raw HTML before any LLM, + phone capture. Measured 2.5x lift in named decisors on US sites (6->15 of 40); Altavia READY went 5->12.
- Gates: VERIFIED_SOFT (catch-all whose identity is corroborated passes, flagged) + channel-bar (min 2; IG required only for IG-native sectors). Per-client spend cap + hard nightly verify cap.
- Next refinement we are adding: prefer a domain-matched email when several appear on a page (one stray off-domain pick observed).

## 5. How to report yield from here (the board model)
Per lane, report **accepted + deliverable contacts per cost and per minute.** NOT raw retrieval speed, NOT raw email yield, NOT 4-field completeness. Your run-2 speed numbers are all retrieval-side (0 mailboxes verified, 0 gates run in your pass), so they cannot stand in for lead velocity. Give us the qualified-per-minute number and we can compare the archive lane against the Places lane honestly.

Do not fabricate fields, guess emails, treat MX as mailbox verification, or send outreach.
