CREATE TABLE IF NOT EXISTS call (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_hash TEXT NOT NULL,
  phone_enc BYTEA,
  plivo_call_uuid TEXT UNIQUE,
  missed_at TIMESTAMPTZ,
  callback_at TIMESTAMPTZ,
  answered_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  duration_seconds INT,
  language TEXT,
  keypad_only BOOLEAN NOT NULL DEFAULT false,
  human_flag BOOLEAN NOT NULL DEFAULT false,
  status TEXT
);
CREATE INDEX IF NOT EXISTS call_phone_hash_idx ON call (phone_hash);
CREATE INDEX IF NOT EXISTS call_missed_at_idx ON call (missed_at);

CREATE TABLE IF NOT EXISTS answer (
  call_id UUID NOT NULL REFERENCES call (id) ON DELETE CASCADE,
  step TEXT NOT NULL,
  key_pressed TEXT,
  value TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS answer_call_id_idx ON answer (call_id);

CREATE TABLE IF NOT EXISTS consent (
  call_id UUID NOT NULL REFERENCES call (id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  granted BOOLEAN NOT NULL,
  prompt_version TEXT,
  hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS consent_call_id_idx ON consent (call_id);

CREATE TABLE IF NOT EXISTS story (
  call_id UUID NOT NULL REFERENCES call (id) ON DELETE CASCADE,
  recording_url TEXT,
  transcript TEXT,
  top1 TEXT,
  top2 TEXT,
  confirmed TEXT,
  stt_ms INT,
  search_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS story_call_id_idx ON story (call_id);

CREATE TABLE IF NOT EXISTS event (
  id BIGSERIAL PRIMARY KEY,
  call_id UUID NOT NULL REFERENCES call (id) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  payload JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS event_call_id_idx ON event (call_id);

CREATE TABLE IF NOT EXISTS nco (
  nco_code TEXT PRIMARY KEY,
  title_en TEXT NOT NULL,
  title_hi TEXT NOT NULL,
  aliases TEXT NOT NULL,
  embedding vector(768)
);

CREATE TABLE IF NOT EXISTS blocked_number (
  phone_hash TEXT PRIMARY KEY,
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
