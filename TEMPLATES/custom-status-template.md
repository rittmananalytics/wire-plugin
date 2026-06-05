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

## Notes

[Project-specific notes here]

## Blockers

[Blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
