# Skill Governance Specification v1.0

Defines token budgets, architecture rules, writing rules, and enforcement for all skills in this repository.

## 1. Token Budgets (Hard Limits)

| File Type | Max Words | Max Tokens | Notes |
|-----------|-----------|------------|-------|
| Coordinator SKILL.md | 600 | 800 | Suite entry point only |
| Specialist SKILL.md | 1,500 | 2,000 | Loaded one at a time |
| Standalone SKILL.md | 1,500 | 2,000 | Self-contained skill |
| Reference file | 1,100 | 1,500 | Loaded conditionally |

**Token estimation:** `words x 1.33`

**Maximum simultaneous context load:** 5,000 tokens (coordinator + largest specialist + largest reference in a suite).

**Standalone context load:** SKILL.md tokens only.

### Overrides

Per-file overrides may be specified in `pipeline/config/budgets.json` under the `overrides` key. Overrides use the file path relative to the repo root as key and a `max_tokens` value.

## 2. File Classification

Classification determines which budget applies to a given file.

| Condition | Classification |
|-----------|---------------|
| Path contains `references/` | Reference |
| File is `SKILL.md` with sibling `skills/` directory | Coordinator |
| File is `SKILL.md` inside a `skills/` directory | Specialist |
| File is `SKILL.md` (none of the above) | Standalone |

### Excluded Paths

These paths are exempt from governance checks:
- `pipeline/` (governance infrastructure itself)
- `eval-cases/` (evaluation artifacts)
- `node_modules/` (dependencies)
- `.github/` (CI configuration)

## 3. Architecture Rules

1. **Coordinators contain ONLY:** classification logic, skill registry, load directive, handoff protocol.
2. **Load one specialist at a time** — never pre-load multiple specialists.
3. **Checklists exceeding 10 items** go in reference files, loaded conditionally.
4. **Eval cases and templates** live outside skill directories.
5. **No cross-references between specialist skills** — use handoff protocol. Shared references in `shared-references/` are exempt.

## 4. Writing Rules

1. **Procedure steps** use imperative sentences — no explanatory prose.
2. **Decision points** as inline conditionals — no nested sub-sections.
3. **One compact output example per skill** — no redundant schema descriptions.
4. **Reference files** are pure content — no preamble or meta-instructions.

### Prose Patterns to Avoid

The following patterns indicate explanatory prose in procedure sections:
- Sentences starting with "This is because..."
- Sentences starting with "The reason for..."
- Sentences starting with "Note that..."
- Paragraphs exceeding 3 sentences in procedure sections
- Passive voice in imperative contexts ("should be done" vs "do")

## 5. Frontmatter Requirements

Every `SKILL.md` must have YAML frontmatter with:

### Required Fields

| Field | Format | Validation |
|-------|--------|------------|
| `name` | kebab-case string | Must match `^[a-z][a-z0-9-]*$` |
| `description` | String | Minimum 10 words |

### Optional Fields

Fields like `license`, `metadata`, `version` are permitted but generate a warning if not in the recognized set: `name`, `description`, `license`, `metadata`.

## 6. Enforcement

### Pre-commit Hooks

All hooks run on the `pre-commit` stage unless noted:

| Hook | Purpose | Blocks Commit? |
|------|---------|---------------|
| `check_token_budget` | Word/token counts vs budgets | Yes |
| `check_frontmatter` | YAML frontmatter validation | Yes |
| `check_references` | Referenced files exist on disk | Yes |
| `check_isolation` | No cross-skill references | Yes |
| `check_prose` | Explanatory prose patterns | No (warn) |
| `check_context_load` | Suite context load ceiling | Yes |
| `check_commit_msg` | Conventional commit format | Yes (commit-msg stage) |

### Conventional Commit Format

Commit messages must match: `type(scope): description`

Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`, `revert`, `skill`.

Scope is optional. Description must be lowercase first character, no trailing period.

### CI Validation

CI workflows provide a safety net beyond local hooks:
- **skill-lint**: Runs all hooks on push/PR
- **skill-analyze**: Pattern analysis on PRs
- **skill-eval**: Evaluation regression testing
- **skill-publish**: Package and release on version tags

### Manual Validation

Run `pre-commit run --all-files` to check compliance manually.

## 7. Versioning

This spec follows semantic versioning. Breaking changes increment the major version.

Current version: **1.0.0**
