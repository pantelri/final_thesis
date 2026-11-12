-- annotation_schema.sql
-- Canonical schema for HGB annotation platform (Masterarbeit)

CREATE TYPE element_type      AS ENUM ('sentence', 'table');
CREATE TYPE length_judg_type  AS ENUM ('ok', 'too_short', 'too_long');
CREATE TYPE applicable_type   AS ENUM ('yes', 'no', 'unsure');
CREATE TYPE fulfilled_type    AS ENUM ('yes', 'partially', 'no');

-- Annotators: identified by hashed access code only
CREATE TABLE annotators (
    id                SERIAL PRIMARY KEY,
    code_hash         TEXT NOT NULL UNIQUE,
    label             TEXT,                          -- e.g. "Prüfer A" (optional)
    is_admin          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consent_given_at  TIMESTAMPTZ
);

-- Obligations: HGB disclosure requirements (R02–R24, ...)
CREATE TABLE obligations (
    id                     VARCHAR(20) PRIMARY KEY,  -- "R02", "R03", ...
    legal_basis            TEXT,
    title_de               TEXT NOT NULL,
    category               TEXT,
    verification_criterion TEXT,
    applicability_type     TEXT,
    applicability_trigger  TEXT
);

-- Companies: one row per Jahresabschluss file
CREATE TABLE companies (
    id        VARCHAR(50) PRIMARY KEY,   -- "Amazon_2024", "BoschMS_2024", ...
    name      TEXT NOT NULL,
    pdf_path  TEXT                       -- absolute path to PDF for in-app display
);

-- Annotation items: one unit = company × obligation × shown passage
CREATE TABLE annotation_items (
    id              SERIAL PRIMARY KEY,
    company_id      VARCHAR(50) NOT NULL REFERENCES companies(id),
    obligation_id   VARCHAR(20) NOT NULL REFERENCES obligations(id),
    passage_text    TEXT NOT NULL,
    passage_start   INT,                 -- char offset in source document
    passage_end     INT,
    in_overlap_set  BOOLEAN NOT NULL DEFAULT FALSE,
    stratum         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Passage sentences / table blocks with stable 0-based indices
CREATE TABLE passage_sentences (
    id            SERIAL PRIMARY KEY,
    item_id       INT NOT NULL REFERENCES annotation_items(id) ON DELETE CASCADE,
    idx           INT NOT NULL,           -- stable index within item
    element_type  element_type NOT NULL DEFAULT 'sentence',
    text          TEXT NOT NULL,
    char_start    INT,
    char_end      INT
);

-- One annotation judgment per annotator per item
CREATE TABLE annotations (
    id               SERIAL PRIMARY KEY,
    item_id          INT NOT NULL REFERENCES annotation_items(id),
    annotator_id     INT NOT NULL REFERENCES annotators(id),
    is_relevant      BOOLEAN,
    length_judgment  length_judg_type,
    is_applicable    applicable_type,
    is_fulfilled     fulfilled_type,
    justification_ok BOOLEAN,            -- kept nullable, NEVER rendered in UI
    comment          TEXT,
    missing_info     TEXT,               -- free text: what felt missing (length_judgment = 'too_short')
    submitted_at     TIMESTAMPTZ,
    reviewed_at      TIMESTAMPTZ,         -- set once revisited via /review; clears it from the re-review queue
    UNIQUE (item_id, annotator_id),
    -- is_fulfilled must be set when applicable=yes and annotation is submitted
    CONSTRAINT fulfilled_requires_applicable CHECK (
        is_applicable IS DISTINCT FROM 'yes'::applicable_type
        OR is_fulfilled IS NOT NULL
        OR submitted_at IS NULL
    )
);

-- Sentence/table elements marked as irrelevant (when length_judgment = 'too_long')
CREATE TABLE irrelevant_elements (
    id             SERIAL PRIMARY KEY,
    annotation_id  INT NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
    sentence_idx   INT NOT NULL,
    UNIQUE (annotation_id, sentence_idx)
);

-- Alternative passages selected from LLM suggestions (when length_judgment = 'too_short')
CREATE TABLE suggested_passages (
    id             SERIAL PRIMARY KEY,
    annotation_id  INT NOT NULL REFERENCES annotations(id) ON DELETE CASCADE,
    passage_text   TEXT NOT NULL,
    source_ref     TEXT,                 -- optional locator from the LLM (heading/page)
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Assignment log: every time an item is served to an annotator
CREATE TABLE assignment_log (
    id            SERIAL PRIMARY KEY,
    item_id       INT NOT NULL REFERENCES annotation_items(id),
    annotator_id  INT NOT NULL REFERENCES annotators(id),
    assigned_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX idx_items_company    ON annotation_items(company_id);
CREATE INDEX idx_items_obligation ON annotation_items(obligation_id);
CREATE INDEX idx_items_overlap    ON annotation_items(in_overlap_set);
CREATE INDEX idx_sentences_item   ON passage_sentences(item_id);
CREATE INDEX idx_annot_item       ON annotations(item_id);
CREATE INDEX idx_annot_annotator  ON annotations(annotator_id);
CREATE INDEX idx_suggested_annotation ON suggested_passages(annotation_id);
CREATE INDEX idx_log_annotator    ON assignment_log(annotator_id);
CREATE INDEX idx_log_item         ON assignment_log(item_id);
