# NL-to-SQL Patterns Reference

> Natural language to SQL generation with guardrails, evaluation, and caching. Part of the [AI Data Integration Skill](../SKILL.md).

---

## Schema Context Strategies

The quality of NL-to-SQL depends heavily on the schema context provided to the LLM. Too little context → inaccurate SQL. Too much → context window waste and confusion.

### Strategy 1: Full Schema (Small Warehouses)

```python
def full_schema_context(allowed_schemas: list[str]) -> str:
    """Include all tables and columns. Works for < 50 tables."""
    context = []
    for schema in allowed_schemas:
        tables = get_tables(schema)
        for table in tables:
            columns = get_columns(schema, table)
            col_lines = [f"  {c['name']} {c['type']}" for c in columns]
            context.append(f"-- {schema}.{table}\n" + "\n".join(col_lines))
    return "\n\n".join(context)
```

### Strategy 2: Relevant Tables (Medium Warehouses)

```python
def relevant_schema_context(
    question: str,
    table_embeddings: list[dict],
    top_k: int = 8,
) -> str:
    """Use embeddings to find relevant tables. Works for 50-500 tables."""
    # Embed the question
    q_embedding = generate_embedding(question)

    # Find most similar tables
    scored = []
    for te in table_embeddings:
        sim = cosine_similarity(q_embedding, te["embedding"])
        scored.append((te, sim))

    top_tables = sorted(scored, key=lambda x: x[1], reverse=True)[:top_k]

    context = []
    for table, score in top_tables:
        context.append(f"-- {table['fqn']} (relevance: {score:.2f})\n{table['ddl']}")

    return "\n\n".join(context)
```

### Strategy 3: Two-Pass (Large Warehouses)

```python
def two_pass_context(question: str) -> str:
    """
    Two-pass approach for large warehouses (500+ tables).

    Pass 1: LLM selects relevant tables from a summary list
    Pass 2: Full column details for selected tables only
    """
    # Pass 1: Table summary (name + description only)
    table_summaries = get_all_table_summaries()  # "schema.table: description"
    summary_text = "\n".join(table_summaries)

    client = anthropic.Anthropic()
    selection = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Fast + cheap for selection
        max_tokens=256,
        system="Given the user question, select the 3-8 most relevant tables. Return only table names, one per line.",
        messages=[{"role": "user", "content": f"Tables:\n{summary_text}\n\nQuestion: {question}"}],
    )

    selected_tables = selection.content[0].text.strip().split("\n")

    # Pass 2: Full schema for selected tables
    context = []
    for table_fqn in selected_tables:
        schema, table = table_fqn.strip().split(".")
        columns = get_columns(schema, table)
        col_lines = [f"  {c['name']} {c['type']}" + (f" -- {c['comment']}" if c.get("comment") else "")
                     for c in columns]
        context.append(f"-- {table_fqn}\n" + "\n".join(col_lines))

    return "\n\n".join(context)
```

---

## Few-Shot Examples

Including example question → SQL pairs dramatically improves accuracy:

```python
FEW_SHOT_EXAMPLES = [
    {
        "question": "What are the top 10 customers by revenue this year?",
        "sql": """SELECT
    c.customer_id,
    c.name,
    SUM(o.amount) as total_revenue
FROM marts.dim_customers c
JOIN marts.fct_orders o ON c.customer_id = o.customer_id
WHERE o.order_date >= DATE_TRUNC('year', CURRENT_DATE())
GROUP BY c.customer_id, c.name
ORDER BY total_revenue DESC
LIMIT 10"""
    },
    {
        "question": "How many orders were placed each month in 2024?",
        "sql": """SELECT
    DATE_TRUNC('month', order_date) as month,
    COUNT(*) as order_count,
    SUM(amount) as total_revenue
FROM marts.fct_orders
WHERE order_date >= '2024-01-01' AND order_date < '2025-01-01'
GROUP BY month
ORDER BY month
LIMIT 100"""
    },
]

def build_few_shot_prompt(question: str, schema_context: str) -> str:
    """Build NL-to-SQL prompt with few-shot examples."""
    examples = "\n\n".join(
        f"Question: {ex['question']}\nSQL:\n{ex['sql']}"
        for ex in FEW_SHOT_EXAMPLES
    )

    return f"""You are a SQL expert. Generate a single SQL query for the given question.

Schema:
{schema_context}

Examples:
{examples}

Rules:
- Use only tables and columns from the schema
- Always include LIMIT (default 100, max 1000)
- Use explicit column names (never SELECT *)
- Use table aliases for readability
- Add comments for complex logic

Question: {question}

SQL:"""
```

---

## Query Validation with sqlglot

```python
import sqlglot
from sqlglot import exp

def validate_and_fix_sql(
    sql: str,
    dialect: str = "snowflake",
    allowed_schemas: list[str] = None,
    max_limit: int = 1000,
) -> tuple[str, list[str]]:
    """
    Validate and auto-fix common issues in AI-generated SQL.

    Returns (fixed_sql, warnings).
    """
    warnings = []

    try:
        parsed = sqlglot.parse_one(sql, dialect=dialect)
    except sqlglot.errors.ParseError as e:
        raise ValueError(f"Invalid SQL: {e}")

    # Must be SELECT
    if not isinstance(parsed, exp.Select):
        raise ValueError("Only SELECT statements are allowed")

    # Check for blocked operations
    for node_type in [exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create]:
        if parsed.find(node_type):
            raise ValueError(f"Blocked operation: {node_type.__name__}")

    # Enforce LIMIT
    limit_node = parsed.find(exp.Limit)
    if not limit_node:
        # Auto-add LIMIT
        parsed = parsed.limit(max_limit)
        warnings.append(f"Added LIMIT {max_limit} (was missing)")
    else:
        limit_val = int(limit_node.expression.this)
        if limit_val > max_limit:
            parsed = parsed.limit(max_limit)
            warnings.append(f"Reduced LIMIT from {limit_val} to {max_limit}")

    # Validate table references
    if allowed_schemas:
        for table in parsed.find_all(exp.Table):
            db = str(table.db).upper() if table.db else None
            if db and db not in [s.upper() for s in allowed_schemas]:
                raise ValueError(f"Access to schema '{db}' is not allowed")

    return parsed.sql(dialect=dialect), warnings
```

---

## Query Caching

Cache NL-to-SQL results to avoid redundant LLM calls:

```python
import hashlib
import json
from pathlib import Path

class NLSQLCache:
    """Cache NL-to-SQL results by question + schema hash."""

    def __init__(self, cache_dir: str = ".nlsql_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _key(self, question: str, schema_hash: str) -> str:
        content = f"{question.strip().lower()}:{schema_hash}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(self, question: str, schema_hash: str) -> str | None:
        """Return cached SQL if available."""
        key = self._key(question, schema_hash)
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            return data["sql"]
        return None

    def put(self, question: str, schema_hash: str, sql: str):
        """Cache a NL-to-SQL result."""
        key = self._key(question, schema_hash)
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({
            "question": question,
            "sql": sql,
            "schema_hash": schema_hash,
        }))

# Usage
cache = NLSQLCache()
cached = cache.get(question, schema_hash)
if cached:
    sql = cached
else:
    sql = generate_sql(question, schema_context)
    cache.put(question, schema_hash, sql)
```

---

## Evaluation Metrics

### Execution Accuracy

```python
def evaluate_nl_to_sql(
    test_cases: list[dict],  # [{"question": ..., "expected_sql": ..., "expected_result": ...}]
    generator_fn,
    executor_fn,
) -> dict:
    """Evaluate NL-to-SQL accuracy."""
    results = {
        "total": len(test_cases),
        "valid_sql": 0,       # Parses without error
        "executes": 0,        # Runs without error
        "correct_result": 0,  # Returns expected result
    }

    for case in test_cases:
        generated_sql = generator_fn(case["question"])

        # Check 1: Valid SQL
        try:
            sqlglot.parse_one(generated_sql)
            results["valid_sql"] += 1
        except Exception:
            continue

        # Check 2: Executes
        try:
            actual_result = executor_fn(generated_sql)
            results["executes"] += 1
        except Exception:
            continue

        # Check 3: Correct result
        if compare_results(actual_result, case["expected_result"]):
            results["correct_result"] += 1

    results["valid_sql_rate"] = results["valid_sql"] / results["total"]
    results["execution_rate"] = results["executes"] / results["total"]
    results["accuracy"] = results["correct_result"] / results["total"]

    return results
```

### Golden Dataset

```python
# Maintain a golden dataset of question → SQL pairs for regression testing
GOLDEN_DATASET = [
    {
        "question": "How many active customers do we have?",
        "expected_sql": "SELECT COUNT(*) FROM marts.dim_customers WHERE is_active = TRUE LIMIT 100",
        "expected_columns": ["count"],
        "expected_row_count": 1,
        "tags": ["aggregation", "simple"],
    },
    {
        "question": "What is the average order value by product category?",
        "expected_sql": """
            SELECT p.category, AVG(o.amount) as avg_order_value
            FROM marts.fct_orders o
            JOIN marts.dim_products p ON o.product_id = p.product_id
            GROUP BY p.category
            ORDER BY avg_order_value DESC
            LIMIT 100
        """,
        "expected_columns": ["category", "avg_order_value"],
        "tags": ["aggregation", "join"],
    },
]
```

---

## Error Recovery

```python
def generate_sql_with_retry(
    question: str,
    schema_context: str,
    executor_fn,
    max_attempts: int = 3,
) -> tuple[str, list[dict]]:
    """Generate SQL with error-driven retry."""
    attempts = []

    for attempt in range(max_attempts):
        sql = generate_sql(
            question,
            schema_context,
            previous_errors=[a.get("error") for a in attempts],
        )

        try:
            # Validate
            sql, warnings = validate_and_fix_sql(sql)

            # Execute
            result = executor_fn(sql)
            attempts.append({"sql": sql, "status": "success", "warnings": warnings})
            return sql, attempts

        except Exception as e:
            attempts.append({"sql": sql, "status": "error", "error": str(e)})

    raise ValueError(f"Failed after {max_attempts} attempts: {attempts}")

def generate_sql(question: str, schema_context: str, previous_errors: list[str] = None) -> str:
    """Generate SQL, incorporating previous error feedback."""
    error_context = ""
    if previous_errors:
        error_context = "\n\nPrevious attempts failed with these errors. Avoid these mistakes:\n"
        error_context += "\n".join(f"- {e}" for e in previous_errors if e)

    # Pass error context to LLM for self-correction
    prompt = build_few_shot_prompt(question, schema_context) + error_context
    return call_llm(prompt)
```
