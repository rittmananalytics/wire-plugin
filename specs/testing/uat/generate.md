---
wire_schema: "1.0"
command: generate
artifact: uat
domain: testing
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
preconditions:
  - artifact: dashboards
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate uat from design and requirements
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# uat Generate Command

Follow `specs/utils/data_quality_engineer_delegate.md` before executing the workflow below.

## Purpose

Generate a UAT test plan that turns every deliverable's acceptance criteria in `requirements_specification.md` into a concrete test scenario a business stakeholder can execute and sign off on. UAT has no automated `validate` step — the stakeholder running through this plan in `/wire:uat-review` **is** the validation — so the plan itself must be complete and unambiguous enough to run without the analyst in the room.

## Usage

```bash
/wire:uat-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must be approved
- Relevant design artifacts should be complete
- At least one development artifact (`dbt`, `dashboards`, `pipeline`, `semantic_layer`) should be complete — a UAT plan for nothing yet built has nothing to test

## Workflow

### Step 1: Read Inputs

**Process**:
1. Read `requirements/requirements_specification.md` — extract the deliverables table (ID, Description, Acceptance Criteria)
2. Read `status.md` to identify which development artifacts are complete and available to test against
3. Read `design/data_model.md` / `development/dashboards.md` (whichever exist) for the concrete field/dashboard names a tester will actually see, so scenarios reference real names, not placeholders

### Step 2: Generate One Test Scenario Per Deliverable

For every deliverable with a stated acceptance criterion, generate a test scenario:

- **Scenario ID**: matches the deliverable ID (e.g. `D3`) so pass/fail traces back to the SOW
- **Setup**: what the tester needs before starting (login, sample data, a specific date range)
- **Steps**: numbered, concrete actions ("Open the Revenue dashboard", "Filter to Q1 2026") — not "verify the dashboard works"
- **Expected Result**: what the tester should see, stated specifically enough that "it looks fine" isn't a valid pass/fail judgment
- **Acceptance Criteria**: copied verbatim from `requirements_specification.md` — the plan doesn't get to soften or reinterpret what was agreed

If a deliverable's acceptance criteria are too vague to turn into concrete steps (e.g. "the dashboard should be useful"), flag it rather than inventing specificity requirements weren't approved with:

```
Deliverable [ID] has no testable acceptance criteria stated in requirements_specification.md ("[criteria text]").

Suggest a specific, testable criterion now, or flag this deliverable for a requirements amendment before UAT sign-off?
```

### Step 3: Generate Cross-Cutting Scenarios

Beyond per-deliverable scenarios, add scenarios for concerns that span deliverables (only include ones actually relevant to what's built):

- **Data freshness**: does the data reflect the expected refresh cadence from `pipeline_design.md`?
- **Access control**: can each stakeholder role see what they're supposed to (and not see what they're not)?
- **Edge cases named in requirements**: any explicitly-discussed edge case (e.g. "what happens with a cancelled subscription") gets its own scenario

### Step 4: Generate UAT Plan

**File**: `.wire/releases/[release_folder]/test/uat_plan.md`

```markdown
# UAT Test Plan: [Project Name]

**Generated**: [Date]
**Testers**: [from requirements_specification.md's stakeholder list, if named]

## How to Use This Plan

Work through each scenario below. Record Pass/Fail and any notes. Any Fail must be discussed before UAT sign-off in `/wire:uat-review`.

## Scenarios

### [Deliverable ID]: [Deliverable Name]

**Setup**: [what's needed before starting]

**Steps**:
1. [Concrete action]
2. [Concrete action]

**Expected Result**: [Specific, checkable outcome]

**Acceptance Criteria** (from requirements): [verbatim from requirements_specification.md]

**Result**: ☐ Pass ☐ Fail
**Notes**:

---

[Repeat per deliverable, then cross-cutting scenarios]

## Sign-off

| Scenario | Result | Tester | Date |
|----------|--------|--------|------|
| [ID] | | | |

**Overall UAT outcome**: ☐ Approved ☐ Changes Requested — recorded via `/wire:uat-review`
```

### Step 5: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.uat section:
   ```yaml
   uat:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: 2026-02-13
     scenario_count: [number of scenarios generated]
   ```
3. Write updated status.md

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `uat`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `uat`
- `artifact_name`: `UAT Plan`
- `file_path`: `.wire/releases/[release_folder]/test/uat_plan.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## uat Generated Successfully

**Scenarios generated**: [N] ([N] per-deliverable, [N] cross-cutting)
**Deliverables with no testable acceptance criteria**: [N] (flagged — see plan)

**File(s):** .wire/releases/[release_folder]/test/uat_plan.md

### Next Steps

1. **Review uat**: `/wire:uat-review <project>` (uat is generate+review only — there is no validate step; sign-off happens directly in review)
```

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### No Development Artifacts Complete

If none of `dbt`, `dashboards`, `pipeline`, `semantic_layer` are complete:
```
Error: No development artifacts are complete yet, so there's nothing to test.

Complete at least one development artifact before generating a UAT plan.
```

### Deliverable Table Missing or Empty

If `requirements_specification.md` has no deliverables table:
```
Error: No deliverables table found in requirements_specification.md.

UAT scenarios are generated one per deliverable — without a deliverables table there's nothing to derive scenarios from. Check that requirements_specification.md follows the standard template.
```

## Output

This command creates:
- `.wire/releases/[release_folder]/test/uat_plan.md` — one test scenario per deliverable acceptance criterion, plus cross-cutting scenarios, plus a sign-off table
- Updates `status.md`
