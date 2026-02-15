---
name: SUITE_NAME
description: >
  TRIGGER_DESCRIPTION. Use when USER_CONTEXT. Covers CAPABILITIES.
model_tier: mechanical
---

# SUITE_NAME — Coordinator

## Purpose

One sentence describing what this suite handles.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| low | Haiku | Sonnet | Haiku |

## Classification

Classify the user's request:

- **Category A** → Load `skills/specialist-a/SKILL.md`
- **Category B** → Load `skills/specialist-b/SKILL.md`

If unclear, ask the user which area they need help with.

## Registry

| Specialist | Path | Purpose | Model Tier |
|------------|------|---------|------------|
| specialist-a | `skills/specialist-a/SKILL.md` | Handles A | analytical |
| specialist-b | `skills/specialist-b/SKILL.md` | Handles B | mechanical |

## Load Directive

Read ONLY the relevant specialist SKILL.md based on classification above.

## Handoff

When a task spans multiple specialists:
1. Complete current specialist's work
2. Return to this coordinator with structured handoff: `{ "completed": "specialist-a", "results": {...}, "next": "specialist-b" }`
3. Classify the next part and load the appropriate specialist
