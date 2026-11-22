---
wire_schema: "1.0"
command: validate
artifact: sprint_plan
domain: discovery
release_types:
  - discovery_shape_up
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: sprint_plan
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate sprint plan point estimates and appetite budget

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Sprint Plan Validate Command

## Purpose

Validates the sprint plan against the appetite budget, checks for 13-point stories (must be broken down), verifies all deliverables from the release brief are covered, and confirms the velocity assumptions are realistic.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/sprint_plan.md`
- `.wire/releases/$ARGUMENTS/planning/release_brief.md` (for deliverable coverage check)

## Workflow

### Step 1: Read Sprint Plan and Release Brief

Resolve release folder. Read both documents.

### Step 2: Run Validation Checks

#### Point estimation checks
- [ ] **No 13-point stories**: Scan all stories — flag any with 13+ points as requiring breakdown
- [ ] **Points sum to a reasonable total**: see "Appetite budget check" below — total points must fit within the velocity-derived capacity for the confirmed batch size, after holding back the buffer for unknowns and rework
- [ ] **No 0-point stories**: Every story has a non-zero point estimate
- [ ] **Epic subtotals correct**: Each epic's subtotal matches the sum of its story points

#### Deliverable coverage
- [ ] **All deliverables covered**: Every deliverable in the release brief (Section 3) maps to at least one epic in the sprint plan
- [ ] **No orphaned epics**: Every epic in the sprint plan maps to a release brief deliverable

#### Structural checks
- [ ] **Sprint goals defined**: Each sprint has a sprint goal
- [ ] **Stories have owners**: At least 80% of stories have an assigned owner (or "TBD" with a plan to assign)
- [ ] **Definition of Done present**: The sprint plan includes a definition of done

#### Reference legibility
- [ ] **reference_legibility**: Every release-brief deliverable code cited (D-n) is paired with its plain-language name at first mention or resolved in the Reference key table — run the check per `specs/utils/reference_legibility.md`

#### Appetite budget check
- [ ] **Total points vs appetite**: capacity = velocity (5 points/day, per generate.md's velocity assumption) × working days in the appetite, minus the buffer held back for unknowns and rework (20% by default — see the sprint plan's own "Buffer" line for the confirmed %)
  - Small batch (1–2 weeks = 10 working days): total points should be ≤ 40 (5 × 10 × 0.8)
  - Big batch (6 weeks = 30 working days): total points should be ≤ 120 (5 × 30 × 0.8)
  - PASS if total points ≤ budget; WARNING if total points ≤ budget × 1.2 (over budget but within a 20% tolerance); FAIL beyond that

### Step 3: Produce Validation Report

**Output location**: `.wire/releases/$ARGUMENTS/planning/sprint_plan_validation.md`

```markdown
# Sprint Plan Validation Report

**Release**: [folder]
**Date**: [today's date]
**Total points**: [X]
**Appetite budget**: [Y points for small/big batch]
**Point budget utilisation**: [X/Y = Z%]

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|-------|--------|------|
| No 13-point stories | ✅ PASS | |
| Points within appetite budget | ⚠️ WARNING | 118 points vs 120 point budget — tight but acceptable |
| All deliverables covered | ✅ PASS | |
| Sprint goals defined | ✅ PASS | |
| Definition of done present | ✅ PASS | |
| reference_legibility | ✅ PASS | all 6 codes defined at first use or in the Reference key |

## Issues to Resolve

[List any FAIL or WARNING items with specific remediation steps]

## Downstream Releases

Ready to spawn: [list from sprint plan]

## Next Steps
[Pass/Fail next steps]
```

### Step 4: Update Release Status

```yaml
sprint_plan:
  validate: "complete"  # or "failed"
```

## Output Files

- `.wire/releases/[folder]/planning/sprint_plan_validation.md`
- Updated `.wire/releases/[folder]/status.md`
