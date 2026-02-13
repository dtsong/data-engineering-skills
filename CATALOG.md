# Data Engineering Skills Catalog

> A curated library of Claude Code skills for data engineering. Each skill provides expert-level guidance for a specific domain.

---

## How to Use This Catalog

1. **Find the skill** that matches your problem (see table below)
2. **Install** the full suite or individual skills using [install.sh](install.sh)
3. **Skills auto-activate** when Claude detects relevant keywords in your conversation
4. **Progressive disclosure**: Skills provide core guidance first, then reference deep-dive materials on request

---

## Skills by Category

### Data Transformation

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [dbt-skill](dbt-skill/) | Standalone | dbt modeling, testing, incremental strategies, CI/CD, performance optimization, governance | **Available** |

**Use when**: Writing SQL transformations, building data models, implementing data quality tests, setting up dbt projects.

### Data Integration

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [integration-patterns-skill](integration-patterns-skill/) | Standalone | iPaaS platforms (Fivetran, Airbyte), API extraction, CDC, webhooks, Reverse ETL, enterprise connectors (Salesforce, NetSuite, Stripe) | **Available** |
| [streaming-data-skill](streaming-data-skill/) | Standalone | Kafka, Flink, Spark Streaming, warehouse streaming (Snowpipe, BigQuery streaming), event architectures | **Available** |

**Use when**: Connecting SaaS tools to warehouses, building real-time data pipelines, implementing CDC, handling event streams.

### Data Orchestration

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [data-orchestration-skill](data-orchestration-skill/) | Standalone | Airflow, Dagster, Prefect, DAG design, scheduling, monitoring, alerting | **Planned (Phase 2)** |

**Use when**: Scheduling pipelines, designing DAGs, implementing retries and alerts, orchestrating multi-step workflows.

### Data Engineering with Python

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [python-data-engineering-skill](python-data-engineering-skill/) | Standalone | dbt Python models, Pandas/Polars transformations, PySpark, API extraction scripts, data validation | **Planned (Phase 2)** |

**Use when**: Writing Python transformations, building custom extractors, processing data with Pandas/Polars/PySpark.

### AI & Data

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [ai-data-integration-skill](ai-data-integration-skill/) | Standalone | AI agents for data workflows, MCP server modules, embeddings pipelines, LLM-powered transformations | **Planned (Phase 3)** |

**Use when**: Building AI-powered data workflows, implementing semantic search, using LLMs for data enrichment.

---

## Shared References

| Resource | Description | Referenced By |
|----------|-------------|---------------|
| [data-quality-patterns](shared-references/data-engineering/data-quality-patterns.md) | Tool-agnostic quality frameworks (four pillars, anomaly detection, alerting matrix) | dbt-skill, python-data-engineering-skill, streaming-data-skill |
| [warehouse-comparison](shared-references/data-engineering/warehouse-comparison.md) | Decision matrix: Snowflake vs BigQuery vs Databricks vs DuckDB | dbt-skill, integration-patterns-skill, streaming-data-skill |

**Use when**: Choosing a warehouse platform, implementing data quality checks, understanding cross-platform trade-offs.

---

## Skill Sizing

| Skill | Core Lines | Reference Lines | Total Lines | File Count | Status |
|-------|------------|-----------------|-------------|------------|--------|
| dbt-skill | 1,200 | 1,800 | 3,000 | 7 | Available |
| integration-patterns-skill | 800 | 1,200 | 2,000 | 5 | Available |
| streaming-data-skill | 1,000 | 1,500 | 2,500 | 6 | Available |
| data-orchestration-skill | 900 | 1,300 | 2,200 | 5 | Planned |
| python-data-engineering-skill | 1,100 | 1,600 | 2,700 | 6 | Planned |
| ai-data-integration-skill | 700 | 1,000 | 1,700 | 4 | Planned |
| **Shared references** | - | 600 | 600 | 2 | Available |
| **Total** | 5,700 | 9,000 | 14,700 | 35 | - |

**Sizing explanation**:
- **Core lines**: SKILL.md prompt content (always included)
- **Reference lines**: Deep-dive reference files (loaded on demand via progressive disclosure)
- **Total lines**: Sum of core + references
- **File count**: Total files per skill (SKILL.md + references)

---

## Role-Based Recommendations

Not sure which skills to install? Here's what we recommend by role:

| Role | Skills to Install | Why |
|------|------------------|-----|
| **Analytics Engineer** | dbt-skill, python-data-engineering-skill | Transform and model data using SQL and Python |
| **Data Platform Engineer** | All skills | Full toolkit for building and maintaining data platforms |
| **Integration Engineer** | integration-patterns-skill, streaming-data-skill, data-orchestration-skill | Connect systems, orchestrate pipelines, handle real-time data |
| **ML Engineer** | python-data-engineering-skill, ai-data-integration-skill | Python-first workflows, AI/ML pipelines |
| **Data Scientist** | dbt-skill, python-data-engineering-skill | Model data for analysis, write Python transformations |

**Install by role**:
```bash
./install.sh --role analytics-engineer
./install.sh --role data-platform-engineer
./install.sh --role integration-engineer
./install.sh --role ml-engineer
```

---

## Quick Start Examples

### "I want to connect Salesforce to Snowflake"

```bash
./install.sh --skills integration-patterns-skill
```

Then ask Claude:
> "How do I set up Fivetran to sync Salesforce to Snowflake?"

**Skill activates**: integration-patterns-skill detects keywords "Fivetran", "Salesforce", "Snowflake"

### "I need to write dbt models with tests"

```bash
./install.sh --skills dbt-skill
```

Then ask Claude:
> "Help me write a dbt staging model for Stripe charges with data quality tests"

**Skill activates**: dbt-skill detects keywords "dbt", "staging model", "tests"

### "I'm building a real-time pipeline with Kafka"

```bash
./install.sh --skills streaming-data-skill
```

Then ask Claude:
> "How do I set up Kafka Connect to stream orders to BigQuery?"

**Skill activates**: streaming-data-skill detects keywords "Kafka", "stream", "BigQuery"

---

## What's Next?

### Phase 2 (Q2 2026)
- data-orchestration-skill (Airflow, Dagster, Prefect)
- python-data-engineering-skill (dbt-py, Pandas, PySpark, API scripts)

### Phase 3 (Q3 2026)
- ai-data-integration-skill (AI agents, MCP modules, embeddings)

### Phase 4 (Q4 2026)
- data-governance-skill (cataloging, lineage, access control)
- data-observability-skill (monitoring, alerting, incident response)

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to contribute**:
- Report issues or request features via [GitHub Issues](https://github.com/dtsong/data-engineering-skills/issues)
- Submit pull requests for new skills or reference materials
- Share feedback on skill quality and usefulness

---

## License

Apache License 2.0

Copyright 2026 Daniel Song

See [LICENSE](LICENSE) for full text.

---

## Related Resources

- [Claude Code Documentation](https://github.com/anthropics/claude-code)
- [dbt Documentation](https://docs.getdbt.com/)
- [Fivetran Documentation](https://fivetran.com/docs)
- [Airbyte Documentation](https://docs.airbyte.com/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Snowflake Documentation](https://docs.snowflake.com/)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Databricks Documentation](https://docs.databricks.com/)

---

**Questions?** Open an issue at [github.com/dtsong/data-engineering-skills/issues](https://github.com/dtsong/data-engineering-skills/issues)
