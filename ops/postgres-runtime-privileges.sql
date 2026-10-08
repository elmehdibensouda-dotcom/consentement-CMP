\set ON_ERROR_STOP on

-- Run as the database owner/DBA after Aman migrations have been applied.
-- Supply psql variables `database_name` and `api_role`; psql quotes them as
-- identifiers below. Re-run after migrations that add application tables,
-- reviewing the table-specific permissions for each new table.

GRANT CONNECT ON DATABASE :"database_name" TO :"api_role";
GRANT USAGE ON SCHEMA public TO :"api_role";

GRANT SELECT ON TABLE
    public.schema_migrations,
    public.users,
    public.organizations,
    public.memberships,
    public.invitations,
    public.ownership_transfers,
    public.properties,
    public.policies,
    public.sessions,
    public.audit_events,
    public.consent_events,
    public.scan_reports,
    public.rate_limit_buckets
TO :"api_role";

GRANT INSERT ON TABLE
    public.users,
    public.organizations,
    public.memberships,
    public.invitations,
    public.ownership_transfers,
    public.properties,
    public.policies,
    public.sessions,
    public.audit_events,
    public.consent_events,
    public.scan_reports,
    public.rate_limit_buckets
TO :"api_role";

GRANT UPDATE ON TABLE
    public.memberships,
    public.invitations,
    public.ownership_transfers,
    public.properties,
    public.policies,
    public.rate_limit_buckets
TO :"api_role";

GRANT DELETE ON TABLE
    public.memberships,
    public.invitations,
    public.sessions,
    public.consent_events,
    public.scan_reports,
    public.rate_limit_buckets
TO :"api_role";
