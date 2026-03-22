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

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.3.0\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"pipeline_design-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.3.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

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
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
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
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
