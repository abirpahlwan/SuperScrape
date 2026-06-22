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
