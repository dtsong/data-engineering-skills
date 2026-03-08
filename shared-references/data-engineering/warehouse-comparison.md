# Data Warehouse Comparison

> Decision matrix for choosing between Snowflake, BigQuery, Databricks, and DuckDB.

---

## Quick Decision Matrix

| Feature | Snowflake | BigQuery | Databricks | DuckDB | Azure Synapse | SQL Server |
|---------|-----------|----------|------------|--------|---------------|------------|
| **Architecture** | Multi-cluster, separated compute/storage | Serverless, auto-scaling | Lakehouse (Delta Lake + Spark) | In-process, embedded | Dedicated/serverless SQL pools + Spark | Traditional RDBMS, columnstore indexes |
| **Pricing** | Per-second compute + storage | Slots (flat-rate) or on-demand/TB | DBUs + storage | Free (local), MotherDuck ($) | Per-DWU (dedicated) or per-TB (serverless) | License + infra or Azure SQL vCore |
| **Streaming** | Snowpipe, Dynamic Tables | Streaming buffer, Dataflow | Structured Streaming, Delta Live Tables | Append-only | Synapse Link, Spark Streaming | CDC, Change Tracking, Service Broker |
| **Python** | Snowpark (DataFrame API + UDFs) | BigQuery DataFrames, BQML | Native PySpark, notebooks, MLflow | Native Python API, Arrow | PySpark (Synapse Spark pools) | Python via sp_execute_external_script |
| **ML/AI** | Cortex AI, Snowpark ML | BQML, Vertex AI | MLflow, Mosaic AI | Use with scikit-learn, PyTorch | Synapse ML, Spark MLlib | SQL Server ML Services (R/Python) |
| **Governance** | Object tags, masking, row-level security | BigLake, column-level security, DLP | Unity Catalog (fine-grained ACLs) | File-level permissions only | Synapse RBAC, Purview, column masking | RLS, dynamic data masking, auditing |
| **SQL Dialect** | ANSI SQL + extensions | GoogleSQL | Spark SQL (Hive-compatible) | PostgreSQL-compatible | T-SQL (dedicated), ANSI SQL (serverless) | T-SQL |
| **Best For** | Enterprise data sharing, multi-cloud, governance | GCP-native, serverless, BigQuery ML | ML/AI workloads, lakehouse, Delta | Local analytics, dev/test, embedded | Microsoft-shop warehouse, ADLS integration | OLTP + light analytics, on-prem, <1TB |

---

## Platform Strengths

### Snowflake

- **Multi-cluster warehouse**: Isolate workloads (ETL vs BI vs data science), auto-scaling, no contention
- **Data sharing**: Share live data across accounts without copying (Snowflake Marketplace)
- **Dynamic Tables**: Auto-refreshing materialized views with declarative lag targets
- **Snowpark**: Python DataFrame API with compute pushdown, Python UDFs
- **Cortex AI**: Built-in LLM functions (sentiment, summarization, embeddings) in SQL
- **Governance**: Object tags, dynamic data masking, row access policies

### BigQuery

- **Serverless**: No warehouses to manage, instant scaling, pay per query or flat-rate slots
- **BQML**: Train ML models (logistic regression, boosted trees, ARIMA, AutoML) in SQL
- **BigLake**: Query data in GCS with BQ security and governance, no duplication
- **Dataform**: Google-native dbt alternative with integrated DAG visualization
- **Streaming buffer**: Sub-second ingestion latency, immediately queryable
- **Materialized views**: Auto-refresh with transparent query rewrites

### Databricks

- **Unity Catalog**: Unified governance for data, ML models, notebooks across clouds with automatic lineage
- **Delta Lake**: ACID transactions, time travel, schema enforcement on data lake files
- **Spark-native**: Best-in-class for PB-scale processing (Python/Scala/SQL)
- **MLflow**: Experiment tracking, model registry, deployment
- **Photon engine**: Vectorized C++ query engine, 2-3x faster SQL queries
- **Notebooks**: Interactive collaboration with integrated clusters and jobs

### DuckDB

- **In-process**: No server, runs in Python/R/Node.js/CLI, sub-second startup
- **Zero config**: `pip install duckdb` and start querying CSV/Parquet/JSON directly
- **Laptop-scale analytics**: Vectorized columnar execution, faster than Pandas for large datasets
- **Parquet/CSV native**: Federated queries across file formats, Hive-style partitions
- **MotherDuck**: Cloud DuckDB for collaboration and hybrid local+cloud queries

### Azure Synapse Analytics

- **Dedicated SQL pools**: Massively parallel processing (MPP) with T-SQL, predictable performance via DWU allocation
- **Serverless SQL pools**: Pay-per-query over ADLS Gen2 Parquet/CSV/JSON, no provisioning
- **Spark pools**: Managed Apache Spark for data engineering and ML workloads
- **Synapse Link**: Near-real-time replication from Cosmos DB, SQL Server, Dataverse without ETL
- **Purview integration**: Automated data cataloging, lineage, and classification

### SQL Server

- **OLTP + analytics**: Columnstore indexes accelerate analytical queries on OLTP databases (100x compression)
- **Temporal tables**: System-versioned tables for automatic SCD Type 2 and point-in-time queries
- **CDC / Change Tracking**: Built-in change capture for incremental data engineering pipelines
- **PolyBase**: Query external Parquet/CSV/Delta from T-SQL without data movement
- **Mature ecosystem**: SSMS, Azure Data Studio, extensive DBA tooling and community

---

## When to Use Each

| Platform | Best For | Avoid When |
|----------|----------|------------|
| **Snowflake** | Enterprise warehousing, multi-cloud, data sharing, clear cost isolation | Small budgets, local-first workflows |
| **BigQuery** | GCP-native, serverless, massive ad-hoc queries, Looker/Vertex AI | Multi-cloud, complex Python UDFs |
| **Databricks** | Lakehouse, ML/AI-first, heavy PySpark, Delta Lake governance | Simple SQL analytics without Spark |
| **DuckDB** | Local dev/test, data exploration, embedded analytics, <100GB | Production OLTP, multi-user concurrency |
| **Azure Synapse** | Microsoft-shop warehouse, ADLS Gen2 integration, mixed SQL/Spark workloads | Small datasets (<100GB), non-Azure environments |
| **SQL Server** | OLTP with analytics, on-prem data residency, existing SQL Server shops, <1TB | PB-scale analytics, multi-cloud, serverless-first |

---

## SQL Dialect Differences

| Feature | Snowflake | BigQuery | Databricks | DuckDB | Synapse/SQL Server |
|---------|-----------|----------|------------|--------|-------------------|
| **Date diff** | `DATEDIFF(day, d1, d2)` | `DATE_DIFF(d1, d2, DAY)` | `DATEDIFF(d1, d2)` | `DATE_DIFF('day', d1, d2)` | `DATEDIFF(day, d1, d2)` |
| **Array index** | `array[0]` (0-based) | `array[OFFSET(0)]` | `array[0]` (0-based) | `array[1]` (1-based) | `JSON_VALUE(arr, '$[0]')` |
| **JSON** | `json:field` / `GET_PATH()` | `JSON_EXTRACT()` | `GET_JSON_OBJECT()` | `json->>'field'` | `JSON_VALUE()` / `OPENJSON()` |
| **QUALIFY** | Supported | Not supported | Not supported | Supported | Not supported (use subquery) |
| **MERGE** | `MERGE INTO` | `MERGE INTO` | `MERGE INTO` (Delta) | Not supported | `MERGE INTO` (native) |

---

## Migration Paths

| From | To | Reason | Complexity |
|------|----|---------| ----------|
| PostgreSQL | BigQuery | Scale, serverless | Low |
| Redshift | Snowflake | Performance, multi-cloud | Medium |
| Hive | Databricks | Lakehouse, performance | Medium |
| On-prem Oracle | Snowflake/BigQuery | Cloud migration | High |
| SQL Server on-prem | Azure Synapse | Scale, managed service, ADLS integration | Medium-High |
| SQL Server on-prem | Azure SQL Database | Cloud lift, minimal rearchitecture | Low-Medium |
| SSIS + SQL Server | ADF + dbt + Synapse/Fabric | Modern ETL, version control, lakehouse | High |

## Tool Ecosystem

| Tool | Snowflake | BigQuery | Databricks | DuckDB | Synapse | SQL Server |
|------|-----------|----------|------------|--------|--------|------------|
| **dbt** | Native | Native | Native | Native (1.5+) | `dbt-synapse` | `dbt-sqlserver` |
| **Fivetran/Airbyte** | Native | Native | Native | Limited | Native | Native |
| **Looker/Tableau** | Native | Native | Native | JDBC | Native | Native |
| **Airflow/Dagster** | Operator/Resource | Operator/Resource | Operator/Resource | Python | Operator/Resource | Operator/Resource |
