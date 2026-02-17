# dlt-extract -- Navigation Eval Cases

Navigation evals test how the agent traverses the skill file tree during execution.
They are distinct from trigger evals (activation) and output evals (result correctness).

---

## Case 1: SKILL.md-sufficient -- Supported File Formats

**Category:** SKILL.md-sufficient

**Input:**
> "What file formats does DLT support for extraction?"

**Expected Navigation:**
1. Read `dlt-extract/SKILL.md`
2. Stop -- the File Source Decision Matrix section answers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** Any reference file

**Observation Points:**
- Agent locates the File Source Decision Matrix in SKILL.md
- Agent does not open any `references/` file
- Agent provides a list of supported file types (CSV, Excel, Parquet, JSON/NDJSON, SharePoint, SFTP) citing SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading references
- **Partial:** Agent reads SKILL.md and one reference but answer comes from SKILL.md
- **Fail:** Agent reads multiple references or answers without consulting SKILL.md

---

## Case 2: Targeted Reference -- Excel from SharePoint

**Category:** Targeted reference

**Input:**
> "How do I set up DLT to read Excel files from SharePoint?"

**Expected Navigation:**
1. Read `dlt-extract/SKILL.md`
2. Follow link to `references/file-sources.md`
3. Stop -- SharePoint backend config and Excel ingestion patterns are in the file sources reference

**Should Read:** `SKILL.md` -> `references/file-sources.md`
**Should NOT Read:** `references/source-patterns.md`, `references/schema-contracts.md`, `references/destinations.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the file-sources reference link
- Agent follows exactly one reference link (file-sources.md)
- Agent combines the Excel ingestion section (custom openpyxl resource) with the SharePoint section (fsspec backend config)
- Agent does not speculatively read other references

**Grading:**
- **Pass:** Agent reads SKILL.md then file-sources.md only, providing both Excel and SharePoint patterns
- **Partial:** Agent reads SKILL.md, file-sources.md, and one additional reference
- **Fail:** Agent reads 3+ references or skips file-sources.md

---

## Case 3: Cross-reference Resistance -- Basic CSV Pipeline

**Category:** Cross-reference resistance

**Input:**
> "Show me a basic DLT pipeline for CSV files"

**Expected Navigation:**
1. Read `dlt-extract/SKILL.md`
2. Stop -- the Quick Start Example section provides a complete CSV pipeline example

**Should Read:** `SKILL.md` only
**Should NOT Read:** `references/file-sources.md` (tempting but unnecessary for a basic example)

**Observation Points:**
- Agent locates the Quick Start Example in SKILL.md which shows a filesystem source reading CSVs
- Agent resists following the link to `references/file-sources.md` for the basic use case
- Agent provides the example directly from SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md Quick Start Example without loading file-sources.md
- **Partial:** Agent reads SKILL.md then file-sources.md but answer only uses SKILL.md content
- **Fail:** Agent loads file-sources.md and multiple other references for a basic example

---

## Case 4: Shared Reference -- DLT vs Fivetran for Client

**Category:** Shared reference

**Input:**
> "Should I use DLT or Fivetran for this client engagement?"

**Expected Navigation:**
1. Read `dlt-extract/SKILL.md`
2. Follow to shared reference `../shared-references/data-engineering/dlt-vs-managed-connectors.md`
3. Stop -- the comparison lives in the shared reference

**Should Read:** `SKILL.md` -> `../shared-references/data-engineering/dlt-vs-managed-connectors.md`
**Should NOT Read:** `references/source-patterns.md`, `references/file-sources.md`, `references/schema-contracts.md`, `references/destinations.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the need for a DLT vs managed connector comparison
- Agent navigates to the shared reference (outside the skill directory)
- Agent does not confuse shared references with skill-local references
- Agent provides a comparison framework from the shared reference, not just skill-local content

**Grading:**
- **Pass:** Agent reads SKILL.md then shared dlt-vs-managed-connectors.md only
- **Partial:** Agent reads SKILL.md, shared reference, and one skill-local reference
- **Fail:** Agent skips the shared reference or reads 3+ files total
