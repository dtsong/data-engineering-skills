# CI/CD & Deployment

> **Part of:** [dbt-skill](../SKILL.md)

## Development Workflow

```
edit SQL -> dbt compile --select model -> dbt run --select model -> dbt test --select model -> iterate
```

Prefer `dbt build` over separate run + test. Build executes in DAG order, testing immediately after each model.

Use `--defer --state ./prod-artifacts` to reference production artifacts during local dev, avoiding full DAG rebuilds.

## Slim CI

Build and test only modified models + downstream descendants using state comparison against production `manifest.json`.

| Selector | Meaning |
|----------|---------|
| `state:modified` | Models with SQL, config, or schema changes |
| `state:modified+` | Modified + all downstream (use this) |
| `state:new` | Newly added models |

```bash
dbt build --select state:modified+ --defer --state ./prod-artifacts
dbt build --select state:modified+ --defer --state ./prod-artifacts --empty  # zero-cost SQL validation (1.8+)
```

Store production `manifest.json` via: GitHub Actions artifact upload, S3/GCS bucket, or dbt Cloud automatic defer.

## GitHub Actions (Snowflake)

```yaml
name: dbt Slim CI
on:
  pull_request:
    branches: [main]
jobs:
  dbt-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install dbt-snowflake
      - name: Create profiles.yml
        run: |
          cat <<EOF > profiles.yml
          my_project:
            target: ci
            outputs:
              ci:
                type: snowflake
                account: "${{ secrets.SNOWFLAKE_ACCOUNT }}"
                user: "${{ secrets.SNOWFLAKE_CI_USER }}"
                password: "${{ secrets.SNOWFLAKE_CI_PASSWORD }}"
                role: ci_role
                database: analytics
                warehouse: ci_wh_xs
                schema: "ci_pr_${{ github.event.pull_request.number }}"
                threads: 4
          EOF
      - run: dbt deps
      - name: Download production manifest
        uses: dawidd6/action-download-artifact@v3
        with: {name: dbt-prod-manifest, workflow: dbt-prod-deploy.yml, branch: main, path: ./prod-artifacts}
        continue-on-error: true
      - name: dbt build
        run: |
          if [ -f ./prod-artifacts/manifest.json ]; then
            dbt build --select state:modified+ --defer --state ./prod-artifacts
          else
            dbt build
          fi
```

**BigQuery differences:** `pip install dbt-bigquery`, use `google-github-actions/auth@v2` for auth, add `maximum_bytes_billed` in profile.

**Production deploy:** Run `dbt build` on merge to main, then `actions/upload-artifact` to save `target/manifest.json` for future Slim CI.

## dbt Cloud Jobs

| Job | Trigger | Command |
|-----|---------|---------|
| CI | Pull request | `dbt build --select state:modified+ --defer --favor-state` |
| Production | Merge to main | `dbt build` (with docs + freshness) |
| Full refresh | Cron daily/weekly | `dbt build --full-refresh -s config.materialized:incremental` |

## Environment Strategy

| Environment | Schema Pattern |
|-------------|---------------|
| Local dev | `dev_<username>` |
| CI | `ci_pr_<number>` |
| Staging | `staging` |
| Production | `prod` |

Override `generate_schema_name`: prod uses custom schema directly (`finance`), dev/ci prefixes with target schema (`dbt_dsong_finance`).

```yaml
# dbt_project.yml
models:
  my_project:
    staging:
      +materialized: view
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: "{{ 'table' if target.name == 'prod' else 'view' }}"
```

## Blue/Green Deployment

Build into shadow schema, verify, then atomically swap with live.

- **Snowflake:** `alter schema analytics.prod swap with analytics.prod_shadow` -- instant, atomic. Swap back to rollback.
- **BigQuery:** Lacks schema swap. Route views to new dataset instead.

**Use when:** Large project with BI consumers or SLA-critical/regulated environments. **Skip when:** Small project (<50 models) or incremental-heavy (full rebuild too expensive).

## Cost Optimization

| Environment | Snowflake Size | Auto-Suspend |
|-------------|---------------|-------------|
| CI | X-SMALL | 60s |
| Dev | X-SMALL | 120s |
| Production | MEDIUM+ | 300s |

**BigQuery:** Set `maximum_bytes_billed` in profiles. Assign CI to separate reservation with limited slots.

### PR Schema Cleanup

```sql
-- macros/drop_pr_schema.sql
{% macro drop_pr_schema(pr_number) %}
    {% do run_query("drop schema if exists " ~ target.database ~ ".ci_pr_" ~ pr_number ~ " cascade") %}
{% endmacro %}
```

Automate via GitHub Actions `pull_request: types: [closed]`.

## SQLFluff Integration

```ini
# .sqlfluff
[sqlfluff]
templater = dbt
dialect = snowflake
max_line_length = 120

[sqlfluff:indentation]
tab_space_size = 4

[sqlfluff:layout:type:comma]
line_position = leading

[sqlfluff:rules:capitalisation.keywords]
capitalisation_policy = lower
```

Add to pre-commit hooks and CI. Use `--format github-annotation` for inline PR annotations.

---

**Back to:** [Main Skill File](../SKILL.md)
