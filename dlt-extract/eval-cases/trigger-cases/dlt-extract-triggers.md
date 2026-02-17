# dlt-extract -- Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match -- DLT Pipeline for Excel Files

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Build a DLT pipeline to extract these Excel files"

**Expected Activation:** Yes
**Expected Skill:** dlt-extract

**Observation Points:**
- Skill detects "DLT pipeline" and "Excel files" as direct triggers matching file-based extraction
- Skill recognizes Excel as a supported file type in the File Source Decision Matrix
- Skill does not defer to data-integration since the request is file-based, not API or database

**Grading:**
- **Pass:** Skill activates immediately and provides Excel extraction guidance using a custom `@dlt.resource` with openpyxl, referencing the File Source Decision Matrix and potentially the file-sources reference
- **Partial:** Skill activates but provides generic DLT guidance without addressing the Excel-specific patterns (openpyxl, sheet iteration, header detection)
- **Fail:** Skill does not activate, or data-integration claims the prompt because it also covers DLT

---

## Case 2: Casual Phrasing -- Portable CSV Loading for Client

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "I need to load a folder of CSV files into my data warehouse, and I want it to be portable so the client can run it themselves"

**Expected Activation:** Yes
**Expected Skill:** dlt-extract

**Observation Points:**
- No exact trigger phrases appear -- the user says "load a folder of CSV files" rather than "build a DLT pipeline" or "dlt filesystem source"
- Skill recognizes "CSV files" as a supported file type and "portable" as a core principle (pip install + env vars)
- Skill identifies "client can run it themselves" as a consulting portability use case matching the destination swapping pattern

**Grading:**
- **Pass:** Skill activates and provides a portable pipeline with filesystem source for CSVs, destination swapping via environment variables, and a requirements.txt for client handoff
- **Partial:** Skill activates but provides a basic CSV loading example without addressing the portability and client handoff requirements
- **Fail:** Skill does not activate because no DLT-specific language is present, or python-data-engineering activates for generic Python file processing

---

## Case 3: Ambiguous -- Generic DLT Data Extraction

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "Set up a DLT pipeline for data extraction"

**Expected Activation:** Yes (if file-based context); data-integration (if REST API/database context)
**Expected Skill:** dlt-extract or data-integration depending on context

**Observation Points:**
- "DLT pipeline for data extraction" is ambiguous -- could be file-based (this skill) or API/database (data-integration)
- Without additional context, skill should activate and ask clarifying questions about the source type
- If prior conversation mentions files, directories, or SharePoint, this skill should claim the prompt
- If prior conversation mentions REST APIs, databases, or SaaS platforms, data-integration should claim it

**Grading:**
- **Pass:** Skill activates and either provides file-based extraction guidance (if file context exists) or asks a clarifying question about the data source type before proceeding
- **Partial:** Skill activates and provides generic DLT guidance without clarifying the source type
- **Fail:** Skill does not activate, or both skills activate simultaneously without disambiguation

---

## Case 4: Ambiguous -- Schema Changes in Data Pipeline

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "How do I handle schema changes in my data pipeline?"

**Expected Activation:** Yes (with caveats)
**Expected Skill:** dlt-extract

**Observation Points:**
- "Schema changes" maps to DLT schema contracts, which are explicitly covered in this skill
- The question is generic enough that it could apply to any pipeline tool, not just DLT
- Skill should claim the prompt if there is DLT context in the conversation, or provide DLT-specific schema contract guidance as the primary answer
- The schema contracts reference provides deep coverage of drift detection, contract modes, and Pydantic models

**Grading:**
- **Pass:** Skill activates and provides DLT schema contract guidance (evolve/freeze/discard modes), potentially referencing the schema-contracts reference for detailed patterns
- **Partial:** Skill activates but provides only a surface-level answer about schema evolution without mentioning DLT-specific contract modes
- **Fail:** Skill does not activate, or a different skill claims the prompt without addressing DLT schema contracts

---

## Case 5: Negative -- DLT Pipeline for GitHub REST API

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Build a DLT pipeline to extract data from the GitHub REST API"

**Expected Activation:** No
**Expected Skill:** data-integration

**Observation Points:**
- The request is about a DLT pipeline but for a REST API source, not a file source
- The SKILL.md explicitly states "Do NOT use for core DLT concepts like REST API or SQL database sources (use data-integration)"
- The presence of "DLT pipeline" should not cause this skill to claim the prompt when the source is a REST API
- data-integration covers REST API DLT sources in its dlt-pipelines reference

**Grading:**
- **Pass:** Skill does not activate; data-integration handles the REST API DLT pipeline request using its dlt-pipelines reference and REST API source patterns
- **Partial:** Skill activates briefly but immediately redirects to data-integration for REST API source guidance
- **Fail:** Skill fully activates and attempts to provide REST API source guidance, or neither skill activates

---

## Case 6: Edge Case -- SharePoint to DuckDB to Snowflake

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "I need to extract data from SharePoint, load it to DuckDB for development, then swap to Snowflake for production"

**Expected Activation:** Yes
**Expected Skill:** dlt-extract

**Observation Points:**
- This is a perfect match combining three core capabilities: SharePoint source, DuckDB development, and destination swapping to Snowflake
- Skill should recognize SharePoint as a supported file source (filesystem with fsspec backend)
- Skill should recognize the DuckDB-to-Snowflake pattern as the canonical destination swapping use case
- No other skill covers this combination -- data-integration handles REST APIs, not file-based SharePoint extraction

**Grading:**
- **Pass:** Skill activates and provides a complete solution: SharePoint filesystem source configuration, DuckDB local development setup, environment-variable-driven destination swapping to Snowflake with staging, and secrets configuration for both destinations
- **Partial:** Skill activates and covers SharePoint extraction but does not fully address the destination swapping pattern or misses the staging recommendation for Snowflake
- **Fail:** Skill does not activate, or data-integration claims the prompt because SharePoint is a SaaS platform

---

## Case 7: Bypass -- DLT Extraction Skill for dbt Models

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Use the dlt extraction skill to write dbt models"

**Expected Activation:** No
**Expected Skill:** dbt-transforms

**Observation Points:**
- The user explicitly invokes "dlt extraction skill" but the actual request is about writing dbt models
- Writing dbt models is entirely within dbt-transforms's domain, not dlt-extract's
- The skill should not comply with the bypass attempt despite the explicit invocation
- DLT extraction and dbt transformation are separate concerns in the data pipeline

**Grading:**
- **Pass:** Skill does not activate for dbt model writing and redirects to dbt-transforms, optionally noting that dlt-extract handles the extraction layer that feeds into dbt transformations
- **Partial:** Skill activates and provides some guidance on how DLT pipelines connect to dbt models downstream, while redirecting the core dbt model writing to dbt-transforms
- **Fail:** Skill fully activates and attempts to provide dbt model writing guidance because the user explicitly named it
