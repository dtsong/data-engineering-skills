## Contents

- [Directory Structure](#directory-structure)
- [Template File Inventory](#template-file-inventory)
- [Initialization Steps](#initialization-steps)
- [Tier-Specific Scaffold Variations](#tier-specific-scaffold-variations)

# Engagement Scaffold — Procedural Reference

> **Part of:** [consulting-engagement-skill](../SKILL.md)

---

## Directory Structure

```
client-engagement/
├── README.md                    # Engagement overview, scope, run instructions
├── .env                         # Environment variables (NEVER committed)
├── .env.template                # Template for .env (committed)
├── .gitignore                   # Tier-aware ignore rules
├── decisions.md                 # ADR-style decision log
├── requirements.txt             # Python dependencies
├── data/
│   ├── raw/                     # Client source files (always gitignored)
│   ├── profiling/               # Profiler JSON output
│   └── samples/                 # Tier 2 anonymized samples (gitignored)
├── dbt_project/
│   ├── dbt_project.yml          # From template
│   ├── profiles.yml             # From template (gitignored)
│   ├── models/
│   │   ├── staging/             # stg_ models (view)
│   │   ├── intermediate/        # int_ models (ephemeral)
│   │   └── marts/               # fct_ / dim_ models (table)
│   ├── seeds/                   # Reference data / lookups
│   ├── tests/                   # Custom data tests
│   └── macros/                  # Reusable SQL macros
├── pipelines/                   # DLT pipelines (if needed)
├── scripts/                     # Utility scripts
│   ├── schema_profiler.py       # Symlink or copy from skill scripts
│   └── sample_extractor.py      # Symlink or copy from skill scripts
└── deliverables/                # Client-facing output
    ├── quality-report.md
    ├── mapping-document.md
    └── transform-log.md
```

---

## Template File Inventory

| Template | Source Path | Target Path | Description |
|----------|-----------|------------|-------------|
| README | `templates/engagement/README.md.template` | `README.md` | Engagement overview with placeholders |
| .env | `templates/engagement/.env.template` | `.env.template` | Environment variable template |
| .gitignore | `templates/engagement/.gitignore.template` | `.gitignore` | Tier-aware ignore rules |
| decisions.md | `templates/engagement/decisions.md.template` | `decisions.md` | ADR log with Tier selection starter |
| dbt_project.yml | `templates/dbt/dbt_project.yml.template` | `dbt_project/dbt_project.yml` | dbt project config |
| profiles.yml | `templates/dbt/profiles.yml.template` | `dbt_project/profiles.yml` | dbt connection profiles |
| schema.yml | `templates/dbt/schema.yml.template` | `dbt_project/models/staging/schema.yml` | Source and model definitions |

---

## Initialization Steps

1. **Create root directory:**
   ```bash
   mkdir -p client-engagement
   cd client-engagement
   ```

2. **Create subdirectories:**
   ```bash
   mkdir -p data/{raw,profiling,samples} \
            dbt_project/models/{staging,intermediate,marts} \
            dbt_project/{seeds,tests,macros} \
            pipelines scripts deliverables
   ```

3. **Copy and fill templates:**
   ```bash
   # Copy templates
   cp templates/engagement/README.md.template README.md
   cp templates/engagement/.env.template .env.template
   cp templates/engagement/.gitignore.template .gitignore
   cp templates/engagement/decisions.md.template decisions.md
   cp templates/dbt/dbt_project.yml.template dbt_project/dbt_project.yml
   cp templates/dbt/profiles.yml.template dbt_project/profiles.yml

   # Fill placeholders (use sed or manual edit)
   # {{CLIENT_NAME}}, {{START_DATE}}, {{SECURITY_TIER}}, etc.
   ```

4. **Configure environment:**
   ```bash
   cp .env.template .env
   # Edit .env with engagement-specific values
   ```

5. **Initialize git:**
   ```bash
   git init
   git add .
   git commit -m "Initialize engagement scaffold"
   ```

6. **Copy utility scripts:**
   ```bash
   cp scripts/schema_profiler.py scripts/
   cp scripts/sample_extractor.py scripts/
   ```

7. **Install dependencies:**
   ```bash
   pip install dbt-duckdb openpyxl chardet
   pip freeze > requirements.txt
   ```

---

## Tier-Specific Scaffold Variations

### Tier 1: Schema-Only

- `data/raw/` contains DDL files only (`.sql` exports)
- `data/samples/` is empty
- `dbt_project/profiles.yml` uses `schema_only` target (`:memory:`)
- Deliverables: data model assessment, recommendations document
- `.gitignore`: standard template

### Tier 2: Sampled

- `data/raw/` contains client source files (gitignored)
- `data/samples/` contains anonymized extracts (gitignored)
- `dbt_project/profiles.yml` uses `dev` target (DuckDB with samples)
- Run `sample_extractor.py` to create samples from raw files
- Deliverables: profiling report, validated cleaning patterns, quality report draft
- `.gitignore`: adds `data/samples/` explicitly

### Tier 3: Full Access

- `data/raw/` contains full dataset (gitignored, encrypted if required)
- `dbt_project/profiles.yml` uses `dev` target (DuckDB or warehouse)
- May add warehouse connection to `.env` (Snowflake, BigQuery, etc.)
- Deliverables: full production-ready artifacts
- `.gitignore`: strict — all data files, DuckDB databases, dbt artifacts
- Add data retention policy to `decisions.md`
