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

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.17\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"release-brief-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.17\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate formal release brief from the approved pitch
---

# Release Brief Generate Command

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

These releases will be created by running: `/wire:release:spawn [folder]` at the end of the sprint plan.

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

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

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
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

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
