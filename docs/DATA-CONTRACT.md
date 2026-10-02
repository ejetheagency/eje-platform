# EJE Platform, Data Contract

_The shape the code depends on. Refactors (splitting app.html, the rebrand, RLS) must NOT silently
change any of this. If a field or rule changes, change it here first, then in code, deliberately._
_Snapshot 2026-09-28._

## Connection
- Supabase project `ogdsuztzhmnnjolilsuo`, REST via PostgREST.
- **Hard cap: 1,000 rows per read.** Every read MUST paginate (`limit`/`offset`). This has already
  bitten count queries. See `scripts/backup-supabase.py` for the pattern.
- URL + anon key are currently **hardcoded in `app.html`** (SB_URL / SB_KEY, ~line 657). This is the
  key that must move server-side in Phase 1 (auth + RLS).

## Workspaces (`client_id`)
| client_id | meaning | state |
|---|---|---|
| `eje` | EJE's own outreach pipeline | active |
| `unabase_default` | EJE Productoras DB (former UnaBase client data) | retained asset, rename pending -> `eje_productoras` |
| `eje_web` | dead Florida-reachout campaign | purge candidate |

The app resolves the active workspace from `localStorage.eje_ws` (Phase 1 replaces this with auth membership).

## Table: `leads`
Top-level columns: `id` (= website domain, the primary key, GLOBAL across all clients),
`company`, `contact_name`, `contact_email`, `contact_phone`, `country`, `industry`, `score`,
`status`, `source_date`, `is_historical`, `lead_data` (JSONB), `client_id`, `created_at`, `updated_at`.

**`id` is globally unique** (not scoped by client_id). A domain already used by one client cannot be
inserted for another, this is a real constraint (hit it with `ocelotefilms.com`).

### `lead_data` (JSONB) shape
`companyName`, `contactName`, `contactEmail`, `companyEmail`, `contactTitle`, `country`, `website`,
`instagramHandle`, `instagramFollowers`, `instagramKind`, `contactLinkedIn`, `pitchEmailES`, `subject`,
`companyBrief`, `unabaseScore` (rename pending -> `score`), `source_date`, `approved`, `readyToSend`,
`_operatorVerified`, `_template` (`A_video` | `B_delegation`), `additionalContacts`, `_verifiedCredits`,
`whyICP`, `_emailVerify`.

### `status` values
`none` (never contacted) · `contacted` · `replied` · `loom_sent` · `meeting` · `closed` · `skip` · `partial`.

### The Hoy contract (what makes a lead show as a first-touch today)
A lead appears in **Hoy** when: `approved: true` AND `readyToSend: true` AND `status: none` AND
`source_date == ejeTodayET()` (today on the 8 AM Chile rollover). Miss any one and it will not surface.

## Cadence engine (the lifecycle)
Touches are counted from `messages_sent`. Next touch by count:
1. **T1** email (`iv 0`)
2. **T2** Instagram DM (`+2 days`), falls back LinkedIn -> WhatsApp -> email if no IG (EJE rule: 2nd touch is IG/LinkedIn, NEVER email)
3. **T3** 2nd email (`+5 days`)
4. **T4** WhatsApp (`+7 days`)
5. monthly thereafter

`replied` / `loom_sent` / `meeting` short-circuit to their own states. Under ISEJE, a lead with **3 touches
is complete** and exits the queue. `status: meeting` also exits the cadence.

## Table: `messages_sent`
`id`, `lead_id`, `user_name`, `channel` (`email` | `ig` | `li` | `wa`), `message_text`, `sent_at`, `client_id`.
This is the **source of truth for what actually went out**. The cadence reads it.

## Table: `actions`
`id`, `lead_id`, `user_name`, `channel`, `completed`, `completed_at`, `client_id`.
Records completion of a channel step. Written delete-then-insert (a uniqueness constraint on the step).

## Reconciliation rule (non-negotiable)
- **Additive only. Never blanket-delete.** A wipe once destroyed 56 real 2nd-touch marks.
- Sends made via **Gmail Schedule Send do NOT tell the platform**, they drift. Reconcile by reading the
  contact@ Sent folder and logging `messages_sent` + `actions` at the real send time, then mark status.
  This is required after every off-day scheduled batch until sending moves server-side (Phase 3).

## Seguimiento (isolated CRM, ISEJE only)
- `tracked_leads`: `id`, `client_id`, `user_name`, `company`, `decisor_name`, `contact_email`,
  `contact_phone`, `instagram`, `linkedin`, `source`, `stage`, `created_at`, `updated_at`.
  **One contact per company today** (multi-contact is a Phase 3 item).
- `tracked_lead_notes`: `id`, `tracked_lead_id`, `client_id`, `user_name`, `note_text`, `stage_at_time`, `created_at`.
- `source`: `ad_ig` | `ad_meta` | `referral` | `inbound` | `event` | `manual` | `other` | `outbound`.
- `stage`: `nuevo` | `contactado` | `respondio` | `conversacion` | `reunion` | `propuesta` | `ganado` | `perdido` | `pausa`.
- These tables NEVER touch the outreach pipeline. That isolation is intentional, keep it.

## Supporting tables
`status_history` (audit), `notes` (per-lead, upsert on `lead_id,user_name`), `landing_events` (ad/landing telemetry).
