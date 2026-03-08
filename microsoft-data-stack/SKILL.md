---
name: microsoft-data-stack
description: "Use this skill when working with Microsoft data technologies. Covers Azure Data Factory orchestration, Azure Synapse Analytics, Microsoft Fabric lakehouse, SQL Server data engineering (CDC, temporal tables, partitioning), ADLS Gen2 storage patterns, SSIS migration guidance, and dbt-sqlserver adapter configuration. Common phrases: \"ADF pipeline\", \"Synapse\", \"Fabric lakehouse\", \"SQL Server CDC\", \"SSIS migration\", \"ADLS Gen2\", \"dbt-sqlserver\". Do NOT use for general pipeline orchestration (use data-pipelines), dbt modeling patterns (use dbt-transforms), or Kafka streaming (use event-streaming)."
model:
  preferred: sonnet
  acceptable: [sonnet, opus]
  minimum: sonnet
  allow_downgrade: false
  reasoning_demand: medium
version: 1.0.0
---

# Microsoft Data Stack Skill for Claude

Expert guidance for data engineering on Microsoft and Azure platforms. Covers ADF, Synapse, Fabric, SQL Server, ADLS Gen2, SSIS migration, and dbt-sqlserver.

## When to Use This Skill

**Activate when:**
- Designing Azure Data Factory pipelines (linked services, integration runtimes, triggers)
- Choosing between Synapse Analytics, Microsoft Fabric, and SQL Server
- Implementing SQL Server CDC, temporal tables, or partition strategies
- Configuring ADLS Gen2 hierarchical namespace, ACLs, or storage integration
- Migrating SSIS packages to modern ETL (ADF, dbt, dlt)
- Setting up dbt-sqlserver or dbt-fabric adapters

**Don't use for:** General orchestration patterns (use `data-pipelines`), dbt modeling methodology (use `dbt-transforms`), Kafka/Flink streaming (use `event-streaming`), Azure DevOps CI/CD.

## Scope Constraints

- Generate ADF pipeline JSON, SQL Server DDL, and configuration guidance only.
- Credential management: reference Azure Key Vault and Managed Identity. Never hardcode secrets. See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md).
- Limit scope to data engineering concerns. Hand off BI/reporting to Power BI documentation and general orchestration to data-pipelines.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Sonnet, Opus | Sonnet |

## Core Principles

1. **Managed Identity over keys** -- Use Azure Managed Identity for service-to-service auth. Key Vault for external secrets only.
2. **Lakehouse by default** -- Store raw data in ADLS Gen2 (Parquet/Delta), transform in Synapse or Fabric, serve from SQL pools or lakehouses.
3. **Metadata-driven pipelines** -- ADF pipelines should be parameterized and table-driven, not one pipeline per table.
4. **Incremental over full load** -- Use watermark columns, CDC, or Change Tracking for incremental extraction.
5. **Right-size the engine** -- SQL Server for OLTP + light analytics, Synapse for warehouse-scale, Fabric for unified lakehouse.

## Platform Decision Matrix

| Factor | SQL Server | Synapse Analytics | Microsoft Fabric |
|--------|-----------|-------------------|------------------|
| **Best for** | OLTP, <1TB analytics, existing SQL Server shops | Dedicated warehouse, complex queries, PB-scale | Unified lakehouse, OneLake, Power BI integration |
| **Compute model** | Always-on instance | Dedicated or serverless SQL pools | Capacity units (CU), pause/resume |
| **Storage** | Local/SAN | ADLS Gen2 (external tables) | OneLake (auto-managed ADLS) |
| **dbt adapter** | `dbt-sqlserver` | `dbt-synapse` | `dbt-fabric` |
| **Cost profile** | License + infra | Per-DWU or per-query | Per-CU capacity reservation |
| **Governance** | SQL Server audit, RLS | Synapse RBAC, column masking | Purview integration, OneLake RBAC |

For detailed comparison, see [Synapse vs Fabric Decision Guide](references/synapse-fabric-decision-guide.md).

## ADF Pipeline Patterns

**Metadata-driven ingestion** -- Single parameterized pipeline reads a control table listing source tables, watermark columns, and destinations. ForEach activity iterates and copies incrementally.

**Integration Runtime tiers:**
- Azure IR: cloud-to-cloud (default)
- Self-Hosted IR: on-prem SQL Server, file shares, legacy systems
- Azure-SSIS IR: lift-and-shift SSIS packages (migration stepping stone only)

For pipeline patterns and linked service config, see [ADF Patterns Reference](references/azure-data-factory-patterns.md).

## SQL Server Data Engineering

**CDC (Change Data Capture):** Captures row-level changes to dedicated change tables. Enable per-table with `sys.sp_cdc_enable_table`. Query changes via `cdc.fn_cdc_get_all_changes_<capture_instance>`.

**Temporal Tables:** System-versioned tables with automatic history tracking. Use for SCD Type 2, audit trails, and point-in-time queries (`FOR SYSTEM_TIME AS OF`).

**Partition Strategies:** Partition large fact tables by date using partition functions and schemes. Enables partition switching for fast loads and archive operations.

## SSIS Migration Quick Guide

| SSIS Component | Modern Replacement | Notes |
|---------------|-------------------|-------|
| Data Flow Task | ADF Copy Activity / dbt model | ADF for E/L, dbt for T |
| Script Task (C#) | Azure Function / Python | Wrap custom logic in serverless functions |
| Execute SQL Task | dbt model / ADF Stored Proc | Prefer dbt for transformations |
| For Loop / ForEach | ADF ForEach activity | Metadata-driven pattern |
| SSISDB Catalog | ADF + Git integration | Version control via Azure DevOps/GitHub |
| Package variables | ADF parameters + Key Vault | Externalize configuration |

For full migration playbook, see [SSIS Migration Playbook](references/ssis-migration-playbook.md).

## dbt-sqlserver Setup

```yaml
# profiles.yml
my_project:
  target: dev
  outputs:
    dev:
      type: sqlserver
      driver: "ODBC Driver 18 for SQL Server"
      server: my-server.database.windows.net
      port: 1433
      database: my_database
      schema: dbt_dev
      authentication: ActiveDirectoryServicePrincipal
      tenant_id: "{{ env_var('AZURE_TENANT_ID') }}"
      client_id: "{{ env_var('AZURE_CLIENT_ID') }}"
      client_secret: "{{ env_var('AZURE_CLIENT_SECRET') }}"
```

**Gotchas:** No `QUALIFY` clause -- use subquery with `ROW_NUMBER()`. No `MERGE` in views. `BOOLEAN` type unavailable -- use `BIT`. Collation-sensitive string comparisons by default.

## Security Posture

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full framework.

- **Auth**: Azure Managed Identity (preferred), Service Principal, Azure AD tokens.
- **Secrets**: Azure Key Vault only. ADF linked services reference Key Vault secrets.
- **Network**: Private endpoints for Synapse/SQL Server. VNet-integrated IR for ADF.
- **Data classification**: Purview for automated scanning. SQL Server column-level classification.

## Reference Files

- [Azure Data Factory Patterns](references/azure-data-factory-patterns.md) -- Pipeline patterns, linked services, integration runtimes, triggers
- [Synapse vs Fabric Decision Guide](references/synapse-fabric-decision-guide.md) -- When to use Synapse vs Fabric vs SQL Server
- [SSIS Migration Playbook](references/ssis-migration-playbook.md) -- SSIS to modern ETL migration patterns

## Handoffs

- **Pipeline orchestration patterns** -> [data-pipelines](../data-pipelines/SKILL.md) (Dagster, Airflow, Prefect scheduling and monitoring)
- **dbt modeling methodology** -> [dbt-transforms](../dbt-transforms/SKILL.md) (staging/marts layers, testing, CI/CD)
- **Data governance features** -> [data-governance](../data-governance/SKILL.md) (cataloging, lineage, classification, access control)
