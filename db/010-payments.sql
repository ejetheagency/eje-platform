-- db/010-payments.sql
-- Records Stripe payment events (activation fees). The webhook (api/stripe-webhook.js) writes here.
-- When a checkout carries metadata.client_id, the webhook also enqueues a `provision_client` job so
-- payment -> activation is automatic. Admin-only (clients never see payments). Additive.
create table if not exists payments (
  id              uuid primary key default gen_random_uuid(),
  stripe_event_id text unique,                 -- idempotency: one row per Stripe event
  type            text,                        -- e.g. checkout.session.completed
  session_id      text,
  payment_link    text,
  customer_email  text,
  amount_total    numeric(12,2),               -- in major units (dollars), not cents
  currency        text,
  client_id       text,                        -- from checkout metadata if present
  status          text default 'received',     -- received | provisioned | manual_review
  raw             jsonb,
  created_at      timestamptz not null default now()
);
create index if not exists payments_client_idx on payments(client_id);

alter table payments enable row level security;
create policy admin_payments on payments for all to public
  using (public.auth_is_admin()) with check (public.auth_is_admin());
