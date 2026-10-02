-- db/009-icps.sql
-- Structured ICP table (ENRICHMENT_MASTER_PLAN §9: `icps`). Until now each client's ICP lived in a
-- flat `clients.icp_config` blob; this promotes it to a first-class, queryable row that the
-- discovery/scoring workers and the self-serve onboarding (activate_client) use. client_leads.icp_id
-- (already in the schema) points here. The app keeps reading clients.icp_config during the transition
-- (activate_client dual-writes), so this is additive and changes no running behavior.

create table if not exists icps (
  id                uuid primary key default gen_random_uuid(),
  client_id         text not null,
  name              text not null default 'default',
  brief             text,                         -- who we target (the ICP description)
  voice             text,                         -- tone/voice guidance for outreach
  decisor_role      text,                         -- owner | founder | CEO | director de marketing ...
  geos              text[],                       -- target countries/regions
  sectors           text[],
  signals           jsonb,                        -- per-client quality signals (icp_config.signals)
  discovery_queries text[],                       -- seed searches for Discovery
  playbook_id       text references playbooks(id),-- default outreach cadence for this ICP
  config            jsonb,                        -- full original icp_config (anything unmapped is preserved)
  active            boolean not null default true,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (client_id, name)
);
create index if not exists icps_client_idx on icps(client_id);

alter table icps enable row level security;
create policy tenant_icps on icps for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));
