-- The training / livelihood options found for a call (step A9/A10), from the SAMPLE dataset.
-- `details` holds the option as the console shows it (reasons, skill gap, scheme, centre);
-- `spoken` = said on the call; `chosen` = the caller pressed its number.
CREATE TABLE IF NOT EXISTS recommendation (
  id BIGSERIAL PRIMARY KEY,
  call_id UUID NOT NULL REFERENCES call (id) ON DELETE CASCADE,
  rank INT NOT NULL,
  course_id TEXT NOT NULL,
  centre_id TEXT,
  score REAL,
  details JSONB NOT NULL,
  spoken BOOLEAN NOT NULL DEFAULT false,
  chosen BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS recommendation_call ON recommendation (call_id);
