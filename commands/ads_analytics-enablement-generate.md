---
description: Generate user training and maintenance documentation
argument-hint: <release-folder>
---

# Generate user training and maintenance documentation

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
description: Generate user training materials and handover documentation for the agentic data stack
argument-hint: <release-folder>
---

# Agentic Data Stack — Enablement Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Produce the user-facing documentation and data team handover materials for the agentic data stack. Users need to know what to ask, what the agent's limitations are, and how to interpret the provenance footer. The data team needs to know how to maintain the skill files as models evolve.

## Usage

```bash
/wire:ads_analytics-enablement-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `launch_gate.review: approved`

## Workflow

### Step 1: Generate User Guide

Write `.wire/<release-folder>/artifacts/agentic_data_stack_user_guide.md`:

```markdown
# [Client] Agentic Data Stack — User Guide

## What It Does

The agentic data stack answers business questions about your data platform in plain English. 
Ask it like you'd ask a data analyst.

## How to Ask Good Questions

**Be specific about time periods:**
- ✅ "Revenue last month" / "Revenue in Q1 2025"
- ❌ "Recent revenue" (ambiguous)

**Name the metric you want:**
- ✅ "Total revenue" / "Order count" / "Active customers"
- ❌ "How are we doing?" (too broad)

**Specify dimensions if you want a breakdown:**
- ✅ "Revenue by channel last quarter"
- ❌ "Revenue" (returns aggregate only)

## Understanding the Source Footer

Every answer includes:
```
Source tier: Semantic | Curated | Raw
Dataset: [table or metric name]
Freshness: [last updated timestamp]
Domain owner: [contact email]
```

**Semantic**: The answer comes from a defined business metric. Highest confidence.  
**Curated**: The answer comes from a governed dbt model. High confidence.  
**Raw**: The answer required ad-hoc SQL. Use with care — verify against a dashboard 
before including in external reports.

## What the Agent Can and Cannot Do

**Can do:**
- Answer questions about [list cleared domains]
- Break down metrics by standard dimensions (date, channel, region, category)
- Identify top-N or bottom-N rankings

**Cannot do (yet):**
- [List blocked domains] — launching in [second wave date]
- Multi-step attribution modelling
- Real-time data (data freshness is [X hours] behind live)
- Write to or modify any data

## When to Double-Check

Always verify against your canonical dashboard or with the domain owner before:
- Including a number in an external report or client presentation
- Making a significant budget or staffing decision
- The answer surprises you significantly
```

### Step 2: Generate Data Team Maintenance Guide

Write `.wire/<release-folder>/artifacts/agentic_data_stack_maintenance_guide.md`:

```markdown
# Agentic Data Stack — Maintenance Guide

## How the Agent Works

The agentic data stack uses three sources:
1. **Semantic layer** (dbt SL / LookML) — defined metrics
2. **DOMAIN_REFERENCE.md files** — per-domain knowledge, collocated with dbt models
3. **Canonical dbt models** — direct SQL fallback

## How to Keep It Accurate

### When you change a dbt model

If you modify a canonical mart model, update the collocated DOMAIN_REFERENCE.md:
- Check the "Key fields" table is still accurate
- Check the "Common Questions" examples still return correct results
- Check the "Known Limitations" section still applies

The CI check will warn if a model SQL changes without the reference file changing.

### When you add a new metric

After adding a metric to the semantic layer:
1. Add it to the relevant DOMAIN_REFERENCE.md "Semantic Layer Metrics" table
2. Add 1–2 example questions covering the new metric to the eval suite
3. Run `./eval/run_evals.sh <domain>` to confirm accuracy is maintained

### Monthly accuracy check

Run the full eval suite monthly:
```bash
cd <dbt_project_path> && ./.claude/eval/run_evals.sh all
```

If any domain drops below its target, investigate immediately — don't wait for users 
to report wrong answers.

## Key Contacts

| Domain | Owner | Contact |
|---|---|---|
| orders | Data Platform | data-platform@company.com |
| customers | Analytics Engineering | analytics@company.com |
```

### Step 3: Update Status

```yaml
enablement:
  generate: complete
  generated_date: YYYY-MM-DD
  user_guide: complete
  maintenance_guide: complete
```

## Output

- `.wire/<release-folder>/artifacts/agentic_data_stack_user_guide.md`
- `.wire/<release-folder>/artifacts/agentic_data_stack_maintenance_guide.md`
- Updated `status.md`

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
