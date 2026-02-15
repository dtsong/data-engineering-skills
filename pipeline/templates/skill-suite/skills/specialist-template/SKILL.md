---
name: SUITE_NAME-specialist
description: >
  Specialist for AREA within the SUITE_NAME suite. Handles SPECIFIC_SCOPE.
model_tier: MODEL_TIER
---

# Specialist Name

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| REASONING_DEMAND | PREFERRED | ACCEPTABLE | MINIMUM |

## Inputs
- `required_input`: DESCRIPTION
- `optional_input` (optional): DESCRIPTION

## Procedure

Step 1: IMPERATIVE_INSTRUCTION.
  - Detail substep
  - If CONDITION → BRANCH_A. Otherwise → BRANCH_B.

Step 2: IMPERATIVE_INSTRUCTION.
  - Note: EDGE_CASE — context that prevents known failure mode.

Step 3: Verify output.
  - Check each item in the Output Contract

## Output Format

```json
{
  "result": "EXAMPLE_VALUE"
}
```

## Handoff

Return to coordinator with:
```json
{ "completed": "specialist-name", "results": {...} }
```

## References
| File | Load When | Contains |
|------|-----------|----------|
| `references/CHECKLIST.md` | Step 2 if CONDITION | Detailed checklist for X |
