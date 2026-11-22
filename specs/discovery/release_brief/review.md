---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review release brief with client and record sign-off

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Release Brief Review Command

## Purpose

Facilitates the formal client review and sign-off of the release brief. This is the contractual commitment — client sign-off on the release brief authorises the team to proceed to sprint planning and delivery. Records the outcome and updates the release status.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/release_brief.md` — must be validated

## Workflow

### Step 1: Locate and Read the Release Brief

Resolve release folder. Read `planning/release_brief.md`. Confirm validation has been run.

### Step 2: Retrieve Meeting Context

Follow `specs/utils/meeting_context.md` — search for transcripts mentioning the release brief, SOW, deliverables, or sign-off.

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
- This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
- Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context

### Step 3: Present for Review

Output the full release brief content, prefaced with any meeting context.

Then use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the release brief review?",
    "header": "Release Brief Review",
    "options": [
      {"label": "Signed off — proceed to sprint planning", "description": "Client has approved the brief and authorised the team to begin"},
      {"label": "Approved with minor changes", "description": "Small wording corrections or clarifications needed — direction is confirmed"},
      {"label": "Scope change requested", "description": "Client wants to change deliverables, timeline, or budget — requires rework"},
      {"label": "On hold", "description": "Client needs more time or has internal approvals to complete before signing off"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect Sign-off Details

Ask:
```
Record the sign-off details (approver name, date, any conditions or notes):
```

### Step 5: Update the Release Brief

Populate Section 12 (Sign-off) with the approver name and date. If minor changes were requested, apply them. Append a `## Review Record` section.

### Step 6: Update Release Status

```yaml
release_brief:
  review: "complete"   # or "pending_rework" / "on_hold"
```

### Step 7: Output Review Summary

```
## Release Brief Review Complete

**Outcome**: [Signed off / Changes requested / On hold]
**Signed by**: [approver name and role]

### Next Steps

[If signed off]:
Generate the sprint plan:
/wire:sprint-plan-generate [folder]

[If scope change]:
Update problem definition and pitch, then regenerate the release brief.

[If on hold]:
Follow up with client. Check back when approvals are complete.
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Output Files

- Updated `.wire/releases/[folder]/planning/release_brief.md`
- Updated `.wire/releases/[folder]/status.md`
