---
wire_schema: "1.0"
command: review
artifact: stakeholder_interview
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
  - artifact: stakeholder_interview
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA peer review of a stakeholder interview write-up
argument-hint: "[release-folder] --stakeholder <slug>"

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Stakeholder Interview — Review

## Purpose

Internal RA peer review of a single stakeholder interview write-up. Reviewer is a peer Lead Consultant or the Head of Delivery. The goal is to catch four kinds of problem before consolidation:

1. A tag classification that doesn't match the supporting bullet
2. A theme that's a workaround disguised as a requirement
3. A verbatim quote that's emotional but doesn't actually do diagnostic work
4. Missing follow-ups (questions the consultant should have asked but didn't)

This is **not** a sponsor-facing review.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`
- The corresponding validation report

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS` and `--stakeholder <slug>`. Read the interview file and validation report. If validation has not passed, prompt: "Validation has not passed for this interview — fix tag completeness first via `/wire:stakeholder-interview-validate`."

### Step 2: Pull meeting context

If `fathom_url` is present, fetch the Fathom transcript via the Fathom MCP server. The reviewer is checking the write-up *against* the source recording, so the transcript matters here.

### Step 3: Present for review

Output the write-up. Then ask the reviewer:

```
Reviewer (peer Lead Consultant or Head of Delivery) — review the write-up. Specifically:

1. Are the four tags correct on every theme? (Especially Hierarchy tier — the rule is "lowest tier whose absence is blocking it")
2. Are any themes actually workarounds disguised as requirements?
3. Does the verbatim quote do diagnostic work, or is it just emotional?
4. What questions should have been asked but weren't?

Record anything that should change.
```

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the peer review of this stakeholder interview?",
    "header": "Interview Peer Review",
    "options": [
      {"label": "Approved", "description": "Write-up is solid and ready to feed consolidation"},
      {"label": "Approved with tag corrections", "description": "Specific tags need changing; apply inline"},
      {"label": "Schedule a follow-up", "description": "Material questions weren't asked — book a 30-min follow-up with the stakeholder"},
      {"label": "Re-draft from transcript", "description": "Write-up materially misrepresents what the stakeholder said"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Capture corrections

If tag corrections were called, ask:
```
List the line numbers and the corrected tags. Apply directly to the write-up.
```

Apply them inline.

If follow-up needed, append a `## Follow-up scheduled` section with the date and the unanswered questions.

If re-draft, set `interviews[<slug>].generate: not_started` and prompt to re-run `/wire:stakeholder-interview-generate` (which will pull the transcript again).

### Step 5: Update status

```yaml
interviews:
  - slug: <slug>
    review: complete    # or "pending_followup" / "pending_rework"
```

The aggregate `stakeholder_interview` review state becomes `complete` only when every interview has `review: complete`.

### Step 6: Output review summary

```
## Interview Review Complete — <slug>

**Outcome**: [Approved / Approved with tag corrections / Schedule follow-up / Re-draft]
**Tag corrections**: [N]
**Follow-up booked**: [yes/no]

### Next Steps

[If approved and at least one other interview still pending]:
Continue reviewing interviews. List remaining via /wire:status

[If this was the last interview and all are complete]:
Move to consolidation:
/wire:requirements-matrix-generate $ARGUMENTS
```

### Step 7: Sync to document store (if approved)

Follow `specs/utils/docstore_sync.md`.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`
