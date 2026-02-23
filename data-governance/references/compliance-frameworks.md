# Compliance Frameworks

## Table of Contents

- GDPR: Pipeline Design Implications
- HIPAA: PHI Handling in Data Pipelines
- SOX: Financial Data Controls and Audit Trails
- CCPA: California Consumer Data Rights
- Compliance Documentation for Delivery
- Disclaimer

---

**DISCLAIMER:** This reference provides engineering-level guidance for implementing technical controls. It is NOT legal counsel. Always consult legal and compliance teams for regulatory interpretation. Flag `# LEGAL REVIEW REQUIRED` on any artifact that makes compliance claims.

## GDPR: Pipeline Design Implications

General Data Protection Regulation applies to EU resident personal data.

| Requirement | Pipeline Impact | Technical Control |
|-------------|----------------|-------------------|
| Right to erasure (Art. 17) | Must be able to delete individual records | Implement soft-delete flag + hard-delete job |
| Data portability (Art. 20) | Must export individual's data in machine-readable format | Export endpoint producing JSON/CSV per customer_id |
| Lawful basis | Must document why data is collected | `meta.lawful_basis` tag on source models |
| Data minimization | Only collect what is necessary | Column pruning in staging models |
| Storage limitation | Retention policies per data category | Automated retention jobs with configurable TTL |

Right-to-erasure implementation pattern:

```sql
-- Soft delete: flag record
UPDATE customers SET is_deleted = TRUE, deleted_at = CURRENT_TIMESTAMP
WHERE customer_id = :target_id;

-- Hard delete job (run after retention window)
DELETE FROM customers WHERE is_deleted = TRUE AND deleted_at < DATEADD(day, -30, CURRENT_TIMESTAMP);

-- Cascade to downstream tables
DELETE FROM orders WHERE customer_id NOT IN (SELECT customer_id FROM customers);
```

dbt meta tags for GDPR compliance:

```yaml
meta:
  compliance: [gdpr]
  lawful_basis: "contract"           # contract | consent | legitimate_interest
  retention_days: 730
  erasure_supported: true
  data_controller: "Company Name"
```

## HIPAA: PHI Handling in Data Pipelines

Health Insurance Portability and Accountability Act applies to Protected Health Information.

| Requirement | Pipeline Impact | Technical Control |
|-------------|----------------|-------------------|
| Minimum necessary | Only process PHI columns needed for the task | Column-level access control + masking |
| Access controls | Track who accesses PHI | Row-level security + audit logging |
| Audit trail | Log all PHI access | Snowflake ACCESS_HISTORY / Azure SQL audit |
| Encryption | PHI encrypted at rest and in transit | Warehouse-native encryption (enabled by default) |
| BAA | Business Associate Agreement with all vendors | Document in compliance manifest |

PHI pipeline pattern:

```yaml
# models/staging/stg_patients.yml
models:
  - name: stg_patients
    meta:
      compliance: [hipaa]
      classification: restricted
      phi_columns: [patient_name, mrn, diagnosis_code, insurance_id]
      access_restricted_to: [clinical_data_team, data_admin]
    columns:
      - name: mrn
        meta:
          classification: restricted
          phi_type: medical_record_number
          masking: sha256_in_non_prod
```

Audit logging query (Snowflake):

```sql
-- Query PHI access history
SELECT
    user_name,
    query_text,
    start_time,
    database_name,
    schema_name
FROM snowflake.account_usage.query_history
WHERE query_text ILIKE '%stg_patients%'
  AND start_time > DATEADD(day, -30, CURRENT_TIMESTAMP)
ORDER BY start_time DESC;
```

## SOX: Financial Data Controls and Audit Trails

Sarbanes-Oxley Act applies to financial reporting data in publicly traded companies.

| Requirement | Pipeline Impact | Technical Control |
|-------------|----------------|-------------------|
| Change management | All pipeline changes documented and approved | Git PRs with required reviewers |
| Segregation of duties | No single person controls end-to-end | Separate roles for dev, review, deploy |
| Audit trail | Complete history of data transformations | dbt run logs + warehouse query history |
| Data integrity | Financial figures must be verifiable | Reconciliation tests (source sum = target sum) |

SOX control tags:

```yaml
meta:
  compliance: [sox]
  sox_control_id: "CTRL-FIN-001"
  change_management: "pr_required"
  segregation: "dev_cannot_deploy"
  reconciliation_test: "tests/reconcile_revenue.sql"
```

Reconciliation test pattern:

```sql
-- tests/reconcile_revenue.sql
-- SOX Control: CTRL-FIN-001 - Revenue figures match source
WITH source_total AS (
    SELECT SUM(amount) AS total FROM {{ source('billing', 'invoices') }}
    WHERE invoice_date >= '{{ var("fiscal_period_start") }}'
),
target_total AS (
    SELECT SUM(revenue) AS total FROM {{ ref('mart_revenue') }}
    WHERE period_start >= '{{ var("fiscal_period_start") }}'
)
SELECT * FROM source_total s, target_total t
WHERE ABS(s.total - t.total) > 0.01  -- tolerance: 1 cent
```

## CCPA: California Consumer Data Rights

California Consumer Privacy Act applies to California resident personal information.

| Requirement | Pipeline Impact | Technical Control |
|-------------|----------------|-------------------|
| Right to know | Disclose what data is collected | Data catalog with classification tags |
| Right to delete | Delete consumer data on request | Erasure pipeline (similar to GDPR Art. 17) |
| Right to opt-out | Honor opt-out of data sale | `opt_out_sale` flag in customer records |
| Non-discrimination | Cannot penalize for exercising rights | No logic that filters by privacy preference |

CCPA-specific meta tags:

```yaml
meta:
  compliance: [ccpa]
  california_consumer_data: true
  sale_of_data: false
  opt_out_supported: true
  disclosure_category: "identifiers"  # per CCPA categories
```

## Compliance Documentation for Delivery

When packaging compliance documentation for client delivery:

```yaml
# compliance_summary.yml
project: "Client Data Platform"
frameworks_applicable: [gdpr, ccpa]
date_assessed: "2025-01-15"
assessed_by: "data-engineering-team"

controls:
  - framework: gdpr
    requirement: "Right to erasure"
    status: implemented
    evidence: "scripts/erasure_pipeline.py"
    last_tested: "2025-01-10"

  - framework: ccpa
    requirement: "Right to delete"
    status: implemented
    evidence: "scripts/erasure_pipeline.py"
    last_tested: "2025-01-10"

  - framework: gdpr
    requirement: "Data minimization"
    status: partial
    gap: "Legacy source tables contain unused PII columns"
    remediation: "Column pruning in staging layer — scheduled Q2"

gaps:
  - description: "No automated retention enforcement"
    severity: medium
    remediation_plan: "Implement TTL-based deletion job"
    target_date: "2025-03-01"

# LEGAL REVIEW REQUIRED: This document describes technical controls only.
# Regulatory compliance determination requires legal counsel review.
```

## Disclaimer

This reference provides patterns for implementing technical controls that support regulatory compliance. It does NOT constitute legal advice. For every compliance-related deliverable:

1. Tag with `# LEGAL REVIEW REQUIRED` in the output
2. Recommend client engage legal counsel for regulatory interpretation
3. Document assumptions about applicability (jurisdiction, data types, business context)
4. Distinguish between "technical control implemented" and "regulatory requirement satisfied"
