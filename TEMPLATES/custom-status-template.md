---
project_id: "{{PROJECT_ID}}"
project_name: "{{PROJECT_NAME}}"
project_type: "custom"
client_name: "{{CLIENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "active"
custom_commands_path: ".wire/releases/{{RELEASE_FOLDER}}/custom-commands"

jira:
  project_key: null
  structure: subtasks       # subtasks (default — one Task + 3 Sub-tasks per artifact) | single_issue (one Task per artifact, status transitions)
  epic_key: null
  artifacts: {}

docstore:
  provider: null
  confluence:
    cloud_id: null
    space_key: null
    parent_page_id: null
    artifacts: {}
  notion:
    parent_page_id: null
    artifacts: {}

# Custom artifact entries are added here by /wire:custom-release-define
# Each entry follows this schema:
#
# [artifact-key]:
#   custom: true
#   source_document: ""       # which SoW/plan doc this deliverable came from
#   generate: not_started     # not_started | complete | fail
#   validate: not_started     # not_started | complete | fail
#   review: not_started       # not_started | approved | changes_requested | blocked
#   file: null                # path to the generated artifact file
#   generated_date: null
#   generated_files: []
#   revision_history: []
artifacts: {}

notes:
  - "Custom release created: {{CREATED_DATE}}"
  - "Source documents: {{SOURCE_DOCUMENTS}}"

blockers: []

# Release budget — what an agent may spend on this release
# (specs/utils/director_operating_model.md, "Budget"). Absent/null means the
# defaults: lanes_max 4, no warehouse restriction, stop at decisions. The release
# director sets it in prose ("two lanes, nothing against a warehouse, stop at
# decisions") and the orchestrating session writes the block. /wire:upgrade never
# writes one: an absent block means no budget was set, not a budget of defaults.
budget: null
#   lanes_max: 2                 # concurrent lanes; default 4
#   model_tier: default          # default | economy
#   warehouse_spend: none        # none | estimate_required | cap:<amount>
#   stop_at: decisions           # decisions | phase_end | never
#   set_by: "..."
#   set_at: "YYYY-MM-DD"

# Decisions waiting on the release director. Replaces the single agents.paused_at
# value below: a release can be waiting on more than one thing at once. Each
# entry carries id, artifact, kind (review | ruling | registry_proposal | budget |
# safety_gate), question, parked_at, and optionally awaiting. The first line of
# every orchestrated session is the count of these and their questions.
parked_decisions: []

agents:
  mode: null              # null | local | managed | orchestrated
  # The release claim. Written by whatever is going to dispatch (the orchestrating
  # session, or /wire:delegate), never by /wire:new or /wire:upgrade. A second
  # session that reads a live claim offers join / take-over / move instead of
  # dispatching. See specs/utils/director_operating_model.md, "The release claim".
  coordinator_session: null
  #   user: "Jane Smith"
  #   session_id: "<claude session id>"
  #   branch: "feat/03-store-dashboards"
  #   claimed_at: "YYYY-MM-DD HH:MM"
  #   last_write: "YYYY-MM-DD HH:MM"    # the 30-minute stall rule reads this
  last_orchestrated: null
  paused_at: null         # superseded by parked_decisions; kept so older readers still resolve
  active_sessions: []
  completed_sessions: []
---

# Project Status: {{PROJECT_NAME}}

**Client**: {{CLIENT_NAME}}
**Project ID**: {{PROJECT_ID}}
**Type**: Custom (project-scoped)
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

## Current Phase: Active

## Next Action

Run the first custom generate command:

```
/[first-artifact-name]-generate {{RELEASE_FOLDER}}
```

Or view all available commands for this release:

```
ls .wire/releases/{{RELEASE_FOLDER}}/custom-commands/
```

## Artifact Status Summary

| Deliverable | Source Doc | Generate | Validate | Review | Ready |
|-------------|-----------|----------|----------|--------|-------|
<!-- Rows added by /wire:custom-release-define -->

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Failed | ⏸️ Not Started | ⚠️ Blocked

## Iterations

Ticket-sized work done inside this release through `/wire:work` (`specs/work.md`). One row per iteration, updated in place; the detail is in `iterations/<ticket>.md`.

| Ticket | Title | Branch | PR | State | Opened | Closed |
|--------|-------|--------|----|-------|--------|--------|

## Notes

[Project-specific notes here]

## Blockers

[Blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
