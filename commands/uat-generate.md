---
description: Generate UAT plan
argument-hint: <project-folder>
---

# Generate UAT plan

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
description: Generate uat from design and requirements
argument-hint: <project-folder>
---

# uat Generate Command

Follow `specs/utils/data_quality_engineer_delegate.md` before executing the workflow below.

## Purpose

Generate a UAT test plan that turns every deliverable's acceptance criteria in `requirements_specification.md` into a concrete test scenario a business stakeholder can execute and sign off on. UAT has no automated `validate` step — the stakeholder running through this plan in `/wire:uat-review` **is** the validation — so the plan itself must be complete and unambiguous enough to run without the analyst in the room.

## Usage

```bash
/wire:uat-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must be approved
- Relevant design artifacts should be complete
- At least one development artifact (`dbt`, `dashboards`, `pipeline`, `semantic_layer`) should be complete — a UAT plan for nothing yet built has nothing to test

## Workflow

### Step 1: Read Inputs

**Process**:
1. Read `requirements/requirements_specification.md` — extract the deliverables table (ID, Description, Acceptance Criteria)
2. Read `status.md` to identify which development artifacts are complete and available to test against
3. Read `design/data_model.md` / `development/dashboards.md` (whichever exist) for the concrete field/dashboard names a tester will actually see, so scenarios reference real names, not placeholders

### Step 2: Generate One Test Scenario Per Deliverable

For every deliverable with a stated acceptance criterion, generate a test scenario:

- **Scenario ID**: matches the deliverable ID (e.g. `D3`) so pass/fail traces back to the SOW
- **Setup**: what the tester needs before starting (login, sample data, a specific date range)
- **Steps**: numbered, concrete actions ("Open the Revenue dashboard", "Filter to Q1 2026") — not "verify the dashboard works"
- **Expected Result**: what the tester should see, stated specifically enough that "it looks fine" isn't a valid pass/fail judgment
- **Acceptance Criteria**: copied verbatim from `requirements_specification.md` — the plan doesn't get to soften or reinterpret what was agreed

If a deliverable's acceptance criteria are too vague to turn into concrete steps (e.g. "the dashboard should be useful"), flag it rather than inventing specificity requirements weren't approved with:

```
Deliverable [ID] has no testable acceptance criteria stated in requirements_specification.md ("[criteria text]").

Suggest a specific, testable criterion now, or flag this deliverable for a requirements amendment before UAT sign-off?
```

### Step 3: Generate Cross-Cutting Scenarios

Beyond per-deliverable scenarios, add scenarios for concerns that span deliverables (only include ones actually relevant to what's built):

- **Data freshness**: does the data reflect the expected refresh cadence from `pipeline_design.md`?
- **Access control**: can each stakeholder role see what they're supposed to (and not see what they're not)?
- **Edge cases named in requirements**: any explicitly-discussed edge case (e.g. "what happens with a cancelled subscription") gets its own scenario

### Step 4: Generate UAT Plan

**File**: `.wire/releases/[release_folder]/test/uat_plan.md`

```markdown
# UAT Test Plan: [Project Name]

**Generated**: [Date]
**Testers**: [from requirements_specification.md's stakeholder list, if named]

## How to Use This Plan

Work through each scenario below. Record Pass/Fail and any notes. Any Fail must be discussed before UAT sign-off in `/wire:uat-review`.

## Scenarios

### [Deliverable ID]: [Deliverable Name]

**Setup**: [what's needed before starting]

**Steps**:
1. [Concrete action]
2. [Concrete action]

**Expected Result**: [Specific, checkable outcome]

**Acceptance Criteria** (from requirements): [verbatim from requirements_specification.md]

**Result**: ☐ Pass ☐ Fail
**Notes**:

---

[Repeat per deliverable, then cross-cutting scenarios]

## Sign-off

| Scenario | Result | Tester | Date |
|----------|--------|--------|------|
| [ID] | | | |

**Overall UAT outcome**: ☐ Approved ☐ Changes Requested — recorded via `/wire:uat-review`
```

### Step 5: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.uat section:
   ```yaml
   uat:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: 2026-02-13
     scenario_count: [number of scenarios generated]
   ```
3. Write updated status.md

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `uat`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `uat`
- `artifact_name`: `UAT Plan`
- `file_path`: `.wire/releases/[release_folder]/test/uat_plan.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## uat Generated Successfully

**Scenarios generated**: [N] ([N] per-deliverable, [N] cross-cutting)
**Deliverables with no testable acceptance criteria**: [N] (flagged — see plan)

**File(s):** .wire/releases/[release_folder]/test/uat_plan.md

### Next Steps

1. **Review uat**: `/wire:uat-review <project>` (uat is generate+review only — there is no validate step; sign-off happens directly in review)
```

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### No Development Artifacts Complete

If none of `dbt`, `dashboards`, `pipeline`, `semantic_layer` are complete:
```
Error: No development artifacts are complete yet, so there's nothing to test.

Complete at least one development artifact before generating a UAT plan.
```

### Deliverable Table Missing or Empty

If `requirements_specification.md` has no deliverables table:
```
Error: No deliverables table found in requirements_specification.md.

UAT scenarios are generated one per deliverable — without a deliverables table there's nothing to derive scenarios from. Check that requirements_specification.md follows the standard template.
```

## Output

This command creates:
- `.wire/releases/[release_folder]/test/uat_plan.md` — one test scenario per deliverable acceptance criterion, plus cross-cutting scenarios, plus a sign-off table
- Updates `status.md`

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
