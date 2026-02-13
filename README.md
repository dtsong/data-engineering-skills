# Data Engineering Skills for Claude Code

[![Claude Skill](https://img.shields.io/badge/Claude-Skill-8A6BFF)](https://github.com/dtsong/data-engineering-skills)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/Skills-6-green.svg)](CATALOG.md)

> Expert-level Claude Code skills for data engineering: dbt, Fivetran, Kafka, Airflow, Snowflake, and more.

This repository contains a curated suite of skills that enable Claude Code to provide expert guidance for data engineering workflows. Whether you're building data pipelines, modeling in dbt, integrating SaaS tools, or streaming events with Kafka, these skills help Claude understand your context and provide detailed, actionable guidance.

**What problem does this solve?** Data engineering involves many specialized tools (dbt, Fivetran, Kafka, Airflow, Snowflake, BigQuery, etc.) with deep best practices. These skills give Claude the domain expertise to help you make decisions, write code, debug issues, and architect solutions across the modern data stack.

---

## What Are You Trying to Do?

Find your use case below and install the corresponding skill:

| I want to... | Use this skill | Status |
|--------------|---------------|--------|
| Connect **Salesforce, NetSuite, Stripe, or HubSpot** to my data warehouse | [integration-patterns-skill](integration-patterns-skill/) | Available |
| Set up **Fivetran or Airbyte** connectors | [integration-patterns-skill](integration-patterns-skill/) | Available |
| Build **real-time streaming pipelines** with Kafka or Flink | [streaming-data-skill](streaming-data-skill/) | Available |
| Stream data into **Snowflake, BigQuery, or Databricks** | [streaming-data-skill](streaming-data-skill/) | Available |
| Write **dbt models, tests, and documentation** | [dbt-skill](dbt-skill/) | Available |
| Set up **dbt CI/CD** with slim CI and artifacts | [dbt-skill](dbt-skill/) | Available |
| Optimize **dbt performance** (incremental models, materializations) | [dbt-skill](dbt-skill/) | Available |
| Write **Python for data engineering** (dbt-py, PySpark, Pandas, API scripts) | python-data-engineering-skill | Planned (Q2 2026) |
| Design **Airflow or Dagster** DAGs | data-orchestration-skill | Planned (Q2 2026) |
| Schedule and monitor **data pipelines** | data-orchestration-skill | Planned (Q2 2026) |
| Use **AI/LLMs in data workflows** (embeddings, semantic search, MCP) | ai-data-integration-skill | Planned (Q3 2026) |
| Choose between **Snowflake, BigQuery, Databricks, or DuckDB** | [shared-references/warehouse-comparison](shared-references/data-engineering/warehouse-comparison.md) | Available |
| Implement **data quality checks** (freshness, completeness, accuracy) | [shared-references/data-quality-patterns](shared-references/data-engineering/data-quality-patterns.md) | Available |

**Don't see your use case?** Check the full [Catalog](CATALOG.md) or open an [issue](https://github.com/dtsong/data-engineering-skills/issues) to request a new skill.

---

## Quick Install

### Option 1: Install All Skills (Recommended for Platform Engineers)

```bash
git clone https://github.com/dtsong/data-engineering-skills
cd data-engineering-skills
./install.sh
```

This installs all available skills to `~/.claude/skills/data-engineering-skills/`.

### Option 2: Install by Role

```bash
./install.sh --role analytics-engineer
./install.sh --role data-platform-engineer
./install.sh --role integration-engineer
./install.sh --role ml-engineer
```

See [Role-Based Presets](#role-based-presets) below for what each role includes.

### Option 3: Install Specific Skills

```bash
./install.sh --skills dbt-skill,streaming-data-skill
./install.sh --skills integration-patterns-skill
```

### Option 4: Manual Install

```bash
git clone https://github.com/dtsong/data-engineering-skills ~/.claude/skills/data-engineering-skills
```

### Update Existing Installation

```bash
cd ~/.claude/skills/data-engineering-skills
git pull
```

Or use the installer:

```bash
./install.sh --update
```

---

## Role-Based Presets

Not sure which skills to install? We've created presets for common roles:

| Role | Skills Installed | Description |
|------|-----------------|-------------|
| **analytics-engineer** | dbt-skill, python-data-engineering-skill | Transform and model data using SQL and Python |
| **data-platform-engineer** | All skills | Full toolkit for building and maintaining data platforms |
| **integration-engineer** | integration-patterns-skill, streaming-data-skill, data-orchestration-skill | Connect systems, orchestrate pipelines, handle real-time data |
| **ml-engineer** | python-data-engineering-skill, ai-data-integration-skill | Python-first workflows, AI/ML pipelines |

**Example**:
```bash
./install.sh --role analytics-engineer
```

This installs:
- dbt-skill (modeling, testing, CI/CD, performance)
- python-data-engineering-skill (dbt-py, Pandas, PySpark, API scripts)
- Shared references (data-quality-patterns, warehouse-comparison)

---

## How Skills Work

Skills are **prompt templates** that give Claude deep domain knowledge. Here's how they work:

1. **Auto-activation**: When you mention keywords like "dbt", "Fivetran", "Kafka", or "Airflow", Claude automatically loads the relevant skill.
2. **Progressive disclosure**: Skills provide core guidance first, then offer references for deep dives (e.g., "See dbt-testing-guide.md for 30+ test examples").
3. **No manual activation needed**: You don't need to explicitly invoke skills—just start asking questions.
4. **Context-aware**: Skills know when to activate based on your conversation, file context, and project structure.

**Example conversation**:

> **You**: "Help me write a dbt staging model for Stripe charges"
>
> **Claude** (dbt-skill auto-activates): "I'll help you create a staging model following dbt best practices. Here's a model that handles Stripe's nested JSON structure and adds data quality tests..."

---

## Suite Overview

### Available Skills

| Skill | Description | Lines | Files |
|-------|-------------|-------|-------|
| [dbt-skill](dbt-skill/) | dbt modeling, testing, incremental strategies, CI/CD, performance, governance | 3,000 | 7 |
| [integration-patterns-skill](integration-patterns-skill/) | Fivetran, Airbyte, API extraction, CDC, Reverse ETL, enterprise connectors | 2,000 | 5 |
| [streaming-data-skill](streaming-data-skill/) | Kafka, Flink, Spark Streaming, warehouse streaming, event architectures | 2,500 | 6 |

### Planned Skills (Phase 2-3)

| Skill | Description | Target Date |
|-------|-------------|-------------|
| data-orchestration-skill | Airflow, Dagster, Prefect, DAG design, scheduling, monitoring | Q2 2026 |
| python-data-engineering-skill | dbt-py, Pandas/Polars, PySpark, API scripts, data validation | Q2 2026 |
| ai-data-integration-skill | AI agents for data, MCP modules, embeddings, LLM transformations | Q3 2026 |

### Shared References

| Reference | Description | Lines |
|-----------|-------------|-------|
| [data-quality-patterns](shared-references/data-engineering/data-quality-patterns.md) | Tool-agnostic quality frameworks (four pillars, anomaly detection, alerting) | 300 |
| [warehouse-comparison](shared-references/data-engineering/warehouse-comparison.md) | Snowflake vs BigQuery vs Databricks vs DuckDB decision matrix | 300 |

See full details in [CATALOG.md](CATALOG.md).

---

## Examples

### Example 1: Setting up Fivetran for Salesforce

```bash
./install.sh --skills integration-patterns-skill
```

Then ask Claude:

> "How do I set up Fivetran to sync Salesforce to Snowflake with incremental updates?"

**Skill activates**: integration-patterns-skill

**Claude provides**:
1. Fivetran connector setup steps
2. Schema mapping guidance
3. Incremental sync configuration
4. Data quality checks for Salesforce data
5. Common gotchas (API limits, field changes)

### Example 2: Writing dbt Models with Tests

```bash
./install.sh --skills dbt-skill
```

Then ask Claude:

> "Help me write a dbt mart model that calculates customer lifetime value with data quality tests"

**Skill activates**: dbt-skill

**Claude provides**:
1. Mart model structure following best practices
2. LTV calculation logic
3. Data quality tests (uniqueness, not-null, ranges)
4. Performance optimization (incremental strategy if needed)
5. Documentation template

### Example 3: Building a Kafka Pipeline

```bash
./install.sh --skills streaming-data-skill
```

Then ask Claude:

> "How do I stream orders from PostgreSQL to BigQuery using Kafka Connect?"

**Skill activates**: streaming-data-skill

**Claude provides**:
1. Kafka Connect source connector config (Debezium for PostgreSQL CDC)
2. Kafka Connect sink connector config (BigQuery)
3. Schema evolution handling
4. Monitoring and alerting setup
5. Error handling and dead letter queue configuration

---

## Contributing

We welcome contributions! Here's how you can help:

### Report Issues or Request Features

Open an issue at [github.com/dtsong/data-engineering-skills/issues](https://github.com/dtsong/data-engineering-skills/issues)

**Examples**:
- "Add Prefect guidance to data-orchestration-skill"
- "Include Polars examples in python-data-engineering-skill"
- "Bug: dbt incremental strategy example has incorrect syntax"

### Submit Pull Requests

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Adding new reference files
- Improving existing skills
- Creating new skills
- Updating documentation

**PR requirements**:
- Link to a GitHub issue (required)
- Clear description of changes
- Examples/tests if applicable
- Follow existing structure and style

### Share Feedback

Tell us how these skills are working for you! Open a discussion at [github.com/dtsong/data-engineering-skills/discussions](https://github.com/dtsong/data-engineering-skills/discussions)

---

## Roadmap

### Phase 1: Core Skills (Complete)
- dbt-skill
- integration-patterns-skill
- streaming-data-skill
- Shared references (data-quality-patterns, warehouse-comparison)

### Phase 2: Orchestration & Python (Q2 2026)
- data-orchestration-skill (Airflow, Dagster, Prefect)
- python-data-engineering-skill (dbt-py, Pandas, PySpark, API scripts)

### Phase 3: AI & Advanced Topics (Q3 2026)
- ai-data-integration-skill (AI agents, MCP, embeddings)
- Advanced streaming patterns (ksqlDB, Flink SQL, event sourcing)

### Phase 4: Governance & Observability (Q4 2026)
- data-governance-skill (cataloging, lineage, access control)
- data-observability-skill (monitoring, alerting, incident response)

---

## License

Apache License 2.0

Copyright 2026 Daniel Song

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at:

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

See [LICENSE](LICENSE) for full text.

---

## Related Resources

- **Claude Code**: [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code)
- **dbt**: [docs.getdbt.com](https://docs.getdbt.com/)
- **Fivetran**: [fivetran.com/docs](https://fivetran.com/docs)
- **Airbyte**: [docs.airbyte.com](https://docs.airbyte.com/)
- **Apache Kafka**: [kafka.apache.org/documentation](https://kafka.apache.org/documentation/)
- **Apache Airflow**: [airflow.apache.org/docs](https://airflow.apache.org/docs/)
- **Dagster**: [docs.dagster.io](https://docs.dagster.io/)
- **Snowflake**: [docs.snowflake.com](https://docs.snowflake.com/)
- **BigQuery**: [cloud.google.com/bigquery/docs](https://cloud.google.com/bigquery/docs)
- **Databricks**: [docs.databricks.com](https://docs.databricks.com/)

---

## Questions?

- **Issues/Features**: [github.com/dtsong/data-engineering-skills/issues](https://github.com/dtsong/data-engineering-skills/issues)
- **Discussions**: [github.com/dtsong/data-engineering-skills/discussions](https://github.com/dtsong/data-engineering-skills/discussions)
- **Email**: Available in GitHub profile

---

**Happy data engineering!** 🚀
