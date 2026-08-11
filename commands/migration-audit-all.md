---
description: Run all platform migration audits in parallel (5 core + optional reverse ETL)
argument-hint: <release-folder>
---

# Run all platform migration audits in parallel (5 core + optional reverse ETL)

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Run all platform migration audits in parallel using dynamic workflow (5 core audits + optional reverse ETL audit)
---

# Migration Audit All — Utility

## Purpose

Fans out all platform migration audit commands simultaneously using parallel subagents. Five core audits always run; a sixth (reverse ETL) runs automatically when `migration.reverse_etl_tool` is set in `status.md`. This reduces total wall-clock time from sequential hours to roughly the duration of the slowest individual audit.

## Arguments

`$ARGUMENTS` — the release folder path (required)

## Workflow

### Step 1: Confirm release type

Read `.wire/releases/$ARGUMENTS/status.md`. Confirm `release_type: platform_migration`. If not, stop.

Check `migration.reverse_etl_tool` — if set (e.g. `hightouch`), the reverse ETL audit will run as a sixth parallel subagent.

Confirm no audits are already complete unless the user explicitly wants to re-run them. List any already-complete audits.

### Step 2: Token cost confirmation

Present the following confirmation prompt — adjust the count and list based on whether reverse_etl_tool is set:

```
This command will launch [5|6] parallel audit subagents simultaneously:
  1. ingestion_audit       — Fivetran connector catalog
  2. db_object_audit       — Database object catalog (INFORMATION_SCHEMA query)
  3. security_audit        — IAM roles and policies catalog
  4. dbt_audit             — dbt project model catalog
  5. orchestration_audit   — Orchestration job catalog
  6. reverse_etl_audit     — Hightouch sync catalog [only if reverse_etl_tool is set]

Estimated token usage: HIGH (particularly for large warehouses or dbt projects).

How would you like to proceed?

A) Run all audits in parallel (fastest — recommended for most engagements)
B) Run audits sequentially instead (lower peak token usage — use for very large projects)
```

Wait for user choice.

**If option B (sequential)** is chosen:
Output the individual commands in order and stop:

```
Run each audit in sequence:

1. /wire:ingestion-audit-generate $ARGUMENTS
2. /wire:db-object-audit-generate $ARGUMENTS
3. /wire:security-audit-generate $ARGUMENTS
4. /wire:dbt-audit-generate $ARGUMENTS
5. /wire:orchestration-audit-generate $ARGUMENTS
[6. /wire:reverse-etl-audit-generate $ARGUMENTS   ← only if reverse_etl_tool is set]

When all audits are complete, run:
/wire:migration-inventory-generate $ARGUMENTS
```

### Step 3: Launch parallel audit subagents (option A)

Dispatch parallel subagents — always launch these five:

- Subagent 1: Follow `specs/migration/ingestion_audit/generate.md` for `$ARGUMENTS`
- Subagent 2: Follow `specs/migration/db_object_audit/generate.md` for `$ARGUMENTS`
- Subagent 3: Follow `specs/migration/security_audit/generate.md` for `$ARGUMENTS`
- Subagent 4: Follow `specs/migration/dbt_audit/generate.md` for `$ARGUMENTS`
- Subagent 5: Follow `specs/migration/orchestration_audit/generate.md` for `$ARGUMENTS`

If `migration.reverse_etl_tool` is set in `status.md`, also dispatch:
- Subagent 6: Follow `specs/migration/reverse_etl_audit/generate.md` for `$ARGUMENTS`

Each subagent writes its own output file and updates status.md independently.

### Step 4: Collect results

Wait for all subagents to complete. Report outcomes:

```
Parallel audit results:

Audit                 | Status   | Output file
----------------------|----------|-------------
ingestion_audit       | complete | audit/ingestion_audit.md
db_object_audit       | complete | audit/db_object_audit.md
security_audit        | complete | audit/security_audit.md
dbt_audit             | complete | audit/dbt_audit.md (+ dbt_audit.csv)
orchestration_audit   | complete | audit/orchestration_audit.md
reverse_etl_audit     | complete | audit/reverse_etl_audit.md  [if applicable]

All audits complete. Next steps:

1. Validate each audit:
   /wire:ingestion-audit-validate $ARGUMENTS
   /wire:db-object-audit-validate $ARGUMENTS
   /wire:security-audit-validate $ARGUMENTS
   /wire:dbt-audit-validate $ARGUMENTS
   /wire:orchestration-audit-validate $ARGUMENTS
   [/wire:reverse-etl-audit-validate $ARGUMENTS]

2. Review each audit with the team.

3. When all audits are approved:
   /wire:migration-inventory-generate $ARGUMENTS
```

If any subagent fails, report the failure and provide the individual command to retry:
```
orchestration_audit failed: [error detail]
Retry: /wire:orchestration-audit-generate $ARGUMENTS
```

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

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
