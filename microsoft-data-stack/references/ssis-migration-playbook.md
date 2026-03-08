## Contents

- [Migration Strategy Overview](#migration-strategy-overview)
- [Component Mapping](#component-mapping)
- [Phase 1: Inventory and Classify](#phase-1-inventory-and-classify)
- [Phase 2: Quick Wins](#phase-2-quick-wins)
- [Phase 3: Complex Migrations](#phase-3-complex-migrations)
- [Phase 4: Decommission SSIS](#phase-4-decommission-ssis)
- [Common Pitfalls](#common-pitfalls)

---

# SSIS Migration Playbook

> Migrating from SSIS to modern ETL tools (ADF, dbt, dlt). Part of the [Microsoft Data Stack Skill](../SKILL.md).

---

## Migration Strategy Overview

**Principle:** Do not lift-and-shift SSIS to Azure-SSIS IR as a permanent solution. Use Azure-SSIS IR only as a temporary bridge while migrating to native ADF + dbt + dlt.

**Target architecture:**
- **Extract/Load:** ADF Copy Activity (structured sources) or dlt (APIs, files, semi-structured)
- **Transform:** dbt models (SQL-first) or ADF Data Flows (low-code, for non-SQL teams)
- **Orchestrate:** ADF triggers and pipeline dependencies
- **Custom logic:** Azure Functions (replacing Script Tasks)

---

## Component Mapping

| SSIS Component | Target Tool | Migration Approach |
|---------------|-------------|-------------------|
| **Data Flow Task** (simple copy) | ADF Copy Activity | Direct mapping; use metadata-driven pattern |
| **Data Flow Task** (transforms) | dbt model | Rewrite as SQL; use staging/marts layers |
| **Execute SQL Task** | dbt model or ADF Stored Proc | Prefer dbt for analytics transforms |
| **Script Task (C#)** | Azure Function | Wrap in HTTP-triggered function; call from ADF |
| **For Loop Container** | ADF ForEach Activity | Read iteration list from Lookup activity |
| **Sequence Container** | ADF Pipeline | Each container becomes a pipeline or activity group |
| **File System Task** | ADF Copy Activity | Use ADLS Gen2 connector with blob triggers |
| **Send Mail Task** | Logic App / ADF Web Activity | Trigger Logic App from ADF on-failure path |
| **Expression / Variable** | ADF Parameter / Expression | `@pipeline().parameters.env`, `@variables('counter')` |
| **SSISDB Catalog** | ADF + Git integration | Source control replaces catalog deployment |
| **Package configurations** | ADF Key Vault linked service | Externalize all config to Key Vault |
| **Event handler (OnError)** | ADF failure dependency path | Add failure activities per pipeline |

---

## Phase 1: Inventory and Classify

1. Query SSISDB to list all packages, execution frequency, and last run status
2. Classify each package into complexity tiers:

| Tier | Criteria | Example | Migration Effort |
|------|---------|---------|-----------------|
| **Simple** | Copy data A to B, no transforms | Flat file to SQL table | 1-2 hours |
| **Moderate** | Copy + SQL transforms, variables, loops | Multi-table ETL with lookups | 1-2 days |
| **Complex** | Script Tasks, custom components, C# logic | API integration with error handling | 3-5 days |
| **Critical** | Undocumented, tightly coupled, business-critical | Legacy finance reconciliation | 1-2 weeks |

3. Prioritize by: business impact (high first), complexity (simple first for quick wins), and dependency chain (leaf packages first)

---

## Phase 2: Quick Wins

Target **Simple** tier packages first to build migration velocity.

**Pattern: Flat file to SQL Server**
- SSIS: File System Task + Data Flow Task with Flat File Source + OLE DB Destination
- ADF: Copy Activity with DelimitedText source (ADLS or blob) + Azure SQL sink
- Improvement: Add blob event trigger for automatic ingestion on file arrival

**Pattern: SQL-to-SQL copy**
- SSIS: Execute SQL Task + Data Flow with OLE DB Source/Destination
- ADF: Copy Activity with SQL source/sink, watermark-based incremental
- Improvement: Metadata-driven pipeline replaces per-table packages

---

## Phase 3: Complex Migrations

**Script Task replacement:**
1. Extract C# logic from Script Task
2. Create Azure Function (HTTP trigger) with equivalent logic
3. Call function from ADF Web Activity, pass parameters as JSON body
4. Handle function response in ADF expression for conditional branching

**Custom Data Flow Component replacement:**
1. Identify the transformation logic (often: lookup, fuzzy matching, custom parsing)
2. Rewrite as dbt macro or Python dbt model if SQL is insufficient
3. For truly complex logic (ML scoring, fuzzy matching): use Azure Function or Databricks notebook called from ADF

**SSISDB catalog migration:**
1. Export all package DTSX files from SSISDB
2. Document connection managers, variables, and configurations
3. Create ADF pipelines per logical package group (not 1:1 with packages)
4. Store pipeline definitions in Git (ADF Git integration)
5. Use ADF deployment pipelines (ARM templates or Bicep) for CI/CD

---

## Phase 4: Decommission SSIS

1. Run new ADF/dbt pipelines in parallel with SSIS for 2-4 weeks
2. Compare output data between old and new (row counts, checksums, spot checks)
3. Redirect downstream consumers to new outputs
4. Disable SSIS jobs in SQL Agent
5. Retain SSISDB backup for 90 days (regulatory reference)
6. Decommission SSIS server or Azure-SSIS IR

---

## Common Pitfalls

| Pitfall | Mitigation |
|---------|-----------|
| Lift-and-shift to Azure-SSIS IR as "done" | Treat Azure-SSIS IR as bridge only; set decommission date |
| 1:1 package-to-pipeline mapping | Consolidate: metadata-driven pipelines replace many packages |
| Ignoring SSIS expressions complexity | Map every expression to ADF equivalent; some need Azure Functions |
| Skipping parallel run validation | Always run old and new in parallel; compare outputs systematically |
| Leaving SQL Agent jobs running | Disable SSIS jobs immediately after validation; dangling jobs cause confusion |
| Not involving business users | Business SMEs validate output correctness; technical tests are insufficient |
