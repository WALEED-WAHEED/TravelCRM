-- Creates the scoped, non-superuser role the app connects as day to day.
-- Row-Level Security (member/migrations/0009_row_level_security.py and
-- siblings) is inert for a table owner or superuser, so the running app
-- must use this role; migrations keep running as the owner/admin.
--
-- Run it as the admin (the role that runs `migrate` and owns the tables),
-- connected to the app database, passing the password as a psql variable:
--
--   psql -U postgres -d travelcrm -v app_password='...' -f scripts/init-scoped-role.sql
--
-- Docker runs it automatically on a fresh data volume through
-- scripts/init-scoped-role.sh. Safe to re-run: it only creates what is
-- missing, resets the password, and re-applies the grants.
\set ON_ERROR_STOP on

SELECT format('CREATE ROLE travelcrm_app WITH LOGIN PASSWORD %L', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'travelcrm_app') \gexec

SELECT format('ALTER ROLE travelcrm_app WITH LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD %L', :'app_password') \gexec

GRANT USAGE ON SCHEMA public TO travelcrm_app;

-- Tables that already exist (re-running on a migrated database) ...
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO travelcrm_app;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO travelcrm_app;

-- ... and every table/sequence the admin creates from now on (each later `migrate`).
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO travelcrm_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO travelcrm_app;
