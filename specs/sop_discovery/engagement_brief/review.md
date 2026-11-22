---
wire_schema: "1.0"
command: review
artifact: engagement_brief
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
  - artifact: engagement_brief
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of the engagement brief (Head of Delivery sign-off)

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Engagement Brief — Review

## Purpose

Internal RA review of the engagement brief. Unlike most Wire `review` actions, this one is **not** sponsor-facing — the engagement brief is an internal artefact. The reviewer is the Head of Delivery (or a peer Lead Consultant), and the goal is to catch framing or scope problems before the consultant walks into the sponsor kick-off.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`
- `.wire/releases/$ARGUMENTS/planning/engagement_brief_validation.md` (if present)

## Workflow

### Step 1: Locate the brief

Resolve `$ARGUMENTS`. Read both files above. If validation report is missing, prompt the user to run `/wire:engagement-brief-validate $ARGUMENTS` first.

### Step 2: Pull meeting context

Follow `specs/utils/meeting_context.md`:
- Search Fathom transcripts for the sales-process meetings tied to this engagement (typically labelled with the client name and pre-dating the SoW signature)
- Surface any decisions, concerns, or commitments the sales team captured that the brief may have missed

If a document store is configured, follow `specs/utils/docstore_fetch.md` to pull any reviewer comments on the Confluence/Notion copy.

### Step 3: Present for review

Output the brief content followed by the meeting context. Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the internal RA review of the engagement brief?",
    "header": "Engagement Brief Review",
    "options": [
      {"label": "Approved", "description": "Brief is solid — ready to walk into the kick-off"},
      {"label": "Approved with edits", "description": "Small corrections needed; apply them inline"},
      {"label": "Needs rework", "description": "Framing or scope problems — regenerate before kick-off"},
      {"label": "Scope changed", "description": "The client has clarified or changed the engagement scope materially"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect reviewer feedback

Ask directly in chat:
```
Please provide any feedback, corrections, or coaching to record:
(Type "none" if no additional feedback)
```

### Step 5: Apply edits or record feedback

- **Approved with edits**: apply specific text corrections inline to `engagement_brief.md`.
- **Needs rework** or **Scope changed**: append a `## Review Feedback` section to the brief listing what needs to change. Do not rewrite — that requires a new generate cycle.

### Step 6: Update status

```yaml
artifacts:
  engagement_brief:
    review: complete    # or "pending_rework"
```

If rework is needed:
```yaml
artifacts:
  engagement_brief:
    generate: not_started
```

### Step 7: Output review summary

```
## Engagement Brief Review Complete

**Outcome**: [Approved / Approved with edits / Needs rework / Scope changed]
**Reviewer**: [Head of Delivery or peer Lead Consultant]
**Feedback recorded**: [yes/no]

### Next Steps

[If approved]:
Draft the stakeholder map:
/wire:stakeholder-map-generate $ARGUMENTS

[If rework needed]:
Update the engagement brief:
/wire:engagement-brief-generate $ARGUMENTS
```

### Step 8: Sync to document store (if approved)

If outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/planning/engagement_brief.md` (if edits applied)
- Updated `.wire/releases/$ARGUMENTS/status.md`
