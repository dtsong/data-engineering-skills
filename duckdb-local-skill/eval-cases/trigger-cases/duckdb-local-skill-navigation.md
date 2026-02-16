# duckdb-local-skill -- Navigation Eval Cases

Navigation evals test how the agent traverses the skill file tree during execution.
They are distinct from trigger evals (activation) and output evals (result correctness).

---

## Case 1: SKILL.md-sufficient -- File Format Support

**Category:** SKILL.md-sufficient

**Input:**
> "What file formats can DuckDB read?"

**Expected Navigation:**
1. Read `duckdb-local-skill/SKILL.md`
2. Stop -- the File Ingestion table lists all supported formats with functions

**Should Read:** `SKILL.md` only
**Should NOT Read:** Any reference file

**Observation Points:**
- Agent locates the File Ingestion decision matrix table in SKILL.md
- Agent does not open `references/file-ingestion.md` or `references/excel-specifics.md`
- Agent provides a format list (CSV, Parquet, JSON, Excel) citing SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading references
- **Partial:** Agent reads SKILL.md and one reference but answer comes from SKILL.md
- **Fail:** Agent reads multiple references or answers without consulting SKILL.md

---

## Case 2: Targeted Reference -- Excel with Merged Cells

**Category:** Targeted reference

**Input:**
> "How do I read an Excel file with merged cells in DuckDB?"

**Expected Navigation:**
1. Read `duckdb-local-skill/SKILL.md`
2. Follow link to `references/excel-specifics.md`
3. Stop -- merged cell handling is in the Excel specifics reference

**Should Read:** `SKILL.md` -> `references/excel-specifics.md`
**Should NOT Read:** `references/file-ingestion.md`, `references/export-patterns.md`, `references/performance.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the Excel Specifics reference link
- Agent follows exactly one reference link
- Agent does not speculatively read file-ingestion.md (despite Excel being a "file")
- Agent provides merged cell handling pattern from excel-specifics.md

**Grading:**
- **Pass:** Agent reads SKILL.md then excel-specifics.md only
- **Partial:** Agent reads SKILL.md, excel-specifics.md, and one additional reference
- **Fail:** Agent reads 3+ references or skips excel-specifics.md

---

## Case 3: Cross-reference Resistance -- Basic CSV Read

**Category:** Cross-reference resistance

**Input:**
> "Read a CSV file into DuckDB"

**Expected Navigation:**
1. Read `duckdb-local-skill/SKILL.md`
2. Stop -- SKILL.md's File Ingestion section and Quick Start cover basic CSV reading

**Should Read:** `SKILL.md` only
**Should NOT Read:** `references/file-ingestion.md` (tempting but unnecessary for basic CSV read)

**Observation Points:**
- Agent locates `read_csv_auto()` in SKILL.md's File Ingestion table and Quick Start
- Agent resists following the link to `references/file-ingestion.md`
- Basic CSV reading does not require detailed parameter documentation

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading file-ingestion.md
- **Partial:** Agent reads SKILL.md then file-ingestion.md but answer only uses SKILL.md content
- **Fail:** Agent loads file-ingestion.md and additional references

---

## Case 4: Shared Reference -- Security for Client Data Analysis

**Category:** Shared reference

**Input:**
> "What security considerations for analyzing client data locally?"

**Expected Navigation:**
1. Read `duckdb-local-skill/SKILL.md`
2. Follow Security Posture link to `../shared-references/data-engineering/security-tier-model.md`
3. Stop -- consulting security tiers define appropriate data access levels

**Should Read:** `SKILL.md` -> `../shared-references/data-engineering/security-tier-model.md`
**Should NOT Read:** `references/file-ingestion.md`, `references/performance.md`, `references/export-patterns.md`, `references/excel-specifics.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the security-tier-model link in Security Posture
- Agent navigates to the shared reference (outside the skill directory)
- Agent does not confuse shared references with skill-local references
- Agent provides tier-based guidance on data access levels for consulting

**Grading:**
- **Pass:** Agent reads SKILL.md then shared security-tier-model reference only
- **Partial:** Agent reads SKILL.md, shared security reference, and one skill-local reference
- **Fail:** Agent skips the shared security reference or reads 3+ files total
