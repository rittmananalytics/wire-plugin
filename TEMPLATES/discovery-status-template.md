---
release_id: "{{RELEASE_ID}}"
release_name: "{{RELEASE_NAME}}"
release_type: "discovery"
project_type: "discovery_shape_up"   # the release-type YAML this release resolves against
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

[Populated by /wire:release-spawn after sprint plan is approved]

## Notes

[Add release-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
