---
wire_schema: "1.0"
command: validate
artifact: stakeholder_map
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
  - artifact: stakeholder_map
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate stakeholder map completeness and coverage

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Stakeholder Map — Validate

## Purpose

Verifies that the stakeholder map covers every in-scope domain with at least one P0/P1 voice, and that every row has the fields needed to schedule and conduct the interview.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md`
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` (to read the in-scope domain list)

## Workflow

### Step 1: Locate the map

Resolve `$ARGUMENTS`. Read both files. If the map is missing: "Run `/wire:stakeholder-map-generate $ARGUMENTS` first."

### Step 2: Run checks

#### Row-level completeness
For every row in the stakeholder table:
- [ ] Slug present and matches `^[a-z][a-z0-9-]+$` (kebab-case, ASCII)
- [ ] Name + title not empty
- [ ] Department populated
- [ ] Priority is one of `P0` / `P1` / `P2`
- [ ] Influence and interest are each one of `H` / `M` / `L`
- [ ] Sentiment is one of `Positive` / `Neutral` / `Sceptical` (no blanks for P0/P1 — guess if you must)
- [ ] Booking owner named
- [ ] Recommended interviewer named (an RA team member)
- [ ] Target week named (1 / 2 / 3)

#### Slug uniqueness
- [ ] Every slug appears at most once

#### Coverage
- [ ] Every in-scope domain from the engagement brief is covered by at least one P0 or P1
- [ ] Sponsor (from engagement brief) is in the table with priority `P0`
- [ ] At least one row has `Role in discovery: Sponsor`
- [ ] At least one row has `Role in discovery: SME` per in-scope domain
- [ ] At least one row references a technical / data owner

#### Volume sanity
- [ ] Total P0 + P1 count is in `[4, 12]` (single-domain) or `[6, 15]` (multi-domain). Flag a WARNING outside that range — too few risks under-coverage; too many risks discovery drift.

### Step 3: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/stakeholder_map_validation.md`

```markdown
# Stakeholder Map Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|---|---|---|
| All rows complete | ✅ | |
| Slug format and uniqueness | ✅ | |
| In-scope domain coverage | ❌ | "Fulfilment" has no P0/P1 stakeholder |
| Sponsor present as P0 | ✅ | |
| Technical/data owner present | ✅ | |
| Volume sanity (P0+P1 count) | ⚠️ | 16 P0+P1 stakeholders for a single-domain discovery — risk of drift |

## Domain coverage

| Domain | P0 count | P1 count | Status |
|---|---|---|---|
| Retail | 2 | 3 | ✅ |
| Fulfilment | 0 | 0 | ❌ No coverage |
| Finance | 1 | 1 | ✅ |

## Issues to Resolve

### FAIL: Fulfilment domain has no stakeholder
Add at least one P0 or P1 from the fulfilment side. Without that voice, fulfilment requirements will be retrofitted from adjacent interviews.

### WARNING: P0+P1 count is high
16 P0+P1 interviews in a single-domain discovery will take 4+ weeks at 4–6 interviews/week. Either narrow the list, plan a longer Phase 2, or downgrade some to group P2 sessions.

## Next Steps

1. Resolve any FAILs
2. Confirm the map with the sponsor: /wire:stakeholder-map-review $ARGUMENTS
```

### Step 4: Update status

```yaml
artifacts:
  stakeholder_map:
    validate: complete   # or "failed"
```

### Step 5: Output summary

## Output Files

- `.wire/releases/$ARGUMENTS/planning/stakeholder_map_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
