---
release_id: "{{RELEASE_ID}}"
release_name: "{{RELEASE_NAME}}"
release_type: "sop_discovery"
client_name: "{{CLIENT_NAME}}"
engagement_name: "{{ENGAGEMENT_NAME}}"
created_date: "{{CREATED_DATE}}"
last_updated: "{{LAST_UPDATED}}"
current_phase: "discovery"
spawned_from: null

# SOP Discovery focus fields (set as the engagement progresses)
in_scope_domains: []
out_of_scope: []
target_playback_date: null
go_no_go_decision: null   # set after the playback: "go" | "no_go" | "conditional"

jira:
  project_key: null
  structure: subtasks       # subtasks (default — one Task + 3 Sub-tasks per artifact) | single_issue (one Task per artifact, status transitions)
  epic_key: null
  artifacts:
    engagement_brief:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    stakeholder_map:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    stakeholder_interview:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    requirements_matrix:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    discovery_analyses:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    findings_playback:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null
    delivery_roadmap:
      task_key: null
      generate_key: null
      validate_key: null
      review_key: null

linear:
  project_id: null
  artifacts:
    engagement_brief: { issue_id: null, generate_id: null, validate_id: null, review_id: null }
    stakeholder_map: { issue_id: null, generate_id: null, validate_id: null, review_id: null }
    stakeholder_interview: { issue_id: null, generate_id: null, validate_id: null, review_id: null }
    requirements_matrix: { issue_id: null, generate_id: null, validate_id: null, review_id: null }
    discovery_analyses: { issue_id: null, generate_id: null, validate_id: null, review_id: null }
    findings_playback: { issue_id: null, generate_id: null, validate_id: null, review_id: null }
    delivery_roadmap: { issue_id: null, generate_id: null, validate_id: null, review_id: null }

artifacts:
  engagement_brief:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  stakeholder_map:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  stakeholder_interview:
    # Aggregate state across all per-stakeholder interview write-ups.
    # Individual interviews are tracked in the `interviews:` array below.
    generate: not_started     # = at least one interview generated
    validate: not_started     # = every generated interview passes four-tag validation
    review: not_started       # = every generated interview has internal RA review complete
    revision_history: []
  requirements_matrix:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  discovery_analyses:
    generate: not_started
    validate: not_started
    review: not_started
    file: null
    generated_date: null
    generated_files: []
    revision_history: []
  findings_playback:
    generate: not_started
    validate: not_started
    review: not_started        # = playback meeting held AND all 7 Sponsor Validation Checklist items recorded
    file: null
    deck_html_path: null
    generated_date: null
    generated_files: []
    revision_history: []
  delivery_roadmap:
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

# Per-stakeholder interview tracker. One entry per interview write-up.
# Populated by /wire:stakeholder-interview-generate; reconciled against
# the stakeholder map by /wire:stakeholder-interview-validate.
interviews: []
# Example entry shape:
#   - slug: maud-bakker
#     stakeholder_name: "Maud Bakker"
#     title: "Head of Retail"
#     priority: P0
#     interviewer: "Mark Rittman"
#     interview_date: null
#     file: "planning/interviews/maud-bakker.md"
#     fathom_url: null
#     generate: complete
#     validate: complete    # all four tags applied to every theme
#     review: complete      # peer/HoD review done
#     themes_tagged: 12     # populated by validate

# Captured at the close of the playback. The release is not "approved"
# until every item is `true` and `playback_held` is `true`.
sponsor_validation:
  playback_held: false
  playback_date: null
  playback_fathom_url: null
  maturity_pin: null                       # e.g. "Data Chaos"
  vision_statement_excerpt: null
  preferred_delivery_option: null          # "build" | "pair" | "coach" | null
  checklist:
    maturity_pin_agreed: false
    hierarchy_diagnosis_agreed: false
    ppt_diagnosis_agreed: false
    vision_statement_endorsed: false
    solution_initiatives_confirmed: false
    delivery_option_named: false
    conflicts_resolved: false
  follow_up_session: null                  # date if any items remain false after the playback

notes:
  - "SOP Discovery release created: {{CREATED_DATE}}"

blockers: []
---

# Release Status: {{RELEASE_NAME}}

**Client**: {{CLIENT_NAME}}
**Release ID**: {{RELEASE_ID}}
**Type**: Discovery (SOP / Canonical)
**Created**: {{CREATED_DATE}}
**Last Updated**: {{LAST_UPDATED}}

## Current Phase: Discovery

## Artifact Status

| Artifact | Generate | Validate | Review | Ready |
|----------|----------|----------|--------|-------|
| engagement_brief | ⏸️ | ⏸️ | ⏸️ | ❌ |
| stakeholder_map | ⏸️ | ⏸️ | ⏸️ | ❌ |
| stakeholder_interview (aggregate) | ⏸️ | ⏸️ | ⏸️ | ❌ |
| requirements_matrix | ⏸️ | ⏸️ | ⏸️ | ❌ |
| discovery_analyses | ⏸️ | ⏸️ | ⏸️ | ❌ |
| findings_playback | ⏸️ | ⏸️ | ⏸️ | ❌ |
| delivery_roadmap | ⏸️ | ⏸️ | ⏸️ | ❌ |
| kickoff_deck | ⏸️ | ⏸️ | ⏸️ | ❌ |

**Legend**: ✅ Complete | 🔄 In Progress | ❌ Not Started | ⚠️ Blocked

## SOP Discovery Workflow

```
Engagement Brief → Stakeholder Map → Kick-off → Stakeholder Interviews (×N)
   → Requirements Matrix → Discovery Analyses (Hierarchy / PPT / Maturity)
   → Findings Playback Deck → Sponsor Playback (the gate)
   → Delivery Roadmap → Spawn Release 1 (or close as no-go)
```

The Findings Playback meeting is the canonical client-facing review gate. The release is not `approved` until every item in `sponsor_validation.checklist` is `true` and `sponsor_validation.playback_held` is `true`.

## Next Action

Draft the engagement brief from the signed SoW and deal record:
```
/wire:engagement-brief-generate {{RELEASE_ID}}_{{RELEASE_NAME}}
```

## Stakeholder Interviews

(Populated as `/wire:stakeholder-interview-generate` is run for each P0/P1 stakeholder. See `interviews:` in the frontmatter for the full record.)

## Sponsor Validation Checklist

(Populated at the playback. See `sponsor_validation:` in the frontmatter.)

- [ ] Maturity Curve pin agreed
- [ ] Hierarchy of Needs diagnosis agreed
- [ ] PPT diagnosis agreed
- [ ] Vision Statement endorsed (both paragraphs)
- [ ] Solution Initiatives confirmed
- [ ] Preferred Delivery Option named
- [ ] Open conflicts resolved (or follow-up scheduled)

## Downstream Releases

[Populated by `/wire:release-spawn` after the playback and roadmap are approved.]

## Notes

[Add release-specific notes here]

## Blockers

[Add any blockers here]

## Session History

| Date | Objective | Accomplished | Next Focus |
|------|-----------|--------------|------------|
