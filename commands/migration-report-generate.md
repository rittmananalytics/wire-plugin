---
description: Generate post-migration report
argument-hint: <release-folder>
---

# Generate post-migration report

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
description: Generate post-migration report
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_report` and `artifact_file_path: migration/migration_report.md` before proceeding.

---

# Migration Report — Generate

## Purpose

Generates the post-migration report summarising what was migrated, the final equivalency state, any known differences accepted, lessons learned, and recommendations for decommissioning the source platform. This is the final deliverable of the platform_migration release.

## Prerequisites

- `cutover review: approved`
- Cutover runbook executed (manual confirmation required)

## Flags

- `--lens defects` — produce the **defect-provenance lens** (see below) instead of the default post-migration summary. Reads the per-wave structured findings the migration gates already wrote and aggregates them; it does not re-run any gate. Writes a separate file (`migration/migration_report_defects.md`), leaving the default report untouched.
- `--client-caught <path>` — optional. A client-PR-review findings file (or a manual `client_caught` tally) logged back against a wave, feeding the client-caught count in the defects lens. When absent, client leakage is reported as "not tracked", never as 0. Ignored without `--lens defects`.

With no `--lens` flag the command behaves exactly as the Workflow below describes — the default post-migration report is unchanged.

## Workflow

### Step 1: Confirm cutover is complete

Ask: "Has the production cutover been executed?" Wait for explicit confirmation before proceeding.

### Step 2: Gather final state

Read:
- All 5 audit files — source platform object counts
- Migration inventory — scoped object counts and effort estimates
- Latest equivalency report — final check results
- Cutover runbook — actual cutover date and duration
- Loop history from status.md — how many equivalency cycles were required

### Step 3: Write the report

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_report.md`

Use the template at `TEMPLATES/migration/migration_report.md`. Include:

**Executive summary**:
- Migration completed on [date] from [source] to [target]
- N objects migrated: X connectors, Y tables, Z dbt models, W jobs
- Final equivalency state: N/N passing, N accepted differences
- Actual vs estimated effort
- Cutover duration

**What was migrated**:
- Per-category counts matching the migration inventory
- Key decisions made during migration (from audit reviews and strategy sign-offs)

**Equivalency outcomes**:
- Final equivalency report summary
- Accepted differences table (object, difference, business justification)
- Equivalency loop history (how many runs were needed)

**Issues encountered**:
- Issues discovered during migration with how they were resolved
- Any issues deferred to post-migration cleanup

**Lessons learned**:
- What worked well
- What would be done differently
- Recommendations for future migrations

**Source platform decommission plan**:
- Recommended timeline for decommissioning source platform
- Objects to retain on source platform (if any)
- Cost savings expected after decommission

### Step 4: Update status

```yaml
artifacts:
  migration_report:
    generate: complete
    file: migration/migration_report.md
    generated_date: "{{TODAY}}"
migration:
  status: complete
  completed_date: "{{TODAY}}"
```

### Step 5: Output next command

```
/wire:migration-report-validate $ARGUMENTS
```


## Defect-provenance lens (`--lens defects`)

Runs instead of Steps 2–3 above when `--lens defects` is supplied (Steps 1, 4, 5 and the hooks still apply). It answers one question across the migration: **where in the pipeline was each defect caught, and is the point of capture shifting left over successive waves?** It is a read-only aggregation over findings the gates already emit — it runs no gate and makes no fix/rule decisions.

### Inputs (whatever exists — a gate that never ran contributes nothing)

Per wave, read the structured findings each gate writes:
- `dbt-migration-lint` results — `migration/lint/wave_{id}_lint.md` / `.json` (rule-id findings).
- `dbt-migration-validate` Check 5 coverage report — the per-model all-code-path coverage table; an unchecked surface is a coverage gap, not a clean pass.
- `equivalency-validate` results — failing objects and their reason (`column_order_drift`, `governance_regression`, `deployment_type_divergence`, value/checksum drift, …).
- `dbt-migration-pre-pr-review` findings — `migration/pre_pr_review/wave_{id}_pre_pr_review.json` (Checks 1–6).
- `dbt-migration-fix` applied-fix summaries — `migration/pre_pr_review/{scope}_fix_report.md` (auto-fixed / escalated-propose / escalated-decision counts).
- **generate-inline** findings — defects `dbt-migration-generate` caught and resolved inline (Check B column-order, materialisation-hook drift, `-- MANUAL REVIEW REQUIRED` flags it raised), where recorded against the wave.
- **Optional** — the `--client-caught` input (a client-PR-review findings file logged back to the migration register, or a manual `client_caught` tally).

Pattern ids (`UNGUARDED_JSON_PARSE`, `DIV0_NULL_COERCION`, `COLUMN_ORDER_DRIFT`, …) and defect classes come from the **active platform pair** — treat them as data. Never hardcode a dialect's pattern list here; the lens aggregates whatever the gates emitted, so a new pair works unchanged.

### Aggregation (per wave)

1. **Stage-of-capture breakdown.** Attribute every distinct defect to the **earliest** gate that caught it, in pipeline order:

   `generate_inline < lint < validate < equivalency < pre_pr_review`

   A defect is identified by its `defect_id` if a gate emitted one, else by `model` + pattern id. The same defect legitimately recurs in several gates' outputs (a later gate re-detecting what an earlier one could have caught) — count it **once**, at its earliest sighting, so the breakdown measures where defects are actually being caught rather than double-counting. Break the counts down by defect class / pattern id. The subset attributed to `pre_pr_review` is the count that survived every earlier gate — the "reached the last internal gate" figure.

2. **Auto-fixed vs escalated split.** From the wave's `dbt-migration-fix` summary: `auto_fixed`, `escalated_propose`, `escalated_decision` (and their `escalated_total`).

3. **Client-caught count.** From the optional `--client-caught` input: the count of findings recorded against the wave **after our gates passed**. If the input is absent, record it as **"not tracked"** — never a silent 0. Leakage-to-client is stated explicitly, so a wave with no tracking is never mistaken for a wave with zero leakage.

4. **Wave-over-wave trend.** Emit the per-wave figures in wave order (total defects, reached-pre_pr_review, auto-fixed, escalated-total, client-caught) so the leftward shift — more caught at generate-inline/lint, fewer surviving to pre-PR review, zero reaching the client — or a regression is visible at a glance.

**Rule candidates (surface only).** A pattern that leaks to the client across two or more waves is listed as a rule candidate — a prompt for a human to consider a new gate rule. The lens never decides that a new defect class warrants a rule; that stays a human decision. It only surfaces the pattern and its wave history.

### Output

Write `.wire/releases/$ARGUMENTS/migration/migration_report_defects.md`. Structure:
- **Header**: the pipeline order used for earliest-gate attribution, the waves covered, and the note that this aggregates existing gate findings — it runs no gate.
- **Per-wave section**: the stage-of-capture table (by stage, broken down by pattern id / defect class), the auto-fixed vs escalated split, and the client-caught figure (integer or "not tracked").
- **Trend**: the wave-ordered rollup table.
- **Rule candidates**: patterns reaching the client in ≥2 waves, with their wave history — flagged for human review, not auto-actioned.
- **Coverage gaps**: any gate whose findings were unavailable for a wave — recorded as "not checked", never folded into a clean count.

### Status (defects lens)

```yaml
artifacts:
  migration_report:
    generate_defects: complete
    file_defects: migration/migration_report_defects.md
    generated_date: "{{TODAY}}"
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_report` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_report` as artifact_id, `Migration Report` as artifact_name, and the `file` value from `artifacts.migration_report` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_report` as artifact, `generate` as action.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
