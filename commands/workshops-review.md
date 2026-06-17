---
description: Record workshop outcomes
argument-hint: <project-folder>
---

# Record workshop outcomes

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
description: Record workshop outcomes and update requirements
argument-hint: <project-folder>
---

# Workshops Review Command

## Purpose

Record outcomes from requirements clarification workshop and update the requirements document with decisions made.

## Usage

```bash
/wire:workshops-review YYYYMMDD_project_name
```

## Prerequisites

- Workshop materials generated (`/wire:workshops-generate` complete)
- Workshop conducted with stakeholders

## Workflow

### Step 1: Locate Workshop Materials

**Process**:
1. Verify workshop materials exist:
   - `requirements/workshop_agenda.md`
   - `requirements/workshop_decision_matrix.md`

### Step 2: Record Workshop Details

**Ask for basic info**:
```
When was the workshop held? (YYYY-MM-DD)
```

**Then ask**:
```
Who attended the workshop? (List names and roles)
```

### Step 3: Fill Decision Matrix

**Output**:
```
## Recording Workshop Decisions

Let's go through each decision point from the workshop.

**Topic 1: Data refresh rate**
Options: Real-time, Near-real-time, Hourly

What was decided?
```

For each topic in the decision matrix:
1. Show the topic and options
2. Ask what was decided
3. Ask for rationale
4. Ask who owns any follow-up actions

### Step 4: Capture Action Items

**Ask**:
```
Were there any action items from the workshop?

List them in this format:
- Action: [description]
- Owner: [name]
- Due date: [YYYY-MM-DD]

(Type 'none' if no action items, or list them)
```

### Step 5: Update Decision Matrix

**Process**:
1. Read `requirements/workshop_decision_matrix.md`
2. Fill in all the decision columns based on responses
3. Add action items section
4. Add workshop metadata (date, attendees)
5. Write updated file

**Output preview**:
```
## Workshop Decisions Matrix - UPDATED

**Workshop Date:** [Date]
**Facilitator:** [Delivery lead]
**Attendees:** [Names and roles from workshop]

| # | Topic | Decision | Rationale | Owner | Follow-up |
|---|-------|----------|-----------|-------|-----------|
| 1 | [Topic 1] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |
| 2 | [Topic 2] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |
| 3 | [Topic 3] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |
| 4 | [Topic 4] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action from workshop] | [Owner] | [Date] | Pending |
| [Action from workshop] | [Owner] | [Date] | Pending |
| [Action from workshop] | [Owner] | [Date] | Pending |
```

### Step 6: Update Requirements Document

**Ask**:
```
Should I update the requirements document with these workshop decisions? (y/n)
```

If yes:
1. Read `requirements/requirements_specification.md`
2. Find sections with [NEEDS CLARIFICATION] or [TBD]
3. Replace with workshop decisions
4. Save updated requirements

### Step 7: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.workshops section:
   ```yaml
   workshops:
     generate: complete
     review: approved
     workshop_date: 2026-02-03
     decisions_count: 4
     action_items: 3
     reviewed_date: 2026-02-03
   ```
3. Also update requirements artifact if modified:
   ```yaml
   requirements:
     ...
     notes: "Updated with workshop decisions from 2026-02-03"
     last_updated: 2026-02-03
   ```
4. Write updated status.md

### Step 7.5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `workshops`
- Action: `review`
- Status: `approved`
- Include workshop date and decisions count in Jira comment

### Step 7.6: Sync to Linear (Optional)

Follow the Linear sync workflow in `specs/utils/linear_sync.md`:
- Artifact: `workshops`
- Action: `review`
- Status: `approved`

### Step 7.7: Sync to Document Store (Optional)

If a document store is configured, follow the workflow in `specs/utils/docstore_sync.md` to re-sync the final workshop materials (agenda, decision matrix) to the configured store. This ensures any updates captured during the workshop are reflected in the client-accessible version.

Fail gracefully if the document store is unavailable.

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## Workshop Outcomes Recorded ✅

**Workshop Date:** 2026-02-03
**Decisions Made:** 4
**Action Items:** 3

**Updated Files:**
- .wire/[folder]/requirements/workshop_decision_matrix.md
- .wire/[folder]/requirements/requirements_specification.md

### Key Decisions

1. **[Topic 1]**: [Decision]
2. **[Topic 2]**: [Decision]
3. **[Topic 3]**: [Decision]
4. **[Topic 4]**: [Decision]

### Next Steps

1. **Complete action items** (3 items pending)

2. **Re-validate requirements** with workshop decisions:
   /wire:requirements-validate [folder]

3. **Get final approval**:
   /wire:requirements-review [folder]

4. **Once approved, proceed to design**:
   /wire:pipeline_design-generate [folder]
```

## Edge Cases

### Workshop Not Held Yet

If workshop hasn't happened:
```
Workshop materials exist but workshop hasn't been held yet.

Schedule and conduct the workshop first, then run this command to record outcomes.
```

### Workshop Materials Not Found

If no workshop materials:
```
Error: Workshop materials not found.

Generate workshop materials first: /wire:workshops-generate [folder]
```

### Some Decisions Not Made

If workshop couldn't decide on some topics:
```
Warning: Not all decisions were made in the workshop.

Record partial decisions? These items remain unresolved:
- Topic 3: [Unresolved topic]
- Topic 5: [Unresolved topic]

You can:
1. Record partial decisions now
2. Schedule follow-up workshop
3. Make decisions offline and come back
```

## Output

This command:
- Updates `requirements/workshop_decision_matrix.md` with decisions
- Updates `requirements/requirements_specification.md` (optional)
- Records action items
- Updates `status.md` with workshop completion

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
