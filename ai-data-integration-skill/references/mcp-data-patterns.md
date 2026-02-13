# MCP Data Patterns Reference

> MCP server architecture for warehouse and data platform integration. Part of the [AI Data Integration Skill](../SKILL.md).

---

## Architecture Overview

An MCP (Model Context Protocol) data server exposes warehouse capabilities as structured tools that AI agents can invoke. The server sits between the agent and the warehouse, enforcing guardrails.

```
┌──────────────┐     MCP Protocol     ┌──────────────────┐     SQL      ┌───────────┐
│  AI Agent    │ ◄──────────────────► │  MCP Data Server  │ ◄──────────► │ Warehouse │
│  (Claude)    │    Tools + Results    │  (Guardrails)     │   Read-Only  │ (Snowflake│
└──────────────┘                      └──────────────────┘              │  BigQuery) │
                                             │                          └───────────┘
                                             │ Audit Log
                                             ▼
                                      ┌──────────────┐
                                      │ audit.ai_log │
                                      └──────────────┘
```

---

## Snowflake MCP Server

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import snowflake.connector
import os
import hashlib
from datetime import datetime

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ROLE
# Configure: export SNOWFLAKE_PRIVATE_KEY_PATH, SNOWFLAKE_WAREHOUSE
# Use a dedicated AI_READER role with read-only access to approved schemas.
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────

class WarehouseConfig:
    """Configuration with enforced guardrails."""
    MAX_ROWS = 1000
    QUERY_TIMEOUT_SECONDS = 30
    ALLOWED_SCHEMAS = ["STAGING", "MARTS", "REFERENCE"]
    BLOCKED_PATTERNS = ["PII", "AUDIT", "ADMIN", "PASSWORD", "SECRET"]
    LOG_ALL_QUERIES = True

app = Server("snowflake-mcp")

def get_connection():
    """Get read-only Snowflake connection."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key_file_path=os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "AI_READER_WH"),
        role=os.environ.get("SNOWFLAKE_ROLE", "AI_READER"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "ANALYTICS"),
    )

def log_query(tool_name: str, params: dict, sql: str, status: str, row_count: int = 0):
    """Audit log every AI-initiated query."""
    if not WarehouseConfig.LOG_ALL_QUERIES:
        return
    conn = get_connection()
    conn.cursor().execute("""
        INSERT INTO audit.ai_query_log (agent_id, prompt_hash, generated_sql, execution_status, result_row_count)
        VALUES (%s, %s, %s, %s, %s)
    """, ("snowflake-mcp", hashlib.sha256(str(params).encode()).hexdigest(), sql, status, row_count))

@app.tool()
async def list_schemas() -> list[TextContent]:
    """List database schemas available to the AI reader role."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SHOW SCHEMAS IN DATABASE")
    schemas = [row[1] for row in cursor.fetchall()
               if row[1].upper() in WarehouseConfig.ALLOWED_SCHEMAS]
    conn.close()
    return [TextContent(type="text", text="\n".join(schemas))]

@app.tool()
async def list_tables(schema_name: str) -> list[TextContent]:
    """List tables in a schema with row counts and descriptions."""
    schema = schema_name.upper()
    if schema not in WarehouseConfig.ALLOWED_SCHEMAS:
        return [TextContent(type="text", text=f"Schema '{schema}' is not accessible")]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT table_name, row_count, comment
        FROM information_schema.tables
        WHERE table_schema = '{schema}'
        ORDER BY table_name
    """)
    rows = cursor.fetchall()
    conn.close()

    lines = [f"{'Table':<40} {'Rows':>12} Description"]
    lines.append("-" * 80)
    for name, count, comment in rows:
        lines.append(f"{name:<40} {count or 0:>12,} {comment or ''}")

    return [TextContent(type="text", text="\n".join(lines))]

@app.tool()
async def describe_table(schema_name: str, table_name: str) -> list[TextContent]:
    """Describe columns, types, and comments for a table."""
    schema, table = schema_name.upper(), table_name.upper()
    if schema not in WarehouseConfig.ALLOWED_SCHEMAS:
        return [TextContent(type="text", text=f"Schema '{schema}' is not accessible")]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT column_name, data_type, is_nullable, comment
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        ORDER BY ordinal_position
    """)
    rows = cursor.fetchall()
    conn.close()

    lines = [f"Table: {schema}.{table}", ""]
    lines.append(f"{'Column':<30} {'Type':<20} {'Nullable':<10} Description")
    lines.append("-" * 90)
    for name, dtype, nullable, comment in rows:
        lines.append(f"{name:<30} {dtype:<20} {nullable:<10} {comment or ''}")

    return [TextContent(type="text", text="\n".join(lines))]

@app.tool()
async def sample_table(
    schema_name: str,
    table_name: str,
    limit: int = 10,
) -> list[TextContent]:
    """Return a small sample from a table. Max 100 rows."""
    schema, table = schema_name.upper(), table_name.upper()
    if schema not in WarehouseConfig.ALLOWED_SCHEMAS:
        return [TextContent(type="text", text=f"Schema '{schema}' is not accessible")]

    limit = min(limit, 100)
    sql = f"SELECT * FROM {schema}.{table} LIMIT {limit}"

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    log_query("sample_table", {"schema": schema, "table": table}, sql, "executed", len(rows))

    # Format as markdown table
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    data_rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]

    return [TextContent(type="text", text="\n".join([header, separator] + data_rows))]

@app.tool()
async def run_query(sql: str) -> list[TextContent]:
    """
    Execute a read-only SQL query with guardrails.

    Guardrails enforced:
    - SELECT statements only (no DDL/DML)
    - LIMIT clause required (max 1000)
    - Only allowed schemas
    - 30-second timeout
    - All queries are audit-logged
    """
    # Validate query
    is_valid, reason = validate_query(sql)
    if not is_valid:
        log_query("run_query", {"sql": sql}, sql, f"rejected: {reason}")
        return [TextContent(type="text", text=f"Query rejected: {reason}")]

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {WarehouseConfig.QUERY_TIMEOUT_SECONDS}")
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        log_query("run_query", {"sql": sql}, sql, "executed", len(rows))

        # Format results
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        data_rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in rows]

        result = "\n".join([header, separator] + data_rows)
        result += f"\n\n({len(rows)} rows returned)"

        return [TextContent(type="text", text=result)]
    except Exception as e:
        log_query("run_query", {"sql": sql}, sql, f"failed: {str(e)}")
        return [TextContent(type="text", text=f"Query error: {str(e)}")]
    finally:
        conn.close()

def validate_query(sql: str) -> tuple[bool, str]:
    """Validate SQL meets all guardrails."""
    sql_upper = sql.strip().upper()

    # Must be SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT statements are allowed"

    # Block DDL/DML keywords
    blocked = ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    for keyword in blocked:
        if f" {keyword} " in f" {sql_upper} ":
            return False, f"Blocked keyword: {keyword}"

    # Must have LIMIT
    if "LIMIT" not in sql_upper:
        return False, "Query must include a LIMIT clause"

    # Check for blocked patterns in table references
    for pattern in WarehouseConfig.BLOCKED_PATTERNS:
        if pattern in sql_upper:
            return False, f"Query references blocked pattern: {pattern}"

    return True, "Valid"
```

---

## BigQuery MCP Server

```python
from google.cloud import bigquery
import os

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa-key.json"
# Or use Application Default Credentials (preferred on GCP)
# Use a dedicated AI reader service account with BigQuery Data Viewer role.
# ─────────────────────────────────────────────────────────────────────

class BigQueryMCPServer:
    """BigQuery MCP server with guardrails."""

    def __init__(self):
        self.client = bigquery.Client(
            project=os.environ.get("GCP_PROJECT_ID"),
        )
        self.allowed_datasets = ["staging", "marts", "reference"]
        self.max_bytes_billed = 1_000_000_000  # 1 GB scan limit

    def run_query(self, sql: str) -> list[dict]:
        """Execute query with cost guardrails."""
        job_config = bigquery.QueryJobConfig(
            maximum_bytes_billed=self.max_bytes_billed,
            use_query_cache=True,
        )

        # Dry run first to check cost
        dry_run_config = bigquery.QueryJobConfig(dry_run=True, use_legacy_sql=False)
        dry_run = self.client.query(sql, job_config=dry_run_config)
        estimated_bytes = dry_run.total_bytes_processed

        if estimated_bytes > self.max_bytes_billed:
            raise ValueError(
                f"Query would scan {estimated_bytes / 1e9:.1f} GB, "
                f"exceeding limit of {self.max_bytes_billed / 1e9:.1f} GB"
            )

        # Execute with timeout
        query_job = self.client.query(sql, job_config=job_config, timeout=30)
        return [dict(row) for row in query_job.result()]
```

---

## Multi-Warehouse MCP Server

For organizations with multiple warehouses, use a unified MCP server that routes to the appropriate backend.

```python
from mcp.server import Server
from mcp.types import TextContent

app = Server("multi-warehouse-mcp")

# Registry of warehouse connections
WAREHOUSES = {
    "snowflake_analytics": SnowflakeBackend(database="ANALYTICS"),
    "bigquery_marketing": BigQueryBackend(dataset="marketing"),
    "duckdb_local": DuckDBBackend(path="local.duckdb"),
}

@app.tool()
async def list_warehouses() -> list[TextContent]:
    """List available warehouse connections."""
    lines = [f"- {name}: {backend.description}" for name, backend in WAREHOUSES.items()]
    return [TextContent(type="text", text="\n".join(lines))]

@app.tool()
async def query(warehouse: str, sql: str) -> list[TextContent]:
    """Run a query against a specific warehouse."""
    if warehouse not in WAREHOUSES:
        return [TextContent(type="text", text=f"Unknown warehouse: {warehouse}")]

    backend = WAREHOUSES[warehouse]
    # Validation and execution handled by backend
    return await backend.execute(sql)
```

---

## Connection Pooling

For production MCP servers, use connection pooling to avoid per-request connection overhead.

```python
from contextlib import contextmanager
import snowflake.connector
from queue import Queue

class ConnectionPool:
    """Simple connection pool for MCP server."""

    def __init__(self, max_connections: int = 5, **conn_kwargs):
        self.pool = Queue(maxsize=max_connections)
        self.conn_kwargs = conn_kwargs
        for _ in range(max_connections):
            self.pool.put(self._create_connection())

    def _create_connection(self):
        return snowflake.connector.connect(**self.conn_kwargs)

    @contextmanager
    def get_connection(self):
        conn = self.pool.get(timeout=10)
        try:
            yield conn
        finally:
            # Verify connection is still valid
            try:
                conn.cursor().execute("SELECT 1")
                self.pool.put(conn)
            except Exception:
                self.pool.put(self._create_connection())

# Usage in MCP tool
pool = ConnectionPool(
    max_connections=5,
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key_file_path=os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"],
    role="AI_READER",
)

@app.tool()
async def run_query(sql: str) -> list[TextContent]:
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        return format_results(cursor)
```

---

## Context Management

### Schema Context Budget

LLMs have limited context windows. Manage schema context carefully:

```python
def build_focused_context(
    question: str,
    all_tables: list[dict],
    max_tables: int = 10,
    max_columns_per_table: int = 20,
) -> str:
    """Build focused schema context relevant to the question."""
    # Step 1: Score tables by relevance to question
    scored_tables = score_table_relevance(question, all_tables)
    top_tables = scored_tables[:max_tables]

    # Step 2: For each table, include only relevant columns
    context_parts = []
    for table in top_tables:
        columns = table["columns"][:max_columns_per_table]
        col_lines = [f"  {c['name']} {c['type']}" + (f" -- {c['comment']}" if c.get('comment') else "")
                     for c in columns]
        context_parts.append(
            f"-- {table['schema']}.{table['name']}"
            + (f" ({table['comment']})" if table.get('comment') else "")
            + "\n" + "\n".join(col_lines)
        )

    return "\n\n".join(context_parts)
```

### Tool Selection by Maturity Level

Configure which MCP tools are available based on the organization's maturity level:

```python
TOOLS_BY_LEVEL = {
    0: [],                                    # Level 0: No MCP tools (code gen only)
    1: ["list_schemas", "list_tables", "describe_table"],  # Metadata only
    2: ["list_schemas", "list_tables", "describe_table", "sample_table"],  # + samples
    3: ["list_schemas", "list_tables", "describe_table", "sample_table", "run_query"],  # + queries
}

def configure_server(level: int):
    """Register only tools appropriate for the trust level."""
    available_tools = TOOLS_BY_LEVEL.get(level, [])
    for tool_name in available_tools:
        app.register_tool(TOOL_REGISTRY[tool_name])
```
