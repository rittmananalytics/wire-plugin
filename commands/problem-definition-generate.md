---
description: Generate structured problem definition for a Shape Up discovery release
argument-hint: <release-folder>
---

# Generate structured problem definition for a Shape Up discovery release

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
description: Generate structured problem definition for a discovery release
---

# Problem Definition Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a structured problem definition document that frames the business problem, current state, desired outcome, and constraints before any solution is proposed. This is the first artifact in a discovery release and feeds directly into the pitch document.

A good problem definition resists the temptation to jump to solutions. Its job is to articulate the problem so clearly and completely that the right solution becomes obvious — not to prescribe one.

## Inputs

**Required**:
- Release folder: `.wire/releases/$ARGUMENTS/` (or `.wire/$ARGUMENTS/` for legacy layout)

**Helpful (read if present)**:
- `engagement/context.md` — engagement overview, client background, objectives
- `engagement/sow.md` — statement of work
- `engagement/calls/` — call transcripts and meeting notes
- Any documents in the release's `artifacts/` folder

## Workflow

### Step 1: Locate the Release

**Process**:
1. Try `.wire/releases/$ARGUMENTS/` first (two-tier layout)
2. Fall back to `.wire/$ARGUMENTS/` (legacy layout)
3. If neither exists, output an error listing available releases and stop

### Step 2: Read Engagement and Release Context

**Process**:
1. Read `engagement/context.md` if it exists — extract client background, engagement objectives, key stakeholders
2. Read `engagement/sow.md` if it exists — extract scope, constraints, budget context
3. Read any files in `.wire/releases/$ARGUMENTS/artifacts/` or `.wire/$ARGUMENTS/artifacts/`
4. Read any call transcripts in `engagement/calls/` — look for problem statements, pain points, current-state descriptions

If no source material is found, proceed to Step 3 (interactive mode) immediately.

### Step 3: Interactive Problem Framing

Ask directly in chat — one question at a time:

**Q1:**
```
Who is experiencing this problem? (Role, team, or group)
```

**Q2:**
```
What are they trying to do? (The job or goal they're trying to accomplish)
```

**Q3:**
```
What is getting in their way right now? (The specific friction or gap)
```

**Q4:**
```
How are they currently working around it? (Workarounds, manual processes, or tools they're using instead)
```

**Q5:**
```
What does "solved" look like? (The outcome when this problem no longer exists — not how to get there)
```

**Q6:**
```
What constraints must any solution respect? (Budget, timeline, technology, compliance, team capacity)
```

**Q7:**
```
What have we already tried or ruled out? (Failed approaches, rejected solutions, non-starters)
```

**Q8:**
```
What are we likely to discover during this engagement that we should observe and document — but NOT attempt to fix ourselves?
(Think: adjacent organisational problems, root causes that belong to the client's internal roadmap, governance issues that are real but outside our delivery scope)
```

If source material was read in Step 2, pre-populate answers from the documents and show them to the user for confirmation rather than asking from scratch.

### Step 4: Generate Problem Definition Document

**Output location**: `.wire/releases/$ARGUMENTS/planning/problem_definition.md`
(Legacy layout: `.wire/$ARGUMENTS/design/problem_definition.md`)

**Document structure**:

```markdown
# Problem Definition: [Engagement Name]

**Release**: [release_folder]
**Client**: [client_name]
**Date**: [generation_date]
**Version**: 1.0

---

## 1. Who Has This Problem

[Role, team, or group experiencing the problem. Be specific — avoid "the business" or "users".]

## 2. What They Are Trying to Do

[The underlying job-to-be-done — the goal the person is trying to accomplish, independent of any solution.]

## 3. What Is Getting in Their Way

[The specific friction, gap, or obstacle. Be concrete. Avoid abstract descriptions like "lack of visibility".]

**Current workarounds**:
[How they cope today — manual processes, spreadsheets, alternative tools, tribal knowledge]

## 4. Impact of the Problem

| Dimension | Current State | Desired State |
|-----------|---------------|---------------|
| Time | | |
| Quality | | |
| Cost / Risk | | |
| Decision making | | |

## 5. What "Solved" Looks Like

[Outcome description — not a solution, but what the world looks like when this problem no longer exists. Write in present tense as if the problem is already solved.]

## 6. Constraints

- **Budget**: [known budget ceiling or "to be determined"]
- **Timeline**: [desired completion or constraint — appetite]
- **Technology**: [must-use or must-avoid platforms/tools]
- **Compliance**: [regulatory, security, or data governance constraints]
- **Team capacity**: [available people and their skills]

## 7. Scope Constraints

### 7a. What this engagement will not produce
[A comprehensive data strategy / full operating model / resolution of problems outside the analytical delivery function — be specific to the engagement]

### 7b. What we will observe but not attempt to resolve
[Organisational capability gaps, governance issues, product definition gaps, team structure problems — things the delivery team will surface and hand back to the client, not fix]

### 7c. Escalation, not investigation
Where the team encounters blockers — missing data, undefined product terminology, access gaps — these will be surfaced to the client engagement lead immediately for resolution. The team will not investigate or work around blockers independently. The team's job is to find the critical path to the first deliverable and name what stands in the way of it.

## 8. Previously Tried or Ruled Out

[Approaches that have been attempted or rejected, and why. Avoids repeating failed paths.]

## 9. Open Questions

| Question | Why It Matters | Owner | Status |
|----------|----------------|-------|--------|
| [question] | [why] | [name] | Open |

## 10. References

[Links to SOW sections, call transcripts, or other source material used in this document]
```

### Step 5: Update Release Status

**Process**:
1. Read `.wire/releases/$ARGUMENTS/status.md`
2. Update the `problem_definition` artifact:
   ```yaml
   problem_definition:
     generate: "complete"
     validate: "not_started"
     review: "not_started"
     file: "planning/problem_definition.md"
     generated_date: [today's date]
   ```
3. Update `last_updated`
4. Write updated status.md

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `problem_definition`
- `artifact_name`: `Problem Definition`
- `file_path`: `.wire/releases/[release_folder]/artifacts/problem_definition.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Problem Definition Generated

File: .wire/releases/[folder]/planning/problem_definition.md

### Summary
- Problem owner: [role/team]
- Core friction: [one-line summary]
- Open questions: [count]

### Next Steps

1. Validate the problem definition:
   /wire:problem-definition-validate [folder]

   Checks: is the problem well-framed? Are constraints specific? Is "solved" measurable?

2. Review with stakeholders:
   /wire:problem-definition-review [folder]

3. When approved, generate the pitch:
   /wire:pitch-generate [folder]
```

## Edge Cases

### No source material and user provides minimal answers
If answers are very thin (single words, unclear), ask follow-up probing questions:
- "Can you give me a concrete example of when this happens?"
- "What does that cost the team in hours per week, or in dollars?"
- "Who is the person most affected by this today?"

### Problem is already well-defined (client has a clear brief)
If the engagement context already contains a clear problem statement, generate the document directly from that material and show it for confirmation rather than stepping through each question.

## Output Files

- `.wire/releases/[folder]/planning/problem_definition.md`
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
