# Activity brief — recent sessions (through 2026-10-04)
What was built and shipped, by workstream. Current state lives in `docs/SESSION_STATE.md`; this is the narrative of activity. Everything below is on `origin/main` unless noted.

## 1. Enrichment factory (backend, Railway nightly)
- **Homepage-first Pivot 1** (`site_decisor`): JSON-LD Person/Org + mailto + Cloudflare cfemail decode on raw HTML before the LLM, + phone capture. Measured **2.5x named-decisor lift (6->15 of 40)** on US sites. This fixed the root cause of US sites returning no decisor. Commit `4aed4d5`.
- **Gate A (free corroboration)**: built + domain-scoped (forward name search pinned by domain/locale, brand-name guard, pivot-19 confirm-by-domain). BUILT, NOT WIRED — pending the 12-lead hand-check review before it goes in front of paid tier2.
- **Gates upgraded**: VERIFIED_SOFT (a catch-all email whose identity is corroborated passes, flagged) + a channel-bar gate (`icp_config.channels={min,required}`; default min 2 + Instagram for IG-native sectors).
- **Treasury**: per-client USD cap (`icp_config.spend_cap_usd`), `night_credit_cap=100` hard per-day verify stop, MillionVerifier as primary verifier.
- **Seed import** (item 6): `seeds/<client>.csv` -> normal chain, nothing skips a gate, each field tagged with the pivot that would have found it. Live.
- Autonomous nightly proven running for all clients; pool-floor sizes discovery per client and alerts under target.

## 2. Altavia / Jose (trial -> full client)
- **Provisioned**: ICP + 14 US/CA Places discovery queries, English composer path, $10 spend cap.
- **Monday report = 20 verified leads** bridged into the app (`leads` table, domain-keyed), real logos (unavatar), clean English briefs, fit re-scored to 83-92 (the factory's generic score mis-ranked US leads at 28-32).
- **Access**: login + view locked to his workspace only (membership), countdown banner + Stripe CTA; after today's call switched trial->FULL access (all buttons, Reporte restored) while KEEPING the time limit (now enforced by a hard expired-gate on Oct 11) and the spend cap. Verified end-to-end as him (login 200, workspaces=['altavia']).
- **Voice**: Jose's real cold-outreach captured and applied as per-industry drafts (law/dental/chiro/real-estate/gym/home) with a `[real fact]` fill-in (never fabricated), grammar-corrected, title-stripped names. Stored on the workspace + in memory.
- **Learning intake**: "Lo que realmente enviaste" capture box -> `sent_actuals` (collect now, mine later). Hook-fact rule captured as doctrine (a fact may open a message only if offer-relevant + recent first-party + phrased as a moment/contrast).
- **Frontend bugs fixed**: duplicate leads (domain-keyed ids), intermittent card-open (card was rendering into a hidden view), "(sin borrador)" draft, mid-word brief cut, fit-score 32. Reply + time tracking tagged per template + industry for the Friday report.

## 3. Codex contact runs processed (74+ records)
- Three runs (10 + 40 + 24) run through our gates: MillionVerifier deliverability + dedup + ICP. Key finding repeated across runs: **source-verified != deliverable** (catch-all domains), and LinkedIn is near-universal while IG yield is high for consumer verticals but low for law.
- **Factory challenge (74 records)**: strict-policy gate = **6 pass / 33 review / 7 reject / 28 duplicate**. Honest self-assessment delivered: the factory can apply a lesson (homepage-first, measured) but **autonomous cross-agent learning is NOT implemented** — a verified system gap, logged with a repair plan. See `docs/audits/altavia-factory-challenge-2026-10-04.md`.
- Codex reframed as **manual input, not a lane**; its archive-mining route spec'd as a future factory provider (`docs/specs/archive-discovery-provider.md`).

## 4. Fernando / 2upLatam (first paying client, go-live Oct 7)
- Confirmed **mined nightly on the cloud** (pool-floor ran Oct 3-4, ~70-80 jobs/night) with all global innovations applied (homepage-first, phone, channel gate correctly min-2+IG, VERIFIED_SOFT). Status 22 READY / 140 target, 174 PARKED.
- Parity gap = Gate A (unwired for everyone) — the biggest unlock for his LATAM leads where SMTP verify is ~82% unreliable.

## 5. Docs + discipline
- `docs/WORKING_RULES.md` (token discipline), `docs/SESSION_STATE.md` (one-page handoff), `docs/audits/session-token-efficiency-2026-10-04.md` (this session's burn retro). Memories updated: Jose voice, hook-fact rule, multi-lane discovery, the autonomous-learning gap.

## Open items (next sessions)
1. 12-lead Gate A hand-check -> wire Gate A -> run 2upLatam PARKED backlog (biggest lever for Fernando).
2. Email-pattern pivot (named leads without an email).
3. ICP-aware scoring (so fit reflects the client, not the productora default).
4. The autonomous-learning repair (route_findings store + route selector + 3-rate instrumentation).
5. Backend enforcement of the Altavia expiry (membership-revocation cron) to harden the client-side gate.
