## Contents

- [Canonical Data Models](#canonical-data-models)
  - [Canonical Customer Model (Pydantic)](#canonical-customer-model-pydantic)
  - [Versioning Strategies](#versioning-strategies)
- [Field Mapping Tables](#field-mapping-tables)
- [Crosswalk Tables](#crosswalk-tables)
  - [Golden Record Resolution](#golden-record-resolution)
- [Schema Drift Detection](#schema-drift-detection)
- [Impact Analysis](#impact-analysis)

---

# Data Mapping and Crosswalks

## Canonical Data Models

A canonical model provides a unified entity representation across systems. Instead of N-squared point-to-point mappings, map each system to/from the canonical model (2N mappings).

**When to use:** 3+ systems sharing entity data, need single source of truth, expect new systems over time.
**When NOT to use:** Simple 2-system integration, real-time ultra-low-latency, identical schemas.

Organize around bounded contexts: Customer Domain (Customer, Contact, Address), Order Domain (Order, OrderLine, Shipment), Product Domain, Finance Domain.

### Canonical Customer Model (Pydantic)

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class Address(BaseModel):
    address_type: str  # billing, shipping, physical
    street_line1: str
    city: str
    state_province: str
    postal_code: str
    country_code: str  # ISO 3166-1 alpha-2
    is_primary: bool = False

class Customer(BaseModel):
    canonical_id: str
    external_ids: dict[str, str] = Field(default_factory=dict)
    customer_name: str = Field(..., min_length=2)
    customer_type: str  # individual, business
    email: EmailStr
    tier: str = "standard"  # prospect, standard, premium, enterprise
    status: str = "active"
    annual_revenue: Optional[float] = Field(None, ge=0)
    addresses: List[Address] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
```

### Versioning Strategies

1. **Version in model name** — `CustomerV1`, `CustomerV2` with migration functions
2. **Schema version field** — `schema_version: int` with `from_dict()` that upcasts
3. **Event sourcing** — Store events, upcast old events to current schema on read

## Field Mapping Tables

Define source-to-canonical mappings with transformation rules.

```sql
CREATE TABLE field_mappings (
  mapping_id SERIAL PRIMARY KEY,
  source_system VARCHAR(100) NOT NULL,
  source_table VARCHAR(100) NOT NULL,
  source_field VARCHAR(100) NOT NULL,
  canonical_entity VARCHAR(100) NOT NULL,
  canonical_field VARCHAR(100) NOT NULL,
  transform_rule TEXT,  -- 'direct', CASE expr, or function name
  data_type VARCHAR(50),
  is_required BOOLEAN DEFAULT FALSE,
  UNIQUE(source_system, source_table, source_field, canonical_field)
);
```

Version-control mappings in YAML, load to DB via script. Validate completeness (all required canonical fields mapped), uniqueness (no duplicate source mappings), and type compatibility.

## Crosswalk Tables

Maintain entity identity across systems. Same entity has different IDs per system; crosswalk resolves them to one canonical ID.

```sql
CREATE TABLE entity_crosswalk (
  crosswalk_id SERIAL PRIMARY KEY,
  entity_type VARCHAR(50) NOT NULL,
  canonical_id VARCHAR(100) NOT NULL,
  source_system VARCHAR(100) NOT NULL,
  source_id VARCHAR(255) NOT NULL,
  confidence DECIMAL(3,2) DEFAULT 1.00,
  match_method VARCHAR(50),  -- exact_id, fuzzy_name, email, manual
  is_active BOOLEAN DEFAULT TRUE,
  UNIQUE(entity_type, source_system, source_id)
);
```

**Matching strategy order:** (1) Exact ID match in crosswalk, (2) Match by external_ids field, (3) Fuzzy match by email or name (confidence < 1.0), (4) Create new canonical ID.

**Translate between systems:**

```sql
SELECT ns.source_id AS netsuite_id
FROM entity_crosswalk sf
JOIN entity_crosswalk ns
  ON sf.canonical_id = ns.canonical_id AND sf.entity_type = ns.entity_type
WHERE sf.source_system = 'salesforce' AND sf.source_id = '001XXX'
  AND ns.source_system = 'netsuite';
```

### Golden Record Resolution

Survivorship rules determine which source value wins per field:
- **Most recent** — timestamps, last_activity_date
- **Highest value** — revenue, scores
- **Longest string** — names, descriptions
- **Source priority** — default fallback (e.g., Salesforce > NetSuite > HubSpot)

## Schema Drift Detection

| Drift Type | Impact | Detection |
|------------|--------|-----------|
| Column added | Low (if optional) | Compare current vs snapshot |
| Column removed | Medium (data loss) | Compare current vs snapshot |
| Type changed | High (breaks transforms) | Compare column types |
| Renamed | High (mapping breaks) | Appears as drop + add |

**Detection approach:** Capture schema snapshots (JSON + hash), compare periodically. Alert severity: removed/type-changed = critical, nullability = high, added = low.

**Handling policies:**
1. **Fail fast** — Stop pipeline on any drift to prevent corruption
2. **Auto-accommodate** — Automatically ALTER TABLE ADD COLUMN for new columns
3. **Alert only** — Log drift, send alert, continue with previous schema

Use Avro Schema Registry for event-driven systems (compatibility checking built in). Use dbt source freshness for warehouse-side monitoring.

## Impact Analysis

Track data lineage to answer: "If source field X changes, what breaks?"

Query path: source field -> field_mappings -> canonical field -> data_lineage -> downstream datasets. Use DataHub, OpenMetadata, or simple lineage tracking table for metadata management.

Tag PII/PHI fields in a classification table. Detect PII by column name hints and data pattern matching. Enforce encryption and masking requirements per classification level.
