---
wire_schema: "1.0"
command: review
artifact: sprint_plan
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
  - artifact: sprint_plan
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review sprint plan with delivery team and record approval

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Sprint Plan Review Command

## Purpose

Facilitates the sprint plan review with the delivery team. Records the team's confirmation that the plan is achievable, the point estimates are realistic, and the team is ready to begin. Upon approval, the discovery release is complete and the team is ready to spawn delivery releases.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/sprint_plan.md` — must be validated

## Workflow

### Step 1: Locate and Read the Sprint Plan

Resolve release folder. Read `planning/sprint_plan.md`. Confirm validation has been run.

### Step 2: Retrieve Meeting Context

Follow `specs/utils/meeting_context.md` — search for transcripts mentioning sprint planning, capacity, timeline, or team availability.

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
- This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
- Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context

### Step 3: Present for Review

Output the sprint plan summary (epics, total points, velocity assumption, timeline), prefaced with any meeting context.

Then use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the sprint plan review?",
    "header": "Sprint Plan Review",
    "options": [
      {"label": "Approved — ready to spawn delivery releases", "description": "The plan is achievable, estimates are realistic, team is ready to go"},
      {"label": "Approved with point adjustments", "description": "Some estimates need updating but the structure is right"},
      {"label": "Sprint structure needs change", "description": "Sprint boundaries or sequencing need to be reworked"},
      {"label": "Scope needs trimming", "description": "Too much work for the appetite — scope must be reduced"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect Feedback and Apply Adjustments

If adjustments were requested, ask for specific changes and apply them to the sprint plan.

### Step 5: Record Review Outcome

Append to `planning/sprint_plan.md`:

```markdown
## Review Record

**Date**: [today's date]
**Outcome**: [Approved / Adjusted / Rework needed]
**Reviewed by**: [team member names]
**Notes**: [key decisions from the review]
**Ready to spawn**: [Yes / No — pending adjustments]
```

### Step 6: Update Release Status

```yaml
sprint_plan:
  review: "complete"
current_phase: "complete"
```

If the entire discovery artifact chain is done:
```yaml
notes:
  - "Discovery complete [date] — ready to spawn delivery releases with /wire:release-spawn"
```

### Step 7: Output Review Summary

```
## Sprint Plan Review Complete ✅

**Outcome**: [outcome]
**Discovery release**: Complete

### The discovery release is now complete.

All four artifacts are approved:
✅ Problem Definition
✅ Pitch
✅ Release Brief
✅ Sprint Plan

### Next Step: Spawn delivery releases

Run the following command to create the delivery release folder structure:
/wire:release-spawn [folder]

This will create:
[list of downstream releases from sprint plan]
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Output Files

- Updated `.wire/releases/[folder]/planning/sprint_plan.md`
- Updated `.wire/releases/[folder]/status.md`
