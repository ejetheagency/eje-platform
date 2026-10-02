-- db/013-pool-floor-log.sql  (STEP 1.5)  Applied to prod 2026-10-02.
-- Nightly pool-floor log: one row per client per night (scheduler.pool_floor), so the 2-night under-50%
-- streak alert can look back. Admin-only.
create table if not exists pool_floor_log (
  id            uuid primary key default gen_random_uuid(),
  client_id     text not null,
  run_date      date not null,
  ready_now     int,
  target        int,
  jobs_enqueued int,
  spend_usd     numeric(10,4),
  under_50pct   boolean,
  created_at    timestamptz not null default now(),
  unique (client_id, run_date)
);
alter table pool_floor_log enable row level security;
drop policy if exists admin_pool_floor_log on pool_floor_log;
create policy admin_pool_floor_log on pool_floor_log for all to public
  using (public.auth_is_admin()) with check (public.auth_is_admin());
