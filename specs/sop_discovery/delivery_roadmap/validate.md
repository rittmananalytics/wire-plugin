---
wire_schema: "1.0"
command: validate
artifact: delivery_roadmap
domain: sop_discovery
release_types:
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: delivery_roadmap
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the delivery roadmap completeness and Release 1 scope realism

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Delivery Roadmap — Validate

## Purpose

Checks the delivery roadmap is complete and that Release 1 scope is realistic against the commercial envelope.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- `engagement/sow.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read inputs.

### Step 2: Section completeness

- [ ] Objectives (3–5 bullets, business-outcome framed)
- [ ] Scope overview with explicit in/out (✅/❌)
- [ ] Breakdown of Release 1 requirements (table populated)
- [ ] Recommendations table (≥ 3 rows, all with named owner + priority)
- [ ] All three Delivery Options present (Build, Pair, Coach)
- [ ] Each option has all 7 dimensions filled
- [ ] Comparison table populated
- [ ] Release 1 plan summary (sprints, go-live, team, dependencies)
- [ ] Discovery exit checklist present

### Step 3: Preferred option check

- [ ] If `sponsor_validation.preferred_delivery_option` is set, the matching option is named as the headline / recommended option in the document
- [ ] If null, the document presents all three as equal and flags "Sponsor decision required"

### Step 4: Scope realism

- [ ] Release 1 row count vs sprint capacity: row count / sprint count ≤ 4 rows per sprint week (flag WARNING if higher — likely over-scoped)
- [ ] Each Phase 1 row in the matrix appears in the breakdown table (no silent drops)
- [ ] Out-of-scope items (`Phase: Future` and `MoSCoW: Won't`) are listed in the Scope overview as ❌

### Step 5: Commercial sanity

- [ ] At least one delivery option has a sprint count and team allocation that fits the SoW contract value (rough sanity check — RA day rate × allocation × sprint length × sprint count)
- [ ] Named client-side dependencies have a contact owner

### Step 6: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/delivery_roadmap_validation.md`

```markdown
# Delivery Roadmap Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Section completeness

| Check | Result | Note |
|---|---|---|
| Objectives | ✅ | 4 bullets, business-outcome framed |
| Scope overview | ✅ | |
| Release 1 breakdown | ✅ | 18 rows |
| Recommendations table | ✅ | 5 rows, owners + priorities |
| Delivery Options | ✅ | All three present |
| Comparison table | ✅ | |
| Release 1 plan summary | ⚠️ | Go-live date missing |
| Exit checklist | ✅ | |

## Preferred option

Sponsor named: Pair
Document headline: Pair ✅

## Scope realism

- Release 1 rows: 18
- Sprint count (Pair option): 5 sprints × 2 weeks
- Rows per sprint week: 1.8 ✅

## Commercial sanity

[…]

## Next Steps

[If PASS]:
Sponsor review of the roadmap:
/wire:delivery-roadmap-review $ARGUMENTS

[If FAIL]:
Fix issues and re-validate.
```

### Step 7: Update status

```yaml
artifacts:
  delivery_roadmap:
    validate: complete   # or "failed"
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/delivery_roadmap_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
