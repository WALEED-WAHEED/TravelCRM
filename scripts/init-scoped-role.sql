-- Runs automatically on first boot of a fresh Postgres data volume, via
-- Postgres's own /docker-entrypoint-initdb.d/ convention (docker-compose
-- mounts this file there — see docker-compose.staging.yml). Creates the
-- scoped, non-superuser role the app actually connects as. Row-Level
-- Security (member/migrations/0009_row_level_security.py and siblings)
-- is inert for a table owner or superuser, so this role — not the
-- POSTGRES_USER superuser docker-compose creates — is what SCOPED_DB_USER
-- / the runtime DB_USER should point at.
--
-- The password here is a placeholder; ALTER ROLE it to match
-- SCOPED_DB_PASSWORD in your real .env before pointing traffic at this
-- environment. Table/sequence grants are applied after migrations run
-- (see docker-entrypoint.sh), not here — this file only runs once, before
-- the app's own tables exist yet.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'travelcrm_app') THEN
        CREATE ROLE travelcrm_app WITH LOGIN PASSWORD 'change-me-see-env-staging-example';
    END IF;
END
$$;
