-- EJE tenant isolation. Mirrors api/_lib/auth.js canAccess: admin (any admin membership) sees all;
-- member sees only their client_id(s). SECURITY DEFINER so the helpers read memberships regardless of its RLS.
create or replace function public.auth_is_admin()
  returns boolean language sql stable security definer set search_path = public as
$fn$ select exists (select 1 from public.memberships where user_id = auth.uid() and role = 'admin') $fn$;

create or replace function public.auth_client_ids()
  returns setof text language sql stable security definer set search_path = public as
$fn$ select client_id from public.memberships where user_id = auth.uid() $fn$;

grant execute on function public.auth_is_admin() to authenticated, anon;
grant execute on function public.auth_client_ids() to authenticated, anon;

-- leads
drop policy if exists "Allow all on leads" on public.leads;
create policy tenant_leads on public.leads for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- messages_sent
drop policy if exists "Allow all on messages_sent" on public.messages_sent;
create policy tenant_messages_sent on public.messages_sent for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- status_history
drop policy if exists "Allow all on status_history" on public.status_history;
create policy tenant_status_history on public.status_history for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- notes
drop policy if exists "Allow all on notes" on public.notes;
create policy tenant_notes on public.notes for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- actions
drop policy if exists "Allow all on actions" on public.actions;
create policy tenant_actions on public.actions for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- tracked_leads (had tl_read/tl_write/tl_update, no delete)
drop policy if exists tl_read on public.tracked_leads;
drop policy if exists tl_write on public.tracked_leads;
drop policy if exists tl_update on public.tracked_leads;
create policy tenant_tracked_leads on public.tracked_leads for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- tracked_lead_notes
drop policy if exists tln_read on public.tracked_lead_notes;
drop policy if exists tln_write on public.tracked_lead_notes;
create policy tenant_tracked_lead_notes on public.tracked_lead_notes for all to public
  using (public.auth_is_admin() or client_id in (select public.auth_client_ids()))
  with check (public.auth_is_admin() or client_id in (select public.auth_client_ids()));

-- ── clients + memberships lockdown (applied same day) ──
alter table public.clients enable row level security;
drop policy if exists tenant_clients on public.clients;
create policy tenant_clients on public.clients for all to public
  using (public.auth_is_admin() or id in (select public.auth_client_ids()))
  with check (public.auth_is_admin());

alter table public.memberships enable row level security;
drop policy if exists own_memberships on public.memberships;
create policy own_memberships on public.memberships for all to public
  using (public.auth_is_admin() or user_id = auth.uid())
  with check (public.auth_is_admin());

-- Applied via Supabase Management API on prod (ogdsuztzhmnnjolilsuo), 2026-10-01.
-- Verified: member sees only own client; admin sees all; cross-tenant write rejected (42501);
-- /api/* unaffected (db.js uses service_role which bypasses RLS). Frontend __ejeSB carries the
-- user JWT (signInWithPassword, persistSession), so these policies govern all direct reads/writes.
