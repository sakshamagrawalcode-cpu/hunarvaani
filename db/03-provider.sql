DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name = 'call' AND column_name = 'plivo_request_uuid') THEN
    ALTER TABLE call RENAME COLUMN plivo_request_uuid TO provider_call_id;
  END IF;
END $$;
ALTER TABLE call ADD COLUMN IF NOT EXISTS provider_call_id TEXT;
CREATE INDEX IF NOT EXISTS call_provider_call_id_idx ON call (provider_call_id);
