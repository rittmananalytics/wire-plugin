---
wire_schema: "1.0"
command: review
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
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review pitch with stakeholders and record the appetite decision

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Pitch Review Command

## Purpose

Facilitates the pitch review with decision-makers. This is the "betting table" moment — the key stakeholders decide whether to bet the team's time (the appetite) on this shaped solution. Records the outcome: approved, approved with conditions, or rejected with reasons.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/pitch.md` — must be validated

## Workflow

### Step 1: Locate and Read the Pitch

Resolve release folder. Read `planning/pitch.md`. Check status.md to confirm validation has been run.

### Step 2: Retrieve Meeting Context

Follow `specs/utils/meeting_context.md`:
- Search for transcripts mentioning the client, the release name, or pitch-related terms ("appetite", "bet", "scope")
- Surface any prior stakeholder concerns or decisions about scope (2–3 bullet points maximum)

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
- This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
- Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context

### Step 3: Present the Pitch for Review

Output the full pitch content, prefaced with any meeting context.

Then output:
```
## Pitch Review — Betting Table

This is the decision point. Reviewing stakeholders decide whether to bet [appetite] on this shaped solution.

Key questions for reviewers:
1. Is the problem worth solving now?
2. Is the proposed solution directionally right (even if details will change)?
3. Is [appetite] the right time budget for this?
4. Are the no-gos and rabbit holes correctly identified?
```

### Step 4: Record the Appetite Decision

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the pitch review?",
    "header": "Pitch Review — Betting Table",
    "options": [
      {"label": "Approved — bet confirmed", "description": "We're committing the appetite to this shaped solution"},
      {"label": "Approved — appetite adjusted", "description": "The solution is right but the time budget needs to change"},
      {"label": "Approved — scope adjusted", "description": "The appetite is right but the solution scope needs narrowing"},
      {"label": "Needs reshaping", "description": "Directionally interesting but the solution needs more work before we bet"},
      {"label": "Rejected", "description": "Not the right problem or not the right time — record reasons"}
    ],
    "multiSelect": false
  }]
}
```

### Step 5: Collect Decision Details

Ask directly in chat:
```
Record the key decisions and reasoning from this review:
(e.g. "Approved. Narrowed to dashboard only, pipeline out of scope for this release. Start date: 15 April.")
```

### Step 6: Update the Pitch (if appetite or scope adjusted)

If appetite was adjusted, update Section 2 of pitch.md with the confirmed appetite.
If scope was adjusted, update Sections 5 (No-gos) and 8 (Downstream Releases) as appropriate.

Append a `## Review Record` section to pitch.md:
```markdown
## Review Record

**Date**: [today's date]
**Outcome**: [Approved / Adjusted / Needs reshaping / Rejected]
**Confirmed appetite**: [Small batch 1–2 weeks / Big batch 6 weeks]
**Key decisions**: [Summary of reviewer decisions]
**Conditions**: [Any conditions on the approval, if applicable]
```

### Step 7: Update Release Status

```yaml
pitch:
  review: "complete"   # or "pending_rework" / "rejected"
```

### Step 8: Output Review Summary

```
## Pitch Review Complete

**Outcome**: [outcome]
**Confirmed appetite**: [appetite]

### Next Steps

[If approved]:
Formalise as a release brief:
/wire:release-brief-generate [folder]

[If needs reshaping]:
Update the pitch and re-validate:
/wire:pitch-generate [folder]  (to regenerate with new inputs)
/wire:pitch-validate [folder]
/wire:pitch-review [folder]

[If rejected]:
Record the rejection reasons in the problem definition and consider whether to:
- Reframe the problem
- Revisit at a later date
- Close this discovery release
```

### Step 9: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Output Files

- Updated `.wire/releases/[folder]/planning/pitch.md` (review record appended)
- Updated `.wire/releases/[folder]/status.md`
