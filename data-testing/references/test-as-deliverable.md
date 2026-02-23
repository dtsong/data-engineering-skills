> **Part of:** [data-testing](../SKILL.md)

# Test as Deliverable

Reference for packaging data test results as client-facing deliverables. Covers report formats, scoring, coverage metrics, and regression suite handoff.

## Test Summary Report Format

Structure for a client-facing test summary:

```markdown
# Data Quality Test Report
**Project:** [Project Name]
**Date:** [Run Date]
**Environment:** [Production / Staging / CI]
**dbt Version:** [x.x.x]

## Executive Summary
- **Total Tests:** [N]
- **Passed:** [N] ([%])
- **Failed:** [N] ([%])
- **Warned:** [N] ([%])
- **Coverage Score:** [%] (see Coverage Metrics below)

## Critical Failures
| Model | Test | Severity | Failing Rows | Recommended Action |
|-------|------|----------|-------------|-------------------|
| fct_orders | unique_order_id | error | 12 | Deduplicate in staging |
| dim_customers | not_null_email | warn | 340 | Review source system |

## Test Results by Layer
### Staging ([N] tests)
[Pass/fail summary table]

### Intermediate ([N] tests)
[Pass/fail summary table]

### Marts ([N] tests)
[Pass/fail summary table]
```

---

## dbt Output to Client Scorecard

Convert `target/run_results.json` into a client scorecard:

### Extracting Results

```bash
# Parse dbt run results into summary CSV
cat target/run_results.json | python3 -c "
import json, sys, csv
data = json.load(sys.stdin)
writer = csv.writer(sys.stdout)
writer.writerow(['model', 'test', 'status', 'execution_time', 'failures'])
for r in data['results']:
    if r['unique_id'].startswith('test.'):
        writer.writerow([
            r.get('depends_on', {}).get('nodes', [''])[0].split('.')[-1],
            r['unique_id'].split('.')[-1],
            r['status'],
            round(r['execution_time'], 2),
            r.get('failures', 0)
        ])
" > test_scorecard.csv
```

### Scorecard Template

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| PK Integrity (unique + not_null) | 100% | 100% | PASS |
| Column Coverage (marts) | 85% | 80% | PASS |
| Column Coverage (staging) | 62% | 60% | PASS |
| Referential Integrity | 98% | 100% | WARN |
| Zero Critical Failures | Yes | Yes | PASS |

---

## Store Failures for Review Lists

Configure `store_failures` to capture failing rows for client review:

```yaml
# dbt_project.yml
tests:
  +store_failures: true
  +schema: dbt_test_failures
```

### Querying Failure Tables

```sql
-- List all failure tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'dbt_test_failures'
ORDER BY table_name;

-- Sample failing rows for client review
SELECT *
FROM dbt_test_failures.unique_fct_orders_order_id
LIMIT 100;
```

---

## Coverage Metrics as Deliverable

### Calculating Coverage from manifest.json

```python
import json

with open('target/manifest.json') as f:
    manifest = json.load(f)

models = {k: v for k, v in manifest['nodes'].items() if v['resource_type'] == 'model'}
tests = {k: v for k, v in manifest['nodes'].items() if v['resource_type'] == 'test'}

for model_key, model in models.items():
    total_cols = len(model.get('columns', {}))
    tested_cols = set()
    for test_key, test in tests.items():
        if model_key in test.get('depends_on', {}).get('nodes', []):
            col = test.get('test_metadata', {}).get('kwargs', {}).get('column_name')
            if col:
                tested_cols.add(col)
    coverage = len(tested_cols) / max(total_cols, 1) * 100
    print(f"{model['name']}: {coverage:.0f}% ({len(tested_cols)}/{total_cols})")
```

---

## Before/After Quality Comparison

Template for migration or refactoring validation:

| Metric | Before | After | Delta | Status |
|--------|--------|-------|-------|--------|
| Total rows | 1,234,567 | 1,234,567 | 0 | PASS |
| Sum(amount) | $45,678,901.23 | $45,678,901.23 | $0.00 | PASS |
| Distinct customers | 89,012 | 89,015 | +3 | REVIEW |
| Null rate (email) | 2.1% | 2.1% | 0.0% | PASS |
| Max(order_date) | 2025-12-31 | 2025-12-31 | 0 days | PASS |

**Generate this table** by running reconciliation queries from `sql-assertion-patterns.md` against both old and new pipeline outputs.

---

## Regression Suite as Handoff Artifact

Package for client team to run independently after engagement ends:

### Suite Contents

```
regression-suite/
  README.md              -- How to run, what to expect
  golden-dataset/        -- Known-good input data (anonymized)
  expected-output/       -- Known-good output for comparison
  run-tests.sh           -- Single command to execute suite
  assertions/            -- SQL assertion files
  report-template.md     -- Blank report template
```

### run-tests.sh Template

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "Running regression suite..."
dbt seed --target ci
dbt build --target ci --select tag:regression
dbt run-operation generate_test_report

echo "Comparing output to golden dataset..."
python3 compare_output.py \
    --expected expected-output/ \
    --actual target/compiled/ \
    --tolerance 0.01

echo "Regression suite complete. See report at target/test_report.md"
```

**Handoff checklist:**
- [ ] Golden dataset anonymized (no PII)
- [ ] All SQL assertions use client's database syntax
- [ ] README documents prerequisites (dbt version, database access)
- [ ] run-tests.sh tested on clean environment
- [ ] Client team demonstrated running suite independently
