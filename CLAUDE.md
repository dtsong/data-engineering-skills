# Data Engineering Skills

## Skill Governance (v1.1)

All skills must comply with the Skill Governance Specification at
`pipeline/specs/SKILL-GOVERNANCE-SPEC.md`.

**Hard limits (enforced — blocks commits):**
- Valid frontmatter with name + description
- All referenced files must exist on disk
- No cross-specialist references (use handoff protocol)
- Suite context load ≤5,500 tokens (coordinator + largest specialist + largest reference)

**Targets (advisory — warns on commit):**
- Coordinator ≤800 tokens (~600w), Specialist ≤2,000 tokens (~1,500w), Reference ≤1,500 tokens (~1,100w)
- Exceeding targets is acceptable when justified by output quality. Document overrides in `pipeline/config/budgets.json`.

**Priority order:** Output quality > Structure > Efficiency > Size.

**Commands:** `skill-audit` (full check), `skill-check <dir>` (single skill), `skill-new <name>` (scaffold).
