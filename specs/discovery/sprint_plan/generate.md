---
wire_schema: "1.0"
command: generate
artifact: sprint_plan
domain: discovery
release_types:
  - discovery_shape_up
  - sop_discovery
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate sprint plan with epics, stories, and point estimates from the release brief
workload: planning
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Sprint Plan Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a detailed sprint plan from the signed-off release brief. Breaks deliverables into epics, stories, and tasks with Fibonacci point estimates (1/2/3/5/8 — no 13-point stories allowed). Produces a plan that is specific enough to start work but not so granular it becomes a Gantt chart.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/release_brief.md` — must be signed off
- `.wire/releases/$ARGUMENTS/planning/pitch.md` — for appetite and scope context

## Workflow

### Step 1: Locate Release and Read Brief

Resolve release folder. Read both `planning/release_brief.md` and `planning/pitch.md`. Verify the release brief has been signed off (check status.md `release_brief.review`).

### Step 2: Determine Sprint Structure

Based on the confirmed appetite:
- **Small batch (1–2 weeks)**: single sprint; 1–3 epics; stories at a fine-grained level
- **Big batch (6 weeks)**: 3–6 sprints of roughly 1 week each; group by epic; stories rolled up to a level appropriate for planning

Ask:
```
What is the sprint length for this release?
(e.g. 1 week, 2 weeks — or just confirm: "1 sprint total" for small batch)
```

### Step 3: Generate Epic and Story Breakdown

For each deliverable in the release brief, generate epics. For each epic, generate stories. For each story, generate tasks and point estimates.

**Point scale** (modified Fibonacci):
- **1 point**: < 2 hours — trivial, no unknowns
- **2 points**: 2–4 hours — straightforward, well-understood
- **3 points**: 4–8 hours — some complexity, dependencies clear
- **5 points**: 1–2 days — significant work, some uncertainty
- **8 points**: 2–4 days — complex, significant unknowns

**Rule**: No story may be 13 points. If a story would be 13 points, it must be broken into two or more stories. (A 13-point story is a sign the scope is not well enough understood to plan.)

**Velocity assumption**: A typical consultant day is 5 story points of focused delivery work. Adjust for part-time allocations.

Generate the breakdown interactively — for each deliverable, propose epics and stories and ask for confirmation before proceeding to the next.

### Step 4: Generate Sprint Plan Document

**Output location**: `.wire/releases/$ARGUMENTS/planning/sprint_plan.md`

Apply the reference-legibility convention (`specs/utils/reference_legibility.md`): the sprint plan cites deliverable codes (D1, D2, …) minted in the release brief, so every "Maps to" line pairs the deliverable's plain-language name with its code, and the Reference key section below resolves each cited code to the release brief.

```markdown
# Sprint Plan: [Release Name]

**Engagement**: [client_name]
**Release**: [folder_name]
**Date**: [generation_date]
**Appetite**: [Small batch — 1–2 weeks | Big batch — 6 weeks]
**Total points**: [sum]
**Estimated duration**: [X sprints of Y days]

---

## Point Scale

| Points | Effort | Complexity |
|--------|--------|------------|
| 1 | < 2 hours | Trivial, no unknowns |
| 2 | 2–4 hours | Straightforward |
| 3 | 4–8 hours | Some complexity |
| 5 | 1–2 days | Significant, some uncertainty |
| 8 | 2–4 days | Complex, significant unknowns |

*No story may be estimated at 13 points — break it down further.*

---

## Sprint [N]: [Theme]
**Dates**: [start] → [end]
**Sprint goal**: [What does "done" look like for this sprint?]
**Point target**: [X points]

### Epic 1: [Deliverable name]
*Maps to: [deliverable plain-language name] (Release Brief D[N])*

| Story | Tasks | Points | Owner | Status |
|-------|-------|--------|-------|--------|
| [Story description] | [comma-separated task list] | 3 | [name] | Not started |
| [Story description] | [comma-separated task list] | 5 | [name] | Not started |

**Epic subtotal**: [X] points

### Epic 2: [Next deliverable]

[Same format]

---

**Sprint [N] total**: [X] points

---

## Overall Summary

| Epic | Points | Sprint |
|------|--------|--------|
| [epic 1] | [X] | 1 |
| [epic 2] | [X] | 1–2 |
| **Total** | **[X]** | [N sprints] |

**Velocity assumption**: [X] points/day × [Y] days = [Z] points capacity

**Buffer**: [X%] — [Y] points held back for unknowns and rework

---

## Reference key

Codes used in this document that are defined in other artifacts:

| Code | Meaning | Defined in |
|------|---------|------------|
| D[N] | [deliverable plain-language name] | planning/release_brief.md |

## Definition of Done

A story is done when:
- [ ] The work described is complete and working
- [ ] Reviewed by at least one other team member
- [ ] Relevant tests or validation checks pass
- [ ] Status updated in this sprint plan

## Downstream Releases

Upon sprint plan approval, the following delivery releases will be created:

| Release Name | Type | Scope | Estimated Start |
|--------------|------|-------|-----------------|
| [name] | [type] | [scope] | [date] |

To create them: `/wire:release-spawn [folder]`
```

### Step 5: Update Release Status

```yaml
sprint_plan:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "planning/sprint_plan.md"
  generated_date: [today's date]
```

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `sprint_plan`
- `artifact_name`: `Sprint Plan`
- `file_path`: `.wire/releases/[release_folder]/artifacts/sprint_plan.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Sprint Plan Generated

File: .wire/releases/[folder]/planning/sprint_plan.md
Total: [X] points across [N] sprints
Downstream releases: [list]

### Next Steps

1. Validate the sprint plan:
   /wire:sprint-plan-validate [folder]

2. Review with delivery team:
   /wire:sprint-plan-review [folder]

3. When approved, spawn delivery releases:
   /wire:release-spawn [folder]
```

## Output Files

- `.wire/releases/[folder]/planning/sprint_plan.md`
- Updated `.wire/releases/[folder]/status.md`
