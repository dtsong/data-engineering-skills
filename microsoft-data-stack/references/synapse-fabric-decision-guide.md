## Contents

- [Decision Matrix](#decision-matrix)
- [When to Use Synapse Analytics](#when-to-use-synapse-analytics)
- [When to Use Microsoft Fabric](#when-to-use-microsoft-fabric)
- [When to Stay on SQL Server](#when-to-stay-on-sql-server)
- [Migration Paths](#migration-paths)
- [Cost Comparison](#cost-comparison)

---

# Synapse vs Fabric Decision Guide

> Choosing the right Microsoft analytics platform. Part of the [Microsoft Data Stack Skill](../SKILL.md).

---

## Decision Matrix

| Factor | SQL Server | Synapse Dedicated | Synapse Serverless | Microsoft Fabric |
|--------|-----------|-------------------|-------------------|------------------|
| **Data volume** | <1TB | 1TB-PB+ | Ad-hoc on ADLS | Any (OneLake) |
| **Concurrency** | High OLTP, moderate analytics | Moderate (workload mgmt) | Low (per-query) | Moderate (capacity-based) |
| **Pricing** | License + infra | Per-DWU (always-on or paused) | Per-TB scanned | Per-CU capacity |
| **Latency** | Sub-second | Seconds | Seconds-minutes | Seconds |
| **dbt adapter** | `dbt-sqlserver` | `dbt-synapse` | Not supported | `dbt-fabric` |
| **Governance** | SQL audit, RLS | Synapse RBAC, Purview | Purview | OneLake RBAC, Purview |
| **Ideal user** | DBA / app developer | Data warehouse team | Data analyst / explorer | Full platform team |

---

## When to Use Synapse Analytics

**Choose Synapse Dedicated Pool when:**
- You have a well-defined star schema workload at TB+ scale
- Predictable query patterns justify reserved compute (DWU allocation)
- You need fine-grained workload management (resource classes, workload groups)
- Existing Synapse investment and team expertise

**Choose Synapse Serverless Pool when:**
- Ad-hoc exploration of Parquet/CSV/JSON in ADLS Gen2
- Cost-sensitive -- pay per TB scanned, no provisioned compute
- Creating logical views over data lake files for downstream tools

**Avoid Synapse when:** Sub-100GB workloads (use SQL Server), need real-time OLTP, or greenfield with no existing Synapse investment (evaluate Fabric first).

---

## When to Use Microsoft Fabric

**Choose Fabric when:**
- Greenfield analytics platform with Power BI as primary consumption layer
- Want unified experience: data engineering, data science, real-time analytics, BI in one platform
- OneLake simplifies storage governance (automatic ADLS Gen2 under the hood)
- Organization has Microsoft 365 E5 or Power BI Premium (Fabric capacity included)
- Need Copilot AI-assisted data exploration

**Fabric-specific capabilities:**
- **Lakehouse:** Managed Delta Lake tables with T-SQL and Spark access
- **Warehouse:** Full T-SQL warehouse semantics on lakehouse data
- **Data Activator:** Event-driven triggers on data changes (no-code)
- **Real-Time Analytics:** KQL-based ingestion and analysis for streaming data

**Avoid Fabric when:** Multi-cloud requirement (Fabric is Azure-only), need full Spark cluster control, or organization is not in Microsoft ecosystem.

---

## When to Stay on SQL Server

**Stay on SQL Server when:**
- Workload is primarily OLTP with analytical queries under 1TB
- Application tightly coupled to SQL Server features (linked servers, CLR, SSRS)
- Regulatory/compliance requires on-premises data residency
- Team expertise is SQL Server DBA, not cloud data engineering
- Budget does not support cloud migration

**SQL Server analytics features often overlooked:**
- Columnstore indexes (100x compression, analytical query acceleration)
- Temporal tables (built-in SCD Type 2)
- PolyBase (query external Parquet/CSV from SQL Server)
- Always On availability groups (HA without cloud)

---

## Migration Paths

| From | To | Approach | Complexity |
|------|-----|---------|------------|
| SQL Server on-prem | Azure SQL Database | Azure Database Migration Service | Low-Medium |
| SQL Server on-prem | Synapse | ADF + schema redesign (star schema) | Medium-High |
| SQL Server on-prem | Fabric Lakehouse | ADF to ADLS, then Fabric shortcuts | Medium |
| Synapse Dedicated | Fabric Warehouse | Fabric migration assistant | Low-Medium |
| SSIS + SQL Server | ADF + dbt + SQL Server/Synapse | Phased: ADF replaces SSIS, dbt replaces stored procs | High |

---

## Cost Comparison

| Platform | Entry Cost | Scale Cost | Pause Support |
|----------|-----------|-----------|---------------|
| SQL Server (on-prem) | License (~$15K/core) | Hardware scaling | N/A |
| Azure SQL Database | ~$5/month (Basic) | vCore scaling | Serverless auto-pause |
| Synapse Dedicated | ~$1.20/hr (DW100c) | Linear with DWU | Manual pause |
| Synapse Serverless | $5/TB scanned | Per-query | Always serverless |
| Fabric | ~$0.36/hr (F2) | Per-CU capacity | Manual pause |

**Cost optimization tips:**
- Synapse: Pause dedicated pools during non-business hours via ADF pipeline or Logic App
- Fabric: Use F2 capacity for dev/test, scale to F64+ for production
- SQL Server: Use Azure Hybrid Benefit for existing licenses
