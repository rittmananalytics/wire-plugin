---
wire_schema: "1.0"
command: validate
artifact: dashboards
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
preconditions:
  - artifact: dashboards
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate dashboards against standards and best practices
argument-hint: <project-folder> [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dashboards Validation Command

## Purpose

Validate generated dashboards against quality standards, naming conventions, and best practices.

## Usage

```bash
/wire:dashboards-validate YYYYMMDD_project_name
```

## Prerequisites

- dashboards must be generated (`/wire:dashboards-generate` complete)

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and checks the named dashboard or tiles of the slice only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. Run every check below against the slice's part. A check that needs the
   whole release (a cross-model consistency check) runs against the slice and
   the parts it depends on, and says so in the report.
3. On a ticket branch, write the result (`pass` or `fail`) to the ticket
   record's front matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`.

## Workflow

### Step 1: Verify dashboards Exists

**Process**:
1. Check that `dashboards.generate == complete` in status.md
2. Verify generated files exist

**If not generated**:
```
Error: dashboards not generated yet.

Run `/wire:dashboards-generate <project>` first.
```

### Step 2: Run Validation Checks

Ground truth is the approved mockup chain, not the dashboard's own claims: read
`design/dashboard_visualization_catalog.csv`, `design/dashboard_spec.md`, the approved semantic
layer, and the generated dashboard files recorded in `status.md` under
`artifacts.dashboards.dashboard_files`.

**Check 1 — Every catalog row produced a tile.** Count tiles across the generated dashboard
files and compare against the catalog row count. A missing tile is a Critical failure: the
stakeholder approved a mockup with that visualization on it.
Severity: **Critical**. Report missing and extra tiles by name.

**Check 2 — No unmapped chart types.** Every tile's `type` was resolved from the mapping table
in `dashboards-generate` Step 3. Any tile that fell through to the table fallback is listed with
the `chart_type` the catalog gave.
Severity: **Critical**.

**Check 3 — Every field resolves against the semantic layer.** For each tile, each entry in
`fields` exists as a real dimension or measure in the approved semantic layer. Field names are
compared exactly, case-sensitive. A field that does not exist means the tile errors for the
first person who opens it.
Severity: **Critical**.

**Check 4 — Model and explore are real and are the ones recorded.** Every tile's `model` and
`explore` match `semantic_layer_model` and `semantic_layer_explore` in `status.md`, and both
exist in the semantic layer.
Severity: **Critical**.

**Check 5 — Every filter in the dashboard spec is present.** Each filter listed under "Filter
Dimensions" in `dashboard_spec.md` exists on the dashboard, with the default value the spec
records, and is listened to by at least one tile. A filter nothing listens to is inert.
Severity: **Major**. Report filters missing, filters with the wrong default, and filters no tile
listens to, separately.

**Check 6 — Tile titles match the catalog.** Each tile's title matches its catalog row's
`visualization_name`. Renaming a tile between mockup approval and delivery breaks the audit
trail even when the numbers are right.
Severity: **Major**.

**Check 7 — Dashboard files parse.** For Looker, the LookML parses and braces balance. For the
other BI tools, the tool's own validator or CLI reports no syntax error. If the tool's validator
cannot be reached, record `unverified` rather than a pass.
Severity: **Critical**. `unverified` is not a pass.

**Check 8 — No mock or literal data in the dashboard layer.** No tile carries hardcoded values,
a table calculation standing in for a missing measure, or a derived table of literal rows. The
same rule `semantic_layer-generate` applies to views applies here.
Severity: **Critical**.

**Check 9 — Filters and tiles agree on grain.** Any tile whose fields do not include the
dimension a listened filter filters on is reported, because that filter will not narrow that
tile.
Severity: **Info**. Legitimate in some designs, worth a reader knowing.

### Step 3: Generate Validation Report

**Output Format**:

```
## Dashboards Validation: [PROJECT_NAME]

**Status:** PASS | FAIL
**Files checked:** [count]  ·  **Tiles checked:** [count]

### Validation Results

| # | Check | Severity | Status | Notes |
|---|-------|----------|--------|-------|
| 1 | Every catalog row produced a tile | Critical | PASS/FAIL | [N catalog rows, N tiles] |
| 2 | No unmapped chart types | Critical | PASS/FAIL | [list] |
| 3 | Every field resolves | Critical | PASS/FAIL | [list] |
| 4 | Model and explore are real | Critical | PASS/FAIL | |
| 5 | Every spec filter is present | Major | PASS/FAIL | [list] |
| 6 | Tile titles match the catalog | Major | PASS/FAIL | [list] |
| 7 | Dashboard files parse | Critical | PASS/FAIL/unverified | |
| 8 | No mock or literal data | Critical | PASS/FAIL | [list] |
| 9 | Filters and tiles agree on grain | Info | PASS/note | [list] |

### Verdict

Any Critical failure is a FAIL. A Major failure is a FAIL unless explicitly waived in the
report with a named reason. Info items never fail the check.

### Next Steps

1. [If FAIL] Fix the listed items and re-run /wire:dashboards-validate <release>
2. [If PASS] Review with stakeholders: /wire:dashboards-review <release>
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.dashboards section:
   ```yaml
   dashboards:
     generate: complete
     validate: pass | fail
     review: not_started
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `dashboards`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Validation Failures

If checks fail:
- Set validate status to `fail`
- List all issues
- Suggest fixes
- User must fix and re-validate

## Output

This command:
- Validates dashboards completeness and quality
- Updates `status.md` with validation results
- Provides actionable feedback if issues found
