---
description: Generate sprint plan with epics, stories, and point estimates
argument-hint: <release-folder>
---

# Generate sprint plan with epics, stories, and point estimates

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
description: Generate sprint plan with epics, stories, and point estimates from the release brief
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
*Maps to: Release Brief D[N]*

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
