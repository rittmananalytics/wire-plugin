---
description: Generate cutover runbook (SAFETY GATE — point of no return)
argument-hint: <release-folder>
---

# Generate cutover runbook (SAFETY GATE — point of no return)

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
description: Generate cutover runbook (SAFETY GATE — point of no return)
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: cutover` and `artifact_file_path: migration/cutover_runbook.md` before proceeding.

---

# Cutover — Generate

## Purpose

Generates the production cutover runbook — the step-by-step procedure for redirecting all production workloads from the source platform to the target platform. This is the point-of-no-return document. Once executed, the source platform is no longer the production system.

## Prerequisites

- `equivalency_validation.status: complete` (checks_failing == 0)
- OR explicit override in status.md with business justification for known differences

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md`
- `.wire/releases/$ARGUMENTS/migration/orchestration_migration_runbook.md`
- Latest equivalency report

## Workflow

### Step 1: Confirm prerequisites

Check `equivalency_validation.status` in status.md. If not `complete`:

If `checks_failing > 0` with no accepted_difference override:
```
Cutover is blocked: N equivalency checks are still failing.
All checks must pass (or be formally accepted) before the cutover runbook can be generated.

Run: /wire:equivalency-validate $ARGUMENTS
```

If there are accepted_difference objects: display a summary and confirm the user wants to proceed with known differences before continuing.

### Step 2: Build the pre-cutover checklist

Assemble from the migration strategy and all approved runbooks:

- [ ] All equivalency checks passing (or accepted differences formally documented)
- [ ] Fivetran target connectors active and syncing on schedule
- [ ] Target dbt project tested and passing all tests
- [ ] Target orchestration jobs created and passing manual test runs
- [ ] BI tool connection strings identified for update
- [ ] Client stakeholders notified of maintenance window
- [ ] **Full cutover rehearsal completed** on staging at production scale (see Step 2a)
- [ ] Rollback decision point agreed (time limit after which rollback is no longer viable)
- [ ] Source-platform decommission scheduled for after the rollback window (default 7–14 days post-cutover)

### Step 2a: Rehearsal (the single biggest de-risker)

The most common migration failure is a cutover that has never been run end to end before the live window. Before the real cutover, execute the entire timed sequence against a staging copy at production scale — same data volumes, same connection-string swaps, same orchestration activation, same smoke tests. Time each step.

The rehearsal proves three things: the sequence is correct and complete, the timings in the runbook are realistic, and the rollback procedure actually works. Record actual step durations and feed them back into the timed sequence below — replace the default T+ offsets with rehearsal-measured timings. A rehearsal that surfaces no surprises is the goal; one that does has paid for itself.

### Step 3: Build the cutover sequence

Generate a time-ordered runbook with:

1. **T-48h**: Final equivalency run and sign-off
2. **T-24h**: Notify all users and downstream consumers of the maintenance window
3. **T-0 (maintenance window start)**: Pause all writes to source platform
4. **T+15min**: Final row count comparison (source vs target)
5. **T+30min**: Update connection strings in BI tools and application configs
6. **T+45min**: Activate target orchestration job schedules
7. **T+60min**: Pause / archive source Fivetran connectors
8. **T+75min**: Smoke test — run key reports on target, compare outputs
9. **T+90min**: Open target platform to all users
10. **T+120min**: Go/no-go decision: full cutover confirmed OR rollback initiated

### Step 4: Build the rollback procedure

**The true point of no return is the first successful production write to the target — not the clock.** Once a downstream system has written data to the target that does not exist on the source, a clean rollback is no longer possible; from that point, issues are resolved by fixing forward. The T+120min decision point is the deadline for making the rollback call *before* that happens. Order the sequence so smoke tests and validation complete before any production write lands on the target.

Document the full rollback procedure (valid until the first production write, and no later than T+120min):
1. Reactivate source Fivetran connectors
2. Revert BI tool connection strings
3. Pause target orchestration jobs
4. Notify users of rollback
5. Root cause analysis before retry

**Rollback decision tree** — not every issue warrants a rollback. Triage by type:

- **Data loss or corruption** → roll back immediately. No evaluation, no negotiation.
- **Performance regression** → evaluate, don't reflexively roll back. Under ~2× slower: optimise in place (clustering, partitioning, slot allocation). Over ~2× slower with no quick fix: roll back and investigate.
- **Minor data discrepancy** (within or near an accepted-difference tolerance) → fix forward. Run a reconciliation job; do not roll back for something a targeted fix resolves.
- **Cosmetic / non-blocking** (a non-critical report renders oddly) → log it, fix forward, proceed.

**Rollback window**: keep the source platform live and in a rollback-ready state for 7–14 days after cutover, not just until T+120min. The T+120min point ends the *fast* rollback option; the extended window covers issues that only surface under a full business cycle (month-end close, a weekly batch). Decommission the source only after the window closes with no rollback triggered — make decommission a distinct, scheduled step, never part of the cutover itself.

### Step 5: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/cutover_runbook.md`

Use the template at `TEMPLATES/migration/cutover_runbook.md`. Include:
- Pre-cutover checklist
- Timed cutover sequence
- Rollback procedure
- Communication templates (maintenance window notification, go-live announcement)
- Post-cutover monitoring checklist

### Step 6: Update status

```yaml
artifacts:
  cutover:
    generate: complete
    file: migration/cutover_runbook.md
    generated_date: "{{TODAY}}"
```

### Step 7: Output summary

```
Cutover runbook generated. This is the point-of-no-return document.

Review carefully before proceeding:
/wire:cutover-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `cutover` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `cutover` as artifact_id, `Cutover Runbook` as artifact_name, and the `file` value from `artifacts.cutover` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `cutover` as artifact, `generate` as action.

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
