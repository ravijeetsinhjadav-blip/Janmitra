-- JanMitra Assist - PostgreSQL 16 Database and Role Initialization Script
-- Creates dedicated local development database and restricted application user
-- (SEC-01, SEC-02: Non-superuser runtime role with scoped schema permissions)

-- 1. Create restricted application user if not exists
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'janmitra_app') THEN
      CREATE ROLE janmitra_app WITH LOGIN PASSWORD 'JanMitra_Secure_Dev_2026!';
   END IF;
END
$do$;

-- 2. Create application database if not exists
SELECT 'CREATE DATABASE janmitra WITH OWNER janmitra_app ENCODING ''UTF8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'janmitra')\gexec

-- 3. Grant schema permissions on public
\c janmitra

GRANT ALL ON SCHEMA public TO janmitra_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO janmitra_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO janmitra_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO janmitra_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO janmitra_app;

-- 4. Verify version and configuration
SELECT version();
