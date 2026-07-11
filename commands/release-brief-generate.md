---
description: Generate formal release brief from the approved pitch
argument-hint: <release-folder>
---

# Generate formal release brief from the approved pitch

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Generate formal release brief from the approved pitch
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

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
