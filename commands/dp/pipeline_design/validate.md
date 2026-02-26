---
description: Validate pipeline design
argument-hint: <project-folder>
---

# Validate pipeline design

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.agent_v2` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.agent_v2/` in specs refers to the `.agent_v2/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Validate pipeline design and data flow diagram against best practices
argument-hint: <project-folder>
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
/dp:pipeline_design:validate YYYYMMDD_project_name
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
Run: /dp:pipeline_design:generate <project_id>
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
| Staging model names | All staging models follow `stg_<source>__<entity>` naming convention | Critical |
| Warehouse model names | All warehouse models follow `<entity>_fct` or `<entity>_dim` convention | Major |
| Error handling specified | Section 3.4 (Error Handling) is non-empty and covers failure detection and alerting | Major |
| Scheduling defined | Section 3.5 (Scheduling) specifies refresh cadences for all sources | Major |
| Design decisions documented | All trade-off decisions are listed as PD-N items, not silently resolved | Major |
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
  /dp:pipeline_design:review <project_id>

[If FAIL]:
  Fix issues in design/pipeline_architecture.md, then re-run:
  /dp:pipeline_design:validate <project_id>
```

### Step 5: Update Status

```yaml
pipeline_design:
  validate: pass | fail
  validated_date: [today]
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
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
- Updates `.agent_v2/<project_id>/status.md` with validate result and date

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /dp:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/dp:*` command that was invoked (e.g., `/dp:requirements:generate`, `/dp:new`, `/dp:dbt:validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/dp:new` created a new project
  - `archived` — `/dp:archive` archived a project
  - `removed` — `/dp:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:35 | /dp:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /dp:requirements:generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /dp:requirements:validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /dp:requirements:review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /dp:conceptual_model:generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /dp:conceptual_model:validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /dp:conceptual_model:generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /dp:conceptual_model:validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /dp:conceptual_model:review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /dp:conceptual_model:generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /dp:conceptual_model:validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /dp:conceptual_model:review | approved | Reviewed by John Doe |
```
