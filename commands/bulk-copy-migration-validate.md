---
description: Validate bulk copy runbook — tenant guard, two-stage gate, scoped service account
argument-hint: <release-folder> [--wave id]
---

# Validate bulk copy runbook — tenant guard, two-stage gate, scoped service account

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
description: Validate bulk copy migration runbook — tenant guard, two-stage gate, scoped service account
argument-hint: <release-folder> [--wave id]
---

# Bulk Copy Migration — Validate

## Flags

- `--wave <id>` — validate the wave-labelled runbook (`bulk_copy_migration_runbook_{wave_id}.md`) against the tables `migration/migration_batching.csv` assigns to this wave, resolved identically to `bulk-copy-migration-generate`'s Step 1w. Every check below reads "in-scope table" as this resolved set instead of every landed table for `include_in_migration: true` connectors.
- `--snapshots` — validate the snapshots-labelled runbook (`bulk_copy_migration_runbook_snapshots.md`) produced by `bulk-copy-migration-generate --snapshots`. Only the snapshot-history-copy checks apply: run **Check 9** over the resolved `copy_and_continue` snapshot set and skip the raw-table checks (Checks 1–2, 4). This is the retrofit companion for a full-migration snapshot-history copy. Standalone scope — abort if combined with `--wave`.

## Validation Checks

Read `status.md` to confirm the run's `method: runbook` and its guard path. Read the bulk copy runbook (wave-labelled under `--wave`, snapshots-labelled under `--snapshots`) and `audit/ingestion_audit.md`.

**Scope guard the checks match.** Determine the runbook's copy path from `status.md` (`artifacts.bulk_copy_migration.scope` / `copy_path`) and validate accordingly:

- **Raw-table / connector copy (carve-out):** `migration.scope == tenant_carveout` and `migration.tenant_predicate` is set. All checks below apply, including the tenant guard (Check 3). This is the existing behaviour.
- **Snapshot-history copy in a full migration (`--snapshots`):** `migration.scope` is `full_migration` or absent, the runbook copies snapshot histories only, and there is **no** tenant predicate. Check 3 (tenant guard on every extract) does **not** apply — the copy is unfiltered by design; note it "not applicable — unfiltered full-migration snapshot copy" rather than failing. Check 9's tenant-predicate sub-clause (d) likewise does not apply in this path. The raw-table checks (Checks 1, 2, 4) are skipped (no raw tables in this runbook).

A `full_migration` runbook that copies **raw/connector tables** is a FAIL — bulk-copy of raw tables is carve-out-only (raw tables re-land via `/wire:ingestion-migration-generate`).

**Check 1 — All in-scope tables in the runbook**
The count of tables in the runbook matches the count of in-scope landed tables (the wave-resolved set under `--wave`, otherwise every landed table for connectors with `include_in_migration: true`) in the ingestion audit.
PASS/FAIL with missing tables listed.

**Check 2 — Each table has a source→target destination mapping**
Every table step names the source Snowflake object and its target BigQuery dataset/table.
PASS/FAIL with gaps.

**Check 3 — Tenant guard on every extract** (carve-out path only)
Every source extract step includes `WHERE {migration.tenant_predicate}`, matching `migration.tenant_predicate` exactly. No step extracts unfiltered data.
PASS: predicate present and matching on all steps.
FAIL: any step missing the predicate or using a different predicate.
**Not applicable to a full-migration snapshot-history copy** (`--snapshots`): that path is unfiltered by design — note "not applicable — unfiltered full-migration snapshot copy" rather than running the scan.

**Check 4 — Two-stage copy with validation gate**
Each table follows the pilot-partition → validation gate → remainder structure. The gate runs equivalency check 1 (row count) and check 6 (checksum), tenant-scoped, and Stage 2 is conditional on both passing.
PASS/FAIL with tables missing the gate.

**Check 5 — Scoped service account and tenant guard documented**
The runbook names a service account scoped to the extracted tenant's target project/dataset (and dedicated staging bucket for GCS-staged), and confirms the destination is `migration.target_project` and not in `data_safety.production_projects`.
PASS/FAIL.

**Check 6 — Credential rotation / staging checklist present**
The runbook includes a credential checklist (scoped SA key, GCS bucket access, target-only BigQuery grants).
PASS/FAIL.

**Check 7 — Source decommission deferred to cutover**
The runbook explicitly notes the source stays live and unmodified during the copy; decommission is deferred to the cutover phase.
PASS: note present.
FAIL: source decommission/deletion steps found in the copy runbook (should be in cutover).

**Check 8 — Post-copy validation steps present**
The runbook hands off to `/wire:equivalency-validate` for the full tenant-scoped seven-check pass once all tables are copied.
PASS/FAIL.

**Check 9 — Snapshot history copies preserve SCD state, ordinal order, and tenant scope**
If the migration register / `dbt_snapshots.csv` lists any `copy_and_continue` snapshots, the runbook has a copy step for each that: (a) lands at the snapshot's exact `target_schema` relation; (b) preserves the payload columns plus the four SCD meta columns (`dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to`) in their ordinal order (payload first, meta columns at the tail in that order), translating types via the pair's `type_mapping.md` / "Snapshot SCD mechanisms" section; (c) reads the source from the frozen clone at baseline `T`, not the live snapshot; (d) **under carve-out only**, applies `WHERE {migration.tenant_predicate}` to the snapshot extract (in a full migration the snapshot-history copy is unfiltered — sub-clause (d) does not apply); and (e) is ordered **before** the target `dbt snapshot` adopt-and-continue run, never after. Any `rebuild_from_T` snapshot is correctly **absent** from the copy runbook (it starts fresh at `T` on a recorded sign-off, so there is no history to copy).
PASS: every `copy_and_continue` snapshot has a conforming copy step and no `rebuild_from_T` snapshot is copied. FAIL: list snapshots with a missing/incomplete copy step, a dropped or reordered meta column, an unfrozen (live) source read, a missing tenant predicate, or a `rebuild_from_T` snapshot erroneously copied. Note "no snapshots in scope" when none apply.

### Update status

```yaml
artifacts:
  bulk_copy_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    snapshots_validate: pass | fail   # set only when run with --snapshots (Check 9 only)
    wave_validate:               # set only when run with --wave, keyed by wave id
      B01: pass | fail
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bulk_copy_migration` as artifact_id, `Bulk Copy Migration` as artifact_name, and the `file` value from `artifacts.bulk_copy_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bulk_copy_migration` as artifact, `validate` as action.

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
