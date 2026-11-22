---
wire_schema: "1.0"
command: review
artifact: mockups
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: mockups
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Record stakeholder review feedback on mockups
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# mockups Review Command

## Purpose

Record stakeholder feedback on the mockups. Captures approval or change requests.

## Usage

```bash
/wire:mockups-review YYYYMMDD_project_name
```

## Prerequisites

- mockups must exist
- `mockups.generate` should be `complete` (mockups is a generate+review artifact — there is no validate step)

## Workflow

### Step 1: Verify Prerequisites

**Process**:
1. Read `status.md`
2. Check that `mockups.generate == complete`

**If generate not complete**:
```
Warning: mockups has not been generated yet.

Run `/wire:mockups-generate <project>` before review.

Proceed anyway? (y/n)
```

### Step 2: Present for Review

**Output**:
```
## mockups Review Session

**Project:** [PROJECT_NAME]
**Files:** [List files being reviewed]

Please review the mockups and provide feedback.
```

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `mockups`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `mockups`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context
4. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Gather Feedback

**Use AskUserQuestion**:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "mockups is complete and approved"},
      {"label": "Changes requested", "description": "mockups needs revisions"},
      {"label": "Needs discussion", "description": "Requires clarification"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If Approved

**Ask for reviewer**:
```
Who approved the mockups? (Name and role)
```

**Update status**:
```yaml
mockups:
  generate: complete
  review: approved
  reviewed_by: "[Reviewer]"
  reviewed_date: 2026-02-13
```

On Claude Code the same approval can be recorded with no model turn: `/wire-approve <artifact> --final [--as internal|client] [--evidence <url>]` (the Wire mod, wire#270) sets `review: approved`, `reviewed_by` and `reviewed_date` as this step does and appends the approval to the artifact's `review_events` list, which this command does not write. Without `--final` it records the event alone and leaves the review state to this command.

### Step 4a.1: On a `dashboard_first` release, generate the visualization catalog

Read `project_type` from `status.md`. If it is **`dashboard_first`** or
**`dashboard_extension`**, run the `/wire:viz_catalog-generate` workflow in full now, exactly as
if the consultant had typed it, and fold its result into the output below.

**Why this is automatic rather than a suggested next step.** `viz_catalog-generate` is
generate-only: no validate, no review, and no human decision inside it. Its entire input is the
two files `mockups-generate` Step 4A already wrote (`design/dashboard_visualization_catalog.csv`
and `design/dashboard_spec.md`), and its output, `design/visualization_catalog.md`, is a
restructuring of them plus a coverage check against the requirements. Its only precondition is
this approval. There is nothing for a person to decide between the two steps.

Left as a manual step it was reliably skipped, because a command that reads files you already
have and writes a third one with a near-identical name reads as duplication. On one engagement
`viz_catalog-generate` ran zero times across four `dashboard_first` releases, which left
`seed_data-generate` without the input it uses to guarantee every catalog measure returns a
non-zero value. Chaining it here removes the opportunity to skip it, on the same principle as
`specs/utils/auto_validate.md`.

**If it fails**, record the failure in the output and continue. Do not roll back the approval:
the mockup is approved either way, and the catalog can be regenerated on its own. Report it as:

```
⚠️  Visualization catalog not generated: [reason]
    Run it before seed data: /wire:viz_catalog-generate [release_folder]
```

**Suggest next steps**:
```
## mockups Approved ✅

**Reviewed by:** [Reviewer]

**Visualization catalog:** design/visualization_catalog.md ([N] visualizations)
[or the warning above, if it failed]

### Next Steps

[Next artifact or phase]
```

### Step 4b: If Changes Requested

**Ask for feedback**:
```
What changes are needed?
```

**Update status**:
```yaml
mockups:
  generate: complete
  review: changes_requested
  feedback: "[Feedback]"
  reviewed_date: 2026-02-13
```

**Suggest iteration**:
```
## mockups Changes Requested 🔄

### Change Requests:
[Feedback]

### Next Steps

1. Address feedback
2. Re-generate: `/wire:mockups-generate <project>`
3. Re-submit for review
```

### Step 5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `mockups`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

### Step 6: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

## Output

This command:
- Records review feedback in `status.md`
- Updates review status
- Suggests next steps
