---
description: Validate problem definition completeness and quality
argument-hint: <release-folder>
---

# Validate problem definition completeness and quality

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
description: Validate problem definition completeness and quality
---

# Problem Definition Validate Command

## Purpose

Validates that the problem definition document is complete, specific, and well-framed before moving to the pitch. Checks structural completeness, specificity of constraints, measurability of the desired outcome, and internal consistency.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/problem_definition.md` (or legacy path)

## Workflow

### Step 1: Locate and Read the Problem Definition

**Process**:
1. Resolve release folder from `$ARGUMENTS` (two-tier: `.wire/releases/$ARGUMENTS/`, legacy: `.wire/$ARGUMENTS/`)
2. Read `planning/problem_definition.md`
3. If file not found, output: "Problem definition not found. Run /wire:problem-definition-generate [folder] first."

### Step 2: Run Validation Checks

Run all checks and collect PASS/FAIL/WARNING results:

#### Section completeness
- [ ] Section 1 (Who Has This Problem) — not empty, names a specific role or team (not "the business")
- [ ] Section 2 (What They Are Trying to Do) — describes a job-to-be-done, not a solution
- [ ] Section 3 (What Is Getting in Their Way) — describes specific friction, not vague "lack of visibility"
- [ ] Section 4 (Impact) — at least 2 rows of the impact table completed
- [ ] Section 5 (What Solved Looks Like) — describes outcome, not implementation
- [ ] Section 6 (Constraints) — budget and timeline fields are not both "to be determined"
- [ ] Section 7 (Out of Scope) — at least one item listed

#### Quality checks
- [ ] **Problem vs solution**: Section 5 does not describe a technical solution (e.g. "build a dashboard") — it describes an outcome (e.g. "the ops team can see overnight exceptions before their morning standup")
- [ ] **Specificity**: Section 3 contains at least one concrete detail (a named system, a process step, a time/cost figure)
- [ ] **Constraints specificity**: At least one constraint is specific (e.g. "£50k" not "limited budget", "Q3 2026" not "soon")
- [ ] **No premature solutions**: None of sections 1–7 describe implementation choices (database, tool names, architecture patterns) unless they are genuine constraints
- [ ] **Open questions tracked**: Section 9 is present and lists any unresolved questions (or explicitly states "None")

#### Consistency checks
- [ ] **Scope boundary**: Items in Section 7 (Out of Scope) do not contradict the desired outcome in Section 5
- [ ] **Constraints vs outcome**: The constraints do not make the desired outcome impossible (flag if they appear to conflict)

### Step 3: Produce Validation Report

**Output location**: `.wire/releases/$ARGUMENTS/planning/problem_definition_validation.md`

```markdown
# Problem Definition Validation Report

**Release**: [folder]
**Date**: [today's date]
**File**: planning/problem_definition.md

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|-------|--------|------|
| Section 1: Who has this problem | ✅ PASS | |
| Section 2: Job-to-be-done | ✅ PASS | |
| Section 3: Specific friction | ⚠️ WARNING | "Lack of visibility" is vague — add a concrete example |
| Section 4: Impact table | ✅ PASS | |
| Section 5: Outcome not solution | ✅ PASS | |
| Section 6: Constraints specific | ❌ FAIL | Budget and timeline are both "to be determined" |
| Section 7: Out of scope | ✅ PASS | |
| Problem vs solution check | ✅ PASS | |
| No premature solutions | ✅ PASS | |
| Open questions tracked | ✅ PASS | |
| Scope consistency | ✅ PASS | |

## Issues to Resolve

### FAIL: Constraints not specific enough
Section 6 shows budget and timeline as "to be determined". At minimum, provide an appetite (e.g. "1–2 weeks" or "6 weeks") before moving to the pitch — the pitch requires a defined appetite.

### WARNING: Friction description is vague
Section 3 describes friction as "lack of visibility into overnight processes". Add a concrete example: what system, what data, what time window, and what the analyst has to do manually instead.

## Next Steps

[If PASS or PASS WITH WARNINGS]:
1. Resolve warnings if applicable
2. Review with stakeholders: /wire:problem-definition-review [folder]
3. Then generate the pitch: /wire:pitch-generate [folder]

[If FAIL]:
1. Fix the issues listed above
2. Re-run validation: /wire:problem-definition-validate [folder]
```

### Step 4: Update Release Status

Update `status.md`:
```yaml
problem_definition:
  validate: "complete"   # or "failed" if FAIL result
```

### Step 5: Output Summary

Show the validation result and the most important issue to fix (if any).

## Output Files

- `.wire/releases/[folder]/planning/problem_definition_validation.md`
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
