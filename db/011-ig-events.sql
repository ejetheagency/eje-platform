-- db/011-ig-events.sql
-- Raw capture of Instagram messaging webhook events (DMs). api/ig-webhook.js writes here. This is the
-- INPUT side of the moat: inbound IG replies, which later get matched to a lead/run and classified
-- (soft_no/reopened/...). For now we store raw; mapping + classification is a follow-up. Admin-only.
create table if not exists ig_events (
  id           uuid primary key default gen_random_uuid(),
  object       text,                 -- 'instagram'
  entry_id     text,                 -- the IG account id the event belongs to
  sender_id    text,
  recipient_id text,
  mid          text unique,          -- message id (idempotency)
  message_text text,
  ts           timestamptz,
  raw          jsonb,
  created_at   timestamptz not null default now()
);
create index if not exists ig_events_sender_idx on ig_events(sender_id);

alter table ig_events enable row level security;
create policy admin_ig_events on ig_events for all to public
  using (public.auth_is_admin()) with check (public.auth_is_admin());
