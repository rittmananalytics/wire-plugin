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
description: Validate the same-instance repoint plan, re-deriving the SQL scan independently from each card's own SQL, proving every source-project reference is accounted for, every remap resolves on the mapped database, and every in-place row has a staging collection
argument-hint: <release-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Carve-out Repoint Plan: Validate

## Validation Checks

Ground truth is each card's own SQL (read from the instance or the audit's serialization export), the confirmed `migration/metabase_db_mapping.csv`, and the instance's actual database, field and collection metadata. The scan is re-derived here from scratch, never read from the plan: the plan's claims are what is being checked. This mirrors `metabase-carveout-transport-validate`, and `metabase-carveout-validate` before it, which re-derives filters from the registry rather than trusting the manifest.

**Check 0: Same instance**
`MB_TARGET_HOST`, where set, resolves to the same instance as `MB_HOST`. A different host is FAIL, reason `cross_instance_target`, naming both hosts: that is a cross-instance move and belongs to the transport pipeline. The whole point of this pipeline is the same-instance case, so the guard is checked before anything else.
PASS/FAIL with both host values.

**Check 1: Plan present and current**
`migration/metabase_carveout_repoint_plan.csv` exists and is not older than `migration/metabase_carveout_manifest.csv` (compare mtimes / the recorded `generated_date` against the manifest's last change). A plan older than the manifest it was generated from is FAIL, reason `plan_stale`: re-run `metabase-carveout-repoint-generate` first.

**Check 2: Every in-scope SQL reference is accounted for**
For every in-scope card, re-derive the fully-qualified reference set from the card's own SQL using the scan rules in `specs/migration/metabase_carveout/transport_generate.md` Step 3, as `specs/migration/metabase_carveout/repoint_generate.md` Step 4 adopts them: comments stripped first, backtick-quoted and unquoted three-part forms matched, two-part references out of scope, only projects in the confirmed mapping's source/shared project set in scope. Every reference so found must have a plan row that is either:

- `rewrite` with a `target_value` equal to the confirmed mapping row's `target_project` for that source project, or
- `no_change_needed` with a non-blank reason.

A reference with no plan row is **unaccounted**: FAIL, listing card and reference. A `rewrite` row whose target project does not come from the confirmed mapping is a guessed mapping: FAIL. A `no_change_needed` row with a blank reason is FAIL. No unaccounted reference, no guessed mapping — a card that reaches the tenant project by connection but still names the shared project in its SQL text reads shared data and reports success, and being on one instance does not change that.
PASS/FAIL with offending references.

**Check 3: No plan row without a reference**
Every `sql_table_reference` plan row matches a reference the re-scan actually found in that card's SQL. A row claiming a rewrite the SQL does not contain means the plan and the cards have diverged: FAIL, reason `unmatched_plan_row`, listing the rows.
PASS/FAIL with offending rows.

**Check 4: Remaps resolve on the mapped database**
Every `database_id` target exists in the instance's database list and matches the confirmed mapping row for that source database id. Every `template_tag_field` target field id exists in the **mapped target database's** field metadata — a field id that resolves only in the source database is FAIL, reason `field_not_in_target_database`, not a pass because the id answers a GET somewhere on the instance. Every card with field-filter template tags has one `template_tag_field` row per tag; a tag with no row is FAIL, reason `tag_not_remapped`.
PASS/FAIL with offending rows.

**Check 5: Destinations exist and in-place rows are staged**
Every `target_collection_id` and every non-blank `stage_collection_id` resolves to a collection that exists on the instance. Every row with `write_mode: in_place` carries a non-blank `stage_collection_id`: FAIL, reason `in_place_without_stage`, because a production card with existing dependents is never rewritten without a staged copy to review first. Every `in_place` row's `target_collection_id` equals the card's current collection: an in-place repoint never moves a card, and a plan that says otherwise is FAIL, reason `in_place_moves_card`.
PASS/FAIL with offending rows.

**Check 6: Closed vocabularies**
`write_mode` is one of `duplicate | in_place`; `rewrite_type` is one of `database_id | template_tag_field | sql_table_reference`; `disposition` is one of `rewrite | no_change_needed`, with `no_change_needed` only on `sql_table_reference` rows. Transport's `snippet_ref`, `card_ref` and `collection_id` types are not valid here — their presence means a cross-instance plan reached this pipeline: FAIL naming the value and the row. Any other value is FAIL naming the value and the row.
PASS/FAIL with offending rows.

**Check 7: Parked rows are genuinely parked**
Every card recorded `blocked_reference` carries reason `shared_snippet_reference` and no rewrite rows; every card recorded `out_of_scope` carries one of `row_not_signed_off | removed_no_tenant_data | layer_not_repointed | layer_requires_opt_in` and no rewrite rows. A parked card with rewrite rows is FAIL: the plan cannot both defer a card and plan a write to it.
PASS/FAIL with offending rows.

The scan, accounting and gating rules above are deterministic. The scan and reference accounting are implemented in `wire/tests/platform_migration/validate_transport_sql_rewrite.py` (shared with transport, unchanged); the repoint-specific gating in Checks 0, 5 and 6 is implemented in `wire/tests/platform_migration/validate_metabase_carveout_repoint.py`. A change to the rules here changes those tests.

### Update status

```yaml
artifacts:
  metabase_carveout_repoint_plan:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Output next command

On PASS:

```
/wire:metabase-carveout-repoint $ARGUMENTS
```

On FAIL, fix the plan and re-run. An unaccounted reference usually means the mapping is missing a shared project row (`metabase-carveout-repoint-generate` Step 2); an unmatched plan row means the plan is stale against the cards; `in_place_without_stage` means the consultant has not yet named the restricted-access collection the change is reviewed in.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout_repoint_plan` as artifact, `validate` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout_repoint_plan` as artifact, `validate` as action.
