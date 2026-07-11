---
description: Deep diagnostics for a specific failing object
argument-hint: <release-folder> --object <table_or_model>
---

# Deep diagnostics for a specific failing object

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
description: Deep diagnostics for a specific failing equivalency object
---

# Equivalency — Investigate

## Purpose

Deep diagnostics for a specific table or dbt model that is failing equivalency checks. Goes beyond the summary-level reporting of `equivalency-validate` to identify the root cause of the failure — whether it is a translation error, a data loading issue, a timing problem, or an expected difference.

## Arguments

`$ARGUMENTS` must include `--object <table_or_model_name>`. Example:
```
/wire:equivalency-investigate 01-migration --object orders_fct
```

## Workflow

### Step 1: Locate the failing object

Read the most recent equivalency report from `migration/equivalency_report_*.md`. Find the entry for the specified object. Load its per-check-type failure details.

### Step 2: Diagnose by failure type

If `migration.scope == tenant_carveout`, apply `migration.tenant_predicate` as a `WHERE` clause on both source and target in every diagnostic query below — including the partition-level, sample, and freshness queries — so the diagnosis matches the scoped row set `equivalency-validate` checked. When `scope` is `full_migration` or absent, run the queries unscoped as written.

Rule out timing before treating any failure as a real data divergence. If the object's SQL references `CURRENT_DATE()`, `NOW()`, or another relative-date function (a relative-date-flagged model per `equivalency-validate` Step 1.5), read the pinned as-of value recorded for it in the failing run's report. If no pinned value was recorded, the checks ran unpinned and the failure may be a live-edge timing artefact — re-run `/wire:equivalency-validate` (which pins the as-of instant for flagged models) before investigating further. If a pinned value was recorded, use that same literal in every diagnostic query below so the diagnosis reproduces the failing run exactly.

**If failing on Row count**:
- Run the row count query for both source and target
- Compare counts at the partition/date level (if partitioned): identify which date ranges have discrepancies
- Check Fivetran sync logs for the connector that loads this table — was the last sync complete?
- Check for soft-deleted rows that might differ between platforms
- For relative-date-flagged models: confirm the failing run used a pinned as-of (see preamble above) — an unpinned run over a "last N days" window can show a false count divergence at the live edge

**If failing on Schema**:
- Show the exact column diff: columns present in source but missing from target, columns present in target but not source, type mismatches
- Cross-reference against the target_setup DDL scripts — was the column included?
- Check for case sensitivity differences in column names

**If failing on Value sampling**:
- Identify which specific columns have statistical deviations
- Run a sample comparison: pull 20 rows from source and target on the same primary key values
- Check for NULL handling differences (COALESCE behaviour, empty string vs NULL)
- Check for timezone differences in TIMESTAMP columns

**If failing on Freshness**:
- Compare `max(loaded_at)` or `max(updated_at)` on source vs target
- Check Fivetran connector status on target — is it running on schedule?
- Check if the target connector completed its initial load

**If failing on dbt tests**:
- Show the full test output for the failing tests
- Identify whether the failure is a not_null, unique, accepted_values, or relationship test
- Check if the test failure exists on source as well (if so, it may be a pre-existing issue, not a migration regression)

### Step 3: Propose fix approach

Based on the diagnosis, propose one or more fix approaches with their trade-offs:

- **Translation fix**: update the dbt model SQL translation or DDL script
- **Configuration fix**: update Fivetran connector mapping or type handling
- **Data reload**: trigger a full historical sync for the connector
- **Accept as expected difference**: document the known difference with business justification (e.g., deprecated column no longer populated)
- **Adjust tolerance**: if the difference is within acceptable business bounds, update the tolerance for this table in migration_strategy.md

### Step 4: Write investigation notes

Append to the latest equivalency report:

```markdown
## Investigation: {{OBJECT_NAME}}

**Investigated**: {{TODAY}}
**Failure types**: [list]
**Root cause**: [description]
**Proposed fix**: [description]
**Fix command**: /wire:equivalency-fix $ARGUMENTS --object {{OBJECT_NAME}} --approach "[brief description]"
```

### Step 5: Output

Print: root cause summary, proposed fix, and the fix command to run.

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
