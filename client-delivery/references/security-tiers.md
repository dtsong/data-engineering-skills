## Contents

- [Tier 1: Schema-Only](#tier-1-schema-only)
- [Tier 2: Sampled](#tier-2-sampled)
- [Tier 3: Full Access](#tier-3-full-access)
- [Tier Escalation Procedure](#tier-escalation-procedure)

# Security Tiers — Procedural Reference

> **Part of:** [client-delivery](../SKILL.md)

---

## Tier 1: Schema-Only

**Access level:** DDL exports, column definitions, table relationships. No row data.

**What to request from client:**
- DDL export scripts or `INFORMATION_SCHEMA` dumps
- Entity-relationship diagrams (if available)
- Data dictionary or column descriptions
- Business rules documentation

**How to configure tools:**
- dbt profile target: `schema_only` (DuckDB `:memory:`)
- Run `dbt compile` to validate SQL without executing
- Profiler: schema metadata mode only (`schema_profiler.py` without `--include-sample`)
- `.gitignore`: standard template (no data files expected)

**What to deliver:**
- Data model assessment: table relationships, naming conventions, type consistency
- Recommendations document: cleaning priorities ranked by inferred impact
- Proposed transformation plan: dbt model stubs with documented assumptions

**Limitations:**
- Cannot validate data quality (no rows to inspect)
- Cannot detect actual null rates, duplicates, or value distributions
- Type inference based on DDL may not reflect actual data

---

## Tier 2: Sampled

**Access level:** Anonymized or masked sample rows. Typically 50-500 rows per table.

**What to request from client:**
- Sample extract: `python scripts/sample_extractor.py` output, or client-provided CSV
- Anonymization confirmation: PII columns masked or removed
- Written acknowledgment that samples are approved for consultant access
- Sample representativeness statement (random, first N, stratified)

**How to configure tools:**
- dbt profile target: `dev` (DuckDB with sample data loaded)
- Load samples: `dbt seed` or DuckDB `COPY FROM` into `data/samples/`
- Profiler: full mode with `--include-sample 10` for column value examples
- `.gitignore`: include `data/samples/` (samples are already anonymized, but still gitignore)

**What to deliver:**
- Profiling report: column-level statistics, quality scores, issue inventory
- Validated cleaning patterns: dbt models tested against sample data
- Quality report draft: findings from sample, extrapolated risk assessment

**Limitations:**
- Sample may not represent edge cases or rare values
- Cardinality estimates may be inaccurate at small sample sizes
- Cannot validate referential integrity across full dataset

---

## Tier 3: Full Access

**Access level:** Complete dataset in a sandbox or dev environment.

**What to request from client:**
- Written authorization for full data access (email or signed scope document)
- Sandbox/dev environment credentials (never production)
- Data retention policy: when must consultant delete local copies
- Incident response contact: who to notify if PII is discovered unexpectedly

**How to configure tools:**
- dbt profile target: `dev` (DuckDB or warehouse with full data)
- Configure warehouse connection in `.env` if using Snowflake/BigQuery
- Profiler: full mode, all columns, all rows
- `.gitignore`: strict — `data/raw/`, `*.xlsx`, `*.csv`, `*.parquet`, `*.duckdb`

**What to deliver:**
- Production-ready dbt models: tested, documented, passing all assertions
- Complete quality report: every table, every column, severity-ranked findings
- Mapping document: full source-to-target with transformation rules
- Transform log: every decision documented with before/after row counts
- Runbook: step-by-step re-execution instructions

**Additional security requirements:**
- Store data in gitignored `data/raw/` only
- Delete local copies after engagement per retention policy
- Log all data access in transform log
- Encrypt local DuckDB file if client requires (`PRAGMA encryption`)

---

## Tier Escalation Procedure

When the current tier limits engagement quality, follow this escalation process:

1. **Document current-tier limitations** — Record specific questions that cannot be answered at the current tier. Example: "Cannot determine actual null rate for `customer_email` without sample data."

2. **Present gap analysis** — Show the client what deliverables are impacted and how quality degrades without escalation. Use the quality report draft to illustrate gaps.

3. **Propose escalation with specific ask** — Request the minimum additional access needed:
   - Tier 1 → Tier 2: "Provide 100 anonymized rows per table, with PII columns masked."
   - Tier 2 → Tier 3: "Provide dev environment access with full dataset. We need this to validate referential integrity and edge cases."

4. **Record the decision** — Add an ADR entry to `decisions.md`:
   ```
   ## ADR-00X: Tier Escalation from {current} to {proposed}
   Date: YYYY-MM-DD
   Status: Proposed | Accepted | Rejected
   Context: {limitations encountered}
   Decision: {escalate or remain}
   Consequences: {impact on deliverables}
   ```

5. **Reconfigure tools** — Update dbt profile target, profiler flags, and `.gitignore` per the new tier's configuration section above.
