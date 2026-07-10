---
description: Validate kick-off deck JSON structure and content completeness
argument-hint: [release-folder]
---

# Validate kick-off deck JSON structure and content completeness

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
description: Validate kick-off deck JSON structure and content completeness
argument-hint: "[release-folder]"
---

# Kickoff Deck — Validate

## Purpose

Checks that the generated kickoff deck is structurally sound and content-complete before the internal review. Produces a PASS/FAIL report. Failures must be resolved before the deck can be reviewed.

## Inputs

- Engagement-level: `.wire/kickoff-deck.html`
- Release-enriched: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`

If neither path resolves to an existing file: stop — "Run `/wire:kickoff-generate` first."

## Workflow

### Step 1: Locate the deck file

Resolve in order:
1. If `<release-folder>` is supplied: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`
2. Else: `.wire/kickoff-deck.html`

Read the file. Extract the EDITMODE block (content between `/*EDITMODE-BEGIN*/` and `/*EDITMODE-END*/`).

### Step 2: JSON structure checks

**FAIL if any of the following**:

| Check | Failure message |
|-------|----------------|
| EDITMODE block is missing | "EDITMODE block not found — template may have been corrupted. Re-run generate." |
| Content between delimiters fails `JSON.parse()` | "EDITMODE block is not valid JSON: [error detail]. Fix and re-run." |
| `slide6Problems` length ≠ 8 | "slide6Problems must have exactly 8 entries (has [n])." |
| `slide8Outcomes` length ≠ 5 | "slide8Outcomes must have exactly 5 entries (has [n])." |
| `slide12W1Items` length ≠ 6 | "slide12W1Items must have exactly 6 entries (has [n])." |
| `slide12W2Items` length ≠ 6 | "slide12W2Items must have exactly 6 entries (has [n])." |
| `slide14Categories` length ≠ 4 | "slide14Categories must have exactly 4 entries (has [n])." |
| `slide6Count` > 8 or < 0 | "slide6Count out of range (must be 0–8)." |
| `slide8Count` > 5 or < 0 | "slide8Count out of range (must be 0–5)." |
| `slide12W1Count` > 6 or < 0 | "slide12W1Count out of range (must be 0–6)." |
| `slide12W2Count` > 6 or < 0 | "slide12W2Count out of range (must be 0–6)." |
| `slide14Count` > 4 or < 0 | "slide14Count out of range (must be 0–4)." |
| Count field > non-empty array entries | "slide6Count claims [n] items but only [m] entries have content." |
| `accentColor` not matching `#[0-9A-Fa-f]{6}` | "accentColor is not a valid hex colour." |
| `slide10Direction` is non-empty and not `"LR"` or `"TB"` | "slide10Direction must be LR or TB." |
| `engagementDate` is non-empty and not matching `YYYY-MM-DD` | "engagementDate is not a valid ISO date." |

### Step 3: Content completeness checks

**WARN (not FAIL) if**:

| Check | Warning message |
|-------|----------------|
| `clientName` is empty or `"CLIENT NAME"` | "clientName is still a placeholder — update before presenting." |
| `engagementDate` is empty | "engagementDate is empty — add a date before presenting." |
| `slide6Count` is 0 | "Problems slide (slide 07) has no content — fill in or the slide will be blank." |
| `slide8Count` is 0 | "Outcomes slide (slide 09) has no content." |
| `slide12W1Count` is 0 and `slide12W2Count` is 0 | "Two-week timeline (slide 13) has no content." |
| `slide14Count` is 0 | "Access requirements (slide 15) has no content." |
| `presenters` is empty or all names are `""` | "Presenter list is empty — add at least one presenter." |
| `slide5Number` is empty | "Big-number slide (slide 05) has no metric — this slide will render empty." |
| `titlePhoto` is empty | "Title slide has no background photo — will render a gradient from accentColor (this is fine)." |

### Step 4: Output the report

```
KICKOFF DECK VALIDATION — [release-folder or "engagement-level"]

PASS / FAIL
-----------
✅ JSON structure valid
✅ Array lengths correct
[or]
❌ slide6Problems must have exactly 8 entries (has 7) — fix before review

WARNINGS
--------
⚠️  clientName is still a placeholder — update before presenting
⚠️  slide14Count is 0 — access requirements slide will be blank

RESULT: PASS with [n] warnings
[or]
RESULT: FAIL — fix [n] errors before proceeding to review
```

### Step 5: Update status

If PASS (even with warnings), update status to:
```yaml
kickoff_deck:
  validate: "complete"
```

If FAIL, leave `validate: "not_started"` and list the errors in the report.

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
