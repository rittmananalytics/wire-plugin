---
description: Human/client adjudication gate — turn the proposed batch partition into a committed schedule
argument-hint: <release-folder>
---

# Human/client adjudication gate — turn the proposed batch partition into a committed schedule

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
description: Human/client adjudication gate — turn the proposed domain-batch partition into a committed schedule
---

# Migration Batching — Review

## Purpose

Generate proposed a partition; this is where the team and client turn it into a committed schedule. The reviewer can rename, merge, or split batches, and assign target dates/sprints and owners. But any change that would violate a dependency edge from validate's Check 3 must either be rejected or explicitly accepted as a documented risk — record the risk acceptance with its rationale. Never silently let the DAG be violated.

## Prerequisites

- `migration/migration_batching.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to surface any Fathom recordings touching scheduling, domain ownership, or sprint sequencing.

### Step 2: Present the batching summary

Display:
- The batch summary table (batch_id, name, domain, object count, effort hours, depends_on_batches, batch-zero prerequisite)
- The batch-level dependency DAG
- The parallel-safe groupings
- The seed-reconciliation note from generate

Reaffirm to the reviewer that these are candidates — no batch has a committed date, owner, or approval yet. This gate is where that happens.

### Step 3: Adjudicate

For each batch, confirm or change its name, composition, and domain grouping, then assign a target date/sprint and an owner.

If a requested change (a merge, split, object move, or scheduling two dependent batches in parallel) would violate a dependency edge from validate's Check 3, surface it immediately: show the edge (objects, batches, direction) and require the reviewer to either **withdraw the change** or **record an explicit risk acceptance** with rationale before proceeding. Do not apply the change without one or the other.

### Step 4: Apply adjudication and record decision

Update `migration_batching.md` (and the affected `migration_batching.csv` rows, e.g. renamed or reassigned batches) to reflect the adjudicated outcomes. Append:

```markdown
## Review — Adjudication

**Internal reviewer**: {{RA_REVIEWER}}
**Client attendees**: {{CLIENT_NAMES}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Final batch schedule
| Batch | Name | Target date / sprint | Owner | Depends on |
|-------|------|---------------------|-------|-----------|

### Adjudicated changes
[Per change: batch, what changed (rename / merge / split / move / reschedule), and rationale]

### Risk acceptances
[Per acceptance: the dependency edge being overridden, who accepted it, and the rationale — or "none"]
```

### Step 5: Update status

```yaml
artifacts:
  migration_batching:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:migration-strategy-generate $ARGUMENTS
```

## Review Gate

This review is the point where the batch plan becomes a committed schedule. The migration strategy and sprint sequencing are built against the adjudicated batches. Re-running `migration-batching-generate` after this gate re-proposes candidates and requires re-adjudication.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact_id, `Migration Batching` as artifact_name, and the `file` value from `artifacts.migration_batching` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_batching` as artifact, `review` as action.

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
