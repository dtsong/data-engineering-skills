# Data Warehouse Comparison

> Decision matrix for choosing between Snowflake, BigQuery, Databricks, and DuckDB.

This reference helps you select the right warehouse for your workload, understand migration paths, and navigate SQL dialect differences.

---

## Quick Decision Matrix

| Feature | Snowflake | BigQuery | Databricks | DuckDB |
|---------|-----------|----------|------------|--------|
| **Architecture** | Multi-cluster, separated compute/storage | Serverless, auto-scaling | Lakehouse (Delta Lake + Spark) | In-process, embedded |
| **Pricing Model** | Per-second compute + storage | Slots (flat-rate) or on-demand queries | DBUs (compute units) + storage | Free (local), MotherDuck ($) |
| **Streaming Support** | Snowpipe, Snowpipe Streaming, Dynamic Tables | Streaming buffer, Dataflow | Structured Streaming, Delta Live Tables | Append-only with triggers |
| **Python Support** | Snowpark (DataFrame API + UDFs) | BigQuery DataFrames (preview), BQML | Native PySpark, notebooks, MLflow | Native Python API, Arrow |
| **ML/AI** | Cortex AI, Snowpark ML, LLMs | BQML, Vertex AI integration | MLflow, Mosaic AI, Unity Catalog lineage | Use with scikit-learn, PyTorch |
| **Governance** | Object tags, masking, row-level security, Horizon | BigLake, column-level security, DLP | Unity Catalog (fine-grained ACLs) | File-level permissions only |
| **Ecosystem** | dbt, Fivetran, Tableau, Hex | Looker, dbt, Dataform, Fivetran | Delta Sharing, MLflow, Spark ecosystem | CLI tools, Jupyter, Metabase |
| **SQL Dialect** | ANSI SQL + extensions | GoogleSQL (formerly Standard SQL) | Spark SQL (Hive-compatible) | PostgreSQL-compatible |
| **Best For** | Enterprises needing data sharing, multi-cloud, governance | Google Cloud native, BigQuery ML, serverless | ML/AI workloads, lakehouse architecture, Delta | Local analytics, dev/test, embedded analytics |
| **Worst For** | Small budgets, local-first workflows | Multi-cloud, complex Python UDFs | Simple SQL analytics without Spark knowledge | Production OLTP, multi-user concurrency |

---

## Snowflake Strengths

### Multi-Cluster Warehouse

**What it is**: Separate compute clusters (virtual warehouses) that auto-suspend and scale independently.

**Why it matters**:
- Isolate workloads (ETL vs BI vs data science)
- Auto-scaling for query concurrency
- No resource contention between teams

**Example use case**:
```sql
-- ETL warehouse (X-Large, auto-suspend after 5 min)
USE WAREHOUSE ETL_WH;
COPY INTO orders FROM @s3_stage;

-- BI warehouse (Medium, auto-suspend after 10 min, auto-scale 1-3 clusters)
USE WAREHOUSE BI_WH;
SELECT * FROM fct_orders WHERE order_date = CURRENT_DATE();

-- Data science workload (Large, dedicated cluster)
USE WAREHOUSE DS_WH;
CALL snowpark_ml_training_procedure();
```

### Data Sharing

**What it is**: Share live data across Snowflake accounts without copying or ETL.

**Why it matters**:
- Vendor data products (monetize data)
- Cross-organization collaboration
- Instant access to shared datasets (no sync lag)

**Example**:
```sql
-- Provider creates share
CREATE SHARE sales_data_share;
GRANT USAGE ON DATABASE sales_db TO SHARE sales_data_share;
GRANT SELECT ON sales_db.public.orders TO SHARE sales_data_share;
ALTER SHARE sales_data_share ADD ACCOUNTS = xyz12345;

-- Consumer accesses share
CREATE DATABASE shared_sales_data FROM SHARE abc67890.sales_data_share;
SELECT * FROM shared_sales_data.public.orders;
```

### Dynamic Tables

**What it is**: Materialized views that auto-refresh based on declarative lag targets.

**Why it matters**:
- Simpler than orchestrating incremental models
- Automatic dependency resolution
- Streaming and batch use cases

**Example**:
```sql
CREATE DYNAMIC TABLE fct_orders_hourly
  TARGET_LAG = '1 hour'
  WAREHOUSE = ETL_WH
AS
  SELECT
    DATE_TRUNC('hour', order_timestamp) AS order_hour,
    SUM(order_total) AS total_revenue,
    COUNT(*) AS order_count
  FROM stg_orders
  GROUP BY 1;
```

### Snowpark

**What it is**: DataFrame API for Python, Scala, Java with pushdown to Snowflake compute.

**Why it matters**:
- Write data engineering in Python (no SQL)
- User-defined functions (UDFs) in Python
- Machine learning pipelines in Snowflake

**Example**:
```python
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col, sum

session = Session.builder.configs(connection_parameters).create()

# DataFrame API
df = session.table("orders") \
    .filter(col("order_date") >= "2026-01-01") \
    .group_by("customer_id") \
    .agg(sum("order_total").alias("total_spent"))

df.write.mode("overwrite").save_as_table("customer_spending")

# Python UDF
from snowflake.snowpark.types import IntegerType

@udf(return_type=IntegerType(), input_types=[IntegerType()])
def double_value(x):
    return x * 2

session.sql("SELECT double_value(revenue) FROM orders").show()
```

### Cortex AI

**What it is**: Built-in LLM functions (summarization, sentiment, translation, embeddings).

**Why it matters**:
- No external API calls
- SQL-native AI functions
- Data stays in Snowflake (governance maintained)

**Example**:
```sql
-- Sentiment analysis
SELECT
  review_id,
  review_text,
  SNOWFLAKE.CORTEX.SENTIMENT(review_text) AS sentiment_score
FROM product_reviews;

-- Text summarization
SELECT
  article_id,
  SNOWFLAKE.CORTEX.SUMMARIZE(article_text) AS summary
FROM news_articles;

-- Embeddings for semantic search
CREATE TABLE article_embeddings AS
SELECT
  article_id,
  SNOWFLAKE.CORTEX.EMBED_TEXT_768('e5-base-v2', article_text) AS embedding
FROM articles;
```

### Governance Features

**Object Tags**:
```sql
CREATE TAG pii_tag ALLOWED_VALUES 'high', 'medium', 'low';
ALTER TABLE customers MODIFY COLUMN email SET TAG pii_tag = 'high';

-- Query by tag
SELECT * FROM SNOWFLAKE.ACCOUNT_USAGE.TAG_REFERENCES
WHERE TAG_NAME = 'PII_TAG' AND TAG_VALUE = 'high';
```

**Dynamic Data Masking**:
```sql
CREATE MASKING POLICY email_mask AS (val STRING) RETURNS STRING ->
  CASE
    WHEN CURRENT_ROLE() IN ('ADMIN', 'COMPLIANCE') THEN val
    ELSE REGEXP_REPLACE(val, '.+@', '****@')
  END;

ALTER TABLE customers MODIFY COLUMN email SET MASKING POLICY email_mask;
```

**Row-Level Security**:
```sql
CREATE ROW ACCESS POLICY region_policy AS (region STRING) RETURNS BOOLEAN ->
  CASE
    WHEN CURRENT_ROLE() = 'GLOBAL_ADMIN' THEN TRUE
    WHEN CURRENT_ROLE() = 'US_ANALYST' AND region = 'US' THEN TRUE
    ELSE FALSE
  END;

ALTER TABLE sales ADD ROW ACCESS POLICY region_policy ON (region);
```

---

## BigQuery Strengths

### Serverless Architecture

**What it is**: No warehouses to manage. Queries auto-scale across Google's infrastructure.

**Why it matters**:
- Zero cluster management
- Instant scaling (1 TB scan in seconds)
- Pay per query (on-demand) or flat-rate slots

**Example**:
```sql
-- No warehouse selection needed, query just runs
SELECT
  customer_id,
  SUM(order_total) AS total_spent
FROM `project.dataset.orders`
WHERE order_date >= '2026-01-01'
GROUP BY customer_id;
```

**Pricing comparison**:
| Model | Cost | Best For |
|-------|------|----------|
| On-demand | $6.25/TB scanned | Unpredictable workloads, small queries |
| Flat-rate (slots) | $2,000/month for 100 slots | Predictable workloads, high query volume |

### Slots Model

**What it is**: Pre-purchased compute capacity (slots = query execution units).

**Why it matters**:
- Cost predictability
- Reservation-based capacity planning
- Auto-scaling within slot limits

**Example**:
```sql
-- Create reservation (via UI or API)
-- 100 slots = ~$2000/month

-- Assign project to reservation
bq mk --reservation --project_id=my-project \
  --location=US --slots=100 my_reservation

-- Queries in this project now use reserved slots
SELECT * FROM large_table; -- Uses reserved capacity
```

### BigLake

**What it is**: Query data in GCS (Parquet, ORC, Avro) with BigQuery security and governance.

**Why it matters**:
- Unified analytics on lake + warehouse
- Fine-grained access control on object storage
- No data duplication

**Example**:
```sql
-- Create BigLake table over GCS
CREATE EXTERNAL TABLE `project.dataset.customer_lake`
WITH CONNECTION `project.region.my_connection`
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://my-bucket/customers/*.parquet']
);

-- Apply column-level security
CREATE POLICY TAXONOMY `projects/my-project/locations/us/taxonomies/12345`
POLICY TAG `PII_HIGH`;

ALTER TABLE `project.dataset.customer_lake`
ALTER COLUMN email SET OPTIONS (policy_tags=('projects/my-project/locations/us/taxonomies/12345/policyTags/67890'));

-- Query with security enforced
SELECT customer_id, email FROM `project.dataset.customer_lake`;
-- Users without PII access see NULL for email
```

### BQML (BigQuery ML)

**What it is**: Train ML models using SQL (no Python required).

**Why it matters**:
- Analysts can build models (logistic regression, boosted trees, ARIMA, AutoML)
- Models stored in BigQuery (governance maintained)
- Predict at scale in SQL

**Example**:
```sql
-- Train a churn prediction model
CREATE OR REPLACE MODEL `project.dataset.churn_model`
OPTIONS(
  model_type='LOGISTIC_REG',
  input_label_cols=['churned']
) AS
SELECT
  total_orders,
  avg_order_value,
  days_since_last_order,
  churned
FROM `project.dataset.customer_features`;

-- Predict churn
SELECT
  customer_id,
  predicted_churned,
  predicted_churned_probs[OFFSET(1)].prob AS churn_probability
FROM ML.PREDICT(MODEL `project.dataset.churn_model`,
  (SELECT * FROM `project.dataset.customers_current`)
);
```

### Dataform

**What it is**: Google-native dbt alternative (SQL-based transformation orchestration).

**Why it matters**:
- Integrated with BigQuery (no external orchestrator)
- Git-based workflow
- DAG visualization in console

**Example** (SQLX file):
```sql
-- definitions/staging/stg_orders.sqlx
config {
  type: "table",
  schema: "staging",
  tags: ["daily"]
}

SELECT
  order_id,
  customer_id,
  order_date,
  order_total
FROM ${ref("raw_orders")}
WHERE order_date >= CURRENT_DATE() - 90
```

### Streaming Buffer

**What it is**: Append data to tables via streaming API with near-real-time availability.

**Why it matters**:
- Sub-second ingestion latency
- No separate streaming infrastructure
- Queryable immediately

**Example**:
```python
from google.cloud import bigquery

client = bigquery.Client()
table_id = "project.dataset.events"

rows_to_insert = [
    {"event_id": "123", "user_id": "456", "event_type": "click", "timestamp": "2026-02-13T10:00:00Z"},
    {"event_id": "124", "user_id": "457", "event_type": "purchase", "timestamp": "2026-02-13T10:01:00Z"},
]

errors = client.insert_rows_json(table_id, rows_to_insert)
if errors:
    print(f"Errors: {errors}")
else:
    print("Rows inserted successfully")

# Query immediately
query = "SELECT * FROM `project.dataset.events` WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE)"
results = client.query(query)
for row in results:
    print(row)
```

### Materialized Views

**What it is**: Pre-computed views that auto-refresh and optimize query rewrites.

**Why it matters**:
- Automatic incremental refresh (no orchestration)
- Query optimizer rewrites queries to use MV (transparent acceleration)

**Example**:
```sql
-- Create materialized view
CREATE MATERIALIZED VIEW `project.dataset.daily_revenue_mv`
AS
SELECT
  DATE(order_timestamp) AS order_date,
  SUM(order_total) AS total_revenue
FROM `project.dataset.orders`
GROUP BY order_date;

-- Query the base table
SELECT order_date, total_revenue
FROM `project.dataset.orders`
GROUP BY order_date;
-- BigQuery automatically uses the MV if applicable
```

---

## Databricks Strengths

### Unity Catalog

**What it is**: Unified governance layer for data, ML models, and notebooks across clouds.

**Why it matters**:
- Fine-grained access control (table, column, row)
- Automatic lineage tracking (data + ML)
- Cross-cloud metadata management

**Example**:
```sql
-- Create catalog hierarchy
CREATE CATALOG production;
CREATE SCHEMA production.sales;
CREATE TABLE production.sales.orders (...);

-- Grant permissions
GRANT SELECT ON TABLE production.sales.orders TO `data-analysts`;
GRANT MODIFY ON SCHEMA production.sales TO `data-engineers`;

-- Row-level security
CREATE FUNCTION production.sales.redact_region(region STRING)
  RETURN CASE
    WHEN IS_ACCOUNT_GROUP_MEMBER('global-admins') THEN region
    ELSE 'REDACTED'
  END;

ALTER TABLE production.sales.orders
  SET ROW FILTER production.sales.redact_region(region) ON (region);
```

**Automatic lineage**:
```python
# Lineage tracked automatically
df = spark.table("production.sales.orders")
df_aggregated = df.groupBy("customer_id").sum("order_total")
df_aggregated.write.saveAsTable("production.sales.customer_totals")

# View lineage in Unity Catalog UI
# Lineage graph: orders -> customer_totals
```

### Delta Lake

**What it is**: Open-source storage layer with ACID transactions, time travel, schema enforcement.

**Why it matters**:
- Reliable updates/deletes on data lake
- Time travel (query historical versions)
- Schema evolution with enforcement

**Example**:
```python
# Write Delta table
df.write.format("delta").mode("overwrite").save("/mnt/delta/orders")

# ACID updates
from delta.tables import DeltaTable

delta_table = DeltaTable.forPath(spark, "/mnt/delta/orders")
delta_table.update(
  condition = "order_status = 'pending'",
  set = { "order_status": "'shipped'" }
)

# Time travel
df_yesterday = spark.read.format("delta").option("versionAsOf", 5).load("/mnt/delta/orders")
df_jan1 = spark.read.format("delta").option("timestampAsOf", "2026-01-01").load("/mnt/delta/orders")

# Schema enforcement
df_bad_schema.write.format("delta").mode("append").save("/mnt/delta/orders")
# Raises error if schema doesn't match
```

### Spark-Native

**What it is**: Databricks is built on Apache Spark (massively parallel processing).

**Why it matters**:
- Best-in-class for large-scale data processing (PB-scale)
- Rich ecosystem (Spark Streaming, MLlib, GraphX)
- Python/Scala/SQL flexibility

**Example**:
```python
# Process 10TB of data in parallel
df = spark.read.parquet("s3://bucket/large-dataset/")

# Complex transformation
from pyspark.sql import functions as F

result = df \
    .filter(F.col("event_date") >= "2026-01-01") \
    .groupBy("user_id") \
    .agg(
        F.count("*").alias("event_count"),
        F.countDistinct("session_id").alias("session_count"),
        F.sum("revenue").alias("total_revenue")
    ) \
    .filter(F.col("event_count") > 10)

# Write partitioned
result.write.partitionBy("event_date").mode("overwrite").parquet("s3://output/user-summary/")
```

### MLflow

**What it is**: Open-source MLOps platform (experiment tracking, model registry, deployment).

**Why it matters**:
- Track experiments (parameters, metrics, artifacts)
- Version models in registry
- Deploy models to production

**Example**:
```python
import mlflow
from sklearn.ensemble import RandomForestClassifier

mlflow.set_experiment("churn-prediction")

with mlflow.start_run():
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 10)

    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=10)
    model.fit(X_train, y_train)

    # Log metrics
    accuracy = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", accuracy)

    # Log model
    mlflow.sklearn.log_model(model, "model")

# Register model
mlflow.register_model("runs:/abc123/model", "ChurnModel")

# Load model for inference
model = mlflow.pyfunc.load_model("models:/ChurnModel/production")
predictions = model.predict(df.toPandas())
```

### Notebooks

**What it is**: Collaborative notebooks with Python, Scala, SQL, R support.

**Why it matters**:
- Interactive data exploration
- Real-time collaboration (Google Docs-style)
- Integrated with clusters and jobs

**Example workflow**:
1. Explore data in notebook
2. Refactor into production job
3. Schedule with Databricks Workflows
4. Monitor with Delta Live Tables

### Photon Engine

**What it is**: Vectorized query engine (C++ rewrite of Spark execution).

**Why it matters**:
- 2-3x faster queries on SQL workloads
- Lower cost per query
- Automatic (enable on cluster)

**Example**:
```python
# Enable Photon in cluster config
{
  "cluster_name": "analytics-cluster",
  "spark_version": "13.3.x-photon-scala2.12",
  "node_type_id": "i3.xlarge",
  "autoscale": {
    "min_workers": 2,
    "max_workers": 8
  }
}

# Queries run 2-3x faster automatically
spark.sql("SELECT * FROM large_table WHERE region = 'US'").show()
```

---

## DuckDB Strengths

### In-Process Architecture

**What it is**: Embedded database (like SQLite) optimized for analytics.

**Why it matters**:
- No server to manage
- Runs in-process (Python, R, Node.js, CLI)
- Sub-second startup

**Example**:
```python
import duckdb

# Query CSV directly
duckdb.sql("SELECT * FROM 'orders.csv' WHERE order_total > 100").show()

# Query Parquet
duckdb.sql("SELECT customer_id, SUM(order_total) FROM 'orders.parquet' GROUP BY customer_id").show()

# Persist to local database
con = duckdb.connect('analytics.duckdb')
con.execute("CREATE TABLE orders AS SELECT * FROM 'orders.csv'")
con.execute("SELECT * FROM orders").fetchall()
```

### Zero Configuration

**What it is**: No installation, no server, no config files.

**Why it matters**:
- pip install duckdb → start querying
- Perfect for local development
- Reproducible environments

**Example**:
```bash
# Install
pip install duckdb

# Query immediately
python -c "import duckdb; duckdb.sql('SELECT 42').show()"
```

### Analytics on Laptop

**What it is**: Optimized for single-node performance (vectorized execution, columnar storage).

**Why it matters**:
- Analyze GBs of data on laptop (no cloud needed)
- Faster than Pandas for large datasets
- Great for prototyping pipelines

**Benchmark** (10M rows):
| Tool | Time |
|------|------|
| Pandas | 45s |
| DuckDB | 3s |
| PostgreSQL | 120s |

**Example**:
```python
import duckdb

# Query 10GB Parquet file on laptop
duckdb.sql("""
  SELECT
    DATE_TRUNC('month', order_date) AS month,
    SUM(order_total) AS revenue
  FROM 'orders_10gb.parquet'
  WHERE order_date >= '2025-01-01'
  GROUP BY month
  ORDER BY month
""").show()
# Completes in ~5 seconds on M1 MacBook
```

### Parquet/CSV Native

**What it is**: Query Parquet, CSV, JSON files directly without loading.

**Why it matters**:
- No ETL to warehouse for exploration
- Federated queries across formats
- Seamless integration with data lakes

**Example**:
```python
# Query multiple formats in one query
duckdb.sql("""
  SELECT
    o.order_id,
    c.customer_name,
    p.product_name
  FROM 'orders.parquet' o
  JOIN 'customers.csv' c ON o.customer_id = c.customer_id
  JOIN 'products.json' p ON o.product_id = p.product_id
""").show()

# Query partitioned Parquet (Hive-style)
duckdb.sql("""
  SELECT * FROM 's3://bucket/orders/year=2026/month=01/*.parquet'
""").show()
```

### MotherDuck (Cloud DuckDB)

**What it is**: Managed DuckDB in the cloud (hybrid execution).

**Why it matters**:
- Collaborate on DuckDB databases
- Hybrid queries (local + cloud)
- Scale beyond laptop

**Example**:
```python
import duckdb

# Connect to MotherDuck
con = duckdb.connect('md:my_database?motherduck_token=abc123')

# Hybrid query (local CSV + cloud table)
con.sql("""
  SELECT
    l.customer_id,
    l.local_metric,
    c.cloud_metric
  FROM 'local_data.csv' l
  JOIN md:my_database.cloud_table c ON l.customer_id = c.customer_id
""").show()
```

---

## Migration Considerations

### Common Migration Paths

| From | To | Reason | Complexity |
|------|----|---------| ----------|
| PostgreSQL | BigQuery | Scale, serverless | Low |
| Redshift | Snowflake | Performance, multi-cloud | Medium |
| Hive | Databricks | Lakehouse, performance | Medium |
| On-prem Oracle | Snowflake/BigQuery | Cloud migration | High |
| Snowflake | Databricks | ML/AI workloads | Medium |
| BigQuery | Snowflake | Multi-cloud, data sharing | Medium |

### SQL Dialect Differences

| Feature | Snowflake | BigQuery | Databricks (Spark SQL) | DuckDB |
|---------|-----------|----------|------------------------|--------|
| **String concat** | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` |
| **Date diff** | `DATEDIFF(day, d1, d2)` | `DATE_DIFF(d1, d2, DAY)` | `DATEDIFF(d1, d2)` | `DATE_DIFF('day', d1, d2)` |
| **Array indexing** | `array[0]` (0-indexed) | `array[OFFSET(0)]` (0) or `array[ORDINAL(1)]` (1) | `array[0]` (0-indexed) | `array[1]` (1-indexed) |
| **JSON extraction** | `json:field` or `GET_PATH()` | `JSON_EXTRACT()` | `GET_JSON_OBJECT()` | `json->>'field'` (PostgreSQL-style) |
| **Window exclude** | `EXCLUDE` clause | Not supported | Not supported | `EXCLUDE` clause |
| **QUALIFY** | Supported | Not supported | Not supported | Supported |
| **Pivot** | `PIVOT()` | `PIVOT()` (different syntax) | `PIVOT()` (Hive-style) | `PIVOT()` |
| **Create table as** | `CREATE TABLE AS` | `CREATE TABLE AS` | `CREATE TABLE AS` | `CREATE TABLE AS` |
| **Merge** | `MERGE INTO` | `MERGE INTO` | `MERGE INTO` (Delta only) | Not supported (use INSERT + UPDATE) |

**QUALIFY example** (Snowflake/DuckDB only):
```sql
-- Get most recent order per customer
SELECT customer_id, order_id, order_date
FROM orders
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) = 1;

-- BigQuery/Databricks require subquery:
SELECT * FROM (
  SELECT
    customer_id, order_id, order_date,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
  FROM orders
)
WHERE rn = 1;
```

### Tool Ecosystem Mapping

| Tool | Snowflake | BigQuery | Databricks | DuckDB |
|------|-----------|----------|------------|--------|
| **dbt** | Native | Native | Native | Native (1.5+) |
| **Fivetran** | Native | Native | Native | Not supported |
| **Airbyte** | Native | Native | Native | Community |
| **Looker** | Native | Native (preferred) | Native | JDBC connector |
| **Tableau** | Native | Native | Native | JDBC connector |
| **Hex** | Native | Native | Native | Python integration |
| **Airflow** | Operator available | Operator available | Operator available | Python operator |
| **Dagster** | Resource | Resource | Resource | Resource |

---

## When to Use Each Platform

### Snowflake

**Best for**:
- Enterprise data warehousing with complex governance
- Multi-cloud or hybrid cloud strategies
- Data sharing with external partners
- Organizations needing clear cost isolation by team

**Example workload**: SaaS company sharing customer usage data with partners via Snowflake Data Marketplace.

### BigQuery

**Best for**:
- Google Cloud-native architectures
- Serverless preference (zero management)
- Massive ad-hoc query workloads (log analysis, clickstream)
- Teams using Looker/Dataform/Vertex AI

**Example workload**: Gaming company analyzing 100TB of event logs daily with BQML churn prediction.

### Databricks

**Best for**:
- Lakehouse architecture (unified data + ML)
- Heavy Python/Spark workloads
- ML/AI-first organizations
- Delta Lake + Unity Catalog governance

**Example workload**: Fintech building real-time fraud detection with Spark Streaming + MLflow.

### DuckDB

**Best for**:
- Local development and testing
- Data exploration on laptops
- Embedded analytics in applications
- Small-to-medium datasets (<100GB)

**Example workload**: Data scientist prototyping pipeline locally before deploying to Snowflake.

---

## Further Reading

- [Snowflake Documentation](https://docs.snowflake.com/)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Databricks Documentation](https://docs.databricks.com/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [dbt Warehouse Adapters](https://docs.getdbt.com/docs/supported-data-platforms)
