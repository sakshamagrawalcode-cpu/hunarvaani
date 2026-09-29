ALTER TABLE call ADD COLUMN IF NOT EXISTS plivo_request_uuid TEXT;
CREATE INDEX IF NOT EXISTS event_kind_idx ON event (kind);
