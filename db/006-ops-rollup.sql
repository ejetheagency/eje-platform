-- Server-side ops/treasury rollup for the admin dashboard (aggregation beyond the 1000-row REST cap).
-- Applied to prod 2026-10-02. Called by api/ops.js via rpc (service key, admin-gated in the endpoint).
create or replace function public.ops_rollup(p_month_start timestamptz, p_today_start timestamptz)
returns json language sql stable as $$
  select json_build_object(
    'spend_month', coalesce((select round(sum(usd_cost)::numeric,2) from cost_ledger where created_at >= p_month_start),0),
    'spend_today', coalesce((select round(sum(usd_cost)::numeric,4) from cost_ledger where created_at >= p_today_start),0),
    'by_provider', (select coalesce(json_agg(row_to_json(t)),'[]') from (
        select provider, round(sum(usd_cost)::numeric,4) usd, count(*) calls
        from cost_ledger where created_at >= p_month_start group by provider order by sum(usd_cost) desc) t),
    'providers', (select coalesce(json_agg(row_to_json(p)),'[]') from (
        select pa.provider, pa.monthly_cap_usd,
               coalesce((select round(sum(usd_cost)::numeric,4) from cost_ledger c
                         where c.provider=pa.provider and c.created_at>=p_month_start),0) spent_month
        from provider_accounts pa order by pa.monthly_cap_usd desc nulls last) p),
    'lead_states', (select coalesce(json_agg(row_to_json(s)),'[]') from (
        select state, count(*) n from client_leads group by state order by count(*) desc) s),
    'queue', (select coalesce(json_agg(row_to_json(q)),'[]') from (
        select status, count(*) n from job_log group by status) q),
    'clients', (select coalesce(json_agg(row_to_json(c)),'[]') from (
        select client_id, count(*) filter (where state='READY') ready,
               count(*) filter (where state='DELIVERED') delivered, count(*) total
        from client_leads group by client_id order by count(*) filter (where state='READY') desc) c),
    'pool', (select json_build_object('companies',(select count(*) from companies),'contacts',(select count(*) from contacts)))
  );
$$;
revoke all on function public.ops_rollup(timestamptz,timestamptz) from anon, authenticated;
