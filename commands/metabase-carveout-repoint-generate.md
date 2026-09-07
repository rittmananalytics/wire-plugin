---
description: Produce the same-instance repoint plan as a dry-run artifact: per warehouse-layer card, the write mode, destinations, database-id and template-tag remaps, and SQL-text rewrites of hardcoded source-project references
argument-hint: <release-folder> [--collection id] [--dashboard id] [--mode duplicate/in_place] [--include-layer card_edit]
---

# Produce the same-instance repoint plan as a dry-run artifact: per warehouse-layer card, the write mode, destinations, database-id and template-tag remaps, and SQL-text rewrites of hardcoded source-project references

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
description: Produce the same-instance repoint plan as a dry-run artifact — per warehouse-layer card, the target collection, the write mode, the database-id and template-tag remaps, and every SQL-text rewrite of a hardcoded source-project table reference, writing nothing to the instance
argument-hint: <release-folder> [--collection <id> | --dashboard <id>] [--mode duplicate|in_place] [--include-layer card_edit]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_carveout_repoint_plan` and `artifact_file_path: migration/metabase_carveout_repoint_plan.csv` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command writes NOTHING to the Metabase instance.

Instance reads (MB_HOST):  card definitions, collection tree, database
                           details, field metadata, snippet bodies
Local writes only:         migration/metabase_carveout_repoint_plan.csv
                           migration/metabase_db_mapping.csv
```

The plan is the dry-run. `metabase-carveout-repoint` is the only command in this pipeline that writes, and it executes only a plan that `metabase-carveout-repoint-validate` has passed.

---

# Metabase Carve-out: Repoint Plan Generate

## Purpose

`metabase-carveout-transport` moves cards to a second, separately-hosted Metabase deployment, and hard-stops when `MB_TARGET_HOST` resolves to the same instance as `MB_HOST` (#255). That guard is correct for transport, but it left two same-instance cases with no supported command: duplicating a card into a different collection on the same instance, and repointing an existing card's underlying warehouse project without moving or duplicating it at all. Both arise when a carve-out's target is a separate BigQuery project reachable from the *same* Metabase instance rather than a separate Metabase deployment — the `warehouse_layer` layer decision, which names the tenant view and the repoint but has never had a mechanic behind it.

This command is the plan step of the same-instance sibling to the transport pipeline: same plan → validate → write shape, same rewrite discipline, no cross-instance machinery. It produces the complete rewrite plan before anything is written: the database-id remap, the template-tag field remaps, and a SQL-text rewrite for every fully-qualified `project.dataset.table` reference to a source or shared project. That last class is the same gap #221 found and fixed for the cross-instance case, and it applies here unchanged: on BigQuery, `` `project.dataset.table` `` in a card's native SQL is a literal, not resolved through the Metabase connection, so repointing `dataset_query.database` alone leaves the card reading the shared project's data while the manifest reports it repointed. Being on one instance does not make the literal resolve differently.

`metabase-carveout-repoint-validate` then re-derives the scan independently and checks the plan; `metabase-carveout-repoint` executes only the validated plan. The rewrite is mechanical once the database mapping is confirmed, so the plan gets deterministic validation, not a second human sign-off: the `metabase_carveout review: approved` gate remains the only write authorisation.

## Scope: cards, not dashboards

The pipeline plans **cards only**. On one instance a dashboard already points at the card ids it uses, so an `in_place` repoint needs no dashboard change at all — preserving the card id is the point. A `duplicate` set that also needs its own dashboard is out of scope here: duplicate the dashboard in Metabase and record the resulting ids, rather than have this pipeline assemble one.

## Prerequisites

- `migration.scope == tenant_carveout`
- `metabase_carveout review: approved`. The plan is derived from the signed-off manifest; there is nothing to plan before sign-off.
- `migration/metabase_carveout_manifest.csv` present, with rows at `signed_off` or later
- Instance credentials: `MB_HOST` + `MB_API_KEY` (read-only use here)
- **Same instance.** If `MB_TARGET_HOST` is set and resolves to a different instance from `MB_HOST`, stop: that is a cross-instance move and belongs to `metabase-carveout-transport-generate`. Report both hosts before planning anything. This is the exact inverse of transport's guard, and the two commands are mutually exclusive by design.

## Flags

- `--collection <id>` / `--dashboard <id>`: narrows within the signed-off set, resolved the same way as `metabase-carveout-generate` Step 1 (a dashboard resolves to its deduped card set).
- `--mode duplicate|in_place`: the default write mode for every planned card. Omitted, the mode is per-row from the manifest's `repoint_mode` column where the consultant has set it, and `duplicate` where they have not. A flag value overrides the column for this run and is recorded per row, so the plan always states the mode rather than leaving it to the write step.
- `--include-layer card_edit`: widens the in-scope layer set (Step 1).

## Inputs

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_manifest.csv`: the signed-off worklist, with its `layer_decision` per row
- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`: collection tree, snippet bodies, card references, the card-to-dashboards reverse index
- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_manifest.csv`: prior repoint state, when it exists (recorded staged and repointed ids)
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`: the database mapping, confirmed here if not already
- `.wire/releases/$ARGUMENTS/status.md`: scope, tenant project, target collection ids

## Workflow

### Step 1: Derive the worklist

Start from the carve-out manifest rows in scope, then apply these rules in order per row:

1. **Row not signed off** (`status: proposed`): no plan rows, recorded `out_of_scope`, reason `row_not_signed_off`.
2. **`action: remove_dashcard`**: no plan rows, reason `removed_no_tenant_data`. The card has no tenant data; repointing it at the tenant project would produce an empty card, not a correct one.
3. **Layer not repointed**: `layer_decision` of `sandboxing` or `dashboard_parameter` gets no plan rows, reason `layer_not_repointed`. Those layers scope a card without changing its query, so there is nothing to repoint.
4. **In scope**: `layer_decision: warehouse_layer` always, and `layer_decision: card_edit` only when `--include-layer card_edit` was passed. A `card_edit` card can carry a hardcoded source-project reference of its own, but including it is the consultant's call, not an inference: without the flag it is `out_of_scope`, reason `layer_requires_opt_in`.

`warehouse_layer | card_edit | sandboxing | dashboard_parameter` is the closed layer vocabulary, unchanged from `metabase-carveout-generate`. Any other value is an error naming the value and the card, never a fall-through to planning a write.

### Step 2: Confirm the database mapping

Write (or re-read) `migration/metabase_db_mapping.csv`, the same file and columns the transport pipeline uses — on a same-instance repoint both sides are databases on one instance:

```
source_database_id, source_database_name, source_project,
target_database_id, target_database_name, target_project, confirmed
```

`source_project` and `target_project` are the GCP projects each database connection points at, read from the instance's database details, never typed from memory. Present the table to the consultant and require `confirmed: yes` per row. Never map by name: a database named like the source one is a hint for the consultant, not a mapping. A shared project that hosts no mapped database but appears in card SQL (a pre-carve-out shared project) is added by the consultant as a mapping row with the target it rewrites to, or the plan cannot account for its references.

A trial repoint at a scratch or playground dataset is an ordinary mapping row: the target database is the connection that reaches the playground project, confirmed like any other. The plan does not distinguish a trial from a production target — the target collection and the write mode do.

The **source/shared project set** is the set of `source_project` values on confirmed rows. It defines the scan scope in Step 4, and `metabase-carveout-repoint-validate` re-reads it from the same confirmed file.

### Step 3: Resolve the destinations and the write mode

Per in-scope card, resolve three things and record them on every plan row for that card:

- **`write_mode`**: `duplicate` (create a second card, leaving the source card untouched) or `in_place` (replace the existing card's query, preserving the card id and everything that already references it). Closed set; the flag or the manifest column decides it, per Step 1's rule.
- **`target_collection_id`**: where the repointed card ends up. For `duplicate`, the collection that receives the new card; it must already exist on the instance (a missing collection is recorded, never created at plan time). For `in_place`, the card's existing collection, unchanged — an in-place repoint never moves a card.
- **`stage_collection_id`**: the restricted-access collection the change is staged in for review before it reaches production. **Required for every `in_place` row**: a production card with existing dependents is never rewritten without a staged copy to review first. Optional for `duplicate` rows, where the new card can go straight to its target collection because nothing references it yet.

A missing or unreadable destination is recorded on the row (`target_collection_missing` / `stage_collection_missing`) rather than assumed. Validate fails those rows; that is the point.

### Step 4: Scan each card's native SQL for fully-qualified references

For each in-scope card with a native query, scan the SQL text using the rules in `specs/migration/metabase_carveout/transport_generate.md` Step 3, unchanged:

1. **Strip comments first.** Remove `/* ... */` blocks and `--` line remainders before scanning (the #200 rule: a reference inside a comment is not a reference).
2. **Match two forms.** Backtick-quoted `` `project.dataset.table` `` (project ids may contain hyphens; BigQuery then requires the backticks), and unquoted three-part `project.dataset.table` (letters, digits, underscores only; a hyphenated project cannot appear unquoted).
3. **Two-part references are out of scope.** `dataset.table` resolves through the card's connection; remapping `dataset_query.database` already handles it.
4. **Only source/shared projects are in scope.** A reference whose project is not in Step 2's source/shared project set (a public dataset, an unrelated third project) is out of scope and gets no plan row.

The scan is textual after comment stripping: it does not parse string literals, so a three-part path inside a literal (a label such as `'see <project>.x.y'`) can surface as a candidate. The scanner never decides that case; it surfaces the reference and the consultant dispositions it (`no_change_needed`, reason naming the literal), rather than the scanner guessing.

One same-instance rule is additional to the transport scan. A card whose SQL uses a `{{snippet: name}}` or `{{#id-name}}` reference whose **body itself** carries an in-scope source-project reference cannot be repointed by rewriting that body: on one instance the snippet is the same object every other card uses, so the rewrite would silently repoint cards outside the carve-out. The card is recorded `blocked_reference`, reason `shared_snippet_reference`, and it stays a parked decision for the consultant (copy the snippet and point the repointed card at the copy, or inline it) rather than an improvised rewrite. Cross-instance transport never meets this, because there the snippet is a separate object created on the target.

### Step 5: Build the plan rows

One plan row per rewrite, `rewrite_type` from the closed vocabulary:

| rewrite_type | source_value | target_value | how the target resolves |
|---|---|---|---|
| `database_id` | source `dataset_query.database` | confirmed target database id | Step 2 mapping row |
| `template_tag_field` | source field id (per tag) | target field id | target database's field metadata |
| `sql_table_reference` | source project | target project | Step 2 mapping row's `target_project` |

Field ids are per-database in Metabase, not per-instance, so a card moving from one database connection to another needs its field-filter tags remapped even though nothing crossed an instance boundary. That is why `template_tag_field` stays in the vocabulary here.

Three of transport's rewrite types are deliberately **absent**: `snippet_ref`, `card_ref` and `collection_id`. Snippet and card ids do not change on one instance, and a repointed card's collection is a destination, not a rewritten reference. Nothing in this pipeline rewrites an id to make it resolve on another deployment, and nothing creates a permission group or a sandboxing policy — that complexity is specific to crossing an instance boundary.

`disposition` is the closed set:

- `rewrite`: `target_value` populated from the confirmed mapping or the target database's metadata.
- `no_change_needed`: the reference deliberately stays as it is, with a recorded reason (e.g. genuinely shared reference data that stays on the shared project). Valid only for `sql_table_reference`, and a blank reason is a defect.

Every `sql_table_reference` row's target project comes from the confirmed mapping row for that source project, never from name similarity. An in-scope reference the consultant cannot yet disposition stays in the plan as `rewrite` with a blank `target_value`; validate will fail it, which is the point: no reference leaves the plan unaccounted.

### Step 6: Write the plan

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_plan.csv`

```
object_type, source_id, name, layer_decision, write_mode,
target_collection_id, stage_collection_id, rewrite_type, reference,
source_value, target_value, disposition, reason
```

`reference` carries the matched text for `sql_table_reference` rows (the canonical `project.dataset.table`) and the tag name for `template_tag_field` rows. A card that is `out_of_scope` or `blocked_reference` gets a single row carrying its reason and no rewrite, so the plan accounts for every signed-off card rather than silently omitting it. The plan is a derived artifact: rewritten from scratch on every run, unlike the repoint manifest, which is the durable upserted record.

### Step 7: Update status

```yaml
artifacts:
  metabase_carveout_repoint_plan:
    generate: complete
    file: migration/metabase_carveout_repoint_plan.csv
    generated_date: "{{TODAY}}"
    planned_cards: N
    write_modes: {duplicate: N, in_place: N}
    sql_references_in_scope: N
    sql_rewrites: N
    no_change_needed: N
    out_of_scope: N
    blocked_reference: N
```

### Step 8: Output next command

```
/wire:metabase-carveout-repoint-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_carveout_repoint_plan.csv`
- `.wire/releases/$ARGUMENTS/migration/metabase_db_mapping.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_repoint_plan` as artifact, `generate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_repoint_plan` as artifact, `generate` as action.

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
