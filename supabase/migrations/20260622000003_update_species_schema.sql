ALTER TABLE species
    DROP COLUMN IF EXISTS scientific_name,
    DROP COLUMN IF EXISTS common_name,
    DROP COLUMN IF EXISTS local_name,
    DROP COLUMN IF EXISTS family,
    DROP COLUMN IF EXISTS description,
    DROP COLUMN IF EXISTS origin,
    DROP COLUMN IF EXISTS uses,
    DROP COLUMN IF EXISTS growing_conditions,
    DROP COLUMN IF EXISTS image_urls,
    ADD COLUMN data JSONB NOT NULL DEFAULT '{}';
