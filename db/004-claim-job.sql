-- Atomic job claim for the factory queue (FOR UPDATE SKIP LOCKED so concurrent workers never double-grant).
-- Applied to prod 2026-10-01 (recorded here for reproducibility; the audit flagged it was in no db/ file).
create or replace function public.claim_job(p_type text default null)
returns setof job_log language plpgsql as $$
declare r public.job_log;
begin
  select * into r from public.job_log
    where status = 'queued' and (p_type is null or type = p_type)
    order by created_at
    for update skip locked limit 1;
  if not found then return; end if;
  update public.job_log set status = 'running', attempt = attempt + 1, updated_at = now()
    where id = r.id returning * into r;
  return next r;
end $$;
revoke all on function public.claim_job(text) from anon, authenticated;
