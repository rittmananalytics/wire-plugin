---
description: Verify LookML view files are valid, canonical models covered, no orphaned column references
argument-hint: <release-folder>
---

# Verify LookML view files are valid, canonical models covered, no orphaned column references

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
description: Verify LookML view files are valid, every canonical model is covered, and no orphaned column references exist
argument-hint: <release-folder>
---

# Agentic Data Stack — LookML Views Validate

## Purpose

Confirm that the generated and updated view files are syntactically valid, structurally complete, and correctly wired into the Looker project before the semantic layer step adds metrics on top.

## Usage

```bash
/wire:ads_lookml-views-validate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `lookml_views.generate: complete` or `skipped`

## Skip Condition

If `lookml_views.generate: skipped` in status.md, output:

```
LookML Views — Validate Skipped (bi_tool is not looker)
```

Update status and stop.

---

## Validation Checks

### Check 1 — LookML Syntax

Run the LookML linter against all modified files:

```bash
# Option A — lookml-lint (open source)
lookml-lint <lookml_project_path>/views/<model_name>.view.lkml

# Option B — Looker CLI (if configured)
looker lookml-test --project <project_name>

# Option C — if neither is available, perform a manual syntax check:
# Scan each generated file for:
#   - Balanced braces {}
#   - Valid parameter names (no unknown keys)
#   - sql_table_name ends with ;;
#   - All sql: parameters end with ;;
```

- [ ] All generated/updated view files pass linting with 0 errors

---

### Check 2 — Every Canonical Model Has a View

Cross-reference the new/modified model list from `canonical_models_lineage.md` against the LookML project scan:

- [ ] Every **new** canonical model has exactly one view file with a matching `sql_table_name`
- [ ] No new canonical model is referenced by zero views
- [ ] No duplicate views reference the same `sql_table_name`

---

### Check 3 — Column References

For each view file generated or updated in this phase, check that every `${TABLE}.<column>` reference exists in the underlying dbt model's schema.yml:

```bash
# Extract column names from schema.yml for each model
grep "name:" <dbt_project_path>/models/marts/<domain>/<model>.yml | awk '{print $2}'

# Compare against ${TABLE}. references in the view file
grep -o '\${TABLE}\.[a-z_]*' <lookml_project_path>/views/<view>.view.lkml | \
  sed 's/${TABLE}\.//'
```

- [ ] Every `${TABLE}.<column>` in generated views maps to a column in the dbt schema.yml
- [ ] No orphaned references from modified views (columns removed from the canonical model but still referenced in the view)

---

### Check 4 — Primary Keys

For each generated view:

- [ ] Exactly one dimension has `primary_key: yes`
- [ ] That dimension references a column with `unique` + `not_null` tests in schema.yml
- [ ] No `# TODO: confirm primary_key` comments remain unresolved

---

### Check 5 — Explore Wiring

Read `lookml_views_notes.md` — check the "Explores Needing Manual Review" section:

- [ ] No new views are in the "needs manual wiring" list (all have been added to an explore, either in this step or by the team)

If views remain unwired, **block progression** with:

```
VALIDATION FAIL — N view(s) not yet added to any explore.
Metrics added by ads_semantic-layer-generate on unwired views will be
unreachable in Looker. Resolve before proceeding:

  <view_name> — add to an explore in <lookml_project_path>/models/<model>.model.lkml

Re-run ads_lookml-views-validate after resolving.
```

---

### Check 6 — No Accidental Measure Changes

Diff each modified view file against its pre-modification state (via git diff):

- [ ] No measures were added or removed in existing view files (measures are `ads_semantic-layer-generate`'s responsibility)
- [ ] No existing `measure:` blocks were altered in any way

---

## Status Update

On pass:

```yaml
lookml_views:
  validate: complete
  validate_date: YYYY-MM-DD
  validation_result: pass
  lint_errors: 0
  coverage_gaps: 0
  orphaned_references: 0
```

On fail, record the specific checks that failed and leave `validate: failed`. Do not proceed to review until all checks pass.

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
