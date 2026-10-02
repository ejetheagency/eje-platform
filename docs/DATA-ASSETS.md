# EJE, Data Assets Inventory

_Snapshot 2026-09-28. Purpose: catalog the valuable data so nothing is lost in the EJE rebrand._
_UnaBase is a FORMER client. Its productora database is retained as an EJE-owned asset, not deleted._

Supabase project `ogdsuztzhmnnjolilsuo`, table `leads`, 1,394 rows total, split by `client_id`.
A full logical backup lives in `backups/` (see `scripts/backup-supabase.py`).

## 1. EJE Productoras DB, formerly `unabase_default`, 932 leads, KEEP (high value)
- **What:** film / TV production companies (productoras) across LatAm + Spain, enriched during the
  UnaBase engagement, named decision-makers, verified emails, Instagram handles, scores.
- **Status mix:** ~597 contacted, 45 replied, 5 booked meetings, rest none / partial.
- **Why it is valuable:** a large, enriched, structured B2B database EJE now owns outright. Reusable for
  future EJE campaigns, or a sellable asset.
- **Go-forward:** rename to **EJE Productoras DB**. Migrate `client_id` `unabase_default` -> `eje_productoras`
  (Phase 2, with the backup as safety net). Relabel the UI workspace from "UnaBase / Scarlett" to
  "EJE · Productoras".

## 2. EJE Outreach, `eje`, 150 leads, ACTIVE
- EJE's own live pipeline (the creative / branding studio batches). Working as intended. No change.

## 3. eje_web, `eje_web`, 312 leads, DEAD (purge candidate)
- The killed `eje-reachout` Florida-website campaign. Bounced / non-existent addresses, no value.
- **Recommend:** export to `backups/` (already captured), then delete from the live table to declutter.

## Supporting data (all EJE-owned, keep)
- `tracked_leads` / `tracked_lead_notes`, the Seguimiento CRM (10 leads, 20 notes). Active.
- `messages_sent` (2,306), `actions` (1,529), `status_history` (113), lifecycle log. Keep.
- `landing_events` (24,301), ad / landing telemetry. Keep for analytics.

## The engine, repo `unabasi-leads`
- The sourcing + enrichment engine that produced the productora reports. With UnaBase gone it is dormant.
- Keep its enriched pool data (`staging/pool-a-tier.json`, `profiles/`) as part of the Productoras DB asset.
- Archive or rename the engine to `eje-productoras-engine` if it will be reused for EJE, otherwise archive.

## Naming debt, rebrand to EJE (Phase 2, needs staging first)
| Now (client name) | Rebrand to (EJE) |
|---|---|
| repo `unabase-app` | `eje-platform` |
| domain `unabase-app.vercel.app` | `app.ejetheagency.com` |
| field `unabaseScore` (in 1,394 records + 12 code refs) | `score` |
| `client_id` `unabase_default` | `eje_productoras` |
| copy: present-tense "trabajando con UnaBase" | past-tense case study, or drop (UnaBase is a former client, the present-tense claim is now inaccurate) |
