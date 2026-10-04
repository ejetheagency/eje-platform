# Spec: archive-mining discovery provider (a nightly discovery LANE)
Status: proposed. Build order: AFTER Gate A, same pattern as the homepage-first pivot-1 extractor (prove a recipe manually, then make it a provider the nightly calls with no human). Owner decision 2026-10-04: Codex is manual input; this is how its archive route becomes a real lane.

## What it is
A discovery provider that, for a client ICP, finds and mines PUBLIC archives that list many named decision-makers at once (podcast RSS feeds, WordPress REST archives `/wp-json/wp/v2/posts`, sitemaps, directory/association/chamber rosters), extracts candidate companies + named people, and feeds them into the normal chain as DISCOVERED leads. It is a LANE that runs beside the Places lane, not a replacement for it.

## Where it sits
`factory/providers/archive_discovery.py`, called by `discovery.discover_for_client` as one of several lanes. The nightly runs all enabled lanes for a client, each writing DISCOVERED `client_leads`; everything downstream (enrich_t1 -> pivot 1 -> Gate A -> verify -> gates) is unchanged. A lane is enabled per client via `icp_config.discovery_lanes` (default: `["places"]`; add `"archive"` when a vertical has archives).

## Interface
`discover(client_id, icp, max_leads) -> {ok, scanned, created, lane:"archive", cost_usd, elapsed_s}`.
Internally: (1) resolve archive sources for the vertical (configured seeds + a cheap search for "<vertical> podcast/guest/directory"), (2) pull each archive ONCE with `requests` and parse locally (RSS/XML, wp-json JSON, sitemap), (3) dedupe teaser/host rows, (4) cheap-LLM role+industry classifier to keep only in-ICP decision-makers (raw email yield greatly overstates buyer yield), (5) resolve each kept person's current company domain, (6) insert company + DISCOVERED client_lead (lineage `source="discovery_archive"`, source_finding_id null = seed).

## Design rules (cheap, deterministic, no headless browser)
- `requests` + stdlib parsers only. Read browser-visible data first (visible text, mailto, JSON-LD, social hrefs) before considering any render; render is out of scope.
- Bounded concurrency 4; preserve final redirect URL + HTTP status + elapsed; cache + parse locally.
- Reconcile mailto-vs-visible (prefer corroborated visible text), accept published cross-domain emails (never rewrite domains), reconcile brand/domain changes, store former domains/emails/handles as aliases.
- Budget rule per lead: 1 archive pull (shared) + 1 homepage + up to 2 deeper pages + 1 targeted search per missing field; park incomplete for a later pass; stop retrying 403/406.
- Incremental: track RSS GUIDs/pubDates, wp post IDs/modified, content hashes, ETag/Last-Modified; recheck changed + held first.

## Measurement (the board model) - REQUIRED
Every lane logs, per run, **accepted + deliverable contacts per cost and per minute** (not retrieval speed, not raw email yield, not field completeness). Store a per-lane row (lane, client, scanned, kept_in_icp, gate_passed, deliverable, cost_usd, elapsed_s). A lane is kept/scaled or retired on its proven qualified-yield-per-cost vs the Places lane. This is what lets many lanes compete honestly.

## Dependency caveat
A vertical must expose a usable public archive. Podcasts/directories/associations often do; a cold Places-only vertical may not. So this lane is ADDITIVE to Places, enabled where it earns its yield, never assumed to be the backbone.

## Build steps
1. `archive_discovery.py` with `discover()` + the RSS/wp-json/sitemap parsers + cheap-LLM classifier.
2. Add `discovery_lanes` to `icp_config`; `discover_for_client` iterates enabled lanes.
3. Per-lane yield table (new small table or cost_ledger tag) + surface in the ops/board view.
4. Prove on one archive-bearing vertical; compare qualified-yield-per-cost to Places before enabling by default.
