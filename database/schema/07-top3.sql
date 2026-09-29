-- The read-back now offers three occupations; the third best match is kept too.
ALTER TABLE story ADD COLUMN IF NOT EXISTS top3 TEXT;
