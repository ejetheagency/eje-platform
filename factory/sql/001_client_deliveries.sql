-- factory/sql/001_client_deliveries.sql
-- The Delivered ledger (operator 2026-10-08). A contact is delivered to a client ONCE, EVER.
-- Run in the Supabase SQL editor (Dashboard -> SQL) OR via a valid PAT / DB connection.
-- Note: the app-facing `leads` are email-keyed, so the stable contact identity is the email (contact_key);
-- contact_id/lead_id are kept for the factory model when known. Unique on (client_id, contact_key).
create table if not exists public.client_deliveries (
  id            bigint generated always as identity primary key,
  client_id     text not null,
  contact_key   text not null,                 -- stable contact identity (email) — the "once ever" key
  contact_id    uuid,                          -- factory contacts.id when known
  lead_id       text,                          -- delivered leads row (domain id)
  report_date   date not null,                 -- FIRST delivery date (dups keep the earliest)
  delivered_at  timestamptz not null default now(),
  unique (client_id, contact_key)
);
create index if not exists client_deliveries_client_idx on public.client_deliveries (client_id);
-- app reads it with the anon key, same as `leads`:
grant select on public.client_deliveries to anon, authenticated;
grant all on public.client_deliveries to service_role;
alter table public.client_deliveries enable row level security;
drop policy if exists client_deliveries_read on public.client_deliveries;
create policy client_deliveries_read on public.client_deliveries for select using (true);
