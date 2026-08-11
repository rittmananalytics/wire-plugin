---
description: Validate Metabase audit completeness and dependency coverage
argument-hint: <release-folder>
---

# Validate Metabase audit completeness and dependency coverage

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
description: Validate Metabase audit completeness, warehouse dependency coverage, permission groups, and migration approach assignments
---

# Metabase Audit — Validate

## Purpose

Checks the Metabase audit for completeness and internal consistency: every card has a migration approach and complexity, warehouse dependencies are mapped with a coverage metric, permission groups are catalogued, database connections are recorded, and the card count matches the source. Produces a PASS/FAIL report with specific gaps to address before review.

## Prerequisites

- `audit/metabase_audit.md` exists (metabase_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/metabase_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, Card Catalog, Hierarchy, Database Connections, Permission Groups, Warehouse Dependency Map, Unresolved Cards, Excluded Cards).

### Step 2: Run validation checks

**Check 1 — All cards have a migration approach**
Every row in the card catalog has a value in `migration_approach` (repoint / rewrite_sql / rebuild / decommission).
PASS/FAIL with cards missing an approach.

**Check 2 — All cards have a complexity rating**
Every row has a `complexity` value (Low / Medium / High).
PASS/FAIL with cards missing complexity.

**Check 3 — Source objects resolved across query types, coverage reported**
Source-object resolution is attempted for both `native` and `mbql` cards. Each card with a resolvable source has ≥1 entry in `warehouse_objects`; each genuinely unresolvable card is marked `source_resolved: false` and listed under "Unresolved cards". The coverage metric (`resolved_card_count` / `active_card_count`) is present, and status.md carries `resolved_card_count`, `unresolved_card_count`, and `source_resolution_coverage_pct`.
PASS: resolution attempted for all query types, coverage present, every unresolved card listed.
FAIL: cards left blank without being listed, or coverage metric missing.

**Check 4 — dbt model cards cross-referenced**
Every card whose resolved source is a dbt model has a note confirming whether that model exists in the dbt audit (or is out of scope).
PASS/FAIL with cards missing the cross-reference.

**Check 5 — Permission groups catalogued**
The audit includes a permission group inventory listing each group and its database/collection access. `permission_group_count` in status.md is > 0 (or a note explains why the instance has none beyond defaults).
PASS/FAIL.

**Check 6 — Database connections recorded**
Every distinct `source_database_id` referenced by a card appears in the database connection inventory with its engine.
PASS/FAIL.

**Check 7 — Archived/unused cards have a decision**
Every archived or unused card has either `migration_approach: decommission` with a reason, or `include_in_migration: true` with a note.
PASS/FAIL with undecided cards. If `data_source: csv` and archived status is unavailable, auto-pass and note that decommission decisions need manual review with the client.

**Check 8 — Card count matches source**
The count of rows in the card catalog matches `card_count` in status.md.
PASS/FAIL.

### Step 3: Write validation report

Append a `## Validation` section to `audit/metabase_audit.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

### Step 4: Update status

```yaml
artifacts:
  metabase_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:metabase-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:metabase-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_audit` as artifact_id, `Metabase Audit` as artifact_name, and the `file` value from `artifacts.metabase_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_audit` as artifact, `validate` as action.

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
