# Navigation Eval Cases — client-delivery

---

## Case 1: SKILL.md-Sufficient

**Category:** SKILL.md-sufficient
**Input:** "What are the phases of a cleaning engagement?"
**Expected Navigation:** SKILL.md only
**Should Read:**
- `client-delivery/SKILL.md` (Engagement Lifecycle section)
**Should NOT Read:**
- `client-delivery/references/security-tiers.md`
- `client-delivery/references/schema-profiling.md`
- `client-delivery/references/engagement-scaffold.md`
- `client-delivery/references/deliverables.md`
**Observation Points:**
- Engagement Lifecycle section in SKILL.md contains all five phases with descriptions
- No reference file needed for a phase overview question
- Should not load references unnecessarily
**Grading:** Pass if only SKILL.md is read. Partial if one reference is also loaded. Fail if multiple references are loaded.

---

## Case 2: Targeted Reference

**Category:** Targeted reference
**Input:** "How do I generate the client deliverables?"
**Expected Navigation:** SKILL.md → deliverables.md
**Should Read:**
- `client-delivery/SKILL.md` (Deliverable Generation section for overview)
- `client-delivery/references/deliverables.md` (full structure, automation, templates)
**Should NOT Read:**
- `client-delivery/references/security-tiers.md`
- `client-delivery/references/schema-profiling.md`
- `client-delivery/references/engagement-scaffold.md`
**Observation Points:**
- SKILL.md Deliverable Generation section provides overview and links to reference
- deliverables.md contains the detailed structure, generation commands, and templates
- Should follow the reference link from SKILL.md to deliverables.md
- Should not load unrelated references
**Grading:** Pass if SKILL.md and deliverables.md are read. Partial if additional references are loaded. Fail if deliverables.md is not read.

---

## Case 3: Cross-Reference Resistance

**Category:** Cross-reference resistance
**Input:** "What security tier should I use?"
**Expected Navigation:** SKILL.md only
**Should Read:**
- `client-delivery/SKILL.md` (Security Tier Selection section)
**Should NOT Read:**
- `client-delivery/references/security-tiers.md` (not needed for basic selection)
- `shared-references/data-engineering/security-tier-model.md`
- `shared-references/data-engineering/security-compliance-patterns.md`
**Observation Points:**
- SKILL.md Security Tier Selection section contains the quick decision table
- The question asks for tier selection guidance, not procedural implementation
- security-tiers.md is only needed when implementing a specific tier's workflow
- Should resist loading reference files for a question answerable from SKILL.md
**Grading:** Pass if only SKILL.md is read. Partial if security-tiers.md is also loaded. Fail if shared references are loaded.

---

## Case 4: Shared Reference

**Category:** Shared reference
**Input:** "How does the consulting security model relate to organizational tiers?"
**Expected Navigation:** SKILL.md → shared security-tier-model.md
**Should Read:**
- `client-delivery/SKILL.md` (Security Posture section for consulting-specific tiers)
- `shared-references/data-engineering/security-tier-model.md` (organization-level tier model)
**Should NOT Read:**
- `client-delivery/references/security-tiers.md` (procedural detail, not the organizational model)
- `client-delivery/references/schema-profiling.md`
- `client-delivery/references/deliverables.md`
**Observation Points:**
- Question asks about relationship between consulting tiers and organizational model
- SKILL.md Security Posture section shows consulting-specific tier capabilities
- Shared security-tier-model.md provides the organizational tier framework
- Should follow the shared reference link, not the consulting-specific reference
**Grading:** Pass if SKILL.md and shared security-tier-model.md are read. Partial if consulting security-tiers.md is also loaded. Fail if shared reference is not consulted.
