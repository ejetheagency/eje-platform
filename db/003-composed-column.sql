-- Composer output stored on the lead so every READY lead is pitch-ready. Applied to prod 2026-10-01.
alter table client_leads add column if not exists composed jsonb;        -- {dossier, pitch, channel, next_action, citations}
alter table client_leads add column if not exists composed_at timestamptz;
