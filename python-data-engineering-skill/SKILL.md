---
name: python-data-engineering-skill
description: "Use when writing Python for data engineering — Polars, Pandas, PySpark DataFrames, dbt Python models, API extraction scripts, data validation with Pydantic or Pandera, or choosing between Python DataFrame libraries"
license: Apache-2.0
metadata:
  author: Daniel Song
  version: 1.0.0
---

# Python Data Engineering Skill for Claude

Expert guidance for Python as a data engineering language. Covers DataFrame libraries (Polars, Pandas, PySpark), dbt Python models, API extraction patterns, and data validation frameworks. Assumes Python proficiency — focuses on data engineering patterns, not language basics.

## When to Use This Skill

**Activate this skill when:**

- Choosing between DataFrame libraries (Polars vs Pandas vs PySpark vs DuckDB)
- Writing data transformations with Polars or Pandas
- Building PySpark jobs for distributed processing
- Writing dbt Python models (using `dbt.ref()`, `dbt.source()`)
- Building API extraction scripts with pagination, rate limiting, and retry
- Implementing data validation with Pydantic, Pandera, or Great Expectations
- Optimizing memory usage for large DataFrame operations
- Converting between DataFrame formats (Polars ↔ Pandas ↔ Arrow ↔ Spark)

**Don't use this skill for:**

- SQL transformations in dbt (use `dbt-skill`)
- DLT pipeline configuration (use `integration-patterns-skill`)
- Kafka/Flink stream processing (use `streaming-data-skill`)
- Dagster/Airflow orchestration (use `data-orchestration-skill`)
- General Python programming (Claude already knows this)
- Web application development (use web-specific skills)

## Core Principles

### 1. Type Safety First

Use type annotations everywhere. Data engineering code processes untrusted data — types catch errors at development time instead of 3 AM in production.

```python
from typing import Iterator
import polars as pl
from pydantic import BaseModel
from datetime import date
from decimal import Decimal

class Order(BaseModel):
    order_id: str
    customer_id: str
    amount: Decimal
    order_date: date

def transform_orders(raw: pl.LazyFrame) -> pl.LazyFrame:
    """Transform raw orders — typed input, typed output."""
    return (
        raw
        .filter(pl.col("amount") > 0)
        .with_columns(
            pl.col("order_date").str.to_date("%Y-%m-%d"),
            pl.col("amount").cast(pl.Decimal(10, 2)),
        )
        .unique(subset=["order_id"])
    )
```

### 2. Immutable Transforms

Never mutate DataFrames in place. Always return new DataFrames from transformations. This makes pipelines reproducible, testable, and debuggable.

```python
# Good: immutable chain
result = (
    df
    .filter(pl.col("status") == "active")
    .with_columns(pl.col("amount") * 1.1)
    .sort("created_at")
)

# Bad: mutation
df["amount"] = df["amount"] * 1.1  # Mutates in place
df = df[df["status"] == "active"]   # Hard to trace
```

### 3. Lazy Evaluation When Possible

Prefer lazy evaluation (Polars LazyFrame, Spark DataFrame) over eager execution. Let the query planner optimize your pipeline.

```python
# Polars: lazy by default for scans
result = (
    pl.scan_parquet("data/*.parquet")  # Lazy — no data loaded yet
    .filter(pl.col("date") >= "2024-01-01")
    .group_by("customer_id")
    .agg(pl.col("amount").sum())
    .sort("amount", descending=True)
    .head(100)
    .collect()  # Executes the optimized plan
)
```

### 4. Memory Efficiency

Data engineering processes large datasets. Be intentional about memory:

- Use appropriate dtypes (`Int32` not `Int64` when range allows)
- Stream/scan instead of loading entire files into memory
- Process in chunks when data exceeds available RAM
- Prefer columnar formats (Parquet, Arrow) over row-based (CSV, JSON)

### 5. Test Data Pipelines

Data pipelines need tests just like application code. Test your transforms with small, representative fixtures.

```python
def test_transform_orders():
    raw = pl.LazyFrame({
        "order_id": ["A", "B", "B", "C"],
        "customer_id": ["c1", "c2", "c2", "c3"],
        "amount": [100.0, -50.0, 200.0, 300.0],
        "order_date": ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"],
    })

    result = transform_orders(raw).collect()

    assert result.shape[0] == 2  # Filtered negative, deduped B
    assert result["order_id"].to_list() == ["A", "C"]
```

---

## DataFrame Library Decision Matrix

| Factor | Polars | Pandas | PySpark | DuckDB (Python) |
|--------|--------|--------|---------|-----------------|
| **Data size** | Single machine (GB-TB via streaming) | Single machine (MB-GB) | Distributed cluster (TB-PB) | Single machine (GB-TB) |
| **Speed** | Very fast (Rust, multi-threaded) | Moderate (single-threaded) | Fast at scale (distributed) | Very fast (vectorized) |
| **Memory** | Efficient (Arrow-native, streaming) | Inefficient (copies, object dtype) | Efficient (distributed) | Efficient (out-of-core) |
| **API style** | Expression-based, method chaining | Index-based, mixed paradigms | SQL-like DataFrame API | SQL-first, DataFrame bridge |
| **Lazy eval** | Yes (LazyFrame) | No (eager only) | Yes (execution plan) | Yes (query plan) |
| **Ecosystem** | Growing (Arrow interop) | Massive (scikit-learn, etc.) | Massive (ML, streaming) | Growing (SQL focus) |
| **dbt support** | Via DataFrame return | Native (`dbt-core`) | Via `dbt-spark` | Via `dbt-duckdb` |
| **Learning curve** | Medium (new API) | Low (widely known) | Medium-High (Spark concepts) | Low (SQL + Python) |
| **Best for** | New projects, performance-critical | Legacy code, ML integration | Big data, Databricks | Analytics, local dev |

### When to Choose Each

**Choose Polars when:**
- Starting a new data pipeline from scratch
- Performance matters (Polars is 5-50x faster than Pandas for most operations)
- Processing files from MB to low-TB range on a single machine
- You want modern, consistent API with fewer footguns

**Choose Pandas when:**
- Integrating with scikit-learn, statsmodels, or other ML libraries that require Pandas
- Maintaining existing Pandas codebases
- Using libraries that only accept Pandas DataFrames
- Quick exploratory analysis in notebooks

**Choose PySpark when:**
- Data exceeds single-machine memory (TB+)
- Running on Databricks or existing Spark infrastructure
- You need distributed processing across a cluster
- Writing dbt Python models on Spark-based warehouses

**Choose DuckDB when:**
- Your primary interface is SQL but you need Python glue
- Processing Parquet/CSV files with SQL queries
- Local development and testing (fast, zero-config)
- Analytical queries on moderate data (complementary to Polars for Python transforms)

---

## Polars Patterns (Primary)

Polars is the recommended DataFrame library for new data engineering work. It's built on Apache Arrow, written in Rust, and provides both eager and lazy evaluation.

### Basic Transforms

```python
import polars as pl

# Read and transform
orders = (
    pl.scan_parquet("raw/orders/*.parquet")
    .filter(
        (pl.col("status").is_in(["completed", "shipped"]))
        & (pl.col("amount") > 0)
    )
    .with_columns(
        # Rename and cast
        pl.col("order_date").str.to_date("%Y-%m-%d").alias("order_date_parsed"),
        pl.col("amount").cast(pl.Decimal(10, 2)),
        # Derived columns
        (pl.col("amount") * pl.col("tax_rate")).round(2).alias("tax_amount"),
        pl.col("customer_id").str.to_uppercase().alias("customer_id_norm"),
    )
    .drop("order_date")
    .rename({"order_date_parsed": "order_date"})
    .unique(subset=["order_id"])
    .sort("order_date")
    .collect()
)
```

### Aggregations

```python
# Group by with multiple aggregations
customer_metrics = (
    orders.lazy()
    .group_by("customer_id")
    .agg(
        pl.col("order_id").count().alias("order_count"),
        pl.col("amount").sum().alias("total_revenue"),
        pl.col("amount").mean().alias("avg_order_value"),
        pl.col("amount").max().alias("max_order_value"),
        pl.col("order_date").min().alias("first_order_date"),
        pl.col("order_date").max().alias("last_order_date"),
        pl.col("product_category").n_unique().alias("unique_categories"),
    )
    .with_columns(
        # Derived metrics
        ((pl.col("last_order_date") - pl.col("first_order_date")).dt.total_days())
        .alias("customer_lifetime_days"),
    )
    .sort("total_revenue", descending=True)
    .collect()
)
```

### Joins

```python
# Multiple join types
enriched_orders = (
    orders.lazy()
    .join(
        customers.lazy(),
        on="customer_id",
        how="left",
    )
    .join(
        products.lazy(),
        on="product_id",
        how="inner",
    )
    .join(
        regions.lazy(),
        left_on="shipping_zip",
        right_on="zip_code",
        how="left",
        suffix="_region",
    )
    .collect()
)
```

### Window Functions

```python
ranked_orders = (
    orders.lazy()
    .with_columns(
        # Rank within customer
        pl.col("amount")
        .rank(method="dense", descending=True)
        .over("customer_id")
        .alias("amount_rank"),

        # Running total within customer
        pl.col("amount")
        .cum_sum()
        .over("customer_id")
        .alias("cumulative_revenue"),

        # Lag/Lead
        pl.col("order_date")
        .shift(1)
        .over("customer_id")
        .alias("prev_order_date"),

        # Percent of customer total
        (pl.col("amount") / pl.col("amount").sum().over("customer_id"))
        .alias("pct_of_customer_total"),
    )
    .collect()
)
```

### Streaming for Large Files

```python
# Process files larger than memory using streaming
result = (
    pl.scan_csv(
        "huge_file.csv",
        dtypes={"id": pl.Int64, "amount": pl.Float64},
    )
    .filter(pl.col("amount") > 100)
    .group_by("category")
    .agg(pl.col("amount").sum())
    .collect(streaming=True)  # Process in batches, constant memory
)
```

For advanced Polars patterns (Arrow interop, custom expressions, DuckDB bridge, performance tuning), see [Polars Patterns Reference →](references/polars-patterns.md)

---

## Pandas Patterns (Legacy/Compatibility)

Use Pandas when integrating with ML libraries or maintaining existing codebases. Prefer method chaining and vectorized operations over iterative patterns.

### Method Chaining (Preferred Style)

```python
import pandas as pd

result = (
    pd.read_parquet("raw/orders.parquet")
    .query("status in ['completed', 'shipped'] and amount > 0")
    .assign(
        order_date=lambda df: pd.to_datetime(df["order_date"]),
        tax_amount=lambda df: (df["amount"] * df["tax_rate"]).round(2),
        customer_id_norm=lambda df: df["customer_id"].str.upper(),
    )
    .drop_duplicates(subset=["order_id"])
    .sort_values("order_date")
    .reset_index(drop=True)
)
```

### Memory Optimization

```python
# Specify dtypes to reduce memory usage
dtypes = {
    "order_id": "string",          # Not object
    "customer_id": "string",
    "amount": "float32",           # Not float64
    "quantity": "int16",           # Not int64
    "status": "category",         # Repeated strings
}

df = pd.read_csv("orders.csv", dtype=dtypes)

# Pandas 2.0+: Arrow backend for better performance
df = pd.read_parquet("orders.parquet", dtype_backend="pyarrow")
```

### Chunked Processing

```python
# Process large CSV files in chunks
results = []
for chunk in pd.read_csv("huge_file.csv", chunksize=100_000):
    processed = (
        chunk
        .query("amount > 0")
        .groupby("category")
        .agg({"amount": "sum"})
    )
    results.append(processed)

final = pd.concat(results).groupby(level=0).sum()
```

For advanced Pandas patterns (Arrow backend, pipe(), memory profiling, anti-patterns), see [Pandas Patterns Reference →](references/pandas-patterns.md)

---

## PySpark Patterns (Distributed)

Use PySpark when data exceeds single-machine memory or when running on Databricks/Spark infrastructure.

### Basic DataFrame Operations

```python
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark = SparkSession.builder.appName("orders_pipeline").getOrCreate()

# Read and transform
orders = (
    spark.read.parquet("s3://data-lake/raw/orders/")
    .filter(
        (F.col("status").isin("completed", "shipped"))
        & (F.col("amount") > 0)
    )
    .withColumn("order_date", F.to_date("order_date", "yyyy-MM-dd"))
    .withColumn("tax_amount", F.round(F.col("amount") * F.col("tax_rate"), 2))
    .dropDuplicates(["order_id"])
    .orderBy("order_date")
)

# Aggregation
customer_metrics = (
    orders
    .groupBy("customer_id")
    .agg(
        F.count("order_id").alias("order_count"),
        F.sum("amount").alias("total_revenue"),
        F.avg("amount").alias("avg_order_value"),
        F.min("order_date").alias("first_order_date"),
        F.max("order_date").alias("last_order_date"),
    )
)

# Window functions
window_spec = Window.partitionBy("customer_id").orderBy("order_date")

ranked = orders.withColumn(
    "order_number", F.row_number().over(window_spec)
).withColumn(
    "cumulative_amount", F.sum("amount").over(window_spec)
)
```

### Pandas UDFs (Preferred Over Regular UDFs)

```python
from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import FloatType
import pandas as pd

@pandas_udf(FloatType())
def normalize_amount(amounts: pd.Series) -> pd.Series:
    """Pandas UDF — vectorized, runs on Arrow batches."""
    mean = amounts.mean()
    std = amounts.std()
    return (amounts - mean) / std

# Apply (much faster than regular UDFs)
orders = orders.withColumn("amount_normalized", normalize_amount("amount"))
```

### Write with Partitioning

```python
# Write partitioned by date for efficient downstream queries
(
    orders
    .repartition("order_date")
    .write
    .partitionBy("order_date")
    .mode("overwrite")
    .parquet("s3://data-lake/processed/orders/")
)
```

For advanced PySpark patterns (Spark Connect, Delta Lake, Databricks specifics, caching strategies), see [PySpark Patterns Reference →](references/pyspark-patterns.md)

---

## dbt Python Models

dbt supports Python models alongside SQL models. Use Python models for transforms that are difficult or impossible in SQL.

### When to Use Python vs SQL in dbt

| Use Python When | Use SQL When |
|----------------|--------------|
| Complex statistical calculations | Joins, filters, aggregations |
| ML model scoring (sklearn predict) | Window functions |
| API calls during transformation | CTEs and subqueries |
| Complex string parsing (regex, NLP) | Type casting, date math |
| External library integration | Pivoting/unpivoting |
| Working with semi-structured data | Standard ELT transforms |

### Basic dbt Python Model

```python
# models/intermediate/int_customer_rfm.py
def model(dbt, session):
    """Calculate RFM (Recency, Frequency, Monetary) scores."""
    # Read upstream models using dbt.ref()
    orders = dbt.ref("stg_orders").to_pandas()  # Returns Pandas DataFrame

    from datetime import datetime
    import pandas as pd

    reference_date = datetime(2024, 12, 31)

    rfm = (
        orders
        .groupby("customer_id")
        .agg(
            recency=("order_date", lambda x: (reference_date - x.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("amount", "sum"),
        )
        .reset_index()
    )

    # Score each dimension (1-5)
    for col in ["recency", "frequency", "monetary"]:
        ascending = col != "recency"  # Lower recency = better
        rfm[f"{col}_score"] = pd.qcut(
            rfm[col], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop"
        ).astype(int) if ascending else pd.qcut(
            rfm[col], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop"
        ).astype(int)

    rfm["rfm_score"] = (
        rfm["recency_score"] * 100
        + rfm["frequency_score"] * 10
        + rfm["monetary_score"]
    )

    return rfm  # dbt writes to warehouse automatically
```

### dbt Python Model with Config

```python
# models/marts/fct_anomaly_scores.py
def model(dbt, session):
    """Detect anomalous orders using Isolation Forest."""
    dbt.config(
        materialized="table",
        packages=["scikit-learn==1.4.0"],  # Specify dependencies
        tags=["ml", "daily"],
    )

    orders = dbt.ref("stg_orders").to_pandas()

    from sklearn.ensemble import IsolationForest
    import numpy as np

    features = orders[["amount", "quantity", "discount_pct"]].fillna(0)
    model = IsolationForest(contamination=0.05, random_state=42)
    orders["anomaly_score"] = model.decision_function(features)
    orders["is_anomaly"] = model.predict(features) == -1

    return orders[["order_id", "anomaly_score", "is_anomaly"]]
```

### dbt Python Model on Snowflake (Snowpark)

```python
# models/intermediate/int_sentiment.py
def model(dbt, session):
    """
    Runs on Snowpark (Snowflake's Python runtime).
    Uses Snowpark DataFrame API, not Pandas.
    """
    dbt.config(materialized="table")

    # session is a Snowpark Session object
    reviews = dbt.ref("stg_reviews")  # Returns Snowpark DataFrame

    from snowflake.snowpark.functions import col, when, length

    return (
        reviews
        .with_column("review_length", length(col("review_text")))
        .with_column(
            "sentiment_bucket",
            when(col("rating") >= 4, "positive")
            .when(col("rating") <= 2, "negative")
            .otherwise("neutral"),
        )
    )
```

---

## API Extraction Patterns

Robust API extraction with typed clients, pagination, rate limiting, and error handling.

### Typed API Client

```python
import httpx
from pydantic import BaseModel
from typing import Iterator, Optional
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential
import os

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export GITHUB_TOKEN="ghp_xxx"
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────

class GitHubIssue(BaseModel):
    id: int
    number: int
    title: str
    state: str
    created_at: datetime
    updated_at: datetime
    body: Optional[str] = None

class GitHubClient:
    """Typed GitHub API client with pagination and retry."""

    def __init__(self, token: str):
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30.0,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _get(self, path: str, params: dict = None) -> httpx.Response:
        response = self.client.get(path, params=params)
        response.raise_for_status()
        return response

    def list_issues(
        self, owner: str, repo: str, since: Optional[str] = None
    ) -> Iterator[GitHubIssue]:
        """Paginate through all issues, yielding typed models."""
        params = {"state": "all", "sort": "updated", "per_page": 100}
        if since:
            params["since"] = since

        url = f"/repos/{owner}/{repo}/issues"
        while url:
            response = self._get(url, params=params)
            for item in response.json():
                yield GitHubIssue.model_validate(item)

            # Follow Link header pagination
            url = response.links.get("next", {}).get("url")
            params = {}  # Params are embedded in next URL

    def close(self):
        self.client.close()

# Usage
client = GitHubClient(token=os.environ["GITHUB_TOKEN"])
issues = list(client.list_issues("dtsong", "data-engineering-skills", since="2024-01-01T00:00:00Z"))
client.close()
```

### Async Extraction

```python
import httpx
import asyncio
from typing import AsyncIterator

class AsyncAPIExtractor:
    """Async API extraction for high-throughput endpoints."""

    def __init__(self, base_url: str, api_key: str, concurrency: int = 10):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
        self.semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(self, path: str) -> dict:
        """Fetch single resource with concurrency control."""
        async with self.semaphore:
            response = await self.client.get(path)
            response.raise_for_status()
            return response.json()

    async def fetch_many(self, paths: list[str]) -> list[dict]:
        """Fetch multiple resources concurrently."""
        tasks = [self.fetch_one(path) for path in paths]
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def close(self):
        await self.client.aclose()

# Usage
async def extract_all_customers():
    extractor = AsyncAPIExtractor(
        base_url="https://api.example.com/v1",
        api_key=os.environ["EXAMPLE_API_KEY"],
        concurrency=5,
    )
    try:
        # Fetch customer list
        customers = await extractor.fetch_one("/customers?limit=1000")

        # Fetch details for each customer concurrently
        detail_paths = [f"/customers/{c['id']}" for c in customers["data"]]
        details = await extractor.fetch_many(detail_paths)

        return [d for d in details if not isinstance(d, Exception)]
    finally:
        await extractor.close()

results = asyncio.run(extract_all_customers())
```

For more extraction patterns (rate limiting, backoff strategies, pagination helpers), see [Extraction Patterns Reference →](references/extraction-patterns.md)

---

## Data Validation

### Pydantic (Row-Level Validation)

```python
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional
from datetime import date
from decimal import Decimal

class OrderRecord(BaseModel):
    """Validate individual order records."""
    order_id: str
    customer_id: str
    amount: Decimal
    quantity: int
    order_date: date
    status: str
    email: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v):
        valid = {"pending", "completed", "shipped", "cancelled", "refunded"}
        if v not in valid:
            raise ValueError(f"Status must be one of {valid}")
        return v

    @model_validator(mode="after")
    def refund_has_original(self):
        if self.status == "refunded" and self.amount > 0:
            raise ValueError("Refunded orders should have negative amount")
        return self

# Validate a batch
def validate_orders(raw_records: list[dict]) -> tuple[list[OrderRecord], list[dict]]:
    """Return valid records and errors separately."""
    valid, errors = [], []
    for record in raw_records:
        try:
            valid.append(OrderRecord.model_validate(record))
        except Exception as e:
            errors.append({"record": record, "error": str(e)})
    return valid, errors
```

### Pandera (DataFrame-Level Validation)

```python
import pandera as pa
from pandera.typing import DataFrame, Series
import polars as pl

class OrderSchema(pa.DataFrameModel):
    """Validate DataFrame structure and values."""
    order_id: Series[str] = pa.Field(unique=True, nullable=False)
    customer_id: Series[str] = pa.Field(nullable=False)
    amount: Series[float] = pa.Field(gt=0, nullable=False)
    quantity: Series[int] = pa.Field(ge=1, le=10000)
    order_date: Series[pa.DateTime] = pa.Field(nullable=False)
    status: Series[str] = pa.Field(isin=["pending", "completed", "shipped", "cancelled"])

    class Config:
        strict = True  # Reject extra columns
        coerce = True  # Auto-cast types

# Validate Pandas DataFrame
@pa.check_types
def process_orders(df: DataFrame[OrderSchema]) -> DataFrame[OrderSchema]:
    """Type-checked function — validates input and output."""
    return df.query("status == 'completed'")

# Validate Polars DataFrame
schema = pa.DataFrameSchema({
    "order_id": pa.Column(str, pa.Check.str_length(min_value=1), unique=True),
    "amount": pa.Column(float, pa.Check.gt(0)),
})
validated = schema.validate(orders_df)  # Raises SchemaError on failure
```

### Great Expectations (Suite-Based Validation)

```python
import great_expectations as gx

# Create context and data source
context = gx.get_context()

# Define expectations
suite = context.add_expectation_suite("orders_quality")
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToNotBeNull(column="order_id")
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeUnique(column="order_id")
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeBetween(
        column="amount", min_value=0, max_value=1_000_000
    )
)
suite.add_expectation(
    gx.expectations.ExpectColumnValuesToBeInSet(
        column="status",
        value_set=["pending", "completed", "shipped", "cancelled"],
    )
)

# Run validation
batch = context.get_batch(
    datasource_name="warehouse",
    data_asset_name="raw.orders",
)
result = batch.validate(suite)

if not result.success:
    failed = [r for r in result.results if not r.success]
    raise ValueError(f"Data quality check failed: {len(failed)} expectations failed")
```

For more validation patterns (contract testing, custom validators, CI integration), see [Data Validation Patterns Reference →](references/data-validation-patterns.md)

---

## DataFrame Interoperability

### Polars ↔ Pandas

```python
import polars as pl
import pandas as pd

# Polars → Pandas
pandas_df = polars_df.to_pandas()

# Pandas → Polars (zero-copy when possible)
polars_df = pl.from_pandas(pandas_df)
```

### Polars ↔ Arrow

```python
import pyarrow as pa

# Polars → Arrow (zero-copy)
arrow_table = polars_df.to_arrow()

# Arrow → Polars (zero-copy)
polars_df = pl.from_arrow(arrow_table)
```

### Polars ↔ DuckDB

```python
import duckdb

# Query Polars DataFrame with DuckDB SQL
result = duckdb.sql("""
    SELECT customer_id, SUM(amount) as total
    FROM polars_df
    GROUP BY customer_id
    ORDER BY total DESC
    LIMIT 10
""").pl()  # Returns Polars DataFrame
```

### Pandas ↔ Spark

```python
# Spark → Pandas (pulls to driver — be careful with large data)
pandas_df = spark_df.toPandas()

# Pandas → Spark
spark_df = spark.createDataFrame(pandas_df)

# Better: Arrow-optimized conversion
spark.conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
pandas_df = spark_df.toPandas()  # Uses Arrow for faster conversion
```

---

## Project Structure

```
my_data_project/
├── src/
│   ├── __init__.py
│   ├── extractors/           # API extraction clients
│   │   ├── __init__.py
│   │   ├── github.py
│   │   └── stripe.py
│   ├── transforms/           # DataFrame transformations
│   │   ├── __init__.py
│   │   ├── orders.py
│   │   └── customers.py
│   ├── validators/           # Data validation schemas
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── models.py             # Pydantic models
├── tests/
│   ├── __init__.py
│   ├── fixtures/             # Test data
│   │   └── orders.parquet
│   ├── test_extractors.py
│   ├── test_transforms.py
│   └── test_validators.py
├── dbt_project/              # If using dbt Python models
│   └── models/
│       └── python/
│           └── int_rfm.py
├── pyproject.toml
└── .env.example              # Document required env vars (never real values)
```

### `pyproject.toml` (Recommended Dependencies)

```toml
[project]
name = "my-data-project"
requires-python = ">=3.11"
dependencies = [
    "polars>=1.0",
    "pyarrow>=15.0",
    "httpx>=0.27",
    "pydantic>=2.0",
    "tenacity>=8.0",
]

[project.optional-dependencies]
pandas = ["pandas>=2.0"]
spark = ["pyspark>=3.5"]
validation = ["pandera>=0.18", "great-expectations>=0.18"]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]
```

---

## Security Posture

This skill generates Python code for data extraction, transformation, and validation.
See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full security framework.

**Credentials required**: API keys/tokens for extraction, database connection strings, cloud storage credentials
**Where to configure**: Environment variables for all secrets. `.env` files for local dev (never commit).
**Minimum role/permissions**: Read-only API tokens for extraction, scoped warehouse access for loading

### By Security Tier

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| Execute Python scripts | Against dev/staging data | Generate code for human review | Generate code only |
| API extraction | Dev/sandbox API tokens | Generate extraction code for review | Generate code only |
| DataFrame transforms | Process dev data locally | Process sample/synthetic data | Generate code only |
| Data validation | Run against dev datasets | Generate validation schemas | Generate schemas only |
| dbt Python models | Execute in dev environment | Generate models for review | Generate models only |

### Credential Best Practices

- **API keys**: Always `os.environ["KEY"]`, never inline. Document required vars in `.env.example`.
- **Database connections**: Use connection strings from environment variables. Prefer key-pair auth.
- **httpx clients**: Pass tokens via constructor, not per-request. Close clients in `finally` blocks.
- **`.env` files**: Use for local development only. Add to `.gitignore`. Provide `.env.example` template.
- **Notebooks**: Never store credentials in notebook cells. Use `%env` or dotenv at the top.

---

## Reference Files

This skill includes detailed reference documentation for deep dives:

- [Polars Patterns →](references/polars-patterns.md) — LazyFrame, expressions, streaming, Arrow interop, DuckDB bridge, performance tuning
- [Pandas Patterns →](references/pandas-patterns.md) — Arrow backend, method chaining, memory optimization, anti-patterns to avoid
- [PySpark Patterns →](references/pyspark-patterns.md) — DataFrame API, Pandas UDFs, Spark Connect, Delta Lake, Databricks patterns
- [Data Validation Patterns →](references/data-validation-patterns.md) — Pydantic v2, Pandera schemas, Great Expectations, contract testing
- [Extraction Patterns →](references/extraction-patterns.md) — httpx clients, async extraction, pagination, rate limiting, retry strategies
