-- Marathi occupation names, spoken in the read-back and summary of Marathi calls.
ALTER TABLE nco ADD COLUMN IF NOT EXISTS title_mr TEXT NOT NULL DEFAULT '';
