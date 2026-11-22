---
wire_schema: "1.0"
command: validate
artifact: pipeline_design
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
  - artifact: pipeline_design
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
  - utils/mml_import
description: Validate pipeline design and data flow diagram against best practices
argument-hint: <project-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pipeline Design Validation Command

## Purpose

Validate the generated pipeline architecture document and embedded Data Flow Diagram against quality standards:
- All source systems from requirements are addressed
- Replication strategy is specified for each source
- Data Flow Diagram is present, complete, and syntactically valid
- All in-scope conceptual model entities are traceable through the DFD
- Design decisions are documented (not silently resolved)
- Error handling and scheduling are specified

## Usage

```bash
/wire:pipeline_design-validate YYYYMMDD_project_name
```

## Prerequisites

- `pipeline_design`: `generate: complete`

## Workflow

### Step 1: Verify Pipeline Design Exists

1. Check `pipeline_design.generate == complete` in `status.md`
2. Check that `design/pipeline_architecture.md` exists

If not found:
```
Error: Pipeline design not yet generated.
Run: /wire:pipeline_design-generate <project_id>
```

### Step 2: Read Inputs

1. Read `design/pipeline_architecture.md`
2. Read `requirements/requirements_specification.md` (for source system and entity cross-check)
3. Read `design/conceptual_model.md` (to verify entity coverage in DFD)

### Step 3: Run Validation Checks

**Architecture Checks**:

| Check | Rule | Severity |
|-------|------|----------|
| Source system coverage | Every source system named in requirements appears in Section 1 | Critical |
| Replication strategy defined | Every source system has a replication method specified (no blanks) | Critical |
| Staging model names | All staging models follow `stg_<source>__<entity>` naming convention (plural or singular entity name) | Critical |
| Warehouse model names | All warehouse models follow `wh_<group>__<entity>_dim`, `_fact` or `_xa` (extended aggregate). Existing `_agg` models are accepted. | Major |
| Error handling specified | Section 3.4 (Error Handling) is non-empty and covers failure detection and alerting | Major |
| Scheduling defined | Section 3.5 (Scheduling) specifies refresh cadences for all sources | Major |
| Design decisions documented | All trade-off decisions are listed as PD-N items, not silently resolved | Major |
| Reference legibility | Every PD code has a bold-title minting site (`**PD-N: Title**`), and every code cited from other artifacts (e.g. FR-n) is expanded at first mention or resolved in a Reference key table — run the `reference_legibility` check per `specs/utils/reference_legibility.md` | Major |
| Technology stack complete | Section 6 lists all layers with technology choices | Info |
| Security/governance addressed | Section 7 covers PII handling and access controls | Info |

**Data Flow Diagram Checks**:

| Check | Rule | Severity |
|-------|------|----------|
| DFD present | Section 4 exists and contains a Mermaid `graph LR` or `graph TD` block | Critical |
| Source systems in DFD | Every source system from Section 1 appears as a node in the DFD | Critical |
| Entity coverage in DFD | Every in-scope entity from the conceptual model appears (directly or via a model) in the DFD | Critical |
| BI layer present | The DFD includes at least one Explore and one Dashboard node | Major |
| Subgraph labels | DFD uses `subgraph` blocks to group Source / Ingestion / Staging / Warehouse / BI layers | Major |
| Arrows are directional | All connections use `-->` (directed), not `---` (undirected) | Major |
| Node labels meaningful | Node labels contain system/model names, not generic placeholders (`<placeholder>`) | Major |
| Mermaid syntax valid | No unclosed subgraphs, malformed node definitions, or syntax errors | Critical |

### Step 4: Generate Validation Report

```
## Pipeline Design Validation: [PROJECT_NAME]

**Status**: PASS | FAIL
**Validated**: [date]

### Architecture Checks

| Check | Status | Notes |
|-------|--------|-------|
| Source system coverage | ✅/❌ | |
| Replication strategy | ✅/❌ | |
| Staging model naming | ✅/❌ | [e.g. "stg_focus_notes should be stg_focus__student_notes"] |
| Warehouse model naming | ✅/⚠️ | |
| Error handling | ✅/⚠️ | |
| Scheduling | ✅/⚠️ | |
| Design decisions documented | ✅/⚠️ | |
| Technology stack | ✅/⚠️ | |
| Security/governance | ✅/⚠️ | |

### Data Flow Diagram Checks

| Check | Status | Notes |
|-------|--------|-------|
| DFD present | ✅/❌ | |
| Source systems in DFD | ✅/❌ | |
| Entity coverage in DFD | ✅/❌ | [e.g. "Enrolment entity from conceptual model not shown"] |
| BI layer present | ✅/⚠️ | |
| Subgraph labels | ✅/⚠️ | |
| Directional arrows | ✅/⚠️ | |
| Node labels meaningful | ✅/⚠️ | |
| Mermaid syntax valid | ✅/❌ | |

### Issues Found

[List each Critical and Major issue with location and suggested fix]

### Next Steps

[If PASS]:
  /wire:pipeline_design-review <project_id>

[If FAIL]:
  Fix issues in design/pipeline_architecture.md, then re-run:
  /wire:pipeline_design-validate <project_id>
```

### Step 5: Update Status

```yaml
pipeline_design:
  validate: pass | fail
  validated_date: [today]
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `pipeline_design`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Placeholder Text in DFD

If the DFD contains unreplaced `<placeholder>` text (e.g. `<System Name>`, `<entity>`), flag as Major — this indicates the DFD was not populated with project-specific values.

### Entity in Conceptual Model Has No Source

If a conceptual model entity does not appear anywhere in the DFD (no staging or warehouse node), flag as Critical — this means there is no defined path to bring that entity's data into the warehouse. It may indicate a data gap that needs to be resolved with the client.

### Multiple Replication Scenarios Still Open

If the pipeline design presents multiple scenarios (A/B/C) but no recommendation has been made and no design decision (PD-N) is recorded for the selection, flag as Major. The scenario must be resolved before development begins.

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
