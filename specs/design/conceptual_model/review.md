---
wire_schema: "1.0"
command: review
artifact: conceptual_model
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: conceptual_model
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review conceptual model with business stakeholders
argument-hint: <project-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Conceptual Model Review Command

## Purpose

Present the conceptual entity model to business stakeholders for approval. This is a **business-level review, not a technical review**. The goal is to confirm:
- The right entities are included and named in the client's own terminology
- No important entities are missing
- Relationships correctly reflect how the business works
- The model aligns with the SOW scope

**Review audience**: Business stakeholders, client subject matter experts, and the project sponsor — not solely the technical team. The pipeline architecture, data model specification, and all dbt code that follow will be constrained by what is approved here. Getting this right now prevents expensive rework later.

## Usage

```bash
/wire:conceptual_model-review YYYYMMDD_project_name
```

## Prerequisites

- `conceptual_model`: `validate: pass`

## Workflow

### Step 1: Verify Prerequisites

Check `conceptual_model.validate == pass` in `status.md`.

If validation has not passed:
```
Error: Conceptual model must pass validation before stakeholder review.
Run: /wire:conceptual_model-validate <project_id>
```

If there are unresolved Open Questions (Section 5 of conceptual_model.md is non-empty), flag this to the consultant:
```
Warning: [N] open questions remain in the conceptual model (Section 5).
These should be resolved in the review session or in a workshop before approval.
```

### Step 2: Present the Conceptual Model

Display `design/conceptual_model.md` in full, including:
- Entity inventory (Section 1)
- erDiagram (Section 2)
- Relationship narrative (Section 3)
- Out-of-scope entities (Section 4)
- **Open questions (Section 5) — highlight prominently**

Suggest the consultant shares this document with stakeholders directly (e.g. in a screen-share, printed, or via a shared link) rather than reading it aloud.

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `conceptual_model`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `conceptual_model`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context
4. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Gather Feedback

Use AskUserQuestion to collect the review outcome:

**Question**: "Has the conceptual model been reviewed with business stakeholders? What is the outcome?"

**Options**:
1. **Approved** — All entities and relationships are correct and complete. No open questions remain. Proceed to pipeline design and data model specification.
2. **Changes requested** — Entities or relationships need updating. Capture the specific changes needed.
3. **Needs discussion** — Further clarification required before approval (open questions unresolved, or significant disagreement on scope).

If "Changes requested": prompt "Please describe the required changes (which entities to add/remove/rename, which relationships to correct):" and capture as notes.

If "Needs discussion": suggest running a workshop.
```
Suggested next step: generate workshop materials to facilitate the discussion.
/wire:workshops-generate <project_id>
```

### Step 4: Update Status

**If approved**:
```yaml
conceptual_model:
  review: approved
  reviewed_by: [name and/or role of approver]
  reviewed_date: [today]
```
Add to status notes: `"Conceptual model approved [date] by [reviewer] — [entity count] entities, [relationship count] relationships confirmed"`

**If changes requested**:
```yaml
conceptual_model:
  review: changes_requested
  reviewed_date: [today]
```
Add to status notes: `"Conceptual model: changes requested [date] — [one-line summary of changes needed]"`

**If needs discussion**:
```yaml
conceptual_model:
  review: pending
```
Add to status blockers: `"Conceptual model review pending — open questions require workshop resolution"`

### Step 5: Suggest Next Steps

**If approved**:
```
## Conceptual Model Approved ✅

The entity model is confirmed by business stakeholders. Downstream design
artifacts are now unblocked.

### Next Steps (can be run in parallel or either order)

Design the data pipeline architecture:
  /wire:pipeline_design-generate <project_id>

Begin the data model specification (dbt layers):
  /wire:data_model-generate <project_id>

Both commands will read the approved conceptual model as a primary input.
```

**If changes requested**:
```
## Changes Required

Update design/conceptual_model.md with the requested changes:
[list changes captured]

Then re-validate and re-review:
  /wire:conceptual_model-validate <project_id>
  /wire:conceptual_model-review <project_id>
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `conceptual_model`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

### Step 7: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Edge Cases

### Stakeholder Not Available for Synchronous Review

If the review must be conducted asynchronously (e.g. by email or shared document):
- Record the date the document was sent and expected response date
- Set status to `pending` with a note
- Add to blockers: `"Conceptual model review pending stakeholder response — sent [date]"`

### Partial Approval (Some Entities Agreed, Others Disputed)

If stakeholders approve some entities but dispute others:
- Do not record as fully approved
- Record as `changes_requested`
- Note specifically which entities/relationships are agreed vs disputed
- Only disputed items need rework — don't regenerate the whole document

### Significant Scope Change Revealed During Review

If the review surfaces a major scope change (e.g. an entirely new domain added, or a core entity removed):
- Record as `changes_requested`
- Note: a significant scope change may also require updating the requirements specification
- Check whether the SOW needs to be amended before proceeding

## Output

- Updates `.wire/<project_id>/status.md` with review outcome, reviewer name, and date
- Notes added to status.md recording the decision and any change requests
