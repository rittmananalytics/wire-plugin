---
wire_schema: "1.0"
command: validate
artifact: conceptual_model
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: conceptual_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
  - utils/mml_import
description: Validate conceptual model completeness and correctness
argument-hint: <project-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Conceptual Model Validation Command

## Purpose

Validate the generated conceptual entity model against quality criteria before presenting it to business stakeholders for review. Checks that:
- All business entities from functional requirements are represented
- All relationships have cardinality defined and labelled
- The diagram contains no column-level implementation detail (it must be conceptual, not physical)
- Entity names follow the PascalCase singular convention
- Open questions are documented rather than silently resolved
- Mermaid erDiagram syntax is correct

## Usage

```bash
/wire:conceptual_model-validate YYYYMMDD_project_name
```

## Prerequisites

- `conceptual_model`: `generate: complete`

## Workflow

### Step 1: Verify Conceptual Model Exists

1. Check `conceptual_model.generate == complete` in `status.md`
2. Check that `design/conceptual_model.md` exists

If not found:
```
Error: Conceptual model not yet generated.
Run: /wire:conceptual_model-generate <project_id>
```

### Step 2: Read Inputs

1. Read `.wire/<project_id>/design/conceptual_model.md`
2. Read `.wire/<project_id>/requirements/requirements_specification.md` (to cross-check entity coverage)

### Step 3: Run Validation Checks

Work through each check systematically. For each Critical failure, the overall result is FAIL. For Major failures, use judgement — multiple Major failures also constitute FAIL.

**Validation Checklist**:

| Check | Rule | Severity |
|-------|------|----------|
| Entity coverage | Every business noun appearing in Functional Requirements (FR-*) sections appears as an entity, or is explicitly listed in Section 4 (Out of Scope) | Critical |
| Cardinality completeness | Every relationship line in the erDiagram has a valid cardinality marker at both ends (e.g. `\|\|--o{`, `}o--o{`) | Critical |
| Relationship labels | Every relationship line has a quoted label (e.g. `"enrolled in"`) | Critical |
| No column leakage | The erDiagram block contains no `{ }` column definitions — entity-only format only | Critical |
| Mermaid syntax validity | No unclosed quotes, malformed cardinality markers, or duplicate entity definitions | Critical |
| PascalCase naming | All entity names are singular PascalCase (e.g. `Student` not `students`, `STUDENT`, or `student_record`) | Major |
| Entity descriptions | Every entity in Section 1 (Entity Inventory) has a description and at least 2 key business attributes | Major |
| Reference legibility | Every reference code cited from other artifacts (e.g. FR-n) is expanded at first mention or resolved in the Reference key table — run the `reference_legibility` check per `specs/utils/reference_legibility.md` | Major |
| Relationship narrative | Section 3 contains at least one explanatory sentence per relationship line in the diagram | Major |
| Open questions documented | Any relationship or entity that is ambiguous has been listed in Section 5 rather than silently resolved | Major |
| Out-of-scope section present | If any entities were considered and excluded, Section 4 is populated | Info |
| Volume estimates | At least some entities have volume/frequency information | Info |

### Step 4: Generate Validation Report

```
## Conceptual Model Validation: [PROJECT_NAME]

**Status**: PASS | FAIL
**Validated**: [date]

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Entity coverage | ✅/❌ | [e.g. "Assignment entity missing — referenced in FR-4"] |
| Cardinality completeness | ✅/❌ | [e.g. "STUDENT -- ENROLMENT line missing cardinality"] |
| Relationship labels | ✅/❌ | |
| No column leakage | ✅/❌ | |
| Mermaid syntax validity | ✅/❌ | |
| PascalCase naming | ✅/⚠️ | |
| Entity descriptions | ✅/⚠️ | |
| Relationship narrative | ✅/⚠️ | |
| Open questions documented | ✅/⚠️ | |
| Out-of-scope section | ✅/⚠️ | |
| Volume estimates | ✅/⚠️ | |

### Issues Found

[List each Critical and Major issue with location and suggested fix. Example:]
❌ CRITICAL: Entity 'Assignment' missing — referenced in FR-4 (assignment mark tracking)
   → Add Assignment entity to Section 1 and erDiagram

❌ CRITICAL: Relationship line "STUDENT -- ENROLMENT" has no cardinality markers
   → Change to "STUDENT ||--o{ ENROLMENT : \"enrolled in\""

⚠️ MAJOR: 'pastoral_note' should be 'PastoralNote' (PascalCase)
   → Rename entity throughout document

### Next Steps

[If PASS]:
  /wire:conceptual_model-review <project_id>

[If FAIL]:
  Fix the issues listed above in design/conceptual_model.md, then re-run:
  /wire:conceptual_model-validate <project_id>
```

### Step 5: Update Status

```yaml
conceptual_model:
  validate: pass | fail
  validated_date: [today]
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `conceptual_model`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Entities in Requirements That Are Genuinely Out of Scope

If an entity is referenced in requirements but is intentionally out of scope (e.g. a future phase deliverable), it must appear in Section 4 with the reason. It is not a validation failure if it is explicitly listed there — it is a failure only if it is completely absent.

### Relationship in Diagram Not Explained in Narrative

If Section 3 is missing a relationship that appears in the erDiagram, add an ⚠️ Major flag. The narrative is important for business stakeholders who cannot read ERD notation.

### Mermaid Syntax Errors

Common Mermaid erDiagram syntax issues to check:
- Relationship labels must be in double quotes: `"label"` not `'label'` or unquoted
- Cardinality markers: valid options are `||`, `o|`, `|o`, `o{`, `{o`, `}|`, `|}`, `}o`, `o}`
- Entity names cannot contain spaces or hyphens (use PascalCase to avoid)
- Each entity can only be defined once in the diagram

## Output

- Validation report (displayed to user)
- Updates `.wire/<project_id>/status.md` with validate result and date


---

## Check: `modality_coverage`

Runs only when `status.md` has `model_source: modality`. Skipped with the reason
recorded otherwise, never reported as PASS.

Both directions, per `specs/utils/mml_import.md`, "The `modality_coverage` check":

1. Every conceptual entity in the `.mml` files appears in this document or in its
   explicitly-excluded list with a reason. Unaccounted entities are FAIL, named.
2. Every entity in this document maps to an MML entity or to a requirement. An
   entity in neither is FAIL, named.

Entities with `type = metric` are outside direction 1: they are semantic-layer
measure candidates, not conceptual entities.

**A missing `entity_resolutions.mml` is never a failure of this check.** The
Modality specification does not define that block, so a model written to the
specification never has one. Treating its absence as a gap would fail every
hand-authored model.

The same applies to a missing `logical_relationships.mml`: cardinality falls
through to the `relationship` block and then the inline verb, and only a
relationship that yields nothing in all three places is `undetermined`.
