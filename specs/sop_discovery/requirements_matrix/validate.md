---
wire_schema: "1.0"
command: validate
artifact: requirements_matrix
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
  - artifact: requirements_matrix
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate the requirements matrix for completeness and tag consistency

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Requirements Matrix — Validate

## Purpose

Checks that the requirements matrix is internally consistent, has no missing tags, and accurately reflects the source interviews. Flags rows where the source-stakeholder count looks wrong, where domain/tag combinations are inconsistent, and where conflicts have been silently picked instead of surfaced.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- All `.wire/releases/$ARGUMENTS/planning/interviews/*.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read the matrix and every interview file.

### Step 2: Row-level checks

For every row in the matrix:
- [ ] `Req ID` matches `^R-[A-Z][A-Z0-9-]+-\d{2}$` and is unique
- [ ] `Domain` matches the domain tag in the row (and is in the in-scope domain list)
- [ ] `Type` is one of `pain` `requirement` `kpi` `risk` `existing-asset`
- [ ] `Hierarchy` is one of `collect` `clean` `define-track` `analyse` `optimise-predict`
- [ ] `PPT axis` is one of `people` `process` `technology`
- [ ] `Title` is non-empty
- [ ] `Description` is non-empty and does not contain TODO or `<placeholder>`
- [ ] `Verbatim quote` is non-empty AND can be found verbatim (case-insensitive) in at least one source interview file
- [ ] `Source stakeholders` list is non-empty
- [ ] Every named source stakeholder appears in the stakeholder map
- [ ] `Count` matches the number of source stakeholders listed
- [ ] `Sponsor backing` is `Y` iff one of the source stakeholders is the sponsor
- [ ] `MoSCoW` and `Phase` are `TBD` (must remain unset until after the three analyses)
- [ ] `Confidence` is one of `High` `Medium` `Low`

### Step 3: Cross-row checks

- [ ] Every interview file is referenced as a source on at least one row (else the file contributed nothing — investigate)
- [ ] No two rows have an identical `Title` + `Domain` (would indicate failed de-duplication)
- [ ] **Coverage**: every in-scope domain has at least one row tagged to it. Domains with fewer than 3 rows are flagged WARNING.
- [ ] **Conflict surfacing**: every contradiction noted in any individual interview write-up (look for phrases like "disagrees", "differs from", "conflicts with") appears in the Conflicts log, OR explicitly in the `Conflicts / open questions` column of a row

### Step 4: Tag distribution sanity

- [ ] At least one row at each Hierarchy tier OR an explicit note in the matrix body saying "no requirements at tier X — foundations are fine / not yet reached"
- [ ] All three PPT axes have at least one row
- [ ] If 80%+ of rows are at a single Hierarchy tier (e.g. all `clean`), this is flagged WARNING — it may be diagnostically correct, but the analyses prose should call this out explicitly

### Step 5: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/requirements_matrix_validation.md`

```markdown
# Requirements Matrix Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}
**Rows checked**: {{N}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Row-level failures

| Req ID | Issue |
|---|---|
| R-RETAIL-03 | Verbatim quote not found in any source interview file |
| R-FINANCE-02 | Count = 3 but only 2 source stakeholders listed |

## Coverage

| Domain | Row count | Status |
|---|---|---|
| Retail | 12 | ✅ |
| Fulfilment | 2 | ⚠️ Under-represented |
| Finance | 7 | ✅ |

## Tag distribution

[Hierarchy and PPT count tables as shown in the matrix, repeated here for the report. Flag any axis or tier with 0 rows.]

## Conflicts log audit

- 4 conflict mentions found in interview files
- 4 appear in the matrix Conflicts log → ✅

## Next Steps

[If PASS]:
Internal RA review of the matrix:
/wire:requirements-matrix-review $ARGUMENTS

[If FAIL]:
Fix the listed row issues and re-run validation.
```

### Step 6: Update status

```yaml
artifacts:
  requirements_matrix:
    validate: complete   # or "failed"
```

### Step 7: Output summary

Show top 3 issues with Req IDs.

## Output Files

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
