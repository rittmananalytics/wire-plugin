---
wire_schema: "1.0"
command: review
artifact: data_app
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: app
      description: "--app <slug>. Review one app (default: every app in status.md)"
preconditions:
  - artifact: data_app
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Record stakeholder review of a Looker Data App against the approved mockup, on the local preview or the published dashboard"
argument-hint: <release-folder> [--app <slug>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# data_app Review Command

**Experimental.** See `data_app-generate` for the marker and what it means.

## Purpose

Record stakeholder feedback on the app: approval or change requests. The reviewer looks at the running app, on the local preview (the sandbox mode, which is how a published tile runs it) or, after `/wire:data_app-publish`, on the Looker instance. Approval here is business acceptance of the app against the mockup. It does not publish anything: publishing is its own confirmed step.

## Usage

```bash
/wire:data_app-review 20260115_acme_dashboards
```

## Prerequisites

- `data_app.validate == pass`

## Workflow

### Step 1: Verify prerequisites

Read `status.md`. If `data_app.validate` is not `pass`:

```
Warning: data_app has not passed validation yet.

Run `/wire:data_app-validate <project>` before review.

Proceed anyway? (y/n)
```

### Step 2: Present for review

For each app, give the reviewer what to open and what to compare it with:

```
## Data App Review Session (experimental)

**Project:**   [PROJECT_NAME]
**App:**       <slug>  ·  <N> widgets from <N> catalog rows
**Mockup:**    design/mockups/<page>.html
**Preview:**   http://localhost:8765/preview-server/?app=apps/<slug>/app.js&sandbox=true
               (start it from the toolkit root: python3 skills/data-app-previewer/tools/start-preview.py apps/<slug>/app.js)
**Published:** <instance>/dashboards/<looker_dashboard_id>   [or "not published yet"]
**Record:**    dev/data_app/<slug>/data_app.md  ·  validation.md

Known limits of a Data App (Looker preview): no embedding, no PDF, no scheduled delivery, no LookML export; the dashboard must not be copied in Looker.
```

Walk the reviewer through the mockup cross-check in `data_app.md` and any `justified` or `acknowledged` warnings, so a deliberate difference from the mockup is approved as such.

### Step 2.5: Retrieve external context (Optional)

1. Follow `specs/utils/meeting_context.md` with artifact name `data_app`.
2. Follow `specs/utils/atlassian_search.md` with artifact name `data_app`.
3. If a document store is configured, follow `specs/utils/docstore_fetch.md` for `data_app` and surface the "Document Store Context" block.
4. If none is available, go to Step 3.

### Step 3: Gather feedback

**Use AskUserQuestion**:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "The app matches the approved mockup and the numbers are right"},
      {"label": "Changes requested", "description": "The app needs revisions"},
      {"label": "Needs discussion", "description": "Requires clarification"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If approved

Ask who approved it (name and role). Update status:

```yaml
artifacts:
  data_app:
    review: approved
    reviewed_by: "[Reviewer]"
    reviewed_date: "{{TODAY}}"
```

```
## Data App Approved ✅

**Reviewed by:** [Reviewer]

### Next Steps

1. Publish to Looker (confirmed step): /wire:data_app-publish <release>
2. [Next artifact or phase]
```

### Step 4b: If changes requested

Ask what changes are needed. Update status:

```yaml
artifacts:
  data_app:
    review: changes_requested
    feedback: "[Feedback]"
    reviewed_date: "{{TODAY}}"
```

```
## Data App Changes Requested 🔄

### Change Requests:
[Feedback]

### Next Steps

1. Address feedback (a change to the mockup goes back through mockups-review first)
2. Re-validate: /wire:data_app-validate <release>
3. Re-submit for review
```

### Step 5: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md`: artifact `data_app`, action `review`, status as written; the reviewer name on approval, the feedback text on changes requested.

### Step 6: Sync to Document Store (Optional)

If a document store is configured and the outcome is Approved, follow `specs/utils/docstore_sync.md` to overwrite the page with `dev/data_app/<slug>/data_app.md`. Otherwise leave the page as it is.

## Output

- Review outcome, reviewer and feedback in `status.md`
- one row in `execution_log.md`
