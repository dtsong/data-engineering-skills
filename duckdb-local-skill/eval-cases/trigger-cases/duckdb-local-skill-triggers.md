# duckdb-local-skill -- Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match -- Load CSV and Profile

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Load this CSV into DuckDB and show column stats"

**Expected Activation:** Yes
**Expected Skill:** duckdb-local-skill

**Observation Points:**
- Prompt contains exact trigger phrases "CSV" and "DuckDB"
- "Load" and "column stats" map directly to file ingestion and data profiling patterns in SKILL.md
- No competing skill handles standalone DuckDB file loading

**Grading:**
- **Pass:** Skill activates and provides `read_csv_auto()` usage with `SUMMARIZE` or column-level profiling SQL
- **Partial:** Skill activates but only shows read without profiling
- **Fail:** Skill does not activate, or dbt-skill activates because it sees "CSV"

---

## Case 2: Casual Phrasing -- Analyze Excel Files with SQL

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "I have a bunch of Excel files I need to analyze with SQL"

**Expected Activation:** Yes
**Expected Skill:** duckdb-local-skill

**Observation Points:**
- No mention of "DuckDB" anywhere in the prompt
- "Excel files" + "analyze with SQL" maps to DuckDB's file ingestion capabilities
- "Bunch of" implies multiple files, which DuckDB handles via glob or multi-sheet reading
- python-data-engineering-skill could compete (pandas can read Excel), but "with SQL" tips toward DuckDB

**Grading:**
- **Pass:** Skill activates and provides DuckDB Excel reading via spatial extension or Python-based approach, with SQL analysis patterns
- **Partial:** Skill activates but only covers single-file reading without addressing "bunch of" (multiple files)
- **Fail:** Skill does not activate, or python-data-engineering-skill activates because it sees "Excel"

---

## Case 3: Ambiguous -- Profile Dataset for Quality

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "Profile this dataset for quality issues"

**Expected Activation:** Yes (with caveats)
**Expected Skill:** duckdb-local-skill (primary), python-data-engineering-skill (possible secondary)

**Observation Points:**
- "Profile" and "quality issues" are covered by SKILL.md's data profiling patterns
- No file format or tool specified -- could be DuckDB or pandas/ydata-profiling
- If a file is provided in context (CSV, Parquet), DuckDB is the natural fit
- If the dataset is a DataFrame in an existing Python session, python-data-engineering-skill may be more appropriate
- Activation depends on surrounding context (file presence, active session)

**Grading:**
- **Pass:** Skill activates and provides DuckDB profiling SQL (SUMMARIZE, NULL rates, cardinality), noting that python-data-engineering-skill offers alternative profiling tools
- **Partial:** Skill activates but provides only basic count/null checks without comprehensive profiling
- **Fail:** Skill does not activate, or activates without acknowledging the ambiguity

---

## Case 4: Ambiguous -- SQL Deduplication

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "Write SQL to deduplicate these customer records"

**Expected Activation:** Yes (with caveats)
**Expected Skill:** duckdb-local-skill (if local files), dbt-skill (if dbt project context)

**Observation Points:**
- Deduplication is a core cleaning pattern covered in SKILL.md's "Cleaning in SQL" section
- "SQL" without specifying dbt or a warehouse suggests standalone SQL, favoring duckdb-local-skill
- If the user has a dbt project open or mentions models/staging, dbt-skill should take priority
- The phrase "these customer records" implies local data rather than a warehouse table

**Grading:**
- **Pass:** Skill activates and provides ROW_NUMBER dedup pattern in DuckDB SQL, noting that if working within a dbt project, dbt-skill's cleaning patterns reference is more appropriate
- **Partial:** Skill activates but provides generic SQL without DuckDB-specific context
- **Fail:** dbt-skill activates without checking for dbt project context, or no skill activates

---

## Case 5: Negative -- dbt Staging Model from CSV

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Create a dbt staging model from this CSV"

**Expected Activation:** No
**Expected Skill:** dbt-skill

**Observation Points:**
- "dbt staging model" is an exact trigger phrase for dbt-skill
- Although a CSV file is mentioned, the request is to create a dbt model, not to query the CSV
- dbt-skill's DuckDB adapter reference covers reading CSVs as dbt sources
- duckdb-local-skill's scope explicitly excludes dbt model building

**Grading:**
- **Pass:** Skill does not activate; dbt-skill handles the request using its DuckDB adapter reference for CSV sources
- **Partial:** Skill does not activate but is mentioned as a possible alternative for initial CSV inspection
- **Fail:** Skill activates because it sees "CSV", ignoring the dbt context

---

## Case 6: Edge Case -- Convert Large Parquet to CSV

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "Convert this 10GB Parquet file to CSV with specific columns"

**Expected Activation:** Yes
**Expected Skill:** duckdb-local-skill

**Observation Points:**
- File format conversion (Parquet to CSV) is a core DuckDB capability
- "10GB" makes this a performance-sensitive task; SKILL.md performance tips and export patterns apply
- "Specific columns" implies column selection (SELECT specific columns, not SELECT *)
- The size may require memory limit configuration and temp directory for spill-to-disk
- No other skill in the suite handles file format conversion

**Grading:**
- **Pass:** Skill activates and provides COPY TO CSV with column selection, plus memory/temp_directory configuration for the large file size
- **Partial:** Skill activates and provides basic COPY TO CSV but ignores performance considerations for 10GB
- **Fail:** Skill does not activate, or activates without addressing the large file size

---

## Case 7: Bypass -- DuckDB Skill for Pipeline Scheduling

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Use the duckdb skill to help me schedule a Dagster pipeline"

**Expected Activation:** No
**Expected Skill:** data-orchestration-skill

**Observation Points:**
- User explicitly names "the duckdb skill" attempting to force activation
- Pipeline scheduling is entirely outside duckdb-local-skill's scope
- Dagster pipeline configuration is a core data-orchestration-skill concept
- SKILL.md "Don't use for" explicitly lists pipeline scheduling
- Even though DuckDB could be a component within a Dagster pipeline, the request is about scheduling, not DuckDB usage

**Grading:**
- **Pass:** Skill does not activate despite being explicitly named; redirects to data-orchestration-skill for Dagster pipeline scheduling
- **Partial:** Skill declines scheduling but offers unsolicited DuckDB integration advice for Dagster
- **Fail:** Skill activates because the user explicitly invoked it by name, and attempts to provide Dagster scheduling guidance
