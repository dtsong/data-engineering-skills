---
name: ai-data-integration-skill
description: "Use when integrating AI/LLMs with data systems — MCP servers for warehouses, natural language to SQL (NL-to-SQL, text-to-SQL), embeddings for data discovery, LLM-powered data enrichment, or designing AI agent access to data platforms"
license: Apache-2.0
metadata:
  author: Daniel Song
  version: 1.0.0
---

# AI Data Integration Skill for Claude

Expert guidance for integrating AI and LLM capabilities with data engineering systems. Covers MCP (Model Context Protocol) server patterns for warehouses, natural-language-to-SQL generation, LLM-powered data transformations, and embeddings for data discovery. Security tiers are deeply integrated — not bolted on.

**This is not an ML/MLOps skill.** It covers how AI agents *interact with* data platforms, not how to train or deploy models.

## When to Use This Skill

**Activate this skill when:**

- Building MCP servers that expose warehouse data to AI agents
- Implementing natural-language-to-SQL (NL-to-SQL / text-to-SQL) interfaces
- Using LLMs for data enrichment, classification, or extraction in pipelines
- Building embeddings pipelines for data catalog search or semantic matching
- Designing AI agent access patterns with appropriate security guardrails
- Evaluating when AI adds value to a data pipeline vs traditional approaches
- Implementing human-in-the-loop review for AI-generated queries or transforms

**Don't use this skill for:**

- ML model training or experiment tracking (use MLOps tools)
- General prompt engineering (use prompt engineering guides)
- Building chatbots or conversational AI (use application-level patterns)
- dbt/DLT/orchestration (use the respective domain skills)
- Python DataFrame transforms without LLM involvement (use `python-data-engineering-skill`)

## Core Principles

### 1. Progressive Trust

Never start with full data access. Graduate AI capabilities through trust levels:

```
Level 0: Code generation only (AI never connects to data)
Level 1: Metadata access (schemas, row counts, column stats)
Level 2: Sampled data access (AI sees representative samples, never full tables)
Level 3: Guarded query execution (read-only, row limits, cost caps, human approval)
```

Most organizations should start at Level 0-1 and never need Level 3. The skill provides value at every level.

### 2. Least Privilege

AI agents should have the minimum data access required for the task:

- **Read-only** connections — never write access
- **Scoped to specific schemas/tables** — never `SELECT *` on everything
- **Row-limited queries** — always enforce `LIMIT` clauses
- **Cost-capped** — set query cost/time budgets to prevent runaway scans
- **Audit-logged** — every AI-initiated query is logged with the prompt that triggered it

### 3. Cost Awareness

LLM calls have real cost implications in data pipelines:

| Operation | Cost Estimate | Latency |
|-----------|--------------|---------|
| Schema context (metadata) | ~$0.001 per table | <1s |
| NL-to-SQL generation | ~$0.01-0.05 per query | 1-3s |
| Row-level LLM enrichment | ~$0.001-0.01 per row | 0.5-2s per row |
| Batch classification (100 rows) | ~$0.05-0.50 per batch | 5-15s |
| Embeddings generation | ~$0.0001 per 1K tokens | <1s per batch |

**Rule of thumb:** If you're calling an LLM per-row on millions of rows, you're doing it wrong. Batch, cache, and use traditional approaches where they suffice.

### 4. Human-in-the-Loop

AI-generated SQL and transforms should be reviewed before execution in regulated environments:

- **Tier 1**: Auto-execute against dev/staging with logging
- **Tier 2**: Generate for human review, execute after approval
- **Tier 3**: Generate code only, human handles all execution

### 5. Determinism Where Possible

LLM outputs are non-deterministic. For data pipelines that require reproducibility:

- Cache LLM results and reuse for identical inputs
- Use structured output (JSON mode) to reduce parsing failures
- Implement fallback logic when LLM output is invalid
- Log all LLM inputs/outputs for debugging and audit

---

## AI-Data Integration Maturity Model

| Level | Name | AI Can Access | AI Can Do | Security Tier |
|-------|------|---------------|-----------|---------------|
| **0** | Code Generation | Nothing — generates code offline | Write SQL, Python, YAML, configs | Tier 3 (Air-Gapped) |
| **1** | Metadata Aware | Schemas, column types, row counts, stats | Generate context-aware SQL using real schema info | Tier 2-3 |
| **2** | Sample Access | Representative data samples (10-100 rows) | Understand data patterns, suggest transforms, validate output | Tier 1-2 |
| **3** | Guarded Execution | Read-only query results (with limits) | Run NL-to-SQL, explore data, answer questions | Tier 1 |

**Most organizations operate at Level 0-1.** Level 2-3 requires explicit security review and approval.

### Level 0: Code Generation (All Tiers)

AI generates SQL, Python, and configuration without any data access. This is the baseline — every organization can use this safely.

```python
# Level 0: AI generates dbt model SQL based on requirements
# No data connection needed — works in Tier 3 (air-gapped)

prompt = """
Generate a dbt staging model for Stripe charges with these columns:
- charge_id (string, primary key)
- customer_id (string, foreign key)
- amount_cents (integer)
- currency (string, 3-letter ISO)
- status (string: succeeded, pending, failed)
- created_at (timestamp)

Include:
- Rename from source column conventions (camelCase → snake_case)
- Cast amount_cents to decimal dollars
- Filter to only succeeded charges
- Add unique + not_null tests on charge_id
"""

# AI generates complete dbt model + schema.yml — no data access required
```

### Level 1: Metadata-Aware (Tier 2-3)

AI reads database schemas and statistics to generate more accurate code.

```python
# Level 1: AI reads INFORMATION_SCHEMA to understand actual table structure
# Connection is read-only, limited to metadata views only

METADATA_QUERY = """
SELECT
    table_schema,
    table_name,
    column_name,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema IN ('RAW', 'STAGING')
ORDER BY table_schema, table_name, ordinal_position
"""

# AI uses real schema info to generate accurate SQL
# Never sees actual row data — only metadata
```

### Level 2: Sample Access (Tier 1-2)

AI can see representative data samples to understand patterns.

```python
# Level 2: AI reads a small sample to understand data patterns
# Enforced via LIMIT and TABLESAMPLE

SAMPLE_QUERY = """
SELECT *
FROM raw.orders
TABLESAMPLE (10 ROWS)  -- Or: LIMIT 10
"""

# AI sees 10 real rows to understand:
# - Actual value formats (dates, IDs, enums)
# - Null patterns
# - Data quality issues
# Then generates more accurate transforms
```

### Level 3: Guarded Execution (Tier 1 Only)

AI executes read-only queries with guardrails.

```python
# Level 3: AI runs NL-to-SQL with guardrails
# Only for Tier 1 (cloud-native) environments with explicit approval

GUARDRAILS = {
    "max_rows": 1000,           # Row limit on all queries
    "max_cost_credits": 1.0,    # Snowflake credit cap
    "timeout_seconds": 30,      # Query timeout
    "allowed_schemas": ["STAGING", "MARTS"],  # Whitelist
    "blocked_tables": ["PII_*", "AUDIT_*"],   # Blacklist
    "read_only": True,          # No DDL/DML
    "require_where_clause": True,  # Prevent full table scans
}
```

---

## MCP Server Patterns for Data

MCP (Model Context Protocol) is the standard interface for AI agents to interact with external tools and data. Building an MCP server for your warehouse gives AI agents structured, controlled access to data.

### Basic MCP Data Server

```python
from mcp.server import Server
from mcp.types import Tool, TextContent
import os

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_ROLE
# Configure: export SNOWFLAKE_PRIVATE_KEY_PATH
# The MCP server connects to the warehouse — credentials must be scoped.
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────

app = Server("warehouse-mcp")

@app.tool()
async def list_schemas() -> list[TextContent]:
    """List available database schemas."""
    schemas = execute_query(
        "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
    )
    return [TextContent(type="text", text=format_results(schemas))]

@app.tool()
async def describe_table(schema_name: str, table_name: str) -> list[TextContent]:
    """Describe columns and types for a specific table."""
    # Validate input to prevent SQL injection
    if not schema_name.isalnum() or not table_name.isalnum():
        return [TextContent(type="text", text="Error: Invalid schema or table name")]

    columns = execute_query(f"""
        SELECT column_name, data_type, is_nullable, comment
        FROM information_schema.columns
        WHERE table_schema = '{schema_name.upper()}'
          AND table_name = '{table_name.upper()}'
        ORDER BY ordinal_position
    """)
    return [TextContent(type="text", text=format_results(columns))]

@app.tool()
async def query_sample(
    schema_name: str,
    table_name: str,
    limit: int = 10,
) -> list[TextContent]:
    """Return a small sample from a table (max 100 rows)."""
    # Enforce guardrails
    limit = min(limit, 100)

    if not schema_name.isalnum() or not table_name.isalnum():
        return [TextContent(type="text", text="Error: Invalid schema or table name")]

    rows = execute_query(
        f"SELECT * FROM {schema_name}.{table_name} LIMIT {limit}"
    )
    return [TextContent(type="text", text=format_results(rows))]

@app.tool()
async def run_read_only_query(sql: str) -> list[TextContent]:
    """
    Execute a read-only SQL query with guardrails.

    Tier 1 only. Query is validated before execution:
    - Must be SELECT (no DDL/DML)
    - Must include LIMIT clause (max 1000)
    - Must not reference blocked schemas/tables
    - Has 30-second timeout
    """
    validation = validate_query(sql)
    if not validation.is_valid:
        return [TextContent(type="text", text=f"Query rejected: {validation.reason}")]

    try:
        results = execute_query(sql, timeout=30)
        return [TextContent(type="text", text=format_results(results))]
    except Exception as e:
        return [TextContent(type="text", text=f"Query error: {str(e)}")]
```

### Tool Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Least privilege** | Separate tools for metadata vs data access. Don't bundle schema browsing with query execution. |
| **Input validation** | Validate all user inputs. Prevent SQL injection via parameterized queries or allowlists. |
| **Output limiting** | Always enforce row limits. Truncate large results. Never stream unbounded results. |
| **Audit logging** | Log every tool invocation with: who (agent), what (tool + params), when, result summary. |
| **Graceful degradation** | Return helpful error messages. Don't expose stack traces or connection strings. |
| **Progressive disclosure** | Offer metadata tools first. Gate data access tools behind explicit configuration. |

For detailed MCP server patterns (multi-warehouse, connection pooling, context management), see [MCP Data Patterns Reference →](references/mcp-data-patterns.md)

---

## NL-to-SQL Patterns

Natural-language-to-SQL translates user questions into warehouse queries. This is the most common AI-data integration pattern.

### Schema Context Injection

The key to accurate NL-to-SQL is providing the right schema context to the LLM:

```python
import anthropic
import os

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export ANTHROPIC_API_KEY="sk-ant-xxx"
# Configure: export SNOWFLAKE_ACCOUNT (for metadata queries)
# ─────────────────────────────────────────────────────────────────────

def build_schema_context(tables: list[str]) -> str:
    """Build schema context string for NL-to-SQL prompt."""
    context_parts = []
    for table in tables:
        columns = get_table_columns(table)  # From INFORMATION_SCHEMA
        col_descriptions = []
        for col in columns:
            desc = f"  - {col['name']} ({col['type']})"
            if col.get("comment"):
                desc += f" -- {col['comment']}"
            col_descriptions.append(desc)

        context_parts.append(
            f"Table: {table}\n"
            f"Columns:\n" + "\n".join(col_descriptions)
        )

    return "\n\n".join(context_parts)

def generate_sql(question: str, schema_context: str) -> str:
    """Generate SQL from natural language question."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system="""You are a SQL expert. Generate a single SQL query that answers the user's question.

Rules:
- Use only the tables and columns provided in the schema context
- Always include a LIMIT clause (default 100, max 1000)
- Use explicit column names (never SELECT *)
- Add comments explaining complex logic
- Return ONLY the SQL query, no explanation""",
        messages=[{
            "role": "user",
            "content": f"""Schema context:
{schema_context}

Question: {question}

Generate SQL:"""
        }],
    )

    return response.content[0].text.strip()
```

### Query Validation

Always validate AI-generated SQL before execution:

```python
import sqlglot

def validate_generated_sql(
    sql: str,
    allowed_schemas: list[str],
    max_limit: int = 1000,
) -> tuple[bool, str]:
    """Validate AI-generated SQL meets guardrails."""
    try:
        parsed = sqlglot.parse_one(sql)
    except sqlglot.errors.ParseError as e:
        return False, f"Invalid SQL syntax: {e}"

    # Must be a SELECT statement
    if parsed.key != "select":
        return False, "Only SELECT queries are allowed"

    # Must have LIMIT clause
    limit_node = parsed.find(sqlglot.exp.Limit)
    if not limit_node:
        return False, "Query must include a LIMIT clause"

    limit_value = int(limit_node.expression.this)
    if limit_value > max_limit:
        return False, f"LIMIT {limit_value} exceeds maximum of {max_limit}"

    # Check table references against allowlist
    for table in parsed.find_all(sqlglot.exp.Table):
        schema = (table.db or "").upper()
        if schema and schema not in [s.upper() for s in allowed_schemas]:
            return False, f"Schema '{schema}' is not in allowed list"

    # No subqueries that bypass limits
    subqueries = list(parsed.find_all(sqlglot.exp.Subquery))
    if len(subqueries) > 3:
        return False, "Too many subqueries (max 3)"

    return True, "Valid"
```

For comprehensive NL-to-SQL patterns (few-shot examples, query caching, evaluation), see [NL-to-SQL Patterns Reference →](references/nl-to-sql-patterns.md)

---

## LLM-Powered Transformations

Use LLMs for transforms that are difficult with traditional code: classification, extraction from unstructured text, enrichment, and data quality assessment.

### When to Use LLM Transforms

| Use LLM When | Use Traditional Code When |
|--------------|--------------------------|
| Classifying free-text into categories | Categories map to simple rules or keywords |
| Extracting entities from unstructured text | Data has consistent structure (regex works) |
| Enriching records with world knowledge | Enrichment comes from a lookup table or API |
| Assessing data quality of text fields | Quality checks are numeric/null/format-based |
| Resolving ambiguous entity matches | Exact or fuzzy string matching suffices |

### Batch Classification Pattern

```python
import anthropic
from pydantic import BaseModel
from typing import Literal
import json

class ClassificationResult(BaseModel):
    id: str
    category: Literal["bug", "feature", "question", "docs", "other"]
    confidence: float

def classify_batch(
    records: list[dict],
    batch_size: int = 50,
) -> list[ClassificationResult]:
    """Classify records in batches for cost efficiency."""
    client = anthropic.Anthropic()
    results = []

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        # Format batch for single LLM call
        batch_text = "\n".join(
            f"[{r['id']}] {r['title']}: {r['description'][:200]}"
            for r in batch
        )

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # Use cheapest model for classification
            max_tokens=2048,
            system="""Classify each item into exactly one category: bug, feature, question, docs, other.
Return JSON array: [{"id": "...", "category": "...", "confidence": 0.0-1.0}]""",
            messages=[{"role": "user", "content": batch_text}],
        )

        batch_results = json.loads(response.content[0].text)
        results.extend(
            ClassificationResult.model_validate(r) for r in batch_results
        )

    return results
```

### Cost-Efficient LLM Pipeline

```python
import polars as pl

def enrich_with_llm(
    df: pl.DataFrame,
    text_column: str,
    output_column: str,
    prompt_template: str,
    cache_path: str = "llm_cache.parquet",
) -> pl.DataFrame:
    """
    LLM enrichment with caching to minimize API costs.

    1. Check cache for previously enriched records
    2. Only call LLM for new/uncached records
    3. Batch LLM calls for efficiency
    4. Save results to cache
    """
    # Load cache
    try:
        cache = pl.read_parquet(cache_path)
        cached_keys = set(cache[text_column].to_list())
    except FileNotFoundError:
        cache = pl.DataFrame()
        cached_keys = set()

    # Filter to uncached records
    uncached = df.filter(~pl.col(text_column).is_in(list(cached_keys)))

    if uncached.height == 0:
        # All cached — just join
        return df.join(cache.select(text_column, output_column), on=text_column, how="left")

    # Call LLM for uncached records (batched)
    new_results = classify_batch(uncached.to_dicts())

    # Update cache
    new_cache_rows = pl.DataFrame([
        {text_column: r.id, output_column: r.category}
        for r in new_results
    ])
    updated_cache = pl.concat([cache, new_cache_rows]) if cache.height > 0 else new_cache_rows
    updated_cache.write_parquet(cache_path)

    # Join enrichment back
    return df.join(updated_cache.select(text_column, output_column), on=text_column, how="left")
```

For more LLM transform patterns (entity extraction, data quality assessment, structured output), see [LLM Transform Patterns Reference →](references/llm-transform-patterns.md)

---

## Embeddings for Data Discovery

Use embeddings to make your data platform searchable by meaning, not just keywords.

### Use Cases

| Use Case | Description | Value |
|----------|-------------|-------|
| **Data catalog search** | "Find tables related to customer churn" | Discover relevant tables by semantic meaning |
| **Column matching** | Match columns across systems by meaning, not name | `cust_id` = `customer_identifier` = `client_no` |
| **Documentation search** | RAG over dbt docs, data dictionaries, runbooks | Answer "how is revenue calculated?" from docs |
| **Query suggestion** | Find similar past queries for a new question | Reuse validated SQL instead of generating new |

### Data Catalog Embedding Pipeline

```python
import anthropic
import numpy as np
from typing import Optional

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export ANTHROPIC_API_KEY="sk-ant-xxx" (or use Voyage/OpenAI)
# Configure: export VECTOR_DB_URL="..." (if using external vector store)
# ─────────────────────────────────────────────────────────────────────

def embed_table_metadata(tables: list[dict]) -> list[dict]:
    """Create embeddings for table metadata (schema + descriptions)."""
    client = anthropic.Anthropic()
    results = []

    for table in tables:
        # Build rich text representation of table
        text = (
            f"Table: {table['schema']}.{table['name']}\n"
            f"Description: {table.get('description', 'No description')}\n"
            f"Columns: {', '.join(c['name'] for c in table['columns'])}\n"
            f"Column details: {'; '.join(f'{c[\"name\"]} ({c[\"type\"]}): {c.get(\"description\", \"\")}' for c in table['columns'])}"
        )

        # Generate embedding (use your preferred provider)
        embedding = generate_embedding(text)

        results.append({
            "table_fqn": f"{table['schema']}.{table['name']}",
            "text": text,
            "embedding": embedding,
        })

    return results

def search_tables(query: str, table_embeddings: list[dict], top_k: int = 5) -> list[dict]:
    """Find tables most relevant to a natural language query."""
    query_embedding = generate_embedding(query)

    # Cosine similarity
    scored = []
    for te in table_embeddings:
        similarity = np.dot(query_embedding, te["embedding"]) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(te["embedding"])
        )
        scored.append({**te, "similarity": similarity})

    return sorted(scored, key=lambda x: x["similarity"], reverse=True)[:top_k]
```

For more embeddings patterns (vector stores, chunking strategies, RAG over documentation), see [Embeddings Pipelines Reference →](references/embeddings-pipelines.md)

---

## Security Posture

This skill generates code that integrates AI/LLMs with data systems. **This is the highest-risk skill in the suite** — AI accessing production data requires careful guardrails.
See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full security framework.

**Credentials required**: LLM API keys, warehouse connections (read-only), vector database access
**Where to configure**: Environment variables for all secrets. Separate credentials for AI access vs human access.
**Minimum role/permissions**: Read-only warehouse role scoped to specific schemas. Separate service account for AI queries.

### By Security Tier

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| Code generation (Level 0) | Yes | Yes | Yes |
| Metadata access (Level 1) | Yes (dev/staging) | Schema metadata only, human approval | No — provide schemas manually |
| Sample data access (Level 2) | Yes (dev data, 10-100 rows) | Synthetic/anonymized samples only | No data access |
| Query execution (Level 3) | Dev/staging with guardrails | No | No |
| NL-to-SQL generation | Generate and execute (dev) | Generate for review | Generate for review |
| LLM enrichment | Process dev data | Process anonymized data | Generate code only |
| MCP server deployment | Dev/staging | Metadata-only tools | Not deployed |
| Embeddings pipeline | Embed metadata + data | Embed metadata only | Embed documentation only |

### AI-Specific Credential Rules

1. **Separate service accounts**: AI agents use a different warehouse account than human users
2. **Read-only roles**: AI warehouse roles have no INSERT/UPDATE/DELETE/DDL permissions
3. **Schema scoping**: AI roles can only access approved schemas (`STAGING`, `MARTS` — never `RAW` or `PII`)
4. **Query logging**: All AI-initiated queries are logged with the originating prompt for audit
5. **Cost controls**: Set warehouse-level credit limits and query timeout for AI service accounts
6. **API key isolation**: LLM API keys for data pipelines are separate from application API keys
7. **Rotation**: Rotate AI service account credentials on shorter cycles than human accounts

### Audit Trail

```sql
-- Snowflake: Create audit table for AI-generated queries
CREATE TABLE IF NOT EXISTS audit.ai_query_log (
    query_id STRING DEFAULT UUID_STRING(),
    agent_id STRING,           -- Which AI agent/MCP server
    prompt_hash STRING,        -- SHA-256 of the originating prompt
    generated_sql STRING,      -- The SQL that was generated
    execution_status STRING,   -- 'approved', 'rejected', 'executed', 'failed'
    result_row_count INTEGER,
    execution_time_ms INTEGER,
    warehouse_credits_used FLOAT,
    reviewed_by STRING,        -- Human reviewer (Tier 2)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

---

## Reference Files

This skill includes detailed reference documentation for deep dives:

- [MCP Data Patterns →](references/mcp-data-patterns.md) — MCP server architecture for warehouses, multi-warehouse support, connection pooling, context management, tool design
- [NL-to-SQL Patterns →](references/nl-to-sql-patterns.md) — Schema context strategies, few-shot examples, query validation, caching, evaluation metrics
- [Embeddings Pipelines →](references/embeddings-pipelines.md) — Vector stores, chunking strategies, data catalog embedding, RAG over documentation
- [LLM Transform Patterns →](references/llm-transform-patterns.md) — Batch processing, entity extraction, classification, structured output, cost optimization
