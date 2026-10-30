---
sidebar_position: 15
title: Review profile
---

# Review profile

`.wire/engagement/review_profile.yml` holds a client's review settings: their pull request template, their tracker, the default review mode and where PR drafts are kept. It lives in the client's repo and their team edits it. `/wire:adopt` proposes a first version from the repo. Every field is optional; without the file, Wire's defaults apply. The full schema is in `wire/schemas/review-profile-schema.md`.

```yaml
schema_version: 1
pr_template: .github/pull_request_template.md
tracker:
  kind: jira
  site: example.atlassian.net
  project_key: DATA
review_mode: new_functionality      # or bug_hunt
drafts_folder: .wire/local/pr_drafts/
requirements_table: true
tested_in_dev: when_available       # required | when_available | off
```

| Field | Used for |
|---|---|
| `pr_template` | The PR body keeps the client's headings. Wire adds its sections under them. |
| `tracker` | The ticket link, and the key Wire looks for in branch names. |
| `review_mode` | `new_functionality` leads with the requirements table; `bug_hunt` leads with rule findings and failure paths. |
| `drafts_folder` | Where a PR body is drafted before posting. It must be git-ignored. |
| `requirements_table` | A requirements table per ticket in the PR body. |
| `tested_in_dev` | Whether `/wire:work` runs `/wire:utils-dev-test-evidence` before publishing. |
| `review_lens` | A client checklist the dbt migration review lens runs over a diff. |

An engagement that already has `.wire/engagement/client_review_profile.yaml` keeps working: Wire reads the new file first and falls back to the old one.

## Review rules

Wherever Wire writes or reviews a PR body:

1. **Rule findings never block.** Each finding from the convention lint on the changed files is `fixed`, `justified` (with a reason) or `acknowledged`. A finding with none is listed as `open`.
2. **A requirements table per ticket.** Each requirement is `met`, `not met` or `can't tell`, with evidence. `met` without evidence counts as `can't tell`.
3. **A deviation is a question.** A requirement that is not met is raised as a question to the ticket owner. Wire does not decide that a deviation is acceptable.

`wire/scripts/review_rules.py` writes both tables from the findings and the requirements:

```markdown
| Rule | Where | Disposition | Reason |
|---|---|---|---|
| AF-005 | `dags/orders_load.py`:14 | fixed | cap read from config |
| AF-104 | `dags/returns_load.py`:30 | acknowledged | |

| Id | Requirement | Status | Evidence |
|---|---|---|---|
| R1 | Load returns daily by 06:00 | met | run finished 05:12 |
| R3 | Alert the data channel on failure | not met | no callback set |
```
