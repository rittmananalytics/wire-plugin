---
release_id: "{{RELEASE_ID}}"
release_name: "{{RELEASE_NAME}}"
release_type: "discovery"
client_name: "{{CLIENT_NAME}}"
engagement_name: "{{ENGAGEMENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "discovery"
spawned_from: null

# Discovery focus fields (set by release-brief-generate)
primary_analytical_focus: null
goal_hierarchy_captured: false
client_satisfaction: null

jira:
  project_key: null
  structure: subtasks       # subtasks (default — one Task + 3 Sub-tasks per artifact) | single_issue (one Task per artifact, status transitions)
  epic_key: null
  artifacts:
    problem_definition:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    pitch:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    release_brief:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    sprint_plan:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null

artifacts:
  problem_definition:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  pitch:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  release_brief:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  sprint_plan:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  kickoff_deck:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []

notes:
  - "Discovery release created: {{CREATED_DATE}}"

blockers: []
---

# Release Status: {{RELEASE_NAME}}

**Client**: {{CLIENT_NAME}}
**Release ID**: {{RELEASE_ID}}
**Type**: Discovery (Shape Up)
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

## Current Phase: Discovery

## Artifact Status

| Artifact | Generate | Validate | Review | Ready |
|----------|----------|----------|--------|-------|
| problem_definition | ⏸️ | ⏸️ | ⏸️ | ❌ |
| pitch | ⏸️ | ⏸️ | ⏸️ | ❌ |
| release_brief | ⏸️ | ⏸️ | ⏸️ | ❌ |
| sprint_plan | ⏸️ | ⏸️ | ⏸️ | ❌ |
| kickoff_deck | ⏸️ | ⏸️ | ⏸️ | ❌ |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Not Started | ⚠️ Blocked

## Discovery Workflow

```
Problem Definition → Pitch → Release Brief → Sprint Plan → Spawn delivery releases
```

## Next Action

Generate problem definition:
```
/wire:problem-definition-generate {{RELEASE_ID}}_{{RELEASE_NAME}}
```

## Downstream Releases

[Populated by /wire:release:spawn after sprint plan is approved]

## Notes

[Add release-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
