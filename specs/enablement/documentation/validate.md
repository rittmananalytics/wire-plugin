---
wire_schema: "1.0"
command: validate
artifact: documentation
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
  - artifact: documentation
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate documentation against standards and best practices
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# documentation Validation Command

## Purpose

Validate that the generated project documentation is internally consistent and actually points at real, current artifacts — a handover document that links to a file that no longer exists, or claims a component is deployed when `status.md` says otherwise, is worse than no documentation at all.

## Usage

```bash
/wire:documentation-validate YYYYMMDD_project_name
```

## Prerequisites

- documentation must be generated (`/wire:documentation-generate` complete)

## Workflow

### Step 1: Verify documentation Exists

**Process**:
1. Check that `documentation.generate == complete` in status.md
2. Verify `enablement/documentation.md` exists

**If not generated**:
```
Error: documentation not generated yet.

Run `/wire:documentation-generate <project>` first.
```

### Step 2: Run Validation Checks

**Validation Checklist**:

| Check | Rule | Severity |
|-------|------|----------|
| Artifact Index links resolve | Every file path in the "Artifact Index" table points to a file that actually exists in `.wire/releases/[release_folder]/` | Critical |
| Artifact Index status matches status.md | Every "Status" value in the Artifact Index table matches the corresponding artifact's real state in `status.md` (no stale "complete" for an artifact that's since regressed, or vice versa) | Critical |
| Data dictionary covers all warehouse models | Every warehouse-layer (`_dim`/`_fact`) dbt model appears in the Data Dictionary section, per `wire/skills/dbt-development/testing-reference.md`'s "warehouse models always 100% documented" convention | Major |
| Data dictionary links, not re-authors, descriptions | Data Dictionary entries reference/link the model's `schema.yml` description rather than containing a materially different, independently-authored description that could drift out of sync | Major |
| Architecture diagram matches complete artifacts | The Mermaid architecture diagram includes only components (`pipeline`, dbt layers, `semantic_layer`, `dashboards`) that are actually `complete` in `status.md` — it doesn't depict a component that hasn't been built yet | Major |
| No unfilled placeholders | The document contains no leftover `[...]`-style placeholder text from the template | Info |
| Runbook has at least one troubleshooting entry | If `deployment` or `data_quality` are complete, the Operational Runbook's Troubleshooting table is not empty | Info |

### Step 3: Generate Validation Report

**Output Format**:

```
## documentation Validation: [PROJECT_NAME]

**Status:** PASS | FAIL

### Validation Results

| Check | Status | Notes |
|-------|--------|-------|
| Artifact Index links resolve | ⚠️ | "Deployment Plan" links to deploy/deployment_plan.md, which does not exist |
| Data dictionary covers all warehouse models | ✅ | |
| Architecture diagram matches complete artifacts | ✅ | |

### Next Steps

1. **Review with stakeholders**: `/wire:documentation-review <project>`
```

### Step 4: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.documentation section:
   ```yaml
   documentation:
     generate: complete
     validate: pass | fail
     review: not_started
     validated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `documentation`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

### Step 5.5: Sync to Linear (Optional)

Follow the Linear sync workflow in `specs/utils/linear_sync.md`:
- Artifact: `documentation`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### Validation Failures

If checks fail:
- Set validate status to `fail`
- List all issues, distinguishing broken links (Critical) from missing dictionary coverage (Major) from cosmetic placeholders (Info)
- Suggest fixes (e.g. "regenerate the Artifact Index — deployment_plan.md was moved or renamed")
- User must fix and re-validate

### Referenced Artifact Regressed Since Generation

If an artifact the documentation references was `complete` when `documentation.md` was generated but has since regressed (e.g. `dashboards` was reset to `in_progress` after a rebuild):
```
Warning: documentation.md was generated when [artifact] was complete, but status.md now shows it as [current_status].

Regenerate documentation once [artifact] is complete again, or note the discrepancy and proceed? (y/n)
```

## Output

This command:
- Validates that documentation's links, status claims, and data dictionary match the real state of the project
- Updates `status.md` with validation results
- Provides actionable feedback if issues found
