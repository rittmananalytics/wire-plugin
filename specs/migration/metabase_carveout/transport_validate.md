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
description: Validate the Metabase carve-out transport plan, re-deriving the SQL scan independently from each card's own SQL, proving every source-project reference is accounted for and every id-rewrite resolves on the target instance
argument-hint: <release-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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
