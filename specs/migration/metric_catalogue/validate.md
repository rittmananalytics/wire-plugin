---
wire_schema: "1.0"
command: validate
artifact: metric_catalogue
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: report
    path: "audit/metric_catalogue.md"
    description: "Validation section appended with a per-check PASS/FAIL table"
preconditions:
  - artifact: metric_catalogue
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: "Experimental: Validate the metric catalogue: reproducible from the audit, every group proposed, every conflict parked or ruled, every finding dispositioned, no sum of ratios proposed"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metric Catalogue: Validate

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. The same steps serve `looker_studio_to_looker` (experimental), which has run end to end once into Looker on two reports, not on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Checks the metric catalogue before the client rules on it. Produces a PASS/FAIL report with the gaps to fix.

## Prerequisites

- `audit/metric_catalogue.md` exists (metric_catalogue generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metric_catalogue.md`, `.csv` and `.json`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/reports/*/report.json`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Run validation checks

**Check 1: The catalogue is reproducible**
Re-run `looker_studio_metrics.py` over the same `report.json` files into a temporary folder; `metric_catalogue.json` must match byte for byte.
PASS/FAIL.

**Check 2: Every group that needs a decision has a proposal**
Every group with class `conflict` or `same_shape_different_fields`, and every `same_definition` group with more than one copy, has a proposal in `metric_catalogue.md`.
PASS/FAIL with the groups missing one.

**Check 3: Every conflict is parked or ruled**
Every `conflict` group has a `parked_decisions` entry in `status.md` or a ruling in `decisions.md`.
PASS/FAIL.

**Check 4: Every finding has a disposition**
Every `sum_of_ratio` finding appears in the Findings section with the corrected form.
PASS/FAIL.

**Check 5: No proposal sums a ratio**
No proposed formula applies `SUM` (or another aggregate) to a field that is itself a per-row division.
PASS/FAIL.

**Check 6: Counts match status.md**
`definition_count`, `group_count`, `conflict_count`, `alias_count`, `finding_count` equal the JSON counts.
PASS/FAIL.

### Step 2: Write validation report

Append a `## Validation` section to `audit/metric_catalogue.md` with a per-check table and a "Gaps to address" list.

### Step 3: Update status

```yaml
artifacts:
  metric_catalogue:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 4: Output next command

If PASS:
```
/wire:metric-catalogue-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:metric-catalogue-validate $ARGUMENTS
```

## Output Files

- Updated `.wire/releases/$ARGUMENTS/audit/metric_catalogue.md` (Validation section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metric_catalogue` as artifact, `validate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metric_catalogue` as artifact_id, `Metric Catalogue` as artifact_name, and the `file` value from `artifacts.metric_catalogue` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metric_catalogue` as artifact, `validate` as action.
