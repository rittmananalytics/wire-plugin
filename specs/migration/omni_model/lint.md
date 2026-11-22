---
wire_schema: "1.0"
command: utility
artifact: omni_model
domain: migration
release_types:
  - bi_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> lints one model batch (default: the most recently written batch)"
produces:
  - type: report
    path: "migration/omni_model/lint_<batch_id>.md"
    description: "Per-rule PASS/FAIL table for the batch with the offending file and key for every failure"
preconditions:
  - artifact: omni_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Offline static lint of the emitted Omni YAML for one batch, catching the translations that would pass Omni's validator and still return the wrong answer, before validate spends a CLI call
argument-hint: <release-folder> [--batch <id>]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding. Note that the gate reads `artifacts.omni_model.generate`; while batches are still being written that field is `in_progress`, and this command may run against any batch already listed in `batches_complete`. Treat a batch present in `batches_complete` as meeting the gate for that batch.

---

# Omni Model: Lint

## Purpose

A static pass over the YAML the converter emitted for one batch. It reads local files only: no Omni CLI, no warehouse, no network. It exists because `omni models validate` checks that the model is well formed, not that it says what the LookML said. A `${TABLE}` left in a `sql:` fails loudly at validate, but a fan-out join whose joined view has no primary key, a bare-scalar measure filter, or a relationship whose cardinality was recorded wrongly can pass validation and fan out or filter wrongly at query time. Those are cheap to catch here and expensive to catch in parity.

Ten rules, each PASS or FAIL for the batch, each failure naming the file and the key.

## Prerequisites

- The batch directory `migration/omni_model/<batch_id>/` exists with at least one emitted file
- `migration/omni_model/<batch_id>/needs_human.json` exists

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/**` (emitted YAML)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv` (for L7: views that already exist on the Omni model but are not in this batch)
- `wire/bi_pairs/looker_to_omni/property_mapping.md` (the Omni timeframe, aggregate type and relationship type lists)

## Rule catalogue

| Rule | Checks | Why |
|---|---|---|
| L1 | No `${TABLE}` anywhere in an emitted file | Omni has no `${TABLE}`; it errors at validate and at query time. A plain column dimension auto-maps by name and needs no `sql:` |
| L2 | No Liquid (`{%`, `%}`, or `{{` outside a topic `always_where_sql` that the plan ruled as an Omni templated filter) in any `sql`, `label`, `description`, `html` or `markdown` value | Liquid does not render in Omni; a label containing `{{` is a literal string in the picker |
| L3 | Every value under `timeframes:` is one of Omni's timeframes: `raw`, `date`, `week`, `month`, `quarter`, `year`, `hour`, `minute`, `second`, `millisecond`, `day_of_week_name`, `day_of_week_num`, `day_of_month`, `day_of_quarter`, `day_of_year`, `hour_of_day`, `month_name`, `month_num`, `quarter_of_year`, `fiscal_quarter`, `fiscal_year` | An unknown timeframe is dropped by Omni, so the field loses a grain the dashboard queries |
| L4 | Every `aggregate_type` is one of `sum`, `count`, `count_distinct`, `average`, `min`, `max`, `median`, `list`, `percentile`, `sum_distinct_on`, `average_distinct_on`, `median_distinct_on`, `percentile_distinct_on`; `percentile` carries a `percentile:` value; `*_distinct_on` carries `custom_primary_key_sql` | `avg` (the LookML habit) is not a value Omni accepts |
| L5 | Every measure `filters:` entry is an operator object (`{ is: ... }`, `{ is_not: ... }`, `{ greater_than: ... }`, and so on), never a bare scalar | `status: complete` is rejected as an invalid filter spec; `is_returned: true` on a boolean is the most common form of the mistake |
| L6 | Every view named in any `relationships.yaml` entry (either side) has a dimension with `primary_key: true` or a `custom_compound_primary_key_sql` | Without a key Omni cannot dedupe the join and aggregates fan out |
| L7 | Every topic `base_view` and every key under `joins:` (at any nesting depth) resolves to a view emitted in this batch, in an earlier complete batch, or present on the Omni model per the audit's `omni_audit` catalog when one exists | A topic that names a missing view validates as a warning and queries as an error |
| L8 | Every `relationship_type` is `one_to_one`, `many_to_one`, `one_to_many`, `many_to_many` or `assumed_many_to_one`; every `join_type` is `always_left`, `inner`, `full_outer`, `cross`, `right_left` or `left_right`; every `join_to_view_as` alias is used in its `on_sql` and in the topic's `joins`, and never appears as a `join_to_view` elsewhere | Omni's documented values (docs.omni.co, relationship-type and join-type parameters). A fan-out relationship (`one_to_many`, `many_to_many`) additionally requires L6 to hold on the joined view, or aggregates fan out |
| L9 | No duplicate dimension or measure name within one view file, and no dimension name that collides with a measure name | Omni keys fields by name in one namespace per view |
| L10 | Every `needs_human.json` item of class `redesign` has no emitted counterpart: no view, dimension or measure of that name in the batch directory | A redesign that was emitted anyway is a guess, and guesses pass validate |

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. Run `python3 <plugin-root>/scripts/bi_to_omni.py lint migration/omni_model/<batch_id>/` first: it checks L0 to L9 that need no Omni call, and L11, a dimension or measure whose SQL refers to its own name (in Omni that is a self-reference, not a column). Then apply the remaining rules by reading, as below. Overall result is PASS only when the script and every rule pass.

## Workflow

### Step 1: Resolve the batch

`--batch <id>` or, absent, the last entry in `artifacts.omni_model.batches_complete`. Stop if the batch directory or `needs_human.json` is missing: the batch has not been generated.

### Step 2: Run the rules

Parse every emitted file as YAML (a parse failure is itself a FAIL under a rule `L0: parseable`, reported first). Apply L1 to L10. Collect every failure as `(rule, file, key path, offending value, what to change)`.

### Step 3: Write the report

`migration/omni_model/lint_<batch_id>.md`:

```markdown
# Omni Model Lint: batch b01

| Rule | Result | Failures |
|---|---|---|
| L0 parseable | PASS | 0 |
| L1 no ${TABLE} | PASS | 0 |
| L2 no Liquid | FAIL | 1 |
| ... | ... | ... |

## Failures

| Rule | File | Key | Value | Change |
|---|---|---|---|---|
| L2 | ANALYTICS/orders.view | dimensions.region_label.sql | `{% if ... %}` | Remove; nh-001 is a redesign item and must not be emitted |
```

Overall result is PASS only when every rule passes.

### Step 4: Update status

```yaml
artifacts:
  omni_model:
    lint: pass | fail
    lint_date: "{{TODAY}}"
    lint_batch: b01
```

### Step 5: Output next command

If PASS:
```
/wire:omni-model-validate $ARGUMENTS --batch <batch_id>
```

If FAIL:
```
Lint failed for batch <batch_id>: <N> failure(s) across <rules>.
Fix the emitted YAML in migration/omni_model/<batch_id>/ (or re-run the converter after
fixing the pair override), rewrite the changed files to the branch, then re-run:
/wire:omni-model-lint $ARGUMENTS --batch <batch_id>
```

A fix to converter output is a fix to the pair tables or the engagement override, not to the emitted file alone. Editing the emitted file by hand and re-running the converter later reintroduces the defect. Record which of the two was done.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_model/lint_<batch_id>.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact, `lint` as action.

3. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_model` as artifact, `lint` as action.
