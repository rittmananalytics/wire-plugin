---
wire_schema: "1.0"
command: utility
artifact: metabase_carveout
domain: migration
release_types:
  - platform_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: metabase_carveout
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
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
