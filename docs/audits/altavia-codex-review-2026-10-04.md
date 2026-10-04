# Altavia: Codex 10-contact review through our backend gates
Date: 2026-10-04. Source: `~/Documents/Codex/2026-10-03/i-x20/outputs/altavia-10-contacts.json`. No outreach sent.

Codex supplied 10 source-enriched decision-makers (source_verified emails, explicitly NOT deliverability-tested). We ran the independent checks our backend adds: MillionVerifier mailbox deliverability + dedup against our DB. ICP eligibility is applied analytically from Codex's evidence and caveats (those gates are not yet automated in code). Nothing had its threshold relaxed.

## Automated backend results
- **MillionVerifier deliverability:** 6/10 deliverable (valid), 4/10 catch-all (accept_all = server accepts anything, deliverability unconfirmed).
- **Dedup:** all 10 net-new (no collision with existing companies/contacts).
- **Channels present:** all 10 have email + a personal LinkedIn; IG on 9/10 but mixed type (person vs business vs founder-brand); phone on 0/10 (Codex did not export phone).

## Per-contact verdict
| ID | Person / firm | Industry, geo | MV deliverability | ICP read (from evidence) | Verdict |
|---|---|---|---|---|---|
| ALT-003 | Romy Jurado / Jurado & Associates | law, Miami FL | deliverable | 11-50, 1 office, Spanish staff | **ACCEPT** (imported) |
| ALT-004 | Tristan Jagroop / Jagroop Law Office | law, Newark CA | deliverable | 2-10, 1 office | **ACCEPT** (imported) |
| ALT-005 | Louis Berk / Louis Berk Law | law, Orlando+Deltona FL | deliverable | 11-50, 2 offices (<=2), Spanish focus | **ACCEPT** (imported) |
| ALT-001 | Ilona Anderson / Carpe Diem Law | law, Miami FL | deliverable | size UNKNOWN, location count not established | ENRICH (confirm size+locations) |
| ALT-006 | Taly Goody / Goody Law Group | law, Palos Verdes CA | deliverable | SIZE CONFLICT (1 vs 8 vs 7+ staff); offices unclear | REVIEW (resolve size/locations) |
| ALT-009 | Marcella Giuffrida / Forte Vita | fitness, LA CA | deliverable | email is her OTHER business (MGPR), not the studio; studio need historical | REVIEW (cross-business email) |
| ALT-002 | Sammy Kim / Law Offices of Sammy Kim | law, Fairfax VA | catch-all | 2-10, 1 office; Korean bilingual (NOT Spanish) | REVIEW (confirm mailbox) |
| ALT-007 | Tara Vasdani / Remote Law Canada | law, Toronto ON | catch-all | 2-10, remote, 1 Toronto base; IG stale (2020) | REVIEW (mailbox + refresh IG) |
| ALT-008 | Carlie Amore / Amore Dentistry | dental, St. Pete + New Orleans | catch-all | locations UNRESOLVED (St Pete/NOLA/Bradenton), size unknown | ENRICH (locations + mailbox) |
| ALT-010 | Brittany Ratelle / Ratelle Law | law, Coeur d'Alene ID | catch-all | solo (1), filing addr is CORRESPONDENCE not operating office | REVIEW (operating office + mailbox) |

**Accepted (3)** are live as READY Altavia leads via the seed pipeline (`seeds/altavia.csv`), each with a verified email and an English pitch. Nothing skipped a gate.

## Prioritized enrichment queue (unresolved 7)
- **P1 (deliverable, one fact from accept):** ALT-001 Ilona (confirm employee count + operating-location count), ALT-006 Taly (resolve the size conflict + office count; she has personal IG + personal LinkedIn, the strongest channel set of the ten).
- **P2 (catch-all email, otherwise eligible, needs deliverability + one ICP fact):** ALT-008 Carlie (operating-location count, could exceed 2), ALT-010 Brittany (confirm a real operating office vs correspondence addr), ALT-007 Tara (refresh IG, confirm mailbox), ALT-002 Sammy (confirm mailbox; log Korean-not-Spanish).
- **P3 (structural caveat):** ALT-009 Marcella (email routes to her PR business MGPR, studio need is historical; decide if a fitness studio reached via a personal PR address is in scope).

## Scraping-approach assessment (which techniques to keep / test / discard)
Context: the sample was purposively selected for successful enrichment and is 8/10 law firms, so its yields are not conversion rates.

- **RETAIN - homepage-first extraction** (mailto + JSON-LD + Cloudflare data-cfemail decode): gave 5/10 person-specific emails on the homepage, +2 on deeper pages. This is the cheap workhorse and maps directly onto the factory's biggest gap tonight (34/40 Altavia leads PARKED for no-named-decisor). Our `site_decisor` should add JSON-LD + data-cfemail decoding.
- **RETAIN - personal-profile attribution via indexed content** (10/10 personal LinkedIn, though only 4/10 straight from the homepage). Preserve channel TYPE: a business/brand IG is not a personal channel and must not be counted as one.
- **ESSENTIAL - our MillionVerifier gate**: 4/10 source-verified emails sit on catch-all domains, so source-verified is necessary but NOT sufficient. This is the single clearest learning: keep deliverability as a hard gate, and route catch-all to a "confirm channel" queue rather than READY.
- **TEST (time-boxed, high-score only) - founder interview / podcast show notes and official filings (USPTO, Sunbiz)** as identity/role fallback. They connected identities on the hard cases (ALT-001, ALT-004, ALT-009) but are slow; and filing addresses are correspondence, NOT operating offices (ALT-010), so never treat a filing address as a location.
- **DISCARD / guard against - inferring intent** from historical hiring or Spanish-language pages. Our own composer tripped on this (Louis Berk pitch said "hiring right now" from a historical post). Tighten signal grounding to verified-current only.

## Proposed measurable experiments (log yield, time, newly-verified fields, identity errors)
1. Add JSON-LD + data-cfemail decoding to `site_decisor`; measure named-decisor rate on the next 40 US discovered leads (baseline tonight: ~15%, 6/40). Target toward the homepage ~50% Codex observed.
2. Catch-all routing: `accept_all` emails go to a confirm-channel queue (secondary email / phone / LinkedIn) instead of READY.
3. Filing/interview fallback only when homepage fails AND lead score is high; cap time per lead and log hit rate.
