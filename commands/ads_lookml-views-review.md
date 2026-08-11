---
description: Looker admin sign-off on view files before semantic layer metric build
argument-hint: <release-folder>
---

# Looker admin sign-off on view files before semantic layer metric build

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Looker admin and data team sign-off on new and updated LookML view files before semantic layer metric build
argument-hint: <release-folder>
---

# Agentic Data Stack — LookML Views Review

## Purpose

Get confirmation from the Looker admin and data team that the generated view files correctly expose the canonical models, are wired into the right explores, and are ready to receive metric definitions from `ads_semantic-layer-generate`.

The audience is technical — Looker developers and analytics engineers, not business stakeholders.

## Usage

```bash
/wire:ads_lookml-views-review YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `lookml_views.validate: complete`

## Skip Condition

If `lookml_views.generate: skipped` in status.md, output:

```
LookML Views — Review Skipped (bi_tool is not looker)
```

Update status and stop.

---

## Workflow

### Step 1: Search Meeting Context

Before presenting the review summary, search Fathom for recent calls that discussed LookML structure, explore design, or Looker project conventions for this client. Surface any decisions or constraints that bear on view file design.

---

### Step 2: Present Review Summary

```
## LookML Views Review

### Views Created (N)

| View | File | Canonical Model | Explore |
|---|---|---|---|
| fct_orders | views/fct_orders.view.lkml | fct_orders | orders_explore |
| dim_customers | views/dim_customers.view.lkml | dim_customers | orders_explore |

### Views Updated (N)

| View | File | Changes |
|---|---|---|
| fct_subscriptions | views/fct_subscriptions.view.lkml | net_mrr renamed from mrr_amount; churn_date added |

### Validation Results

- LookML syntax: PASS (0 errors)
- Column references: PASS (0 orphaned)
- Primary keys: PASS
- Explore wiring: PASS (all views reachable)

### What Happens Next

ads_semantic-layer-generate will add measure definitions to these view files
(no structural changes — measures only). Confirm the view scaffolding is
correct before proceeding.
```

---

### Step 3: Review Questions

Ask the Looker admin and data team to confirm:

1. **Explore coverage** — are all new views in the correct explores? Are there existing explores that also need access to the new views?
2. **View naming** — do the generated view names follow the project's existing convention?
3. **Label conventions** — do dimension labels match how the business refers to these fields?
4. **Hidden fields** — are the correct FK and technical columns marked `hidden: yes`?
5. **Missing dimensions** — are there ARRAY/STRUCT columns (skipped in generation) that need manual view expansion before metrics can reference them?

---

### Step 4: Handle Feedback

For each piece of feedback, apply changes to the view files and re-run `ads_lookml-views-validate` before returning to this review.

Common changes at this stage:
- Rename a view or dimension to match existing project conventions
- Add a missing explore join
- Adjust `hidden` flags
- Resolve a `# TODO: confirm primary_key` comment

Do not add measures — any metric-level feedback belongs in the `ads_semantic-layer-design` review, which has already been completed. Log it in `lookml_views_notes.md` under a "Deferred to semantic layer" section instead.

---

### Step 5: Record Sign-off

```yaml
lookml_views:
  review: approved
  reviewer: Name
  review_date: YYYY-MM-DD
  notes: ""
```

Once approved, `ads_semantic-layer-generate` can proceed.

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
