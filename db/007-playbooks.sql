-- db/007-playbooks.sql
-- Outreach playbook engine. Implements docs/OUTREACH_PLAYBOOKS.md with the two structural
-- fixes from docs/decisions/003-outreach-playbooks-audit-2026-10-02.md:
--   F1: engagement is a SEPARATE lifecycle from the ENRICHMENT_MASTER_PLAN §4 machine. It lives
--       on playbook_runs.state and is NEVER added to /packages/lead_state (that stays §4 only).
--   F2: engagement_events remains the SINGLE source of truth. We add run linkage + outcome here
--       instead of a parallel `touches` table, so the learning worker reads one log, not two.
-- Additive only (new tables + nullable columns). Changes no running behavior: the app.html
-- cadence keeps working until a worker reads these tables.

-- The library: an approach-level sequence, not messages (ties to §11 templates).
create table if not exists playbooks (
  id          text primary key,                 -- pb_eje_default, pb_001_channel_switch_reopen
  name        text not null,
  version     int  not null default 1,
  channel_set text[] not null default '{}',
  mode        text not null default 'broad',    -- broad | account_based
  author      text,                             -- 'eje' (system) or a client_id
  status      text not null default 'draft',    -- draft | active | retired
  created_at  timestamptz not null default now(),
  constraint playbooks_mode_chk   check (mode in ('broad','account_based')),
  constraint playbooks_status_chk check (status in ('draft','active','retired'))
);

-- One step = one touch: channel + trigger + intent (+ which template approach to generate from).
create table if not exists playbook_steps (
  id              bigint generated always as identity primary key,
  playbook_id     text not null references playbooks(id) on delete cascade,
  step_no         int  not null,
  trigger         jsonb not null default '{}'::jsonb,   -- { start | after_days | if | on }
  channel         text not null,                        -- email|instagram_dm|linkedin|whatsapp|voice_note|call
  intent          text not null,                        -- REQUIRED (doc §6 rule 2): shown to the client as the "why"
  template_id     uuid references templates(id),        -- approach, not text (§11)
  required_fields text[] not null default '{}',
  stop_if         text,
  next_state      text,                                 -- engagement state to set after this step (e.g. nurture)
  meta            jsonb not null default '{}'::jsonb,   -- example / notes / example_prompt / nurture_rule
  constraint playbook_steps_intent_chk check (length(btrim(intent)) > 0),
  unique (playbook_id, step_no)
);

-- One run = this playbook applied to one lead for one client. STATE here is the engagement
-- lifecycle (F1), distinct from client_leads.state (enrichment).
create table if not exists playbook_runs (
  id             uuid primary key default gen_random_uuid(),
  playbook_id    text not null references playbooks(id),
  client_id      text not null,
  client_lead_id uuid references client_leads(id) on delete cascade,  -- new model
  legacy_lead_id text,                            -- bridge to the old flat `leads` table (current outreach)
  started_at     timestamptz not null default now(),
  current_step   int not null default 0,
  state          text not null default 'running',
  updated_at     timestamptz not null default now(),
  constraint playbook_runs_state_chk check (state in
    ('running','replied','soft_no','hard_no','reopened','nurture','converted','stopped'))
);
create index if not exists playbook_runs_client_state_idx on playbook_runs(client_id, state);
create index if not exists playbook_runs_legacy_idx       on playbook_runs(legacy_lead_id);
create index if not exists playbook_runs_lead_idx         on playbook_runs(client_lead_id);

-- F2: single source of truth. engagement_events gains run linkage + the playbook outcome vocabulary.
alter table engagement_events add column if not exists run_id  uuid references playbook_runs(id) on delete set null;
alter table engagement_events add column if not exists step_no int;
alter table engagement_events add column if not exists outcome text;  -- none|seen|replied|soft_no|hard_no|question|reopened|asked_for_material
create index if not exists engagement_run_idx on engagement_events(run_id);

-- ── RLS (mirror the §9 pattern). Runs are tenant-scoped; the library is shared-readable, admin-writable. ──
alter table playbooks      enable row level security;
alter table playbook_steps enable row level security;
alter table playbook_runs  enable row level security;

-- Library readable when active, or to its author, or admin; writes admin-only (service_role bypasses).
create policy read_playbooks on playbooks for select to public
  using (public.auth_is_admin() or status = 'active' or author in (select public.auth_client_ids()));
create policy admin_playbooks on playbooks for all to public
  using (public.auth_is_admin()) with check (public.auth_is_admin());

create policy read_playbook_steps on playbook_steps for select to public
  using (public.auth_is_admin() or exists (
    select 1 from playbooks p where p.id = playbook_steps.playbook_id
      and (p.status = 'active' or p.author in (select public.auth_client_ids()))));
create policy admin_playbook_steps on playbook_steps for all to public
  using (public.auth_is_admin()) with check (public.auth_is_admin());

-- Runs: member sees own client's; admin all.
create policy tenant_playbook_runs on playbook_runs for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));
