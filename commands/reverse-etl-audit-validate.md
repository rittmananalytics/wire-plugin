---
description: Validate reverse ETL audit completeness and dependency mapping
argument-hint: <release-folder>
---

# Validate reverse ETL audit completeness and dependency mapping

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
description: Validate reverse ETL audit completeness, warehouse dependency coverage, and migration approach assignments
---

# Reverse ETL Audit — Validate

## Purpose

Checks the reverse ETL audit for completeness and internal consistency. Confirms every sync has a migration approach, all warehouse dependencies are mapped, Lightning engine requirements are flagged, and the sync count matches the source data. Produces a PASS/FAIL report with specific gaps to address before review.

## Prerequisites

- `audit/reverse_etl_audit.md` exists (reverse_etl_audit generate: complete)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load the audit

Read `audit/reverse_etl_audit.md`. Confirm it is non-empty and contains the expected sections (Summary, Sync Catalog, Warehouse Dependency Map, Lightning Engine Syncs, Excluded Syncs).

### Step 2: Run validation checks

**Check 1 — All syncs have a migration approach**
Every row in the sync catalog has a value in the `migration_approach` column (repoint / rewrite_model / rebuild / decommission).
PASS: All rows populated.
FAIL: List syncs missing a migration approach.

**Check 2 — All syncs have a complexity rating**
Every row has a value in the `complexity` column (Low / Medium / High).
PASS: All rows populated.
FAIL: List syncs missing complexity.

**Check 3 — Source objects resolved across all model types, coverage reported**
Source-object resolution is attempted for every model type (`rawSql`, `dbtModel`, `table`, `custom`) — not just `rawSql`. Each sync with a resolvable source has at least one entry in `warehouse_objects`; each sync that genuinely could not be resolved is marked `source_resolved: false` and listed explicitly under "Unresolved syncs". The audit reports the source-resolution coverage metric (`resolved_sync_count` / `active_sync_count`), and status.md carries `resolved_sync_count`, `unresolved_sync_count`, and `source_resolution_coverage_pct`.
PASS: Resolution attempted for all model types, coverage metric present, and every unresolved sync is listed (none silently blank).
FAIL: `table`/`custom` syncs left blank without being listed as unresolved, or the coverage metric is missing.

**Check 4 — dbt model syncs cross-referenced**
Every sync with `model_type: dbtModel` has the dbt model name listed and a note confirming whether that model exists in the dbt audit (or noting it is out of scope).
PASS: All dbt model syncs have a cross-reference note.
FAIL: List dbt model syncs without cross-reference.

**Check 5 — Lightning engine syncs flagged**
If `lightning_sync_count` in status.md is > 0, the audit includes a Lightning Engine section listing the affected syncs and the two schema requirements.
PASS: Section present and populated, or lightning_sync_count = 0.
FAIL: Lightning syncs exist but section is missing or empty.

**Check 6 — Disabled/broken syncs have a decision**
If `data_source` in status.md is `hightouch_api` or `csv`: every sync with `status: disabled` or `status: interrupted` has either `migration_approach: decommission` with a reason, or `include_in_migration: true` with a note explaining why it will be migrated despite its current status.
PASS: All non-active syncs have a clear decision.
FAIL: List undecided non-active syncs.

If `data_source: git`: sync status is unavailable from Git files. Auto-pass this check and note in the validation report:
```
Check 6 skipped — audit sourced from Git files; runtime sync status not available.
Review sync decommission decisions manually with the client before proceeding to review.
```

**Check 7 — Sync count matches source**
The count of rows in the sync catalog matches `sync_count` in status.md.
PASS: Counts match.
FAIL: Report discrepancy.

**Check 8 — Row volume estimates present**
If `data_source` is `hightouch_api` or `csv`: at least 80% of active syncs have a non-null `last_run_rows`. Syncs with no run history should have a note.
PASS: ≥80% of active syncs have row volumes.
FAIL: Report percentage and list syncs missing estimates.

If `data_source: git`: row volumes are unavailable. Auto-pass this check and note in the validation report:
```
Check 8 skipped — audit sourced from Git files; runtime row volumes not available.
Row volume estimates are needed for cutover sequencing. Obtain these from the client
(Hightouch UI → sync run history) and add to the audit before migration inventory is drafted.
```

**Check 9 — `migration_approach` is inside the closed vocabulary (v3.11.7)**
Every row's `migration_approach` is one of exactly `repoint`, `rewrite_model`, `rebuild`, `decommission` (`specs/utils/reverse_etl_approach.md`). No blanks, no synonyms, no fifth value.
PASS: every row inside the set. FAIL: list each offending sync id with the value found, and the closed set.

This is a producer-side check because the vocabulary has already drifted once on the consumer side, silently. Two commands shipped keying on `retire`, a value this audit never writes, so on a release with 98 `decommission` syncs one command would have authored 98 unnecessary twins and the other would have listed none of them for retirement. Neither errored. Enforcing the set only in the consumers means each consumer discovers the drift independently, which is how one token became four commands' worth of the same bug. It is enforced here, where the value is written.

### Step 3: Write validation report

Append a `## Validation` section to `audit/reverse_etl_audit.md`:

```markdown
## Validation

**Run date**: {{TODAY}}
**Overall result**: PASS | FAIL

| Check | Result | Detail |
|-------|--------|--------|
| 1. Migration approaches complete | PASS/FAIL | ... |
| 2. Complexity ratings complete | PASS/FAIL | ... |
| 3. rawSql warehouse objects extracted | PASS/FAIL | ... |
| 4. dbt model syncs cross-referenced | PASS/FAIL | ... |
| 5. Lightning engine syncs flagged | PASS/FAIL | ... |
| 6. Non-active syncs have decisions | PASS/FAIL | ... |
| 7. Sync count matches source | PASS/FAIL | ... |
| 8. Row volume estimates present | PASS/FAIL | ... |

### Gaps to address
[List any FAIL items with specific syncs to fix]
```

### Step 4: Update status

```yaml
artifacts:
  reverse_etl_audit:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Step 5: Output next command

If PASS:
```
/wire:reverse-etl-audit-review $ARGUMENTS
```

If FAIL:
```
Validation failed. Address the gaps listed above, then re-run:
/wire:reverse-etl-audit-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_audit` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_audit` as artifact_id, `Reverse ETL Audit` as artifact_name, and the `file` value from `artifacts.reverse_etl_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_audit` as artifact, `validate` as action.

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
