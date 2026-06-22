CREATE TABLE species (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url      TEXT NOT NULL UNIQUE,
    raw_markdown    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    image_urls          JSONB NOT NULL DEFAULT '[]',
    taxonomy            JSONB NOT NULL DEFAULT '{}',
    names               JSONB NOT NULL DEFAULT '{}',
    description         JSONB NOT NULL DEFAULT '{}',
    morphology          JSONB NOT NULL DEFAULT '{}',
    ecology             JSONB NOT NULL DEFAULT '{}',
    phenology           JSONB NOT NULL DEFAULT '{}',
    reproduction        JSONB NOT NULL DEFAULT '{}',
    economic_importance JSONB NOT NULL DEFAULT '{}',
    specimen_data       JSONB NOT NULL DEFAULT '{}',
    media_summary       JSONB NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_species_source_url ON species (source_url);

GRANT ALL ON TABLE species TO anon, service_role;

ALTER TABLE species ENABLE ROW LEVEL SECURITY;

CREATE POLICY service_role_all ON species
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY anon_select ON species
    FOR SELECT
    TO anon
    USING (true);
