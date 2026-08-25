---
description: Validate the transport plan: re-derive the SQL scan from each card's own SQL, prove every source-project reference accounted for and every id-rewrite resolves on the target
argument-hint: <release-folder>
---

# Validate the transport plan: re-derive the SQL scan from each card's own SQL, prove every source-project reference accounted for and every id-rewrite resolves on the target

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
description: Validate the Metabase carve-out transport plan, re-deriving the SQL scan independently from each card's own SQL, proving every source-project reference is accounted for and every id-rewrite resolves on the target instance
argument-hint: <release-folder>
---

# Metabase Carve-out Transport Plan: Validate

## Validation Checks

Ground truth is each card's own SQL (read from the source instance or the audit's serialization export), the confirmed `migration/metabase_db_mapping.csv`, and the target instance's actual database and field metadata. The scan is re-derived here from scratch, never read from the plan: the plan's claims are what is being checked. This mirrors `metabase-carveout-validate`, which re-derives filters from the registry rather than trusting the manifest.

**Check 1: Plan present and current**
`migration/metabase_carveout_transport_plan.csv` exists and is not older than `migration/metabase_carveout_manifest.csv` (compare mtimes / the recorded `generated_date` against the manifest's last change). A plan older than the manifest it was generated from is FAIL, reason `plan_stale`: re-run `metabase-carveout-transport-generate` first.

**Check 2: Every in-scope SQL reference is accounted for**
For every in-scope card, re-derive the fully-qualified reference set from the card's own SQL using the scan rules in `specs/migration/metabase_carveout/transport_generate.md` Step 3: comments stripped first, backtick-quoted and unquoted three-part forms matched, two-part references out of scope, only projects in the confirmed mapping's source/shared project set in scope. Every reference so found must have a plan row that is either:

- `rewrite` with a `target_value` equal to the confirmed mapping row's `target_project` for that source project, or
- `no_change_needed` with a non-blank reason.

A reference with no plan row is **unaccounted**: FAIL, listing card and reference. A `rewrite` row whose target project does not come from the confirmed mapping is a guessed mapping: FAIL. A `no_change_needed` row with a blank reason is FAIL. No unaccounted reference, no guessed mapping.
PASS/FAIL with offending references.

**Check 3: No plan row without a reference**
Every `sql_table_reference` plan row matches a reference the re-scan actually found in that card's SQL. A row claiming a rewrite the SQL does not contain means the plan and the cards have diverged: FAIL, reason `unmatched_plan_row`, listing the rows.
PASS/FAIL with offending rows.

**Check 4: Id-rewrites resolve on the target instance**
Every `database_id` target exists in the target instance's database list; every `template_tag_field` target field id exists in the mapped target database's field metadata; every `snippet_ref` / `card_ref` / `collection_id` row with a recorded target id answers a GET on the target; every `pending_create` row names a source object that is itself in the plan's worklist, so transport's dependency ordering will create it.
PASS/FAIL with offending rows.

**Check 5: Closed vocabularies**
`rewrite_type` is one of `database_id | template_tag_field | snippet_ref | card_ref | collection_id | sql_table_reference`; `disposition` is one of `rewrite | pending_create | no_change_needed`; `pending_create` appears only on `snippet_ref` / `card_ref` / `collection_id` rows and `no_change_needed` only on `sql_table_reference` rows. Any other value is FAIL naming the value and the row.
PASS/FAIL with offending rows.

The scan and accounting rules above are deterministic and implemented literally in `wire/tests/platform_migration/validate_transport_sql_rewrite.py`; a change to the rules here changes that test.

### Update status

```yaml
artifacts:
  metabase_carveout_transport_plan:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Output next command

On PASS:

```
/wire:metabase-carveout-transport $ARGUMENTS
```

On FAIL, fix the plan and re-run: an unaccounted reference usually means the mapping is missing a shared project row (`metabase-carveout-transport-generate` Step 2), and an unmatched plan row means the plan is stale against the cards.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_transport_plan` as artifact, `validate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_transport_plan` as artifact, `validate` as action.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
