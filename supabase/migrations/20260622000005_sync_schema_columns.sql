ALTER TABLE species
    DROP COLUMN IF EXISTS distribution,
    DROP COLUMN IF EXISTS uses,
    DROP COLUMN IF EXISTS conservation,
    DROP COLUMN IF EXISTS ethnobotany,
    ADD COLUMN economic_importance JSONB NOT NULL DEFAULT '{}';
