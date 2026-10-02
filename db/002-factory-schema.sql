-- ============================================================================
-- EJE FACTORY SCHEMA  —  DESIGN ONLY, NOT YET APPLIED (Phase 1).
-- The global-dedupe backbone + cost governance + lead state machine from
-- docs/ENRICHMENT_MASTER_PLAN.md §9 + §4, plus the dream-team's signals + email
-- cost-cascade needs. Reuses the RLS helpers auth_is_admin() / auth_client_ids()
-- from db/rls-2026-10-01-tenant-isolation.sql.
--
-- TWO ZONES:
--   GLOBAL POOL  = shared across clients, enriched ONCE, reused many times.
--                  Members NEVER see the pool directly (library model) — access
--                  only via the service-role /api. RLS = admin-only.
--   PER-CLIENT   = a client's pipeline + results. RLS = tenant-scoped (member sees own).
-- Workers use the service_role key (bypasses RLS). The browser never reads the pool.
-- ============================================================================

-- ─────────────────────────── GLOBAL POOL ───────────────────────────

-- Companies: deduped across ALL clients. dedupe_key handles domain-less (IG-only) leads
-- so a pyme without a website is still trackable (fixes the "no domain => dropped" bug).
create table if not exists companies (
  id               uuid primary key default gen_random_uuid(),
  dedupe_key       text unique not null,        -- domain | 'ig:'||handle | 'name:'||norm||'|'||country
  domain           text,
  name             text not null,
  country          text,
  industry         text,
  website          text,
  instagram        text,
  linkedin         text,
  brief            text,
  logo_url         text,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now(),
  last_enriched_at timestamptz
);
create index if not exists companies_domain_idx on companies(domain);

-- Contacts: people at companies, global, with a verification freshness date (don't pay twice).
create table if not exists contacts (
  id                uuid primary key default gen_random_uuid(),
  company_id        uuid not null references companies(id) on delete cascade,
  full_name         text,
  first_name        text,
  title             text,
  is_decision_maker boolean default false,
  email             text,
  email_status      text default 'unknown',     -- unknown | pattern | verified | invalid | catchall
  email_source      text,                        -- free | pattern | reacher | icypeas | prospeo | hunter | apollo
  email_verified_at timestamptz,
  phone             text,
  linkedin_url      text,
  instagram         text,
  created_at        timestamptz default now(),
  updated_at        timestamptz default now(),
  last_verified_at  timestamptz
);
create index if not exists contacts_company_idx on contacts(company_id);
create unique index if not exists contacts_company_email_idx on contacts(company_id, lower(email)) where email is not null;

-- Shared findings board: every worker writes what it found; others read it BEFORE re-working.
-- This is how "agents exchange ideas" without talking (cheap + debuggable).
create table if not exists enrichment_findings (
  id          uuid primary key default gen_random_uuid(),
  company_id  uuid not null references companies(id) on delete cascade,
  field       text not null,                     -- email | instagram | brief | employee_count | ...
  value       jsonb,
  source      text,                               -- provider/strategy that found it
  strategy_id uuid,
  confidence  real default 0.5,
  cost_usd    numeric(10,5) default 0,
  found_at    timestamptz default now()
);
create index if not exists findings_company_field_idx on enrichment_findings(company_id, field);

-- "Why-now" signals (dream-team Signal Spotter): the layer that actually lifts replies.
create table if not exists signals (
  id          uuid primary key default gen_random_uuid(),
  company_id  uuid not null references companies(id) on delete cascade,
  type        text not null,                      -- hiring | new_location | posting_spike | funding | press | ...
  detail      text,
  strength    real default 0.5,
  source      text,
  detected_at timestamptz default now(),
  expires_at  timestamptz
);
create index if not exists signals_company_idx on signals(company_id);

-- Logos/assets: store the URL only; the app never processes images.
create table if not exists assets (
  id          uuid primary key default gen_random_uuid(),
  company_id  uuid not null references companies(id) on delete cascade,
  kind        text default 'logo',
  url         text not null,
  source      text,                               -- brandfetch | site_meta | unavatar | monogram
  width       int,
  created_at  timestamptz default now()
);
create index if not exists assets_company_idx on assets(company_id);

-- ─────────────────────────── PER-CLIENT ───────────────────────────

-- The pipeline link: client ↔ company, with lifecycle state. Replaces the per-client
-- semantics of the old flat `leads` table. legacy_lead_id bridges existing outreach rows.
create table if not exists client_leads (
  id             uuid primary key default gen_random_uuid(),
  client_id      text not null,
  company_id     uuid not null references companies(id) on delete cascade,
  contact_id     uuid references contacts(id),    -- the chosen decision-maker for THIS client
  state          text not null default 'DISCOVERED',
  score          int,
  cycle_count    int default 0,
  source         text,                            -- how discovered for this client
  icp_id         uuid,
  ready          boolean default false,
  hold_reason    text,
  quality_flags  jsonb,
  legacy_lead_id text,                            -- = old leads.id (text) for migration bridging
  discovered_at  timestamptz default now(),
  delivered_at   timestamptz,
  created_at     timestamptz default now(),
  updated_at     timestamptz default now(),
  unique (client_id, company_id)
);
create index if not exists client_leads_client_state_idx on client_leads(client_id, state);
create index if not exists client_leads_legacy_idx on client_leads(legacy_lead_id);
-- State machine (ENRICHMENT_MASTER_PLAN §4). Transitions enforced in /packages/lead_state;
-- this CHECK is the DB guardrail.
alter table client_leads drop constraint if exists client_leads_state_chk;
alter table client_leads add constraint client_leads_state_chk check (state in
  ('DISCOVERED','T1_ENRICHING','SCORED','DISCARDED','GATE_CHECK','T2_ENRICHING','T3_REASONING','READY','PARKED','DELIVERED'));

-- Quality gate outcomes per lead: records WHICH fields are missing so the next pass targets only those.
create table if not exists gate_results (
  id             uuid primary key default gen_random_uuid(),
  client_lead_id uuid not null references client_leads(id) on delete cascade,
  client_id      text not null,
  gate           text not null,
  passed         boolean not null,
  missing_fields jsonb,
  checked_at     timestamptz default now()
);
create index if not exists gate_results_lead_idx on gate_results(client_lead_id);

-- Client actions on leads: feeds learning + the north-star metric (replies per 100 delivered).
create table if not exists engagement_events (
  id             uuid primary key default gen_random_uuid(),
  client_id      text not null,
  client_lead_id uuid references client_leads(id) on delete cascade,
  event          text not null,                   -- viewed | contacted | replied | positive_reply | meeting | won | ignored
  channel        text,
  at             timestamptz default now(),
  meta           jsonb
);
create index if not exists engagement_client_event_idx on engagement_events(client_id, event);

-- Precomputed daily reports. The web app ONLY reads these (no computation in the request path).
create table if not exists reports (
  id          uuid primary key default gen_random_uuid(),
  client_id   text not null,
  report_date date not null,
  payload     jsonb not null,
  created_at  timestamptz default now(),
  unique (client_id, report_date)
);

-- ─────────────────────────── LEARNING ───────────────────────────
create table if not exists strategies (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  description text,
  channel     text,
  active      boolean default true,
  created_at  timestamptz default now()
);
create table if not exists strategy_runs (
  id                 uuid primary key default gen_random_uuid(),
  strategy_id        uuid references strategies(id),
  company_id         uuid references companies(id),
  client_lead_id     uuid references client_leads(id),
  fields_found       int default 0,
  fields_passed_gate int default 0,
  reply_outcome      text,                         -- backfilled from engagement_events
  cost_usd           numeric(10,5) default 0,
  ran_at             timestamptz default now()
);

-- ─────────────────────────── TEMPLATES ───────────────────────────
-- A template is an APPROACH, not a message (ENRICHMENT_MASTER_PLAN §11). Messages are generated per recipient.
create table if not exists templates (
  id              uuid primary key default gen_random_uuid(),
  owner_client_id text,                            -- null/shared = community
  channel         text not null,                   -- email | whatsapp | instagram_dm | linkedin
  approach        text,
  tone            text,
  structure       jsonb,
  required_fields jsonb,
  shared          boolean default false,
  created_at      timestamptz default now()
);
create table if not exists template_stats (
  template_id      uuid primary key references templates(id) on delete cascade,
  sends            int default 0,
  replies          int default 0,
  positive_replies int default 0,
  meetings         int default 0,
  updated_at       timestamptz default now()
);

-- ─────────────────────────── TREASURY (D8) ───────────────────────────
-- Every external call logs here. can_spend() reads provider_accounts + plan budgets + this ledger.
create table if not exists cost_ledger (
  id           uuid primary key default gen_random_uuid(),
  provider     text not null,                      -- gemini | groq | apollo | hunter | icypeas | serper | ...
  client_id    text,
  company_id   uuid,
  job_type     text,
  credits_used numeric(12,4) default 0,
  usd_cost     numeric(10,5) default 0,
  estimated    boolean default true,
  created_at   timestamptz default now()
);
create index if not exists cost_ledger_client_idx on cost_ledger(client_id, created_at);
create index if not exists cost_ledger_provider_idx on cost_ledger(provider, created_at);

create table if not exists provider_accounts (
  provider          text primary key,
  credits_remaining numeric(12,4),
  monthly_cap_usd   numeric(10,2),
  meta              jsonb,
  updated_at        timestamptz default now()
);

-- ─────────────────────────── JOBS ───────────────────────────
-- Live queue = Supabase pgmq (one queue per job type). This table is the audit/observability log.
create table if not exists job_log (
  id             uuid primary key default gen_random_uuid(),
  type           text not null,
  client_id      text,
  company_id     uuid,
  client_lead_id uuid,
  status         text,                             -- queued | running | done | failed | dead
  attempt        int default 0,
  estimated_cost numeric(10,5) default 0,
  error          text,
  created_at     timestamptz default now(),
  updated_at     timestamptz default now()
);
create index if not exists job_log_status_idx on job_log(status, type);

-- ═══════════════════════════ RLS ═══════════════════════════
-- Per-client tables = tenant-scoped (member sees own; admin all). Reuse the helpers.
alter table client_leads       enable row level security;
alter table gate_results       enable row level security;
alter table engagement_events  enable row level security;
alter table reports            enable row level security;

create policy tenant_client_leads on client_leads for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));
create policy tenant_gate_results on gate_results for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));
create policy tenant_engagement on engagement_events for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));
create policy tenant_reports on reports for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- Global pool = members NEVER read it directly (the library stays invisible). Admin-only;
-- workers use service_role (bypasses RLS). Enabling RLS with an admin-only policy denies members.
alter table companies           enable row level security;
alter table contacts            enable row level security;
alter table enrichment_findings enable row level security;
alter table signals             enable row level security;
alter table assets              enable row level security;
alter table strategies          enable row level security;
alter table strategy_runs       enable row level security;
alter table cost_ledger         enable row level security;
alter table provider_accounts   enable row level security;
alter table job_log             enable row level security;

create policy admin_companies           on companies           for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_contacts            on contacts            for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_findings            on enrichment_findings for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_signals             on signals             for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_assets              on assets              for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_strategies          on strategies          for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_strategy_runs       on strategy_runs       for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_cost_ledger         on cost_ledger         for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_provider_accounts   on provider_accounts   for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_job_log             on job_log             for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());

-- Templates: owner sees own; everyone sees shared/community; only owner/admin writes.
alter table templates      enable row level security;
alter table template_stats enable row level security;
create policy tenant_templates on templates for all to public
  using (public.auth_is_admin() or shared = true or owner_client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or owner_client_id in (select public.auth_client_ids()));
create policy read_template_stats on template_stats for select to public using (true);  -- community stats are public (min-sample gated in app)

-- ═══════════════════════════ pgmq QUEUES (run once; needs the extension) ═══════════════════════════
-- create extension if not exists pgmq;
-- select pgmq.create('discovery'); select pgmq.create('enrich_t1'); select pgmq.create('enrich_t2');
-- select pgmq.create('gates');     select pgmq.create('reasoning_t3'); select pgmq.create('assets');
-- select pgmq.create('signals');   select pgmq.create('reports');
