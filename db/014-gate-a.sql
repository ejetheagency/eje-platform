-- db/014-gate-a.sql  (STEP 3 lineage + PIVOT_ENGINE §4b Gate A corroboration)  Applied 2026-10-03.
-- Keeps enrichment_findings (NOT renamed to facts, per decision 004). Adds the lineage edge + the
-- corroboration graph + a persons candidate store. Idempotent.

-- STEP 3: lineage so a fact can be walked back to its seed, and the corroboration fields §4b needs.
alter table enrichment_findings add column if not exists source_finding_id uuid references enrichment_findings(id);
alter table enrichment_findings add column if not exists pivot_name  text;
alter table enrichment_findings add column if not exists first_party boolean default false;
alter table enrichment_findings add column if not exists person_key  text;         -- normalized full name + company
alter table enrichment_findings add column if not exists verified_at timestamptz;   -- null until a gate/verifier confirms
alter table enrichment_findings add column if not exists evidence_url text;
alter table enrichment_findings add column if not exists source_type text;          -- e.g. operator_seed
create index if not exists ef_person_idx on enrichment_findings(company_id, person_key);

-- §4b: corroboration edges. Written ONLY by the corroboration pivot after it fetched evidence.
create table if not exists corroborations (
  id               uuid primary key default gen_random_uuid(),
  company_id       uuid not null references companies(id) on delete cascade,
  person_key       text not null,
  fact_id          uuid references enrichment_findings(id) on delete cascade,
  confirms_fact_id uuid references enrichment_findings(id) on delete cascade,
  relation         text,     -- same_name | same_role | same_company | same_handle | same_email | contradicts
  source_pivot     text,
  confidence       numeric,
  evidence_url     text,
  created_at       timestamptz not null default now()
);
create index if not exists corroborations_person_idx on corroborations(company_id, person_key);

-- §4b: persons candidate store (the worker maintains it; operator may prefer a pure view, flagged in the report).
create table if not exists persons (
  id                        uuid primary key default gen_random_uuid(),
  company_id                uuid not null references companies(id) on delete cascade,
  person_key                text not null,
  name                      text,
  role                      text,
  first_party_count         int default 0,
  independent_source_count  int default 0,
  corroboration_score       numeric default 0,
  contradiction_count       int default 0,
  email                     text,
  email_status              text,
  email_verify_method       text,
  discovered_via            text,
  gate_a_passed_at          timestamptz,
  gate_b_passed_at          timestamptz,
  updated_at                timestamptz not null default now(),
  unique (company_id, person_key)
);

alter table corroborations enable row level security;
alter table persons        enable row level security;
create policy admin_corroborations on corroborations for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
create policy admin_persons        on persons        for all to public using (public.auth_is_admin()) with check (public.auth_is_admin());
