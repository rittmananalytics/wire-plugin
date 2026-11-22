---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of the requirements matrix

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Requirements Matrix — Review

## Purpose

Internal RA review of the consolidated requirements matrix before the three analyses are run. Reviewer is the Head of Delivery + one peer Lead Consultant. Goal: catch classifications that don't match the supporting evidence, missed conflicts, or under-coverage that the analyses would otherwise inherit.

This review is **not** sponsor-facing. The sponsor sees the analyses output, not the matrix.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix_validation.md`
- All interview write-ups

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read the matrix, validation report, and reference the interview files.

### Step 2: Pull supporting context

If a document store is configured, follow `specs/utils/docstore_fetch.md` to pull any reviewer comments on the Confluence/Notion mirror of the matrix.

### Step 3: Present for review

Output:
1. The validation result and any FAILs/WARNINGs
2. The Hierarchy and PPT tag distribution previews
3. A list of the Conflicts log entries

Then prompt the reviewer:

```
Review focus (do not skip):

1. Hierarchy classifications — sample at least 5 rows and confirm each is the LOWEST tier whose absence blocks the requirement. Refusing to drop a requirement to `clean` because it sounds nicer is the most common failure here.

2. PPT classifications — for any row tagged `technology`, ask: is this really a technology problem, or is it a process problem dressed up? The playbook's failure-mode table specifically calls out the temptation to default to `technology`.

3. Conflicts — are there genuine contradictions buried in the matrix that aren't in the Conflicts log? If so, they need to surface in the Findings Playback as forced-decision items.

4. Under-coverage — are there in-scope domains where the matrix is suspiciously thin? Either there's nothing there (a finding in itself), or interviews were missing.

5. Sponsor's voice — does any row directly contradict something the sponsor said? Flag.
```

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the internal RA review of the requirements matrix?",
    "header": "Requirements Matrix Review",
    "options": [
      {"label": "Approved", "description": "Matrix is ready — proceed to the three analyses"},
      {"label": "Approved with reclassifications", "description": "Specific rows need tag changes; apply inline"},
      {"label": "Re-consolidate", "description": "Material issues with de-duplication or missing rows — regenerate from interviews"},
      {"label": "Reopen interviews", "description": "Gaps require a follow-up interview or a missed P0/P1 to be booked"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture corrections

If reclassifications were called, apply them inline. For each: record the original tag, new tag, and reviewer reason in a `## Review Decisions` section.

### Step 5: Update status

```yaml
artifacts:
  requirements_matrix:
    review: complete    # or "pending_rework" / "pending_followup"
```

### Step 6: Output summary

```
## Requirements Matrix Review Complete

**Outcome**: [Approved / Approved with reclassifications / Re-consolidate / Reopen interviews]
**Reclassifications applied**: [N]
**Conflicts added to log**: [N]

### Next Steps

[If approved]:
Run the three analyses (Hierarchy / PPT / Maturity Curve):
/wire:discovery-analyses-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
