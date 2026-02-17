## Contents

- [Decision Matrix](#decision-matrix)
- [Decision Flowchart](#decision-flowchart)
- [Consulting Context Factors](#consulting-context-factors)
- [Hybrid Patterns](#hybrid-patterns)
- [Migration Paths](#migration-paths)

---

# DLT vs Managed Connectors

> **Shared reference** — used by data-integration, dlt-extract, client-delivery

## Decision Matrix

| Factor | DLT (dlthub) | Fivetran | Airbyte | Custom Python |
|--------|-------------|----------|---------|---------------|
| **Setup time** | Hours (code) | Minutes (UI) | Minutes (UI/code) | Days |
| **Maintenance** | You own it | Managed | Self-hosted or Cloud | You own it |
| **File sources (CSV/Excel)** | First-class (filesystem source) | Limited | Good | Full control |
| **SaaS connectors** | 50+ verified + custom | 300+ managed | 350+ community | Unlimited |
| **Schema management** | Auto-evolve + contracts + Pydantic | Auto-evolve only | Auto-evolve + normalization | Manual |
| **Incremental loading** | Built-in cursor + merge state | Built-in | Built-in | Manual |
| **Cost model** | Free + your compute | Per-MAR ($$$) | Self-host ($$) or Cloud ($$$) | Compute only ($) |
| **Client handoff** | Git repo, pip install | Dashboard access | Dashboard or Terraform | Git repo |
| **Portability** | Destination-agnostic | Vendor lock-in | Moderate | Full control |
| **Testing** | pytest, schema validation | Limited | Connection tests | Full control |
| **Best for** | Custom sources, files, consulting | Standard SaaS, non-technical | Self-hosted, open source | Unique protocols |

## Decision Flowchart

```
Start: What are you extracting?
│
├─ Local files (CSV, Excel, Parquet, JSON)
│   └─ Use DLT with filesystem source or duckdb
│       (Fivetran/Airbyte don't handle local files well)
│
├─ Standard SaaS API (Salesforce, Stripe, HubSpot, etc.)
│   ├─ Client already has Fivetran/Airbyte? → Use existing connector
│   ├─ Budget allows managed connector? → Fivetran (lowest maintenance)
│   ├─ Need self-hosted? → Airbyte
│   └─ Need custom logic or cost control? → DLT
│
├─ Custom/internal API
│   ├─ REST with pagination? → DLT REST API source
│   ├─ Complex auth or protocol? → Custom Python or DLT custom source
│   └─ GraphQL? → DLT with custom resource
│
├─ Database replication (CDC)
│   ├─ Real-time needed? → Debezium (see data-integration)
│   ├─ Batch OK? → DLT SQL source or Fivetran
│   └─ Snowflake Streams available? → Use native (see data-integration)
│
└─ SharePoint / network drive / SFTP
    └─ DLT with filesystem source + appropriate transport
        (Managed connectors rarely cover these well)
```

## Consulting Context Factors

**Portability:** DLT pipelines are Git repos that run anywhere with `pip install`. Managed connectors require dashboard access or Terraform configs. For client handoff, DLT is simpler.

**Security tiers:** At Schema-Only (Tier 1), DLT can run in schema-discovery mode without extracting data. Managed connectors always extract data.

**Cost transparency:** DLT cost = your compute. Managed connector cost = per-MAR pricing that scales with data volume. For short engagements, DLT avoids recurring SaaS costs.

**Client infrastructure:** If the client already runs Fivetran, adding a new connector is minutes. Don't force DLT if the client's team maintains Fivetran.

**Engagement duration:** Short engagements (1-2 weeks) favor DLT for quick setup and teardown. Long-term engagements may justify managed connector investment.

## Hybrid Patterns

### Pattern 1: Managed SaaS + DLT Custom

Use Fivetran/Airbyte for standard SaaS connectors the client already has. Use DLT for custom file sources, internal APIs, or one-off extractions.

```
Fivetran → Salesforce, Stripe, HubSpot (standard SaaS)
DLT      → Client Excel files, internal REST API, SharePoint
Both     → Load to same warehouse, same schema conventions
```

### Pattern 2: DLT Dev → Managed Prod

Use DLT during the engagement for rapid iteration. Hand off managed connector configs for production to reduce client maintenance burden.

```
During engagement: DLT pipelines (fast iteration, easy testing)
Client handoff:    Fivetran/Airbyte configs (lower maintenance for client team)
```

### Pattern 3: DLT Everywhere (Consulting-Portable)

Use DLT for all sources. Package as a Git repo with CI/CD. Client runs on their infrastructure.

```
All sources → DLT pipelines in Git repo
CI/CD       → GitHub Actions / GitLab CI
Client runs → pip install + env vars + cron/orchestrator
```

Best for: technical clients, cost-sensitive, custom sources, full consultant control.

## Migration Paths

### Fivetran → DLT

1. Export Fivetran connector configs (API or dashboard)
2. Map each connector to DLT verified source or REST API source
3. Replicate schema naming conventions (`_fivetran_synced` → DLT `_dlt_load_id`)
4. Test row counts and schema parity
5. Switch over source-by-source

### DLT → Fivetran

1. Document each DLT source's API endpoints and auth
2. Find matching Fivetran connector (check connector catalog)
3. Configure in Fivetran dashboard
4. Validate schema mapping (column names may differ)
5. Deprecate DLT pipeline after validation period

### Custom Python → DLT

1. Wrap existing extraction functions as `@dlt.resource` decorators
2. Add `@dlt.source` for grouping related resources
3. Replace manual state tracking with DLT incremental cursors
4. Replace manual schema handling with DLT schema contracts
5. Replace manual loading with `dlt.pipeline().run()`
