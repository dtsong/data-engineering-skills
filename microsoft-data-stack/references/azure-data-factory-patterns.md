## Contents

- [Metadata-Driven Ingestion](#metadata-driven-ingestion)
- [Linked Service Patterns](#linked-service-patterns)
- [Integration Runtime Selection](#integration-runtime-selection)
- [Trigger Patterns](#trigger-patterns)
- [Error Handling and Monitoring](#error-handling-and-monitoring)

---

# Azure Data Factory Patterns

> Pipeline patterns, linked services, and integration runtimes. Part of the [Microsoft Data Stack Skill](../SKILL.md).

---

## Metadata-Driven Ingestion

Build one pipeline that ingests N tables by reading from a control table.

```sql
-- Control table in SQL Server / Synapse
CREATE TABLE etl.pipeline_config (
    source_schema    NVARCHAR(128),
    source_table     NVARCHAR(128),
    watermark_column NVARCHAR(128) NULL,
    destination_path NVARCHAR(512),
    load_type        NVARCHAR(20) DEFAULT 'incremental', -- 'full' or 'incremental'
    is_active        BIT DEFAULT 1
);
```

**Pipeline structure:**
1. **Lookup** activity reads active rows from `etl.pipeline_config`
2. **ForEach** iterates over results (batch size 20, sequential = false for parallelism)
3. **If Condition** branches on `load_type`
4. **Copy Activity** uses parameterized source query with watermark filter
5. **Stored Procedure** updates watermark after successful copy

```json
{
  "source": {
    "type": "AzureSqlSource",
    "sqlReaderQuery": "SELECT * FROM @{item().source_schema}.@{item().source_table} WHERE @{item().watermark_column} > '@{activity('GetWatermark').output.firstRow.last_watermark}'"
  },
  "sink": {
    "type": "ParquetSink",
    "storeSettings": {
      "type": "AzureBlobFSWriteSettings"
    },
    "formatSettings": {
      "type": "ParquetWriteSettings"
    }
  }
}
```

**Benefits:** Add new tables by inserting rows -- no pipeline changes. Consistent error handling. Centralized monitoring.

---

## Linked Service Patterns

| Source Type | Linked Service | Auth Method | IR |
|------------|---------------|-------------|-----|
| Azure SQL Database | AzureSqlDatabase | Managed Identity | Azure IR |
| On-prem SQL Server | SqlServer | Windows Auth / SQL Auth | Self-Hosted IR |
| ADLS Gen2 | AzureBlobFS | Managed Identity | Azure IR |
| Azure Key Vault | AzureKeyVault | Managed Identity | Azure IR |
| REST API | RestService | Service Principal / API Key | Azure IR |
| Salesforce | Salesforce | OAuth | Azure IR |

**Key Vault pattern:** Store connection strings and API keys in Key Vault. Reference in linked services via `AzureKeyVaultSecret` type. ADF Managed Identity needs `Key Vault Secrets User` role.

---

## Integration Runtime Selection

| Scenario | IR Type | Notes |
|----------|---------|-------|
| Cloud-to-cloud (Azure SQL to ADLS) | Azure IR | Auto-resolve region, no setup |
| On-prem to cloud | Self-Hosted IR | Install on VM with network access to source |
| SSIS package execution | Azure-SSIS IR | Runs SSISDB packages; use as migration bridge only |
| Cross-region copy | Azure IR (specific region) | Pin IR region to reduce egress |

**Self-Hosted IR sizing:** 4+ cores, 16GB+ RAM. Enable HA with 2+ nodes. Register via Key rather than manual UI setup for automation.

---

## Trigger Patterns

| Trigger Type | Use Case | Example |
|-------------|----------|---------|
| Schedule | Regular batch loads | Daily at 06:00 UTC |
| Tumbling window | Ordered, catchup-aware batches | Hourly with 2-hour retry window |
| Event (blob) | File arrival in ADLS | New Parquet lands in `/raw/orders/` |
| Custom event | Event Grid integration | External system publishes event |

**Tumbling window** is preferred for incremental loads -- handles backfill, retries, and dependency chaining natively.

---

## Error Handling and Monitoring

**Activity-level:** Set retry count (3), retry interval (30s), and timeout per activity. Use `@activity('CopyData').output.errors` for conditional paths.

**Pipeline-level:** Add Web activity on failure path to post to Slack/Teams webhook. Log failures to `etl.pipeline_log` table for tracking.

**Azure Monitor:** Enable diagnostic settings on ADF. Route to Log Analytics for KQL queries. Alert on pipeline failure rate > threshold.

```kql
ADFPipelineRun
| where Status == "Failed"
| where TimeGenerated > ago(1h)
| summarize FailureCount = count() by PipelineName
| where FailureCount > 2
```
