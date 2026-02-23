# Pipeline — Governance Tooling

CI scripts, validation hooks, and specifications that enforce skill quality across the repository.

## Directory Structure

| Directory | Contents |
|-----------|----------|
| `config/` | Budget thresholds (`budgets.json`), model routing rules (`model-routing.yaml`), security suppressions |
| `hooks/` | Pre-commit hooks — frontmatter, references, isolation, context load, token budget, prose patterns |
| `scripts/` | Standalone analysis and packaging scripts — budget reports, eval runners, portability checks |
| `specs/` | Governance specifications that define the rules hooks enforce |
| `templates/` | Scaffold templates for new standalone skills and skill suites |

## Usage

### Run all pre-commit hooks

```bash
pre-commit run --all-files
```

### Individual hooks

```bash
python3 pipeline/hooks/check_frontmatter.py
python3 pipeline/hooks/check_references.py
python3 pipeline/hooks/check_context_load.py
python3 pipeline/hooks/check_isolation.py
python3 pipeline/hooks/check_token_budget.py
python3 pipeline/hooks/check_prose.py
```

### Budget and analysis reports

```bash
python3 pipeline/scripts/budget-report.py
python3 pipeline/scripts/context-load-analysis.py
bash pipeline/scripts/validate-structure.sh
```

## Specifications

- [Skill Governance Spec](specs/SKILL-GOVERNANCE-SPEC.md) — structural integrity, token budgets, writing rules
- [Skill Security Spec](specs/SKILL-SECURITY-SPEC.md) — credential handling, prompt injection prevention, scope constraints
- [Skill Model Routing Spec](specs/SKILL-MODEL-ROUTING-SPEC.md) — model preferences, budget zones, degradation rules
- [Skill Trigger Reliability Spec](specs/SKILL-TRIGGER-RELIABILITY-SPEC.md) — description quality, activation phrases, negative boundaries
