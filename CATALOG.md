# Data Engineering Skills Catalog

> A curated library of Claude Code skills for data engineering. Each skill provides expert-level guidance for a specific domain.

---

## How to Use This Catalog

1. **Find the skill** that matches your problem (see table below)
2. **Install** the full suite or individual skills using [install.sh](install.sh)
3. **Skills auto-activate** when Claude detects relevant keywords in your conversation
4. **Progressive disclosure**: Skills provide core guidance first, then reference deep-dive materials on request
5. **Security-first**: All skills follow the [Security & Compliance Patterns](shared-references/data-engineering/security-compliance-patterns.md) framework with three security tiers

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
| [integration-patterns-skill](integration-patterns-skill/) | Standalone | iPaaS platforms (Fivetran, Airbyte), DLT (dlthub), API extraction, CDC, webhooks, Reverse ETL, enterprise connectors (Salesforce, NetSuite, Stripe) | **Available** |
| [streaming-data-skill](streaming-data-skill/) | Standalone | Kafka, Flink, Spark Streaming, warehouse streaming (Snowpipe, BigQuery streaming), event architectures | **Available** |

**Use when**: Connecting SaaS tools to warehouses, building data ingestion pipelines with DLT or iPaaS, implementing CDC, handling event streams.

### Data Orchestration

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [data-orchestration-skill](data-orchestration-skill/) | Standalone | Dagster (assets, resources, sensors), Airflow (DAGs, operators, TaskFlow), Prefect, scheduling, monitoring, dagster-dbt and dagster-dlt integrations | **Phase 1** |

**Use when**: Scheduling pipelines, designing asset-based workflows (Dagster) or DAGs (Airflow), orchestrating dbt + DLT + streaming, implementing retries and alerts.

### Data Engineering with Python

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [python-data-engineering-skill](python-data-engineering-skill/) | Standalone | dbt Python models, Pandas/Polars transformations, PySpark, API extraction scripts, data validation | **Phase 2** |

**Use when**: Writing Python transformations, building custom extractors, processing data with Pandas/Polars/PySpark.

### AI & Data

| Skill | Type | Description | Status |
|-------|------|-------------|--------|
| [ai-data-integration-skill](ai-data-integration-skill/) | Standalone | MCP server patterns for warehouses, NL-to-SQL, embeddings pipelines, LLM-powered transformations, progressive AI integration with security tiers | **Phase 3** |

**Use when**: Building MCP servers for data tools, implementing NL-to-SQL, using LLMs for data enrichment, designing AI-data interaction patterns.

---

## Shared References

| Resource | Description | Referenced By |
|----------|-------------|---------------|
| [data-quality-patterns](shared-references/data-engineering/data-quality-patterns.md) | Tool-agnostic quality frameworks (four pillars, anomaly detection, alerting matrix) | dbt-skill, python-data-engineering-skill, streaming-data-skill |
| [warehouse-comparison](shared-references/data-engineering/warehouse-comparison.md) | Decision matrix: Snowflake vs BigQuery vs Databricks vs DuckDB | All skills |
| [security-compliance-patterns](shared-references/data-engineering/security-compliance-patterns.md) | Three-tier security framework, credential management, data classification, AI-specific risks, compliance patterns (SOC2, HIPAA, PCI, GDPR) | **All skills** |

**Use when**: Choosing a warehouse platform, implementing data quality checks, understanding security requirements, managing credentials across tools.

---

## Skill Sizing

| Skill | Core Lines | Reference Lines | Total Lines | File Count | Status |
|-------|------------|-----------------|-------------|------------|--------|
| dbt-skill | 1,200 | 1,800 | 3,000 | 7 | Available |
| integration-patterns-skill | 800 | 2,000 | 2,800 | 6 | Available (DLT reference added) |
| streaming-data-skill | 1,000 | 1,500 | 2,500 | 6 | Available |
| data-orchestration-skill | 900 | 1,600 | 2,500 | 6 | Phase 1 |
| python-data-engineering-skill | 1,100 | 1,600 | 2,700 | 6 | Phase 2 |
| ai-data-integration-skill | 700 | 1,050 | 1,750 | 5 | Phase 3 |
| **Shared references** | - | 2,000 | 2,000 | 4 | Available |
| **Total** | 5,700 | 11,550 | 17,250 | 40 | - |

**Sizing explanation**:
- **Core lines**: SKILL.md prompt content (always included)
- **Reference lines**: Deep-dive reference files (loaded on demand via progressive disclosure)
- **Total lines**: Sum of core + references
- **File count**: Total files per skill (SKILL.md + references)

---

## Security Tiers

All skills support three security tiers. Choose based on your organization's requirements:

| Tier | Description | AI Can Do | AI Cannot Do |
|------|-------------|-----------|-------------|
| **Tier 1: Cloud-Native** | Standard cloud security | Execute against dev/staging, read sample data | Access production, modify IAM |
| **Tier 2: Regulated** | SOC2/HIPAA/PCI environments | Read schemas/metadata, generate code for review | Execute against production, see row-level data |
| **Tier 3: Air-Gapped** | Maximum restriction | Generate code, SQL, YAML, configs | Connect to any data system |

See [Security & Compliance Patterns](shared-references/data-engineering/security-compliance-patterns.md) for full details.

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

### "I want to ingest data from a REST API using DLT"

```bash
./install.sh --skills integration-patterns-skill
```

Then ask Claude:
> "Help me build a DLT pipeline to ingest data from the GitHub API into Snowflake"

**Skill activates**: integration-patterns-skill detects keywords "DLT", "pipeline", "ingest", "Snowflake"

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

### Phase 0: Security Foundation (Complete)
- Security & Compliance Patterns shared reference
- Security Posture sections added to all existing skills
- Credential management best practices across all code examples

### Phase 1: Orchestration + DLT (Next)
- data-orchestration-skill (Dagster-first, Airflow secondary, dagster-dbt + dagster-dlt integrations)
- DLT reference module added to integration-patterns-skill
- Expanded warehouse-comparison.md (Unity Catalog, Delta Live Tables, DuckDB local dev, Iceberg)

### Phase 2: Python Data Engineering
- python-data-engineering-skill (Polars, Pandas, PySpark, dbt-py, API extraction)

### Phase 3: AI Data Integration
- ai-data-integration-skill (MCP servers, NL-to-SQL, embeddings, LLM transforms)
- AI data patterns shared reference

### Community Expansion
- Additional skills via community PRs (governance, observability, etc.)
- Quality bar: must match existing skill depth and security conventions

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
- [DLT Documentation](https://dlthub.com/docs/)
- [Dagster Documentation](https://docs.dagster.io/)
- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Fivetran Documentation](https://fivetran.com/docs)
- [Airbyte Documentation](https://docs.airbyte.com/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Snowflake Documentation](https://docs.snowflake.com/)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)
- [Databricks Documentation](https://docs.databricks.com/)

---

**Questions?** Open an issue at [github.com/dtsong/data-engineering-skills/issues](https://github.com/dtsong/data-engineering-skills/issues)
