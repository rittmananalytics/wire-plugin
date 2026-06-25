---
description: Client DPO/legal sign-off gate for the data residency assessment
argument-hint: <release-folder>
---

# Client DPO/legal sign-off gate for the data residency assessment

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Sign-off gate for the data residency assessment — client DPO/legal determines the flagged items and signs off
---

# Data Residency Assessment — Review

## Purpose

The sign-off gate for the data residency assessment (Stage 1 deliverable D3). RA presents the structured assessment; the client's DPO/legal addresses every **[CLIENT DPO/LEGAL]** item — above all the lawful basis and the historical-window retention ruling — and signs off. RA does not own these determinations; the gate cannot be cleared by RA alone.

## Prerequisites

- `migration/data_residency_assessment.md` exists with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions of GDPR, data residency, retention, the historical data window, or the DPA.

### Step 2: Present the assessment for sign-off

Display:
- The processor-not-counsel framing and the controller/processor split
- The data inventory in scope and the historical window
- The residency constraints for the target region
- The consolidated **[CLIENT DPO/LEGAL]** items requiring the client's determination
- The processor safeguards RA will implement

### Step 3: Gather the client's determinations

Walk the client DPO/legal through each **[CLIENT DPO/LEGAL]** item and record their determination in the document — in particular:

1. The lawful basis for processing and retaining the data being migrated.
2. The retention ruling on the ~3-year historical window — migrate the full window, or trim it.
3. Any cross-border transfer mechanism required (e.g. SCCs), if data leaves the region.
4. Any additional safeguards the client requires of RA as processor.

RA records the client's answers; RA does not supply them.

### Step 4: Record decision and sign-off

Complete the sign-off block. Approve only when every **[CLIENT DPO/LEGAL]** item is addressed and the client DPO/legal has signed:

```markdown
## Sign-off

- All [CLIENT DPO/LEGAL] items addressed by the client: ☑ / ☐
- Historical-window retention basis confirmed by the client: ☑ / ☐

**Client DPO / legal sign-off**: {{CLIENT_DPO_NAME}}  **Date**: {{TODAY}}
**RA reviewer**: {{REVIEWER_NAME}}  **Date**: {{TODAY}}
**Decision**: approved | changes_requested
```

If any item is unresolved, record `changes_requested` and list what the client still owes before sign-off.

### Step 5: Update status

```yaml
artifacts:
  data_residency_assessment:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    client_signoff: "{{CLIENT_DPO_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:migration-strategy-generate $ARGUMENTS
```

## Review Gate

This is the GDPR / data-residency sign-off gate (Stage 1, D3). It clears only on the client DPO/legal's determination of the flagged items — RA cannot self-approve, because the lawful basis and retention ruling are the controller's to make. The carve-out's bulk copy of the historical window proceeds against the retention basis confirmed here.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact_id, `Data Residency Assessment` as artifact_name, and the `file` value from `artifacts.data_residency_assessment` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `data_residency_assessment` as artifact, `review` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

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
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

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
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
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
