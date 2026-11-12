-- Non-destructive migration: add annotations.reviewed_at (re-review queue fix).
-- Once an annotator revisits an item via /review and re-saves, reviewed_at is set
-- so the item drops out of the re-review queue even if a trigger still matches
-- (e.g. they confirm "still not relevant", or an item hit both triggers).
-- Safe to run repeatedly; preserves all existing data.
--
-- Apply:
--   docker compose exec -T db psql -U annotation -d annotation < scripts/migrate_reviewed_at.sql

ALTER TABLE annotations ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
