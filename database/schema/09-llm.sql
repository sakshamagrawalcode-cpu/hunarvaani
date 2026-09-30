-- What the India-hosted LLM understood from the work story: occupations, years, skills, wants,
-- and the sentence said back to the caller.
ALTER TABLE story ADD COLUMN IF NOT EXISTS llm JSONB;
