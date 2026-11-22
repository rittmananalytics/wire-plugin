---
wire_schema: "1.0"
command: review
artifact: dbtcharts
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: dbtcharts
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
  - utils/meeting_context
  - utils/atlassian_search
  - utils/docstore_fetch
  - utils/jira_sync
  - utils/docstore_sync
description: Review the dbt Charts boards with stakeholders — rendered boards and the generation report presented, external context gathered, approval or change requests recorded
argument-hint: <release-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# dbtcharts Review Command

## Purpose

Present the boards for stakeholder sign-off and record the outcome. A review is never run without a person's decision (`specs/utils/director_operating_model.md`, "Review as a ruling").

## Usage

```bash
/wire:dbtcharts-review 01-dbt-foundation
```

## Prerequisites

- `dbtcharts.validate == pass` (enforced by the precondition gate)

## Workflow

### Step 1: Verify Prerequisites

Read `status.md`. If `dbtcharts.validate` is not `pass`, the gate has already stopped the command; if the verdict was PASS WITH WARNINGS, list the warnings first so the reviewer sees them before the boards.

### Step 2: Present for Review

```
## dbt Charts Review Session

**Project:**   [PROJECT_NAME]
**Boards:**    N under <charts_dir>
**Renders:**   dev/dbtcharts/<board>.png (one per board), or "not rendered (<reason>)"
**Report:**    dev/dbtcharts_generation_report.md

| Board | Subject area | Charts | Renamed | Dropped | Added | needs_human decided |
|---|---|---|---|---|---|---|
```

Show each render, or where renders were not produced, offer `dct serve` from the dbt project directory and give the URL it prints. Walk the reviewer through the curation table: what the scaffold proposed and what changed, board by board. The things worth their attention are the ones a script could not decide: the measure and date each fact was charted by, the charts that were dropped, and the `needs_human` items sent back to the dbt work.

### Step 2.5: Retrieve External Context (Optional)

1. Follow `specs/utils/meeting_context.md` with artifact name `dbtcharts`: decisions in recorded meetings about which numbers the client wants to see and how.
2. Follow `specs/utils/atlassian_search.md` with artifact name `dbtcharts`.
3. If a document store is configured, follow `specs/utils/docstore_fetch.md` for reviewer comments on the generation report.
4. If none is available, go to Step 3.

### Step 3: Gather Feedback

Use AskUserQuestion:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "The boards are complete and approved"},
      {"label": "Changes requested", "description": "The boards need revisions"},
      {"label": "Needs discussion", "description": "Requires clarification"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If Approved

Ask who approved (name and role). Update status:

```yaml
dbtcharts:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "[Reviewer]"
  reviewed_date: "{{TODAY}}"
```

```

On Claude Code the same approval can be recorded with no model turn: `/wire-approve <artifact> --final [--as internal|client] [--evidence <url>]` (the Wire mod, wire#270) sets `review: approved`, `reviewed_by` and `reviewed_date` as this step does and appends the approval to the artifact's `review_events` list, which this command does not write. Without `--final` it records the event alone and leaves the review state to this command.

## dbt Charts boards approved

**Reviewed by:** [Reviewer]

### Next Steps
1. Commit the boards and dbt_charts.yml on the release branch with the dbt models (/wire:utils-commit <release>)
2. `dct init ci` in the dbt project adds the GitHub Actions workflow that runs dct validate on every PR
3. To publish, `dct skills cloud-setup` walks the dbtcharts.com connection; record the published URL in status.md under dbtcharts.published_url
```

### Step 4b: If Changes Requested

Record each change as a numbered item with the board and chart it applies to, and who asked for it. Update status:

```yaml
dbtcharts:
  review: changes_requested
  review_feedback:
    - "[Change 1]"
  reviewed_by: "[Reviewer]"
  reviewed_date: "{{TODAY}}"
```

```
## dbt Charts boards: changes requested

### Change requests
1. [board / chart]: [change] (asked by [who])

### Next Steps
1. Apply the changes: curation edits go straight into the board YAML; a change to what a model exposes goes back to /wire:dbt-generate <release>
2. /wire:dbtcharts-validate <release>
3. /wire:dbtcharts-review <release>
```

Boards are edited, never regenerated, to apply a change request: `--force` rewrites the scaffold and loses the curation.

### Step 5: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` with artifact `dbtcharts`, action `review`, and the outcome.

### Step 6: Sync to Document Store (Optional)

If a document store is configured, follow `specs/utils/docstore_sync.md` with `artifact_id: dbtcharts`, `artifact_name: dbt Charts boards`, `file_path: .wire/releases/[release_folder]/dev/dbtcharts_generation_report.md`.

## Output

The status update, the approval or change list, and:

```
Ran: /wire:dbtcharts-review <release>
```
