---
wire_schema: "1.0"
command: generate
artifact: release_brief
domain: discovery
release_types:
  - discovery_shape_up
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: pitch
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate formal release brief from the approved pitch

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Release Brief Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a formal release brief from the approved pitch. The release brief is the commitment document — it specifies exactly what will be delivered, what the team will do, the timeline, the constraints, and the sign-off requirements. It is more precise than the pitch and is used to formally begin work.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/pitch.md` — must be reviewed and approved

## Workflow

### Step 1: Locate Release and Read Pitch

Resolve release folder. Read `planning/pitch.md`. Verify pitch has been approved (check status.md `pitch.review`). If not approved, stop and prompt the user to complete the pitch review first.

Also read:
- `engagement/context.md` if present
- `engagement/sow.md` if present (for budget and contract terms)

### Step 2: Identify Downstream Delivery Releases

From Section 8 of the pitch (Downstream Releases), extract the planned delivery releases. If Section 8 is empty or "TBD", ask:

```
Based on the approved pitch, what delivery releases will this discovery release produce?
(e.g. "01-data-foundation: pipeline_only, 02-reporting: dashboard_extension")

List them as: [name]: [type]
```

### Step 2b: Establish Primary Analytical Focus and Goal Hierarchy

Before generating the brief, ask explicitly:

```
The SOW/pitch lists the following engagement goals:
[list goals extracted from pitch or SOW]

1. Which of these is the PRIMARY use case — the single analytical domain that all discovery work is in service of?
   (e.g. "Customer acquisition funnel", "Merchant 360", "Operational productivity reporting")

2. For each remaining goal, assign a priority:
   - Primary: must achieve in this engagement
   - Secondary: assess and recommend only — do not design or build
   - Future: out of scope this engagement, note and defer
```

Record the answers as:
- `primary_analytical_focus`: [the ONE named use case]
- `goal_hierarchy`: a table of goals with assigned priorities

### Step 3: Generate the Release Brief

**Output location**: `.wire/releases/$ARGUMENTS/planning/release_brief.md`

Apply the reference-legibility convention (`specs/utils/reference_legibility.md`): the deliverable codes (D1, D2, …) and assumption codes (A1, A2, …) minted below are defined by their table rows, which carry their plain-language names. If the brief cites a code defined in another artifact, add a Reference key section in the canonical format from that spec.

```markdown
# Release Brief: [Release Name]

**Engagement**: [client_name]
**Release folder**: [folder_name]
**Date**: [generation_date]
**Version**: 1.0
**Status**: Draft

---

## 0. Primary Analytical Focus

**Priority use case**: [ONE named use case agreed with the client at kick-off]

All discovery work — stakeholder interviews, entity model, data source assessment, solution definition — is conducted in service of this use case. Other analytical domains surfaced during discovery will be noted for future phases but will not be scoped or designed during this release.

**Goal hierarchy**:

| Goal | Priority | What this engagement will do |
|------|----------|------------------------------|
| [Goal 1] | Primary | Design and deliver |
| [Goal 2] | Primary | Design and deliver |
| [Goal 3] | Secondary | Assess and recommend — do not design solutions |
| [Goal 4] | Secondary | Assess and recommend — do not design solutions |
| [Goal 5] | Future | Note and defer to a future release |

**What this discovery will not produce**: A comprehensive data strategy, a full analytics operating model, or remediation plans for organisational or governance issues that fall outside the analytical delivery function. Where root causes are found that go beyond this scope, they will be documented and handed back to the client.

## 1. Executive Summary

[2–3 sentence summary of what this release delivers and why. Written for a stakeholder who hasn't read the pitch.]

## 2. Appetite and Timeline

**Appetite**: [Small batch — 1–2 weeks | Big batch — 6 weeks]
**Confirmed by**: [who approved the pitch]
**Start date**: [date or TBD]
**End date**: [date or TBD]

## 3. Deliverables

| # | Deliverable | Description | Acceptance Criteria | Owner |
|---|------------|-------------|---------------------|-------|
| D1 | [name] | [what it is] | [how we know it's done] | [name/role] |
| D2 | [name] | [what it is] | [how we know it's done] | [name/role] |

**Completion definition**: This release is complete when all deliverables above are signed off by [approver role].

## 4. Downstream Releases Produced

This discovery release will produce the following delivery releases upon completion of the sprint plan:

| Release Name | Type | Scope Summary | Priority |
|--------------|------|---------------|----------|
| [name] | [type] | [1-line scope] | 1 |
| [name] | [type] | [1-line scope] | 2 |

These releases will be created by running: `/wire:release-spawn [folder]` at the end of the sprint plan.

## 5. What Is Out of Scope

[From pitch Section 5 (No-gos) — formalised as contractual boundaries]

- [Item 1]
- [Item 2]
- [Item 3]

**Scope change process**: Any additions to scope require a new pitch or formal change request.

## 6. Assumptions

| # | Assumption | Impact if Wrong | Owner |
|---|-----------|-----------------|-------|
| A1 | [assumption] | [impact] | [owner] |

## 7. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|------------|--------|------------|-------|
| [risk] | H/M/L | H/M/L | [mitigation] | [owner] |

## 8. Resources

| Role | Name | Allocation | Responsibilities |
|------|------|------------|-----------------|
| Engagement Lead | [name] | [%] | [responsibilities] |
| [role] | [name] | [%] | [responsibilities] |

## 9. Budget

**Engagement budget**: [from SOW, or "to be confirmed"]
**This release**: [estimated cost, or "included in engagement budget"]
**Payment milestone**: [when this release triggers a payment, if applicable]

## 10. Dependencies and Prerequisites

| Dependency | Owner | Required By | Status |
|-----------|-------|-------------|--------|
| [dependency] | [owner] | [date] | Open |

## 11. Communication and Governance

**Stakeholder updates**: [frequency and format]
**Decision-making authority**: [who can approve changes]
**Escalation path**: [who to escalate to if blocked]

## 12. Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Client sponsor | | | |
| Engagement lead | | | |

*Signature indicates agreement with the scope, timeline, budget, and deliverables defined in this document.*
```

### Step 4: Update Release Status

```yaml
release_brief:
  generate: "complete"
  validate: "not_started"
  review: "not_started"
  file: "planning/release_brief.md"
  generated_date: [today's date]
primary_analytical_focus: "[value captured in Step 2b]"
goal_hierarchy_captured: true
```

### Step 5: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `release_brief`
- `artifact_name`: `Release Brief`
- `file_path`: `.wire/releases/[release_folder]/artifacts/release_brief.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 6: Confirm and Suggest Next Steps

```
## Release Brief Generated

File: .wire/releases/[folder]/planning/release_brief.md

Downstream releases identified: [list from Section 4]

### Next Steps

1. Validate the release brief:
   /wire:release-brief-validate [folder]

2. Review and sign off with the client:
   /wire:release-brief-review [folder]

3. When signed off, generate the sprint plan:
   /wire:sprint-plan-generate [folder]
```

## Output Files

- `.wire/releases/[folder]/planning/release_brief.md`
- Updated `.wire/releases/[folder]/status.md`
