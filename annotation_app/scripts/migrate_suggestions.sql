-- Non-destructive migration for Milestone 3.5/4 (too_short LLM suggestions).
-- Safe to run repeatedly; preserves all existing data.
--
-- Apply:
--   docker compose exec -T db psql -U annotation -d annotation < scripts/migrate_suggestions.sql

ALTER TABLE annotations ADD COLUMN IF NOT EXISTS missing_info TEXT;

CREATE TABLE IF NOT EXISTS suggested_passages (
    id             SERIAL PRIMARY KEY,
    annotation_id  INT NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
    passage_text   TEXT NOT NULL,
    source_ref     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_suggested_annotation ON suggested_passages(annotation_id);
