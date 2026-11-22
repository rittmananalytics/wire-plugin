---
wire_schema: "1.0"
command: review
artifact: problem_definition
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
  - artifact: problem_definition
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review problem definition with stakeholders and record outcome

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Problem Definition Review Command

## Purpose

Facilitates stakeholder review of the problem definition document. Retrieves relevant meeting context, presents the document for review, records feedback and the review decision, and updates the release status.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/problem_definition.md` (or legacy path)

## Workflow

### Step 1: Locate the Problem Definition

Resolve release folder from `$ARGUMENTS`. Read `planning/problem_definition.md`. If not found, prompt the user to generate it first.

### Step 2: Check for Meeting Context

Follow the workflow in `specs/utils/meeting_context.md`:
- Search for recent Fathom meeting transcripts mentioning the release or client name
- Specifically look for references to: problem definition, business problem, current state, constraints
- Summarise any relevant meeting decisions or concerns (2–3 bullet points maximum)

If no meeting context is found, proceed without it.

If a document store is configured, follow `specs/utils/docstore_fetch.md`:
- Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
- This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
- Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context

### Step 3: Present for Review

Output the full problem definition document content for review, prefaced with any meeting context found.

Then ask using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "What is the outcome of the problem definition review?",
    "header": "Problem Definition Review",
    "options": [
      {"label": "Approved — proceed to pitch", "description": "The problem is well-defined and we're ready to shape a solution"},
      {"label": "Approved with minor edits", "description": "Some small corrections needed, but the direction is right"},
      {"label": "Needs rework", "description": "The problem framing needs significant changes before we can shape a solution"},
      {"label": "Problem scope changed", "description": "The client has clarified or changed the problem significantly"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4: Collect Feedback

Ask directly in chat:
```
Please provide any feedback, corrections, or clarifications to record:
(Type "none" if no additional feedback)
```

Wait for user response.

### Step 5: Apply Minor Edits (if applicable)

If "Approved with minor edits" was selected and the user provided specific text corrections, apply them directly to `problem_definition.md`.

If "Needs rework" or "Problem scope changed" was selected, note the feedback in the document under a new `## Review Feedback` section but do not rewrite the document — that requires a new generate cycle.

### Step 6: Update Release Status

```yaml
problem_definition:
  review: "complete"   # or "pending_rework" if rework needed
```

If rework is needed, also set:
```yaml
problem_definition:
  generate: "not_started"   # reset to trigger a new generate cycle
```

### Step 7: Output Review Summary

```
## Problem Definition Review Complete

**Outcome**: [Approved / Approved with edits / Needs rework / Scope changed]
**Reviewer feedback recorded**: [yes/no]

### Next Steps

[If approved]:
Generate the pitch:
/wire:pitch-generate [folder]

[If rework needed]:
Update the problem definition:
/wire:problem-definition-generate [folder]
Then re-run validation and review.
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Output Files

- Updated `.wire/releases/[folder]/planning/problem_definition.md` (if edits applied)
- Updated `.wire/releases/[folder]/status.md`
