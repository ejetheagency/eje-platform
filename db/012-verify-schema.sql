-- db/012-verify-schema.sql  (STEP 1.5)  Applied to prod 2026-10-02.
-- Verifier interface + Gate B (SMTP) tracking. Idempotent.
alter table contacts add column if not exists email_verify_method   text;        -- 'smtp' | 'corroboration'
alter table contacts add column if not exists email_verify_attempts int default 0; -- unknown/timeout retry cap (max 2)
alter table provider_accounts add column if not exists quota_paid int;  -- purchased credits (e.g. MillionVerifier)
alter table provider_accounts add column if not exists quota_free int;

-- MillionVerifier verifier account. credits_remaining is updated live by the adapter on every call, so the
-- ledger is no longer blind to the real vendor wall. 500 = the credits on the account tonight.
insert into provider_accounts (provider, quota_paid, quota_free, credits_remaining)
  select 'millionverifier', 500, 0, 500
  where not exists (select 1 from provider_accounts where provider = 'millionverifier');
