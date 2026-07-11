---
description: Apply agreed fix and re-run equivalency checks for affected objects
argument-hint: <release-folder> --object <name> --approach <description>
---

# Apply agreed fix and re-run equivalency checks for affected objects

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
description: Apply agreed fix and re-run equivalency checks for affected objects
---

# Equivalency — Fix

## Purpose

Applies a specific fix to a failing equivalency object and re-runs the equivalency checks for that object (and any objects that depend on it). Updates the loop history in status.md. This is a targeted repair command — it does not re-run checks for the entire scope.

## Arguments

Required:
- `--object <name>` — the table or dbt model to fix
- `--approach <description>` — brief description of the fix being applied

Example:
```
/wire:equivalency-fix 01-migration --object orders_fct --approach "Add COALESCE for NULL handling in subtotal column"
```

## Workflow

### Step 1: Load context

Read the investigation notes for this object from the latest equivalency report. Confirm the `--approach` matches or builds on the proposed fix.

### Step 2: Apply the fix

Based on the `--approach`:

**If SQL translation fix**:
- Open the translated model at `migration/dbt/{model_name}.sql`
- Apply the correction
- Update the diff file
- Re-run `dbt compile` for the model if target profile available

**If DDL fix**:
- Open the relevant target_setup_scripts SQL file
- Apply the correction
- Note that the DDL change may need to be applied to the target platform manually

**If configuration fix** (Fivetran mapping, type handling):
- Document the configuration change required
- If Fivetran MCP available: apply the mapping change via MCP
- Otherwise: write detailed manual steps for the engineer to apply

**If accepted difference**:
- Document the business justification
- Update the equivalency tolerance for this table in migration_strategy.md
- Mark the object as `accepted_difference` in status.md

### Step 3: Re-run checks for affected objects

Identify all objects that depend on the fixed object (using the dependency graph from migration_inventory.md).

Re-run all per-object check types (row count, schema, value sampling, freshness, dbt tests, row-level checksum) for:
- The fixed object
- All direct dependents of the fixed object

If the fix touches a column feeding a business invariant, re-run that invariant too.

If `migration.scope == tenant_carveout`, apply `migration.tenant_predicate` as a `WHERE` clause on both source and target when re-running these checks, exactly as `equivalency-validate` does. When `scope` is `full_migration` or absent, re-run unscoped.

If the fixed object or any re-checked dependent is a relative-date-flagged model (`equivalency-validate` Step 1.5), resolve a fresh pinned as-of for this re-run, apply the same literal substitution over the compiled SQL on both sides, and record the pinned value in the fix entry (Step 4). Never re-run a flagged model's checks unpinned.

### Step 4: Update status

Add a `fix` entry to the loop history:

```yaml
migration:
  equivalency_validation:
    loop_history:
      - run: N
        date: "{{PREVIOUS_DATE}}"
        passing: X
        failing: Y
      - fix:
          date: "{{TODAY}}"
          object: "{{OBJECT_NAME}}"
          approach: "{{APPROACH}}"
          pinned_as_of: "{{PINNED_AS_OF_TS}}"   # UTC; only when re-checked objects include relative-date-flagged models
          result: "passing" | "still_failing"
```

Update `checks_failing` with the new total after re-checking affected objects.

### Step 5: Output

If the object now passes:
```
Fix applied successfully. {{OBJECT_NAME}} now passes all equivalency checks.
Checks failing: N (was N+1)

/wire:equivalency-validate $ARGUMENTS   ← run full check when all fixes applied
```

If the object still fails:
```
Fix applied but {{OBJECT_NAME}} still failing.
Check type still failing: [type]

Re-investigate:
/wire:equivalency-investigate $ARGUMENTS --object {{OBJECT_NAME}}
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
