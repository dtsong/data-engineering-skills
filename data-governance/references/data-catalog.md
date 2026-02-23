# Data Catalog Patterns

## Table of Contents

- dbt Docs as Zero-Cost Catalog
- Column-Level Documentation
- Source Metadata Documentation
- Tagging via Meta Config
- External Catalog Tools
- When to Upgrade from dbt Docs

---

## dbt Docs as Zero-Cost Catalog

dbt docs is the default catalog for any project with a dbt layer. Generate and serve locally:

```bash
dbt docs generate
dbt docs serve --port 8080
```

Key advantages: version-controlled, auto-generated lineage graph, zero infrastructure cost.

Configure `dbt_project.yml` for consistent documentation:

```yaml
# dbt_project.yml
models:
  my_project:
    +persist_docs:
      relation: true
      columns: true
```

This pushes column descriptions into the warehouse metadata (Snowflake `COMMENT`, BigQuery `description`).

## Column-Level Documentation

Every column in staging and mart models should have a description. Use schema YAML files:

```yaml
# models/staging/stg_customers.yml
models:
  - name: stg_customers
    description: "Cleaned customer records from source CRM system."
    columns:
      - name: customer_id
        description: "Primary key. Surrogate key generated from source system ID."
        data_tests:
          - unique
          - not_null
      - name: email
        description: "Customer email address. Classification: PII."
        meta:
          classification: pii
          owner: data-engineering
      - name: created_at
        description: "Timestamp when customer record was created in source system."
```

Documentation coverage target: 100% of columns in mart models, 80% of staging models.

## Source Metadata Documentation

Document all source systems with freshness expectations:

```yaml
# models/staging/src_crm.yml
sources:
  - name: crm
    description: "Salesforce CRM data replicated via Fivetran."
    database: raw_db
    schema: crm_salesforce
    loader: fivetran
    loaded_at_field: _fivetran_synced
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    tables:
      - name: accounts
        description: "Account records from Salesforce."
        meta:
          classification: internal
          data_owner: sales-ops
```

## Tagging via Meta Config

Use `meta` for machine-readable governance tags:

```yaml
meta:
  classification: confidential    # public | internal | confidential | restricted
  data_owner: team-name           # owning team
  pii_columns: [email, phone]     # columns containing PII
  retention_days: 730             # data retention policy
  compliance: [gdpr, ccpa]        # applicable regulations
```

Apply at model, column, or source level. Query tags programmatically:

```sql
-- Snowflake: query persisted comments
SELECT table_name, comment
FROM information_schema.tables
WHERE comment ILIKE '%classification%';
```

## External Catalog Tools

When dbt docs are insufficient, consider these tools:

| Tool | Best For | Integration |
|------|----------|-------------|
| OpenMetadata | Open-source, self-hosted, REST API | dbt metadata ingestion connector |
| DataHub | LinkedIn-backed, strong lineage | dbt + Airflow connectors |
| Atlan | Managed SaaS, collaboration features | dbt Cloud native integration |
| Collibra | Enterprise governance, business glossary | API-based ingestion |

Integration pattern for OpenMetadata:

```yaml
# openmetadata_dbt_ingestion.yaml
source:
  type: dbt
  serviceName: my_dbt_project
  sourceConfig:
    config:
      dbtConfigSource:
        dbtCatalogFilePath: target/catalog.json
        dbtManifestFilePath: target/manifest.json
```

## When to Upgrade from dbt Docs

Upgrade from dbt docs to an external catalog when:

1. **Multi-tool lineage** -- Data flows through systems beyond dbt (Spark, Airflow, custom ETL) and you need unified lineage.
2. **Business glossary** -- Business users need to search and discover data assets without dbt knowledge.
3. **Collaboration** -- Multiple teams need to annotate, request access, or discuss data assets.
4. **Automated classification** -- You need ML-based PII detection beyond manual `meta` tags.
5. **Access governance** -- Catalog must integrate with access request workflows.

If none of these apply, dbt docs is sufficient. Do not add infrastructure cost without a documented limitation.
