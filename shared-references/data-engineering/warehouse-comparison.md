# Data Warehouse Comparison

> Decision matrix for choosing between Snowflake, BigQuery, Databricks, and DuckDB.

---

## Quick Decision Matrix

| Feature | Snowflake | BigQuery | Databricks | DuckDB |
|---------|-----------|----------|------------|--------|
| **Architecture** | Multi-cluster, separated compute/storage | Serverless, auto-scaling | Lakehouse (Delta Lake + Spark) | In-process, embedded |
| **Pricing** | Per-second compute + storage | Slots (flat-rate) or on-demand/TB | DBUs + storage | Free (local), MotherDuck ($) |
| **Streaming** | Snowpipe, Dynamic Tables | Streaming buffer, Dataflow | Structured Streaming, Delta Live Tables | Append-only |
| **Python** | Snowpark (DataFrame API + UDFs) | BigQuery DataFrames, BQML | Native PySpark, notebooks, MLflow | Native Python API, Arrow |
| **ML/AI** | Cortex AI, Snowpark ML | BQML, Vertex AI | MLflow, Mosaic AI | Use with scikit-learn, PyTorch |
| **Governance** | Object tags, masking, row-level security | BigLake, column-level security, DLP | Unity Catalog (fine-grained ACLs) | File-level permissions only |
| **SQL Dialect** | ANSI SQL + extensions | GoogleSQL | Spark SQL (Hive-compatible) | PostgreSQL-compatible |
| **Best For** | Enterprise data sharing, multi-cloud, governance | GCP-native, serverless, BigQuery ML | ML/AI workloads, lakehouse, Delta | Local analytics, dev/test, embedded |

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

---

## When to Use Each

| Platform | Best For | Avoid When |
|----------|----------|------------|
| **Snowflake** | Enterprise warehousing, multi-cloud, data sharing, clear cost isolation | Small budgets, local-first workflows |
| **BigQuery** | GCP-native, serverless, massive ad-hoc queries, Looker/Vertex AI | Multi-cloud, complex Python UDFs |
| **Databricks** | Lakehouse, ML/AI-first, heavy PySpark, Delta Lake governance | Simple SQL analytics without Spark |
| **DuckDB** | Local dev/test, data exploration, embedded analytics, <100GB | Production OLTP, multi-user concurrency |

---

## SQL Dialect Differences

| Feature | Snowflake | BigQuery | Databricks | DuckDB |
|---------|-----------|----------|------------|--------|
| **Date diff** | `DATEDIFF(day, d1, d2)` | `DATE_DIFF(d1, d2, DAY)` | `DATEDIFF(d1, d2)` | `DATE_DIFF('day', d1, d2)` |
| **Array index** | `array[0]` (0-based) | `array[OFFSET(0)]` | `array[0]` (0-based) | `array[1]` (1-based) |
| **JSON** | `json:field` / `GET_PATH()` | `JSON_EXTRACT()` | `GET_JSON_OBJECT()` | `json->>'field'` |
| **QUALIFY** | Supported | Not supported | Not supported | Supported |
| **MERGE** | `MERGE INTO` | `MERGE INTO` | `MERGE INTO` (Delta) | Not supported |

---

## Migration Paths

| From | To | Reason | Complexity |
|------|----|---------| ----------|
| PostgreSQL | BigQuery | Scale, serverless | Low |
| Redshift | Snowflake | Performance, multi-cloud | Medium |
| Hive | Databricks | Lakehouse, performance | Medium |
| On-prem Oracle | Snowflake/BigQuery | Cloud migration | High |

## Tool Ecosystem

| Tool | Snowflake | BigQuery | Databricks | DuckDB |
|------|-----------|----------|------------|--------|
| **dbt** | Native | Native | Native | Native (1.5+) |
| **Fivetran/Airbyte** | Native | Native | Native | Limited |
| **Looker/Tableau** | Native | Native | Native | JDBC |
| **Airflow/Dagster** | Operator/Resource | Operator/Resource | Operator/Resource | Python |
