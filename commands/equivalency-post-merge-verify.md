---
description: Post-merge production verification: wait for the client pipeline to materialise merged models, compare at the full verdict bar, advance the register to production_verified
argument-hint: <release-folder> [--models list] [--no-wait]
---

# Post-merge production verification: wait for the client pipeline to materialise merged models, compare at the full verdict bar, advance the register to production_verified

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
description: Post-merge production verification — wait for the client pipeline to materialise merged models, compare production tables at the full verdict bar, advance the register to production_verified
argument-hint: <release-folder> [--models list] [--no-wait] [--wait-timeout minutes]
---

# Equivalency — Post-Merge Verify

## Purpose

The assurance state the register's `merged` stage deliberately is not: a merged model has been accepted by the client, but nothing yet proves the production build of that model produces equivalent rows. This command closes that gap per merged model set. It is a **thin orchestrator**: the waiting and the register stage advance live here; every comparison runs through `equivalency-validate --run-point post_merge_prod`, so there is exactly one comparison engine.

## Scope

Default scope: every register row with `delivery_stage = merged` and no `run_point = post_merge_prod` row with verdict `pass`/`pass_qualified` in `migration/migration_verdict_log.csv`. `--models` restricts to named models within that set.

## Workflow

### Step 1 — Wait for materialisation (target metadata, not the scheduler)
For each in-scope model, poll the production target's table metadata (BigQuery: `INFORMATION_SCHEMA.TABLES` / `__TABLES__` last-modified; Snowflake: `INFORMATION_SCHEMA.TABLES.LAST_ALTERED`) until the object's last-modified instant is later than its PR merge time (from `gh pr view` on the row's `pr_url`). This is deliberately orchestration-tool-agnostic: no scheduler API, whatever runs the client's DAG. Poll at a low cadence (every 10 minutes, `--wait-timeout` default 240). `--no-wait` skips the wait and compares whatever is materialised now, flagging not-yet-rebuilt models `stale_materialisation` and excluding them from verdicts. On timeout, report the unmaterialised set and proceed with the rest.

### Step 2 — Compare in production
Invoke `equivalency-validate $ARGUMENTS --run-point post_merge_prod --models <materialised set>`. The target side is the **production** dataset (the merged models' real relations), not the scratch dataset; the source side and every check, pin, and taxonomy rule are exactly as that command specifies. The full verdict bar applies — this run point exists to catch what a sandbox cannot (production partitioning, prod-only data, the client's own build), so it is never run at a reduced bar.

### Step 3 — Advance the register
The merge step of `equivalency-validate` (rules in `specs/migration/equivalency/verdict_schema.md`) records the `post_merge_prod` verdicts in the verdict log and advances `delivery_stage` to `production_verified` for `pass`/`pass_qualified`. Divergent models keep `delivery_stage: merged`; each divergence is drilled to a named mechanism, and any `fail` (a translation defect that reached production) is escalated immediately: report it, reference `equivalency-investigate`, and flag it for the defect-class flywheel (sweep the estate for the same class).

### Step 4 — Update status and report

```yaml
artifacts:
  equivalency:
    post_merge_verify:
      last_run_date: "{{TODAY}}"
      models_verified: <n>
      models_divergent: <n>
      models_unmaterialised: <n>
```

Output: the verified/divergent/unmaterialised counts, each divergence with its mechanism, and — when divergent or unmaterialised models remain — the re-run line:

```
/wire:equivalency-post-merge-verify $ARGUMENTS
```

## Notes for the implementer

- Keep this command free of comparison logic. If a check needs to differ at this run point, the change belongs in `equivalency-validate`, keyed off `--run-point`, not here.
- A `post_merge_prod` divergence with a benign mechanism (e.g. prod partition filter semantics) is a `diff_*` verdict, not a silent pass — the named-mechanism discipline applies with extra force in production.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.
2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `post_merge_verify` as action.
3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `post_merge_verify` as action.

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
