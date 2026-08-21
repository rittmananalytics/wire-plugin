---
description: Validate ingestion audit completeness and migration flags
argument-hint: <release-folder>
---

# Validate ingestion audit completeness and migration flags

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
description: Validate ingestion audit completeness and migration flags
---

# Ingestion Audit — Validate

## Purpose

Checks the ingestion audit for completeness, flag consistency, and that every connector has been assigned a complexity rating and a migration decision. Produces a PASS/FAIL report with specific gaps to address before the audit can proceed to review.

## Prerequisites

- `audit/ingestion_audit.md` exists (ingestion_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/ingestion_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, By-service-type, Migration flags, Recommended order).

### Step 2: Run validation checks

## Validation Checks

**Check 1 — All connectors have a complexity rating**
Every row in the connector table has a value in the `complexity` column (Low / Medium / High).
PASS: All rows populated.
FAIL: List rows missing complexity.

**Check 2 — All connectors have a migration decision**
Every connector has `include_in_migration: true` or `include_in_migration: false` (not blank or "TBD").
PASS: All decisions populated.
FAIL: List connectors missing a decision.

**Check 3 — Broken connectors are addressed**
Any connector with `status: broken` has `migration_notes` explaining whether it will be repaired before migration or excluded.
PASS: All broken connectors have a note.
FAIL: List broken connectors without notes.

**Check 4 — Column exclusions flagged**
If `fivetran_column_selections.csv` was loaded, every connector with exclusions has a note in the audit.
PASS: Exclusions accounted for.
FAIL: List connectors with exclusions not noted in the audit.

**Check 5 — Row volume estimates present**
At least 80% of connectors have a non-null `row_count_estimate`. (Exact counts are not required — an order-of-magnitude estimate suffices.)
PASS: ≥80% populated.
FAIL: Report percentage populated and list connectors missing estimates.

**Check 6 — Recommended migration order is logical**
Low-complexity connectors appear before High-complexity in the recommended order. Any High-complexity connector appearing before a Low one must have a written justification.
PASS: Order is consistent with complexity ratings.
FAIL: List out-of-order entries.

**Check 7 — Connector count matches source**
If data source was Fivetran MCP: the count in `status.md` (`connector_count`) matches the rows in the audit table.
If data source was CSV: the count matches the CSV row count (excluding header).
PASS: Counts match.
FAIL: Report discrepancy.

### Step 3: Write validation report

Append a `## Validation` section to `audit/ingestion_audit.md`:

```markdown
## Validation

**Run date**: {{TODAY}}
**Overall result**: PASS | FAIL

| Check | Result | Detail |
|-------|--------|--------|
| 1. Complexity ratings complete | PASS/FAIL | ... |
| 2. Migration decisions complete | PASS/FAIL | ... |
| 3. Broken connectors addressed | PASS/FAIL | ... |
| 4. Column exclusions flagged | PASS/FAIL | ... |
| 5. Row volume estimates present | PASS/FAIL | ... |
| 6. Migration order logical | PASS/FAIL | ... |
| 7. Connector count matches source | PASS/FAIL | ... |

### Gaps to address
[List any FAIL items with specific connectors/rows to fix]
```

### Step 4: Update status

```yaml
artifacts:
  ingestion_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:ingestion-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:ingestion-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_audit` as artifact_id, `Ingestion Audit` as artifact_name, and the `file` value from `artifacts.ingestion_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_audit` as artifact, `validate` as action.

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
