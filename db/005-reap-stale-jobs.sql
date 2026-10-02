-- Re-queue jobs orphaned by a dead worker/container (stuck in 'running'). Retries until p_max_attempts, then dead-letters.
-- Applied to prod 2026-10-02. Called by run_nightly at the start of each run (queue.reap()).
create or replace function public.reap_stale_jobs(p_minutes int default 10, p_max_attempts int default 5)
returns int language plpgsql as $$
declare n int;
begin
  update public.job_log
    set status = case when attempt >= p_max_attempts then 'dead' else 'queued' end, updated_at = now()
    where status = 'running' and updated_at < now() - (p_minutes || ' minutes')::interval;
  get diagnostics n = row_count;
  return n;
end $$;
revoke all on function public.reap_stale_jobs(int, int) from anon, authenticated;
