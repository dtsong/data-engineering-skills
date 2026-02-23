# Classification Policies

## Table of Contents

- Classification Taxonomy
- PII Detection Patterns
- PHI Detection Patterns
- Automated Classification from Schema Profiles
- Classification as dbt Meta Tags
- Masking and Hashing Recommendations

---

## Classification Taxonomy

Four-tier classification system applied to every column:

| Level | Label | Description | Examples |
|-------|-------|-------------|----------|
| 1 | Public | No restrictions; safe for external sharing | Product names, public pricing |
| 2 | Internal | Business-internal; no customer data | Internal KPIs, aggregated metrics |
| 3 | Confidential | Contains PII or business-sensitive data | Email, phone, revenue figures |
| 4 | Restricted | Regulated data requiring specific controls | SSN, medical records, financial account numbers |

Default classification: **Internal** (Level 2). Columns are Internal until explicitly classified otherwise.

Escalation rule: if any column in a table is Restricted, the table inherits Restricted classification for access control purposes.

## PII Detection Patterns

Regex patterns for common PII fields. Apply to column names and sample values:

```python
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "phone_us": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "date_of_birth": r"\b(?:dob|date_of_birth|birth_date|birthdate)\b",
}

# Column name patterns (match on column names, case-insensitive)
PII_COLUMN_NAMES = [
    r"(?i)(first|last|full)_?name",
    r"(?i)email",
    r"(?i)(phone|mobile|cell)_?(number|num)?",
    r"(?i)ssn|social_security",
    r"(?i)(street|mailing|billing|home)_?address",
    r"(?i)zip_?code|postal_?code",
    r"(?i)credit_card|card_number|cc_num",
    r"(?i)passport",
    r"(?i)driver_?license",
]
```

## PHI Detection Patterns

Protected Health Information patterns (HIPAA-regulated):

```python
PHI_PATTERNS = {
    "mrn": r"\b(?:MRN|medical_record)[-_\s]?\d{6,10}\b",
    "npi": r"\b\d{10}\b",  # National Provider Identifier (10 digits)
    "icd10": r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b",  # ICD-10 diagnosis codes
    "cpt": r"\b\d{5}\b",  # CPT procedure codes (5 digits)
    "dea": r"\b[A-Z]{2}\d{7}\b",  # DEA number
}

PHI_COLUMN_NAMES = [
    r"(?i)medical_record|mrn",
    r"(?i)diagnosis|icd_?code",
    r"(?i)procedure_code|cpt",
    r"(?i)prescription|medication",
    r"(?i)insurance_id|member_id",
    r"(?i)provider_npi|npi",
    r"(?i)patient_name|patient_id",
]
```

PHI columns are always classified as **Restricted** (Level 4).

## Automated Classification from Schema Profiles

Run classification against information_schema:

```sql
-- Snowflake: extract column names for pattern matching
SELECT
    table_schema,
    table_name,
    column_name,
    data_type,
    comment AS existing_classification
FROM information_schema.columns
WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
ORDER BY table_schema, table_name, ordinal_position;
```

Python classification script pattern:

```python
import re

def classify_column(column_name: str, sample_values: list[str] = None) -> str:
    """Return classification level based on column name and optional sample values."""
    for pattern in PII_COLUMN_NAMES:
        if re.search(pattern, column_name):
            return "confidential"
    for pattern in PHI_COLUMN_NAMES:
        if re.search(pattern, column_name):
            return "restricted"
    if sample_values:
        for value in sample_values:
            if re.search(PII_PATTERNS["ssn"], str(value)):
                return "restricted"
            if re.search(PII_PATTERNS["email"], str(value)):
                return "confidential"
    return "internal"  # default
```

## Classification as dbt Meta Tags

Apply classification results as dbt `meta` tags:

```yaml
models:
  - name: stg_customers
    columns:
      - name: customer_id
        meta:
          classification: internal
      - name: email
        meta:
          classification: confidential
          pii_type: email
      - name: ssn_hash
        meta:
          classification: restricted
          pii_type: ssn
          masking: sha256
      - name: created_at
        meta:
          classification: public
```

Validate classification coverage with a dbt macro:

```sql
-- macros/check_classification_coverage.sql
{% macro check_classification_coverage() %}
    {% set models = graph.nodes.values() | selectattr("resource_type", "equalto", "model") %}
    {% for model in models %}
        {% for col in model.columns.values() %}
            {% if col.meta.get("classification") is none %}
                {{ log("WARN: " ~ model.name ~ "." ~ col.name ~ " missing classification", info=true) }}
            {% endif %}
        {% endfor %}
    {% endfor %}
{% endmacro %}
```

## Masking and Hashing Recommendations

| Classification | Recommended Protection | Implementation |
|---------------|----------------------|----------------|
| Public | None | Direct access |
| Internal | Role-based access | RBAC grants |
| Confidential | Column masking in non-prod | Dynamic data masking or views |
| Restricted | Hash or tokenize at ingestion | SHA-256 hash; original in secure vault |

Snowflake dynamic data masking example:

```sql
CREATE OR REPLACE MASKING POLICY pii_mask AS (val STRING)
RETURNS STRING ->
    CASE
        WHEN CURRENT_ROLE() IN ('DATA_ENGINEER', 'DATA_ADMIN') THEN val
        ELSE '***MASKED***'
    END;

ALTER TABLE stg_customers MODIFY COLUMN email
    SET MASKING POLICY pii_mask;
```

SHA-256 hashing at ingestion:

```sql
-- Apply in staging model to hash PII before downstream consumption
SELECT
    customer_id,
    SHA2(email, 256) AS email_hash,
    SHA2(ssn, 256) AS ssn_hash,
    created_at
FROM {{ source('crm', 'customers') }}
```
