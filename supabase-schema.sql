-- ═══════════════════════════════════════════════════════════
-- UnaBase Supabase Schema — Full (idempotent, safe to re-run)
-- ═══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  contact_name TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  country TEXT,
  industry TEXT,
  score INTEGER DEFAULT 0,
  status TEXT DEFAULT 'none',
  source_date TEXT,
  is_historical BOOLEAN DEFAULT FALSE,
  lead_data JSONB,
  client_id TEXT NOT NULL DEFAULT 'unabase_default',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS actions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  lead_id TEXT REFERENCES leads(id),
  user_name TEXT DEFAULT 'scarlett',
  channel TEXT NOT NULL,
  completed BOOLEAN DEFAULT TRUE,
  client_id TEXT NOT NULL DEFAULT 'unabase_default',
  completed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages_sent (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  lead_id TEXT REFERENCES leads(id),
  user_name TEXT DEFAULT 'scarlett',
  channel TEXT NOT NULL,
  message_text TEXT NOT NULL,
  client_id TEXT NOT NULL DEFAULT 'unabase_default',
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notes (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  lead_id TEXT REFERENCES leads(id),
  user_name TEXT DEFAULT 'scarlett',
  note_text TEXT,
  client_id TEXT NOT NULL DEFAULT 'unabase_default',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS status_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  lead_id TEXT REFERENCES leads(id),
  user_name TEXT DEFAULT 'scarlett',
  status TEXT NOT NULL,
  client_id TEXT NOT NULL DEFAULT 'unabase_default',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages_sent ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE status_history ENABLE ROW LEVEL SECURITY;

-- Policies (DROP IF EXISTS + CREATE to be idempotent)
DO $$ BEGIN
  DROP POLICY IF EXISTS "Allow all on leads" ON leads;
  CREATE POLICY "Allow all on leads" ON leads FOR ALL USING (true) WITH CHECK (true);
  DROP POLICY IF EXISTS "Allow all on actions" ON actions;
  CREATE POLICY "Allow all on actions" ON actions FOR ALL USING (true) WITH CHECK (true);
  DROP POLICY IF EXISTS "Allow all on messages_sent" ON messages_sent;
  CREATE POLICY "Allow all on messages_sent" ON messages_sent FOR ALL USING (true) WITH CHECK (true);
  DROP POLICY IF EXISTS "Allow all on notes" ON notes;
  CREATE POLICY "Allow all on notes" ON notes FOR ALL USING (true) WITH CHECK (true);
  DROP POLICY IF EXISTS "Allow all on status_history" ON status_history;
  CREATE POLICY "Allow all on status_history" ON status_history FOR ALL USING (true) WITH CHECK (true);
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_leads_client ON leads(client_id);
CREATE INDEX IF NOT EXISTS idx_actions_client ON actions(client_id);
CREATE INDEX IF NOT EXISTS idx_messages_client ON messages_sent(client_id);
CREATE INDEX IF NOT EXISTS idx_notes_client ON notes(client_id);
CREATE INDEX IF NOT EXISTS idx_status_client ON status_history(client_id);

-- Unique constraint: one action per (lead, channel, user, client)
-- Prevents duplicate action rows from double-clicks, network retries,
-- or self-heal race conditions. Safe to re-run (IF NOT EXISTS).
CREATE UNIQUE INDEX IF NOT EXISTS idx_actions_unique
  ON actions(lead_id, channel, user_name, client_id);

-- ═══ MESSAGE DEDUPLICATION ═══
-- Composite unique: one message per (lead, channel, text, sent_at, user, client).
-- This allows real follow-ups (different sent_at) while blocking exact duplicates.
-- Safe to re-run (IF NOT EXISTS).
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_unique
  ON messages_sent(lead_id, channel, message_text, sent_at, user_name, client_id);

-- ═══ CLEANUP: Remove historical near-duplicate messages ═══
--
-- WHY THIS IS SAFE:
--   The bug created duplicate rows whose sent_at values differ by < 60 seconds
--   (client now() vs server DEFAULT NOW(), or self-heal replay on reload).
--   A legitimate follow-up to the same lead on the same channel would be sent
--   hours or days later — never within 60 seconds of an identical message.
--   This query ONLY deletes the later row when two rows match on
--   (lead_id, channel, message_text, user_name, client_id) AND their sent_at
--   timestamps are within 60 seconds of each other. Follow-ups sent on a
--   different day (or even a different hour) are never touched.
--
-- RUN ON SUPABASE DASHBOARD IN THIS ORDER:

-- ── STEP 1: PREVIEW — see what WOULD be deleted (run first, review) ──
--
-- SELECT
--   a.id            AS row_to_delete,
--   a.lead_id,
--   a.channel,
--   LEFT(a.message_text, 40) AS text_preview,
--   a.sent_at       AS dup_sent_at,
--   b.sent_at       AS kept_sent_at,
--   EXTRACT(EPOCH FROM (a.sent_at - b.sent_at)) AS drift_seconds
-- FROM messages_sent a
-- JOIN messages_sent b
--   ON  a.lead_id       = b.lead_id
--   AND a.channel        = b.channel
--   AND a.message_text   = b.message_text
--   AND a.user_name      = b.user_name
--   AND a.client_id      = b.client_id
--   AND a.id             > b.id                        -- b is the earlier row (kept)
--   AND ABS(EXTRACT(EPOCH FROM (a.sent_at - b.sent_at))) < 60  -- within 60s = bug artifact
-- ORDER BY a.lead_id, a.channel, a.sent_at;

-- ── STEP 2: DELETE — remove only the near-duplicate rows ──
--
-- DELETE FROM messages_sent a
-- USING messages_sent b
-- WHERE a.lead_id       = b.lead_id
--   AND a.channel        = b.channel
--   AND a.message_text   = b.message_text
--   AND a.user_name      = b.user_name
--   AND a.client_id      = b.client_id
--   AND a.id             > b.id
--   AND ABS(EXTRACT(EPOCH FROM (a.sent_at - b.sent_at))) < 60;
