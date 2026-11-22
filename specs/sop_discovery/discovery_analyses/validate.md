---
wire_schema: "1.0"
command: validate
artifact: discovery_analyses
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
  - artifact: discovery_analyses
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the three analyses — completeness, chart shape, diagnosis grounding, Maturity pin evidence

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Discovery Analyses — Validate

## Purpose

Checks that the three analyses are complete, internally consistent, grounded in the matrix evidence, and ready to drive the Findings Playback deck. This validation is the last gate before client-facing deliverables; failures here propagate into the deck.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- All interview write-ups

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read all inputs.

### Step 2: Hierarchy analysis checks

- [ ] All five tiers appear in the distribution table (even if some have count 0)
- [ ] Counts in the distribution table match the actual `Hierarchy` column in the requirements matrix (cross-check)
- [ ] Diagnosis section has 4–6 bullets
- [ ] At least 2 of those bullets reference a specific verbatim quote
- [ ] No diagnosis bullet is generic boilerplate ("the client needs to invest in their data foundations" — flag as too vague)
- [ ] Per-tier supporting quotes section has at least one quote per non-zero tier

### Step 3: PPT analysis checks

- [ ] All three axes appear (People / Process / Technology) with counts
- [ ] Counts match the `PPT axis` column in the matrix
- [ ] Diagnosis has 4–6 bullets and names a binding constraint axis explicitly
- [ ] Word clouds have 6–12 labels per axis
- [ ] Word cloud labels are not the same as the axis name (i.e. not just `#People` `#Process` — actual themes)
- [ ] Per-axis supporting quotes present

### Step 4: Maturity Curve checks

- [ ] Pin is exactly one of the five stages
- [ ] Justification has 3–5 bullets
- [ ] Each justification bullet cites either a verbatim quote or a specific row from the matrix
- [ ] Pin is consistent with the Hierarchy and PPT distributions:
  - If Hierarchy is bottom-heavy (Collect/Clean dominate) and PPT diagnosis names Process or Technology as binding, pin should be **Data Chaos** or **Order** — flag if higher
  - If Hierarchy is top-heavy and PPT diagnosis is People-led, pin can be **Democratisation** or higher
  - Otherwise flag for reviewer confirmation

### Step 5: MoSCoW + Phase checks

- [ ] Every row in the requirements matrix now has a MoSCoW value (no remaining `TBD`)
- [ ] Every row has a Phase value
- [ ] Phase 1 row count is realistic for the SoW commercial envelope (flag a WARNING if >25 rows — usually means too much made it into Phase 1)

### Step 6: Conflict resolution checks

- [ ] Every conflict in the matrix Conflicts log has an entry in the `Sponsor decisions required` section, OR has been resolved with an explicit RA-side decision recorded
- [ ] No conflict is silently picked (i.e. row appears in matrix with one classification but no decision record)

### Step 7: Quote-bank checks

- [ ] Current State opener has 3–4 quotes
- [ ] Desired Future State opener has 2–3 quotes
- [ ] Each per-axis divider has 3 quotes
- [ ] Every quote is found verbatim in at least one interview write-up

### Step 8: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/discovery_analyses_validation.md`

```markdown
# Discovery Analyses Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Hierarchy of Needs

| Check | Result | Note |
|---|---|---|
| All five tiers in table | ✅ | |
| Counts match matrix | ✅ | |
| Diagnosis bullets | ✅ | 5 bullets, 3 with quotes |

## PPT

| Check | Result | Note |
|---|---|---|
| All three axes present | ✅ | |
| Word cloud completeness | ⚠️ | Technology word cloud has only 4 labels — add 2 more |

## Maturity Curve

| Check | Result | Note |
|---|---|---|
| Pin set | ✅ | Data Chaos |
| Justification | ✅ | |
| Pin consistent with distributions | ✅ | Bottom-heavy hierarchy + Process-binding PPT supports Data Chaos |

## MoSCoW + Phase

| Check | Result | Note |
|---|---|---|
| Every row tagged | ✅ | |
| Phase 1 size | ⚠️ | 28 rows in Phase 1 — consider deferring some to Phase 2 |

## Sponsor decisions

3 unresolved conflicts surfaced — all in the `Sponsor decisions required` section. ✅

## Quote bank

All quotes verifiable in source interviews. ✅

## Issues to Resolve

[List FAILs and WARNINGs]

## Next Steps

[If PASS]:
Internal RA review (Head of Delivery + peer):
/wire:discovery-analyses-review $ARGUMENTS

[If FAIL]:
Fix the listed issues and re-run validation.
```

### Step 9: Update status

```yaml
artifacts:
  discovery_analyses:
    validate: complete   # or "failed"
```

### Step 10: Output summary

## Output Files

- `.wire/releases/$ARGUMENTS/planning/discovery_analyses_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
