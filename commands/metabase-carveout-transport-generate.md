---
description: Produce the transport plan as a dry-run artifact: the four id-rewrites plus SQL-text rewrites of hardcoded source-project table references, writing nothing to either instance
argument-hint: <release-folder> [--collection id] [--dashboard id]
---

# Produce the transport plan as a dry-run artifact: the four id-rewrites plus SQL-text rewrites of hardcoded source-project table references, writing nothing to either instance

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
description: Produce the transport plan for the Metabase carve-out as a dry-run artifact, covering the four id-rewrites plus every SQL-text rewrite of a hardcoded source-project table reference, writing nothing to either instance
argument-hint: <release-folder> [--collection <id> | --dashboard <id>]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_carveout_transport_plan` and `artifact_file_path: migration/metabase_carveout_transport_plan.csv` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command writes NOTHING to either Metabase instance.

Source instance reads (MB_HOST):        card definitions, database details
Target instance reads (MB_TARGET_HOST): database list, field metadata
Local writes only:                      migration/metabase_carveout_transport_plan.csv
                                        migration/metabase_db_mapping.csv
```

The plan is the dry-run. `metabase-carveout-transport` is the only command in this pipeline that creates objects, and it executes only a plan that `metabase-carveout-transport-validate` has passed.

---

# Metabase Carve-out: Transport Plan Generate

## Purpose

Transport rewrites the ids that do not survive an instance boundary, but a card's native SQL can also name the source GCP project directly (#221). On a BigQuery target, `` `project.dataset.table` `` in the SQL is a literal, not resolved through the Metabase connection: repointing `dataset_query.database` does not touch it, so the transported card keeps reading the shared project's data while the manifest reports `transported`. `metabase-equivalency-validate` cannot catch it either, because both sides read the same literal table and match. For BigQuery this is the normal way to reference another project, not an edge case.

This command produces the complete transport plan before anything is written: the four id-rewrites transport already performs (database id, template-tag field ids, snippet/card references, collection id) plus a SQL-text rewrite mapping for every fully-qualified table reference to a source or shared project. `metabase-carveout-transport-validate` then re-derives the scan independently and checks the plan; `metabase-carveout-transport` executes only the validated plan. The rewrite is mechanical once the database mapping is confirmed, so the plan needs deterministic validation, not a second human sign-off: the `metabase_carveout review: approved` gate remains the only write authorisation.

## Prerequisites

- `migration.scope == tenant_carveout`
- `metabase_carveout review: approved`. The plan is derived from the signed-off manifest; there is nothing to plan before sign-off.
- `migration/metabase_carveout_manifest.csv` present, with rows at `signed_off` or later
- Source instance credentials: `MB_HOST` + `MB_API_KEY` (read-only use)
- Target instance credentials: `MB_TARGET_HOST` + `MB_TARGET_API_KEY` (read-only use here: database list and field metadata). Credentials are never written into any file this command produces.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_manifest.csv`: the signed-off worklist
- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`: object graph (snippets, card references), collection tree
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_manifest.csv`: prior transport state, when it exists (recorded target ids)
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`: the database mapping, confirmed here if not already
- `.wire/releases/$ARGUMENTS/status.md`: scope, tenant project, target instance

## Workflow

### Step 1: Derive the worklist

Derive the worklist exactly as `specs/migration/metabase_carveout/transport.md` Step 1 derives it: same rule order, same reasons. Rows that transport would not attempt (`not_attempted`, `skipped_duplicate`) get no plan rows; the plan covers only the objects transport will create. `--collection <id>` / `--dashboard <id>` narrows the same way.

### Step 2: Confirm the database mapping

Write (or re-read) `migration/metabase_db_mapping.csv`, extended with the connection projects:

```
source_database_id, source_database_name, source_project,
target_database_id, target_database_name, target_project, confirmed
```

`source_project` and `target_project` are the GCP projects each database's connection points at, read from the instances' database details, never typed from memory. Present the table to the consultant and require `confirmed: yes` per row. Never map by name: a target database named like the source one is a hint for the consultant, not a mapping. A shared project that hosts no mapped database but appears in card SQL (a pre-carve-out shared project) is added by the consultant as a mapping row with the target it rewrites to, or the plan cannot account for its references.

The **source/shared project set** is the set of `source_project` values on confirmed rows. This set defines the scan scope in Step 3, and `metabase-carveout-transport-validate` re-reads it from the same confirmed file.

### Step 3: Scan each card's native SQL for fully-qualified references

For each in-scope card with a native query, scan the SQL text. The rules are deterministic:

1. **Strip comments first.** Remove `/* ... */` blocks and `--` line remainders before scanning (the #200 rule: a reference inside a comment is not a reference).
2. **Match two forms.** Backtick-quoted `` `project.dataset.table` `` (project ids may contain hyphens; BigQuery then requires the backticks), and unquoted three-part `project.dataset.table` (letters, digits, underscores only; a hyphenated project cannot appear unquoted).
3. **Two-part references are out of scope.** `dataset.table` resolves through the card's connection; repointing `dataset_query.database` already handles it.
4. **Only source/shared projects are in scope.** A reference whose project is not in Step 2's source/shared project set (a public dataset, an unrelated third project) is out of scope and gets no plan row.

The scan is textual after comment stripping: it does not parse string literals, so a three-part path inside a literal (a label such as `'see <project>.x.y'`) can surface as a candidate. The scanner never decides that case; it surfaces the reference and the consultant dispositions it (`no_change_needed`, reason naming the literal), rather than the scanner guessing.

### Step 4: Build the plan rows

One plan row per rewrite, `rewrite_type` from the closed vocabulary:

| rewrite_type | source_value | target_value | how the target resolves |
|---|---|---|---|
| `database_id` | source `dataset_query.database` | confirmed target database id | Step 2 mapping row |
| `template_tag_field` | source field id (per tag) | target field id | target database's field metadata |
| `snippet_ref` | source snippet id | recorded target id, or blank | prior transport manifest, else `pending_create` |
| `card_ref` | source card id | recorded target id, or blank | prior transport manifest, else `pending_create` |
| `collection_id` | source collection id | recorded target id, or blank | prior transport manifest, else `pending_create` |
| `sql_table_reference` | source project | target project | Step 2 mapping row's `target_project` |

`disposition` is the closed set:

- `rewrite`: `target_value` populated from the confirmed mapping or target metadata.
- `pending_create`: the target object does not exist yet; transport creates it in its Step 3 dependency ordering. Valid only for `snippet_ref`, `card_ref`, `collection_id`.
- `no_change_needed`: the reference deliberately stays as it is, with a recorded reason (e.g. genuinely shared reference data that stays on the shared project). Valid only for `sql_table_reference`, and a blank reason is a defect.

Every `sql_table_reference` row's target project comes from the confirmed mapping row for that source project, never from name similarity. An in-scope reference the consultant cannot yet disposition stays in the plan as `rewrite` with a blank `target_value`; validate will fail it, which is the point: no reference leaves the plan unaccounted.

### Step 5: Write the plan

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_plan.csv`

```
object_type, source_id, name, rewrite_type, reference,
source_value, target_value, disposition, reason
```

`reference` carries the matched text for `sql_table_reference` rows (the canonical `project.dataset.table`) and the tag or reference name for id-rewrites. The plan is a derived artifact: rewritten from scratch on every run, unlike the transport manifest, which is the durable upserted record.

### Step 6: Update status

```yaml
artifacts:
  metabase_carveout_transport_plan:
    generate: complete
    file: migration/metabase_carveout_transport_plan.csv
    generated_date: "{{TODAY}}"
    planned_objects: N
    sql_references_in_scope: N
    sql_rewrites: N
    no_change_needed: N
```

### Step 7: Output next command

```
/wire:metabase-carveout-transport-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_transport_plan.csv`
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_transport_plan` as artifact, `generate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_transport_plan` as artifact, `generate` as action.

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
