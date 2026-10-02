# 003 · Consistency pass + audit: OUTREACH_PLAYBOOKS.md

Date: 2026-10-02. Scope: audit the fifth addendum doc (`docs/OUTREACH_PLAYBOOKS.md`) against
`ENRICHMENT_MASTER_PLAN.md` (§4 lifecycle, §9 data model, §11 template library), the applied
factory schema (`db/002-factory-schema.sql`), and the existing decisions (000, 001, 002).
Verdict up front: **adopt as the seed of the playbook library.** Two structural fixes are
required before any code is written (findings F1 and F2). Everything else aligns.

## What the doc adds
- A *playbook* = an ordered sequence of touches (channel + delay + intent + template + stop rules),
  stored as data, executed by the task worker, measured by outcome, shown to the client as the
  "why" behind each siguiente tarea.
- Four tables: `playbooks`, `playbook_steps`, `playbook_runs`, `touches`.
- Three engagement states: `SOFT_NO`, `REOPENED`, `NURTURE`.
- Playbook 01 (`pb_001_channel_switch_reopen`), reconstructed from the Daniela run.

## Findings

### F1 (HIGH, must fix before coding): the new states are a POST-DELIVERY lifecycle, not §4
§4 is the **enrichment** state machine (`DISCOVERED -> ... -> READY -> DELIVERED`, plus `PARKED`/
`DISCARDED`), owned by `/packages/lead_state` and stored in `client_leads.state`. It answers "is
this lead pitch-ready?" `SOFT_NO`/`REOPENED`/`NURTURE` answer a different question, "how is the
outreach conversation going?", and only begin AFTER `DELIVERED`. The doc's phrase "extend master
plan §4" is misleading.
- **Decision:** keep §4 untouched. Model engagement as a **separate** state machine that starts at
  `DELIVERED`, tracked on `playbook_runs.state` (and optionally mirrored to a new
  `client_leads.engagement_state`). Do NOT add `SOFT_NO`/`NURTURE` transitions into
  `/packages/lead_state`. Two machines, one per question.

### F2 (HIGH, must fix before coding): `touches` overlaps the existing `engagement_events`
§9 and the schema already define `engagement_events` ("client actions on leads", `db/002` line 145),
and `strategy_runs.reply_outcome` is explicitly "backfilled from engagement_events". The doc's
`touches` table (sent_at, channel, outcome) is a second log of the same reality, which will drift
and split the learning signal.
- **Decision:** one source of truth. `engagement_events` stays canonical. `touches` becomes the
  playbook-run-scoped execution log that **writes an `engagement_event` on every send/outcome**
  (carrying `run_id` + `step_no`), OR fold the `touches` columns into `engagement_events` with
  `run_id`/`step_no` added. The Strategist reads one table, not two.

### F3 (MEDIUM): "No send outside a playbook run" supersedes the current EJE cadence
Doc §6 rule 1 says every send belongs to a run. Today EJE sends run through the hardcoded cadence in
`public/app.html` (`cadNext`: 1er email -> IG DM -> 2do email) and the Hoy/Tareas queue. This is an
architectural change, not a conflict.
- **Decision:** before enforcing the rule, encode the current EJE cadence as `pb_eje_default` so
  nothing is lost, then migrate sends onto runs incrementally. Not a blocker; sizes the work.

### F4 (MEDIUM, dependency): the soft_no/hard_no/question classifier needs inbound replies
Doc §6 rule 3 requires classifying replies. We do not yet capture inbound replies reliably (the
mailbox + IG reconcile crons are still pending, see the reliability-crons plan). The playbook
learning loop is gated on that data.
- **Decision:** build reply capture first; until then, the client marks the outcome by hand (the doc
  already supports this, the task worker records the marked outcome).

### F5 (LOW): naming + config consistency
- Casing: §4 enrichment states are UPPERCASE; `playbook_runs.state` is lowercase. Keep engagement
  run states lowercase (they are run states); avoid introducing UPPERCASE duplicates of the same
  names. (Pre-existing, unrelated: §9 calls the queue `jobs`; the schema uses `job_log`.)
- Config: add `nurture_max_touches` (3) and `nurture_interval_days` (21) to `config/thresholds.json`,
  consistent with the config-driven rule.

### F6 (ALIGNED): §11 template library
`playbook_steps.template_id` references the existing `templates` table, and the doc restates §11's
core principle (a template is an approach, not text; examples are illustrations, not strings to
reuse). The applied schema already has `templates` + `template_stats`. Fully consistent.

### F7 (ALIGNED): doctrine
The playbook codifies existing operator doctrine: long-game nurture (leave in NURTURE, not CLOSED),
the capacity-question-not-interest-question close, voice-note-after-a-no, reframe-in-their-words, and
celebrate-what-they-have. It is the operational form of the nurture thesis logged this session.

### F8 (Rule 1, PASS): no em dashes
The original paste contained em dashes. The saved `docs/OUTREACH_PLAYBOOKS.md` was cleaned on write
(em dashes replaced, encoding normalized to UTF-8). Compliant with the global no-em-dash rule.

## Where it slots in the build (§12)
Post-`READY`/`DELIVERED`, so it is a later phase: it depends on the template library (§11) and on
reply capture (F4). Build after enrichment reliably reaches READY and daily reports ship. Phase 0 of
THIS feature = create the 4 tables (with F1/F2 applied) and encode `pb_eje_default` + `pb_001`.

## Net
No contradictions with the master plan once F1 (separate engagement machine) and F2 (single event
log) are honored. Adopt the doc as the library seed; implement the two structural fixes at table-
design time, not after.
