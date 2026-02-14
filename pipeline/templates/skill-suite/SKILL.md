---
name: {{SUITE_NAME}}
description: Use when [describe when this suite should activate — minimum 10 words for governance compliance]
---

# {{SUITE_NAME}} — Coordinator

## Purpose

[One sentence describing what this suite handles.]

## Classification

Classify the user's request:

- **[category-1]** → load `skills/[specialist-1]/SKILL.md`
- **[category-2]** → load `skills/[specialist-2]/SKILL.md`

If unclear, ask the user which area they need help with.

## Registry

| Specialist | Handles |
|------------|---------|
| [specialist-1] | [scope] |
| [specialist-2] | [scope] |

## Load Directive

Load ONE specialist at a time based on classification above.

## Handoff

When a task spans multiple specialists:
1. Complete current specialist's work
2. Return to this coordinator
3. Classify the next part
4. Load the appropriate specialist
