-- The caller's words in English, for the team console (Sarvam translate).
ALTER TABLE story ADD COLUMN IF NOT EXISTS transcript_en TEXT;
