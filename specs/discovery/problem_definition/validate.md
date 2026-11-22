---
wire_schema: "1.0"
command: validate
artifact: problem_definition
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
  - artifact: problem_definition
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate problem definition completeness and quality

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Problem Definition Validate Command

## Purpose

Validates that the problem definition document is complete, specific, and well-framed before moving to the pitch. Checks structural completeness, specificity of constraints, measurability of the desired outcome, and internal consistency.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/problem_definition.md` (or legacy path)

## Workflow

### Step 1: Locate and Read the Problem Definition

**Process**:
1. Resolve release folder from `$ARGUMENTS` (two-tier: `.wire/releases/$ARGUMENTS/`, legacy: `.wire/$ARGUMENTS/`)
2. Read `planning/problem_definition.md`
3. If file not found, output: "Problem definition not found. Run /wire:problem-definition-generate [folder] first."

### Step 2: Run Validation Checks

Run all checks and collect PASS/FAIL/WARNING results:

#### Section completeness
- [ ] Section 1 (Who Has This Problem) — not empty, names a specific role or team (not "the business")
- [ ] Section 2 (What They Are Trying to Do) — describes a job-to-be-done, not a solution
- [ ] Section 3 (What Is Getting in Their Way) — describes specific friction, not vague "lack of visibility"
- [ ] Section 4 (Impact) — at least 2 rows of the impact table completed
- [ ] Section 5 (What Solved Looks Like) — describes outcome, not implementation
- [ ] Section 6 (Constraints) — budget and timeline fields are not both "to be determined"
- [ ] Section 7 (Out of Scope) — at least one item listed

#### Quality checks
- [ ] **Problem vs solution**: Section 5 does not describe a technical solution (e.g. "build a dashboard") — it describes an outcome (e.g. "the ops team can see overnight exceptions before their morning standup")
- [ ] **Specificity**: Section 3 contains at least one concrete detail (a named system, a process step, a time/cost figure)
- [ ] **Constraints specificity**: At least one constraint is specific (e.g. "£50k" not "limited budget", "Q3 2026" not "soon")
- [ ] **No premature solutions**: None of sections 1–7 describe implementation choices (database, tool names, architecture patterns) unless they are genuine constraints
- [ ] **Open questions tracked**: Section 9 is present and lists any unresolved questions (or explicitly states "None")

#### Consistency checks
- [ ] **Scope boundary**: Items in Section 7 (Out of Scope) do not contradict the desired outcome in Section 5
- [ ] **Constraints vs outcome**: The constraints do not make the desired outcome impossible (flag if they appear to conflict)

#### Reference legibility
- [ ] **reference_legibility**: Every reference code used is defined at first use or resolved in a Reference key table — run the check per `specs/utils/reference_legibility.md` (passes trivially if the document uses no codes)

### Step 3: Produce Validation Report

**Output location**: `.wire/releases/$ARGUMENTS/planning/problem_definition_validation.md`

```markdown
# Problem Definition Validation Report

**Release**: [folder]
**Date**: [today's date]
**File**: planning/problem_definition.md

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|-------|--------|------|
| Section 1: Who has this problem | ✅ PASS | |
| Section 2: Job-to-be-done | ✅ PASS | |
| Section 3: Specific friction | ⚠️ WARNING | "Lack of visibility" is vague — add a concrete example |
| Section 4: Impact table | ✅ PASS | |
| Section 5: Outcome not solution | ✅ PASS | |
| Section 6: Constraints specific | ❌ FAIL | Budget and timeline are both "to be determined" |
| Section 7: Out of scope | ✅ PASS | |
| Problem vs solution check | ✅ PASS | |
| No premature solutions | ✅ PASS | |
| Open questions tracked | ✅ PASS | |
| Scope consistency | ✅ PASS | |

## Issues to Resolve

### FAIL: Constraints not specific enough
Section 6 shows budget and timeline as "to be determined". At minimum, provide an appetite (e.g. "1–2 weeks" or "6 weeks") before moving to the pitch — the pitch requires a defined appetite.

### WARNING: Friction description is vague
Section 3 describes friction as "lack of visibility into overnight processes". Add a concrete example: what system, what data, what time window, and what the analyst has to do manually instead.

## Next Steps

[If PASS or PASS WITH WARNINGS]:
1. Resolve warnings if applicable
2. Review with stakeholders: /wire:problem-definition-review [folder]
3. Then generate the pitch: /wire:pitch-generate [folder]

[If FAIL]:
1. Fix the issues listed above
2. Re-run validation: /wire:problem-definition-validate [folder]
```

### Step 4: Update Release Status

Update `status.md`:
```yaml
problem_definition:
  validate: "complete"   # or "failed" if FAIL result
```

### Step 5: Output Summary

Show the validation result and the most important issue to fix (if any).

## Output Files

- `.wire/releases/[folder]/planning/problem_definition_validation.md`
- Updated `.wire/releases/[folder]/status.md`
