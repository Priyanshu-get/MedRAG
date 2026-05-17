-- ============================================================
-- MedRAG PostgreSQL Initialization Script
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- ============================================================
-- Documents metadata table (source chunks + FTS)
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id              BIGSERIAL PRIMARY KEY,
    chunk_id        VARCHAR(512)  UNIQUE NOT NULL,
    pmid            VARCHAR(50),
    pmc_id          VARCHAR(50),
    doi             VARCHAR(512),
    title           TEXT          NOT NULL DEFAULT '',
    authors         TEXT[]        DEFAULT '{}',
    journal         VARCHAR(1000) DEFAULT '',
    pub_date        VARCHAR(50)   DEFAULT '',
    abstract        TEXT          DEFAULT '',
    chunk_text      TEXT          NOT NULL DEFAULT '',
    source_type     VARCHAR(50)   DEFAULT 'pubmed',  -- pubmed | pmc | semantic_scholar | clinical_trials
    url             VARCHAR(2000) DEFAULT '',
    indexed_at      TIMESTAMPTZ   DEFAULT NOW(),

    -- Generated FTS column (PostgreSQL 12+)
    search_vector   TSVECTOR GENERATED ALWAYS AS (
        to_tsvector(
            'english',
            coalesce(title, '')       || ' ' ||
            coalesce(chunk_text, '')  || ' ' ||
            coalesce(abstract, '')    || ' ' ||
            coalesce(journal, '')
        )
    ) STORED
);

-- ============================================================
-- Indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_docs_chunk_id      ON documents (chunk_id);
CREATE INDEX IF NOT EXISTS idx_docs_pmid          ON documents (pmid);
CREATE INDEX IF NOT EXISTS idx_docs_doi           ON documents (doi);
CREATE INDEX IF NOT EXISTS idx_docs_source_type   ON documents (source_type);
CREATE INDEX IF NOT EXISTS idx_docs_indexed_at    ON documents (indexed_at DESC);
CREATE INDEX IF NOT EXISTS idx_docs_search_vector ON documents USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_docs_title_trgm    ON documents USING GIN (title gin_trgm_ops);

-- ============================================================
-- Query log table (anonymized — no PII stored)
-- ============================================================
CREATE TABLE IF NOT EXISTS query_logs (
    id              BIGSERIAL PRIMARY KEY,
    query_hash      VARCHAR(64)   NOT NULL,  -- SHA-256 of query (anonymized)
    has_answer      BOOLEAN       DEFAULT FALSE,
    confidence      FLOAT         DEFAULT 0.0,
    source_count    INT           DEFAULT 0,
    response_ms     INT           DEFAULT 0,
    created_at      TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_hash       ON query_logs (query_hash);
