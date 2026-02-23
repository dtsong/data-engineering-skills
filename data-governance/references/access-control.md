# Access Control Patterns

## Table of Contents

- RBAC for Snowflake
- RBAC for Azure SQL / SQL Server
- dbt Grants Config
- Least-Privilege Patterns
- Row-Level Security Patterns
- Access Audit Documentation

---

## RBAC for Snowflake

Standard role hierarchy for analytics warehouses:

```sql
-- Create functional roles
CREATE ROLE IF NOT EXISTS data_reader;
CREATE ROLE IF NOT EXISTS data_analyst;
CREATE ROLE IF NOT EXISTS data_engineer;
CREATE ROLE IF NOT EXISTS data_admin;

-- Build hierarchy: admin > engineer > analyst > reader
GRANT ROLE data_reader TO ROLE data_analyst;
GRANT ROLE data_analyst TO ROLE data_engineer;
GRANT ROLE data_engineer TO ROLE data_admin;

-- Grant database-level access
GRANT USAGE ON DATABASE analytics_db TO ROLE data_reader;
GRANT USAGE ON ALL SCHEMAS IN DATABASE analytics_db TO ROLE data_reader;
GRANT SELECT ON ALL TABLES IN DATABASE analytics_db TO ROLE data_reader;

-- Grant future tables (auto-apply to new objects)
GRANT SELECT ON FUTURE TABLES IN DATABASE analytics_db TO ROLE data_reader;

-- Engineer: read raw + write to staging/mart
GRANT USAGE ON DATABASE raw_db TO ROLE data_engineer;
GRANT SELECT ON ALL TABLES IN DATABASE raw_db TO ROLE data_engineer;
GRANT CREATE TABLE ON SCHEMA analytics_db.staging TO ROLE data_engineer;
GRANT CREATE TABLE ON SCHEMA analytics_db.marts TO ROLE data_engineer;

-- Admin: full control
GRANT ALL PRIVILEGES ON DATABASE analytics_db TO ROLE data_admin;
GRANT ALL PRIVILEGES ON DATABASE raw_db TO ROLE data_admin;
```

Assign roles to users:

```sql
GRANT ROLE data_analyst TO USER jane_doe;
GRANT ROLE data_engineer TO USER john_smith;
```

## RBAC for Azure SQL / SQL Server

```sql
-- Create database roles
CREATE ROLE data_reader;
CREATE ROLE data_analyst;
CREATE ROLE data_engineer;

-- Grant schema-level permissions
GRANT SELECT ON SCHEMA::marts TO data_reader;
GRANT SELECT ON SCHEMA::staging TO data_analyst;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::staging TO data_engineer;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::marts TO data_engineer;

-- Add users to roles
ALTER ROLE data_reader ADD MEMBER [jane.doe@company.com];
ALTER ROLE data_engineer ADD MEMBER [john.smith@company.com];

-- Grant execute on stored procedures
GRANT EXECUTE ON SCHEMA::dbo TO data_engineer;
```

## dbt Grants Config

dbt can manage grants declaratively in `dbt_project.yml`:

```yaml
# dbt_project.yml
models:
  my_project:
    staging:
      +grants:
        select: ['data_engineer', 'data_analyst']
    marts:
      +grants:
        select: ['data_reader', 'data_analyst', 'data_engineer']
```

Per-model grants in schema YAML:

```yaml
models:
  - name: mart_revenue
    config:
      grants:
        select: ['data_analyst', 'finance_team']
    meta:
      classification: confidential
      data_owner: finance
```

Grant management behavior:
- `dbt run` applies grants after model materialization
- Use `+grants` at folder level for consistent defaults
- Override at model level for exceptions (restricted data)

## Least-Privilege Patterns

| Principle | Implementation |
|-----------|---------------|
| Default deny | New roles start with zero permissions |
| Schema-level grants | Grant at schema level, not database level |
| Read-only default | Analysts get SELECT only; no INSERT/UPDATE/DELETE |
| Time-bounded access | Use Snowflake `GRANT ... WITH GRANT OPTION` sparingly |
| Service accounts | Separate role for dbt runner, Fivetran loader, BI tool |

Service account pattern:

```sql
-- dbt service account: read raw, write analytics
CREATE ROLE dbt_runner;
GRANT SELECT ON ALL TABLES IN DATABASE raw_db TO ROLE dbt_runner;
GRANT ALL ON SCHEMA analytics_db.staging TO ROLE dbt_runner;
GRANT ALL ON SCHEMA analytics_db.marts TO ROLE dbt_runner;
CREATE USER dbt_service PASSWORD = '...' DEFAULT_ROLE = dbt_runner;
GRANT ROLE dbt_runner TO USER dbt_service;

-- Fivetran loader: write to raw only
CREATE ROLE fivetran_loader;
GRANT ALL ON SCHEMA raw_db.crm_salesforce TO ROLE fivetran_loader;
```

## Row-Level Security Patterns

Snowflake row access policies:

```sql
-- Create a mapping table: which role sees which regions
CREATE TABLE access_control.region_access (
    role_name STRING,
    region STRING
);

INSERT INTO access_control.region_access VALUES
    ('sales_us', 'US'),
    ('sales_eu', 'EU'),
    ('sales_global', 'US'),
    ('sales_global', 'EU');

-- Create row access policy
CREATE OR REPLACE ROW ACCESS POLICY region_filter AS (region_col STRING)
RETURNS BOOLEAN ->
    EXISTS (
        SELECT 1 FROM access_control.region_access
        WHERE role_name = CURRENT_ROLE()
          AND region = region_col
    )
    OR CURRENT_ROLE() IN ('DATA_ADMIN', 'SYSADMIN');

-- Apply to table
ALTER TABLE mart_orders ADD ROW ACCESS POLICY region_filter ON (region);
```

Azure SQL row-level security:

```sql
-- Create filter predicate function
CREATE FUNCTION dbo.fn_region_filter(@region NVARCHAR(50))
RETURNS TABLE WITH SCHEMABINDING AS
RETURN
    SELECT 1 AS result
    WHERE @region IN (
        SELECT region FROM dbo.user_region_access
        WHERE user_name = USER_NAME()
    )
    OR IS_MEMBER('data_admin') = 1;

-- Create security policy
CREATE SECURITY POLICY RegionFilter
    ADD FILTER PREDICATE dbo.fn_region_filter(region) ON dbo.mart_orders;
```

## Access Audit Documentation

Document all access grants in a version-controlled manifest:

```yaml
# access_manifest.yml
roles:
  - name: data_reader
    description: "Read-only access to mart layer"
    databases: [analytics_db]
    schemas: [marts]
    permissions: [SELECT]
    members: [jane.doe, bob.jones]
    last_reviewed: "2025-01-15"

  - name: data_engineer
    description: "Read raw, read/write analytics"
    databases: [raw_db, analytics_db]
    schemas: [staging, marts, raw_db.*]
    permissions: [SELECT, INSERT, UPDATE, DELETE, CREATE TABLE]
    members: [john.smith, alice.wang]
    last_reviewed: "2025-01-15"

  - name: dbt_runner
    description: "Service account for dbt transformations"
    type: service_account
    databases: [raw_db, analytics_db]
    permissions: [SELECT on raw_db, ALL on analytics_db.staging, ALL on analytics_db.marts]
    last_reviewed: "2025-01-15"
```

Review schedule: quarterly for all roles. Flag roles with no access in 90 days for removal.
