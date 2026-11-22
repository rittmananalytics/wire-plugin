---
wire_schema: "1.0"
command: validate
artifact: pitch
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
  - artifact: pitch
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate pitch document structure, completeness, and Shape Up quality

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pitch Validate Command

## Purpose

Validates that the pitch document is complete and meets the Shape Up quality bar — not too detailed (avoids over-specification), not too vague (enough to bet on). Checks all 10 sections, appetite specificity, solution sketch quality, and the "no premature solution" constraint.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/pitch.md`

## Workflow

### Step 1: Read the Pitch

Resolve release folder. Read `planning/pitch.md`. If not found, prompt to generate first.

### Step 2: Run Validation Checks

#### Section completeness
- [ ] Section 1 (Problem) — present, summarises the problem for a decision-maker, references who has it
- [ ] Section 2 (Appetite) — explicitly states "Small batch" or "Big batch" with a time range; includes scope implications
- [ ] Section 3 (Solution Sketch) — present and non-empty; describes core user/system behaviour
- [ ] Section 4 (Rabbit Holes) — at least 1 rabbit hole named and described
- [ ] Section 5 (No-gos) — at least 2 no-gos listed
- [ ] Section 6 (Risks) — risk table has at least 1 row
- [ ] Section 7 (Success Criteria) — at least 2 measurable criteria listed as checkboxes
- [ ] Section 8 (Downstream Releases) — present (even if "TBD" or "none identified yet")
- [ ] Section 9 (Timeline) — all milestone dates present (or clearly marked TBD)
- [ ] Section 10 (The Bet) — non-empty, makes a case for doing this now

#### Quality checks
- [ ] **Appetite is specific**: Section 2 uses "Small batch (1–2 weeks)" or "Big batch (6 weeks)" — not vague phrases like "a few sprints"
- [ ] **Solution is shaped, not specified**: Section 3 describes behaviour without prescribing implementation choices (no specific database, no exact API design, no pixel-perfect UI)
- [ ] **Solution is not just restating the problem**: Section 3 proposes something, not just re-describes what's wrong
- [ ] **Success criteria are measurable**: Each criterion in Section 7 can be verified as true or false after delivery
- [ ] **No-gos are genuine boundaries**: Section 5 items would be tempting to add (otherwise they wouldn't need to be called out)
- [ ] **The Bet is persuasive**: Section 10 answers "why now" — not just "what"

#### Consistency checks
- [ ] **Appetite vs scope**: The solution in Section 3 is achievable within the stated appetite in Section 2
- [ ] **No-gos vs solution**: Nothing in the no-gos list contradicts the proposed solution
- [ ] **Success criteria vs problem**: Success criteria in Section 7 map back to the problem described in Section 1

#### Reference legibility
- [ ] **reference_legibility**: Every reference code used is defined at first use or resolved in a Reference key table — run the check per `specs/utils/reference_legibility.md` (passes trivially if the document uses no codes)

### Step 3: Produce Validation Report

**Output location**: `.wire/releases/$ARGUMENTS/planning/pitch_validation.md`

```markdown
# Pitch Validation Report

**Release**: [folder]
**Date**: [today's date]
**File**: planning/pitch.md

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|-------|--------|------|
| Section 1: Problem summary | ✅ PASS | |
| Section 2: Appetite specific | ⚠️ WARNING | States "a few weeks" — must be "Small batch (1–2 weeks)" or "Big batch (6 weeks)" |
| Section 3: Solution sketched | ✅ PASS | |
| Section 4: Rabbit holes | ✅ PASS | |
| Section 5: No-gos | ✅ PASS | |
| Section 6: Risks | ✅ PASS | |
| Section 7: Measurable criteria | ❌ FAIL | Criterion 2 is not measurable: "users are happier" |
| Section 8: Downstream releases | ✅ PASS | |
| Section 9: Timeline | ✅ PASS | |
| Section 10: The Bet | ✅ PASS | |
| Appetite specificity | ⚠️ WARNING | |
| Solution shaped, not spec'd | ✅ PASS | |
| Appetite vs scope | ✅ PASS | |

## Issues to Resolve

### FAIL: Success criterion not measurable
Section 7 criterion 2: "users are happier" cannot be verified. Replace with a specific, observable outcome (e.g. "Operations team reports 0 overnight exception emails going unaddressed for 5 consecutive business days").

### WARNING: Appetite wording
Replace "a few weeks" in Section 2 with the standard Shape Up phrasing.

## Next Steps
[Pass/Fail next steps]
```

### Step 4: Update Release Status

```yaml
pitch:
  validate: "complete"  # or "failed"
```

## Output Files

- `.wire/releases/[folder]/planning/pitch_validation.md`
- Updated `.wire/releases/[folder]/status.md`
