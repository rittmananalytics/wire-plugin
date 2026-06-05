---
description: Run equivalency checks across all in-scope tables (parallel fan-out)
argument-hint: <release-folder>
---

# Run equivalency checks across all in-scope tables (parallel fan-out)

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.7.4\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"equivalency-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.7.4\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Run equivalency checks across all in-scope tables (repeatable loop, parallel fan-out)
---

# Equivalency — Validate

## Purpose

This is a repeatable loop command — not a standard generate/validate/review artifact. It runs all five check types (row count, schema, value, freshness, dbt tests) across all in-scope migration objects, updates the equivalency tracking block in status.md, and unblocks the cutover command when `checks_failing == 0`.

Each invocation adds a new entry to `equivalency_validation.loop_history` in status.md, preserving the full audit trail of every run.

## Prerequisites

- `orchestration_migration review: approved`
- Target platform has data (Fivetran connectors have completed at least one sync)

## Behaviour

This command can be run as many times as needed. There is no "approved" state — the loop continues until equivalency passes or the team decides to proceed to cutover despite known failures (requires explicit override).

## Workflow

### Step 1: Load scope

Read the list of in-scope tables and dbt models from `migration/migration_inventory.md`. This is the full check scope.

For projects with >50 in-scope objects: fan out checks in parallel subagents — one per schema or one per dbt layer. Each subagent runs all 5 check types for its assigned objects and reports back. This dramatically reduces wall-clock time for large migrations.

### Step 2: Run all 5 check types

For each in-scope object, run:

**Check type 1 — Row count**
```sql
-- Source
SELECT COUNT(*) AS row_count FROM source_project.source_schema.table_name;
-- Target
SELECT COUNT(*) AS row_count FROM target_db.target_schema.table_name;
```
PASS: |source_count - target_count| / source_count ≤ tolerance (default 0.1%, configurable per table in migration strategy)
FAIL: Count outside tolerance

**Check type 2 — Schema**
Compare column names, types, and nullability between source and target.
PASS: All columns match (modulo expected type translations per type_mapping.md)
FAIL: Missing columns, extra columns, or unexpected type changes

**Check type 3 — Value sampling**
For numeric columns: compare mean, min, max, null percentage (sample 10K rows if table >10M rows)
For string columns: compare distinct count and null percentage
PASS: Statistical measures within ±1% (configurable)
FAIL: Deviation outside threshold

**Check type 4 — Freshness**
Compare max(updated_at) or max(loaded_at) between source and target.
PASS: Target is within max(sync_frequency, 24h) of source
FAIL: Target data is more than 24 hours stale relative to source

**Check type 5 — dbt tests**
Run `dbt test --profiles-dir ~/.dbt --target target_profile` for the translated dbt models.
PASS: All tests pass
FAIL: List failing tests

### Step 3: Compile results

Aggregate:
- `checks_total`: total checks run
- `checks_passing`: checks that passed all 5 types
- `checks_failing`: checks with at least one failure
- `checks_by_type`: breakdown of pass/fail per check type
- Per-object summary: which checks passed/failed for each object

### Step 4: Write equivalency report

**Output location**: `.wire/releases/$ARGUMENTS/migration/equivalency_report_{run_number}.md`

Use the template at `TEMPLATES/migration/equivalency_report.md`. Include:
- Run summary: date, run number, total/passing/failing
- Objects failing by check type
- Top 10 failures sorted by severity (schema failures first, then count, then value)

### Step 5: Update status

```yaml
migration:
  equivalency_validation:
    checks_total: N
    checks_passing: N
    checks_failing: N
    last_run_date: "{{TODAY}}"
    loop_history:
      - run: 1
        date: "{{TODAY}}"
        passing: N
        failing: N
        report: migration/equivalency_report_1.md
    status: "passing" | "failing" | "complete"
```

Set `status: complete` only when `checks_failing == 0`.

### Step 6: Output results

If `checks_failing == 0`:
```
All equivalency checks PASS (N/N objects)
Cutover is now unblocked.
/wire:cutover-generate $ARGUMENTS
```

If `checks_failing > 0`:
```
Equivalency checks: N passing, N failing

Top failures:
[List top 5 failing objects with check type and detail]

To investigate a specific failure:
/wire:equivalency-investigate $ARGUMENTS --object <table_or_model>

To apply a fix and re-run affected checks:
/wire:equivalency-fix $ARGUMENTS --object <name> --approach <description>

Re-run all checks after fixes:
/wire:equivalency-validate $ARGUMENTS
```

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
