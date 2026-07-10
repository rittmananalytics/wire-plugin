---
description: Generate Metabase migration runbook — translate card SQL, remap permission groups, two-stage connection repoint
argument-hint: <release-folder>
---

# Generate Metabase migration runbook — translate card SQL, remap permission groups, two-stage connection repoint

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
description: Generate the Metabase reporting-layer migration runbook — translate card SQL to the target dialect, remap permission groups, validate on a decoy collection/connection, two-stage connection repoint with per-stage rollback
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_migration` and `artifact_file_path: migration/metabase_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before modifying any Metabase configuration, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source warehouse ([source_platform]): READ ONLY.
  Do NOT delete or repoint the production database connection during the
  migration phase. The existing Snowflake connection stays live as the
  rollback path until cutover.

Validation runs against a DECOY collection and a NON-PRODUCTION database
  connection only. Production cards, dashboards, and their consumers are
  never touched during validation.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not point any connection at these):
  [list each production project ID]
```

If any action would repoint or delete the production database connection outside the cutover sequence, or run validation against production cards, stop and report the conflict before proceeding.

---

# Metabase Migration — Generate

## Purpose

Generates the runbook for migrating the client's Metabase reporting layer from the source warehouse (Snowflake) to the target (BigQuery). The pivot is the **Metabase database connection** — cards follow the connection they reference, so the migration adds a target BigQuery connection, translates native-SQL cards to the target dialect, remaps permission groups, validates against a **decoy collection and non-production connection**, and cuts over by repointing the database connection in **two stages with per-stage rollback**.

This is a **reporting-layer** migration, the Metabase counterpart to reverse ETL migration. It is **not gated by `migration.scope`** — it runs for any migration where the client uses Metabase.

## Cannot proceed without a client-supplied query inventory

This command **requires a client-supplied Metabase query inventory** — the set of cards and their SQL the client confirms as in scope (the audit's catalog, validated and signed off, or a client export). Card SQL drives translation and validation, and inferring it is not safe enough to migrate against. If no client-supplied inventory is available, **stop**:

```
Metabase migration cannot proceed without a client-supplied query inventory.

Provide the confirmed card/SQL inventory (the approved metabase_audit catalog,
or a client export at migration/metabase_query_inventory.csv) and re-run:
/wire:metabase-migration-generate $ARGUMENTS
```

## Prerequisites

- `target_setup review: approved` — target warehouse objects exist
- `metabase_audit review: approved`
- A client-supplied query inventory is present (see above) — hard requirement
- `dbt_migration: complete` for any batch containing models referenced by in-scope cards (cannot validate those cards until their models exist on target)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`
- `.wire/releases/$ARGUMENTS/migration/metabase_query_inventory.csv` (or the approved audit catalog) — the client-supplied inventory
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/status.md`
- Canonical platform pair files at `wire/platform_pairs/<source>_to_<target>/` (translation guide, type mapping)

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved` and `metabase_audit review: approved`. Confirm the client-supplied query inventory is present — if not, stop with the message above. If `dbt_migration` exists, confirm which batches are complete and which cards are thereby unblocked.

Activate the `metabase` skill for connection details and the object hierarchy.

### Step 2: Build the additive target connection and decoy environment

The production database connection is not touched during the migration phase. Work additively:

1. **Add a target BigQuery database connection** in Metabase alongside the existing Snowflake connection (`POST /api/database` or via the CLI). This is additive — the Snowflake connection stays in place.
2. **Create a throwaway decoy collection** to hold test copies of in-scope cards. Production cards and dashboards are left untouched.
3. **Use a non-production database connection for validation** — the test copies in the decoy collection run against the target BigQuery connection scoped to non-production data. No production card is repointed to validate.

### Step 3: Translate cards by approach

Load in-scope cards from the client inventory and group by approach (from the audit). Process `repoint` first, then `rewrite_sql`, then `rebuild`.

- **repoint** — MBQL cards and portable-SQL cards: no SQL change; they resolve against the target connection once it is the card's database. Verify the card returns rows on the target connection; if a `repoint` card fails, downgrade it to `rewrite_sql`.
- **rewrite_sql** — translate the card's `dataset_query.native.query` from the source dialect to **BigQuery** using the platform-pair guide (`wire/platform_pairs/snowflake_to_bigquery/translation_guide.md`) and the §-level reference for gotchas. Test the translated SQL against the target connection — row count and result shape match the source card output against a frozen baseline. Record a before/after SQL diff in the runbook.
- **rebuild** — cards depending on a source-only construct are rebuilt against the target connection; capture the original definition first.

Make the test copies (in the decoy collection) point at the target BigQuery connection; leave production cards on Snowflake until cutover.

### Step 4: Remap permission groups

From the audit's permission group inventory, map each group's data permissions onto the target BigQuery connection and the migrated collections. Produce a permission-group remap table:

```
group_name, source_db_permission, target_db_permission, collection_permissions, notes
```

Apply the remap via the permission graph (`PUT /api/permissions/graph`) at cutover, not during the migration phase. Record the before/after graph so it can be reverted.

### Step 5: Validate on the decoy collection against a frozen baseline

Validate the test copies in the decoy collection only — never production cards. Compare against a **frozen source baseline** (not moving production), per the migration strategy's equivalency section. Per in-scope card:

1. **Result comparison** — run the test card on the target BigQuery connection and compare row count, key columns, and aggregates against the frozen source baseline result.
2. **Dashboard spot-check** — for dashboards built from migrated cards, confirm the decoy copies render with matching values.

No production card or dashboard is repointed to validate.

### Step 6: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/metabase_migration_runbook.md`

Structure:
1. Topology and rationale (additive target connection + decoy collection; connection is the cutover pivot)
2. Build steps (add target BigQuery connection, create decoy collection, copy test cards)
3. Pre-flight checklist (target objects exist, dbt batches complete, client inventory present, source baseline frozen, decoy collection + non-production connection in place)
4. Per-card translation — repoint / rewrite_sql (with SQL diff) / rebuild (with rebuild plan)
5. **Permission group remap table** (source → target permissions per group)
6. Decoy mapping (production card → test copy in decoy collection; production connection → target connection)
7. Validation procedure — result comparison vs frozen baseline on the decoy collection only
8. **Two-stage cutover sequence with per-stage rollback**:
   - **Stage 1 — pilot repoint.** Repoint a pilot subset of cards (or a pilot connection) from Snowflake to BigQuery, or promote the validated test cards. Validate the pilot on real (non-decoy) consumers. **Rollback:** repoint the pilot back to the Snowflake connection (`PUT /api/database/:id` with the original engine + details), restore any rewritten card SQL from the saved diffs.
   - **Stage 2 — full connection repoint.** Repoint the production Metabase database connection from Snowflake to BigQuery (`PUT /api/database/:id`), so all remaining cards/dashboards resolve against the target. Apply the permission-group remap. **Rollback:** repoint the production connection back to Snowflake details and revert the permission graph to the saved before-state.
9. Rollback procedures consolidated per stage, with the exact connection details and permission graph needed to revert each.

The production Snowflake connection stays live and untouched until Stage 1, and remains the rollback path through Stage 2.

### Step 7: Update status

```yaml
artifacts:
  metabase_migration:
    generate: complete
    file: migration/metabase_migration_runbook.md
    generated_date: "{{TODAY}}"
    repoint_count: N
    rewrite_sql_count: N
    rebuild_count: N
    permission_groups_remapped: N
    decoy_collection: "{{DECOY_COLLECTION_NAME}}"
    query_inventory_source: "approved_audit" | "client_export"
```

### Step 8: Output next command

```
/wire:metabase-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/metabase_migration_runbook.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact_id, `Metabase Migration` as artifact_name, and the `file` value from `artifacts.metabase_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_migration` as artifact, `generate` as action.

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
