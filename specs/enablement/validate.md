---
wire_schema: "1.0"
command: validate
artifact: training
domain: enablement
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: training
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate training against standards and best practices
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# training Validation Command

## Purpose

Validate generated training materials against the completeness and deliverability checks `training_generate.md` itself defines in "Validation Checks (for next step)", plus the structural cross-references between a training type's session plan, exercise workbook, and delivery checklist.

## Usage

```bash
/wire:training-validate YYYYMMDD_project_name
```

## Prerequisites

- training must be generated (`/wire:training-generate` complete)

## Workflow

### Step 1: Verify training Exists

**Process**:
1. Check that `training.generate == complete` in status.md
2. Verify generated files exist for every training type listed in `artifacts.training.session_plans`:
   - `enablement/training_<type>_session_plan.md`
   - `enablement/training_<type>_slides.md`
   - `enablement/training_<type>_exercises.md`
   - `enablement/training_<type>_quick_reference.md`
3. Verify `enablement/training_delivery_checklist.md` exists (shared across all training types)

**If not generated**:
```
Error: training not generated yet.

Run `/wire:training-generate <project>` first.
```

### Step 2: Run Validation Checks

**Validation Checklist** (per training type, unless noted as delivery-checklist-level):

| Check | Rule | Severity |
|-------|------|----------|
| Learning objectives present | Session plan's "Learning Objectives" section has at least one objective, and no objective is left as an unfilled `[...]` placeholder | Critical |
| Learning objectives are specific | Each objective names a concrete skill/action (not generic filler text like "understand the platform") | Major |
| Prerequisites stated | Session plan's "Prerequisites" section lists at least one required item | Major |
| Agenda timing is realistic | Each agenda part has a stated duration, and the parts' durations sum to the session's stated total "Duration" (± 5 minutes) | Major |
| Exercises are cross-referenced | Every exercise named in the session plan's "Hands-On Exercises" section has a matching entry (same name) in that training type's `_exercises.md` workbook | Critical |
| Exercise solutions present | Every exercise in `_exercises.md` has a corresponding entry under its "Solutions" section | Major |
| Post-session support defined | Session plan's "Post-Session Support" section lists at least one resource or support channel | Major |
| Delivery checklist references all files | `training_delivery_checklist.md`'s "Materials to Share" section (or equivalent) accounts for the session plan, slides, exercises, and quick reference file actually generated for every training type in scope | Major |
| No unfilled placeholders | None of the generated files contain literal `[...]`-style placeholder text left over from the template | Info |

### Step 3: Generate Validation Report

**Output Format**:

```
## training Validation: [PROJECT_NAME]

**Status:** PASS | FAIL

### Validation Results

| Training Type | Check | Status | Notes |
|----------------|-------|--------|-------|
| Data Team Enablement | Learning objectives present | ✅ | |
| Data Team Enablement | Agenda timing is realistic | ✅ | |
| Data Team Enablement | Exercises are cross-referenced | ⚠️ | Exercise 3 in session plan has no matching entry in training_data_team_exercises.md |
| End User Training | Post-session support defined | ✅ | |
| (shared) | Delivery checklist references all files | ✅ | |

### Next Steps

1. **Review with stakeholders**: `/wire:training-review <project>`
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.training section:
   ```yaml
   training:
     generate: complete
     validate: pass | fail
     review: not_started
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `training`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

### Step 5.5: Sync to Linear (Optional)

Follow the Linear sync workflow in `specs/utils/linear_sync.md`:
- Artifact: `training`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Validation Failures

If checks fail:
- Set validate status to `fail`
- List all issues, grouped by training type
- Suggest fixes (e.g. "add a matching exercise entry", "state a duration for Part 3")
- User must fix and re-validate

### Exercise Cross-Reference Mismatch

If a session plan names an exercise that has no matching workbook entry (or vice versa — a workbook exercise never referenced in any session plan's agenda):
```
Warning: Exercise cross-reference mismatch for [Training Type].

Session plan references: [Exercise names from session plan]
Exercise workbook contains: [Exercise names from _exercises.md]

Missing from workbook: [list]
Orphaned in workbook (not referenced in any session plan): [list]
```
This is a Critical-severity check only when the workbook is missing an exercise the session plan promises to cover; an orphaned workbook exercise (extra material not used in the agenda) is a Major-severity note, not a failure.

## Output

This command:
- Validates training completeness, cross-references, and deliverability per training type
- Updates `status.md` with validation results
- Provides actionable feedback if issues found
