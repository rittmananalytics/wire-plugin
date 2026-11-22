---
wire_schema: "1.0"
command: validate
artifact: release_brief
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
  - artifact: release_brief
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate release brief against the pitch and check deliverable clarity

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Release Brief Validate Command

## Purpose

Validates that the release brief is consistent with the approved pitch, that all deliverables have clear acceptance criteria, that the budget and timeline are populated, and that the downstream release list is complete and actionable.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/release_brief.md`
- `.wire/releases/$ARGUMENTS/planning/pitch.md` (for consistency check)

## Workflow

### Step 1: Read Both Documents

Read `planning/release_brief.md` and `planning/pitch.md`. If either is missing, prompt the user to generate the missing document first.

### Step 2: Run Validation Checks

#### Section completeness
- [ ] Section 1 (Executive Summary) — present and non-empty
- [ ] Section 2 (Appetite and Timeline) — appetite matches the pitch's confirmed appetite; start date and end date present or marked TBD with a reason
- [ ] Section 3 (Deliverables) — at least 1 deliverable with acceptance criteria; acceptance criteria are specific and verifiable
- [ ] Section 4 (Downstream Releases) — present; at least 1 downstream release listed with type and scope summary
- [ ] Section 5 (Out of Scope) — at least 2 items matching the pitch's no-gos
- [ ] Section 6 (Assumptions) — at least 1 assumption listed
- [ ] Section 7 (Risks) — at least 1 risk listed
- [ ] Section 8 (Resources) — engagement lead named
- [ ] Section 9 (Budget) — not blank
- [ ] Section 10 (Dependencies) — present (even if "None")
- [ ] Section 12 (Sign-off) — table present with client sponsor role

#### Consistency with pitch
- [ ] **Appetite match**: Section 2 appetite matches pitch Section 2 appetite (after any review adjustment)
- [ ] **No-gos carried through**: Items in brief Section 5 cover the pitch's no-gos (brief may be more specific, but nothing should be dropped)
- [ ] **Downstream releases match**: Brief Section 4 matches pitch Section 8 (or explains deviations)
- [ ] **Success criteria**: Brief deliverable acceptance criteria can be mapped to pitch success criteria — nothing promised in the pitch is missing from the brief

#### Deliverable quality checks
- [ ] Each acceptance criterion is specific: can be verified as true or false
- [ ] No acceptance criterion uses vague language: "good quality", "fast enough", "user-friendly" (flag these)
- [ ] Each deliverable has an assigned owner

#### Reference legibility
- [ ] **reference_legibility**: Every reference code used (D-n, A-n, and any code cited from other artifacts) is defined at first use or resolved in a Reference key table — run the check per `specs/utils/reference_legibility.md`

### Step 3: Produce Validation Report

**Output location**: `.wire/releases/$ARGUMENTS/planning/release_brief_validation.md`

Report format follows the same structure as other Wire validation reports: result (PASS/FAIL/WARNINGS), check table, issues to resolve, next steps.

### Step 4: Update Release Status

```yaml
release_brief:
  validate: "complete"  # or "failed"
```

## Output Files

- `.wire/releases/[folder]/planning/release_brief_validation.md`
- Updated `.wire/releases/[folder]/status.md`
