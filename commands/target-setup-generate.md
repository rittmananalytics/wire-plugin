---
description: Generate target warehouse DDL scripts (SAFETY GATE)
argument-hint: <release-folder>
---

# Generate target warehouse DDL scripts (SAFETY GATE)

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
description: Generate target warehouse DDL scripts (SAFETY GATE — writes to target platform)
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: target_setup` and `artifact_file_path: migration/target_setup_scripts/MANIFEST.md` before proceeding.

---

# Target Setup — Generate

## Purpose

Generates the DDL scripts required to create all databases, schemas, tables, views, roles, and policies on the target platform. The scripts are written to disk for review before any are executed. This command produces scripts only — it does not execute them.

## Prerequisites

- `migration/migration_strategy.md` with `review: approved`
- Target platform credentials available (or scripts will be generated for manual execution)

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/audit/db_object_audit.md`
- `.wire/releases/$ARGUMENTS/audit/security_audit.md`
- Platform pair type mapping: `wire/platform_pairs/{pair}/type_mapping.md`

## Workflow

### Step 0: Pre-generation permissions and connectivity check

Run these checks before generating any scripts. A runbook that will fail on first execution wastes the review gate.

**Step 0.1: Read target platform from status.md**

Read `migration.target_platform`, `migration.target_project` (BigQuery) or `migration.target_account` (Snowflake), and `migration.service_account_key_path` (BigQuery) from status.md.

**Step 0.2: Check service account key file (BigQuery only)**

If `target_platform` is `bigquery` and `service_account_key_path` is set:

```bash
ls "[service_account_key_path]" 2>/dev/null && echo "KEY_FOUND" || echo "KEY_MISSING"
```

If `KEY_MISSING`:
```
❌ Pre-flight failed: service account key file not found at [service_account_key_path]
   Update migration.service_account_key_path in status.md with the correct path and re-run.
```
Stop.

**Step 0.3: BigQuery MCP probe (BigQuery target only)**

If the BigQuery MCP server is connected, run:

```
mcp__claude_ai_BigQuery_MCP__list_dataset_ids:
  project_id: "[target_project]"
```

Interpret the result:
- **Success** — the target project is reachable and the credential has at least `bigquery.datasets.list`. Record: `✓ Target project [target_project] is accessible.`
- **Permission denied / 403** — the credential lacks the required permissions. Output:
  ```
  ❌ Pre-flight failed: cannot list datasets in [target_project].
     Required permission: bigquery.datasets.create (and bigquery.tables.create).
     Grant the service account the BigQuery Data Editor role on [target_project] and re-run.
  ```
  Stop.
- **Project not found / 404** — Output:
  ```
  ❌ Pre-flight failed: project [target_project] not found or not accessible.
     Check that migration.target_project in status.md is correct and that the
     service account belongs to (or has been granted access to) that project.
  ```
  Stop.

**Step 0.4: BigQuery MCP unavailable**

If the BigQuery MCP server is not connected, do not block progress. Instead:

1. Output a warning:
   ```
   ⚠️  BigQuery MCP not connected — skipping automated permission check.
       Add a manual pre-flight check to the generated runbook (Step 0 below).
   ```
2. Add the following section as **Step 0: Pre-flight manual check** at the top of the generated `MANIFEST.md`:
   ```markdown
   ## Step 0: Pre-flight checklist (run before executing any scripts)

   Before running any DDL scripts, verify the following manually:

   - [ ] Service account key exists at: [service_account_key_path]
   - [ ] Service account has BigQuery Data Editor role on project: [target_project]
   - [ ] Target project [target_project] exists and is accessible
   - [ ] `gcloud auth activate-service-account --key-file=[service_account_key_path]`
   - [ ] `bq ls --project_id=[target_project]` returns without error
   ```

**Step 0.5: Snowflake target**

If `target_platform` is `snowflake`, skip steps 0.2–0.4. Snowflake connectivity is verified when the consultant first runs a query via the Snowflake MCP. Add a manual pre-flight note to the MANIFEST.md advising the consultant to confirm their Snowflake role has `CREATE SCHEMA` and `CREATE TABLE` on the target database.

### Step 1: Confirm prerequisites

1. Confirm `migration_strategy review: approved` in status.md. If not, stop with message.
2. Read source and target platforms from status.md.
3. If target setup scripts already exist in `migration/target_setup_scripts/`, ask whether to regenerate.

### Step 2: Generate schema DDL

For each database/schema in the db_object audit with `migration_approach` of `recreate_ddl` or `translate_view`:

- Generate `CREATE DATABASE IF NOT EXISTS` (Snowflake) or `CREATE SCHEMA IF NOT EXISTS` (BigQuery) statements
- Apply naming conventions consistent with target platform (snake_case for BQ datasets, etc.)
- Include `COMMENT` clauses where source had descriptions

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/01_schemas.sql`

### Step 3: Generate table DDL

For each table with `migration_approach: recreate_ddl`:

- Translate column types using the type mapping file
- Apply partitioning/clustering equivalents per the migration strategy
- Generate `CREATE TABLE IF NOT EXISTS` with full column definitions
- Include `COMMENT ON TABLE` and `COMMENT ON COLUMN` statements

For tables with incompatible types (flagged `evaluate` in the type mapping), insert a `-- TODO: manual review required` comment in the DDL.

**Automated first pass (snowflake → bigquery only)**: when the target is BigQuery and the migration strategy elects to use it, run the source DDL through the BigQuery Migration Service as a first pass, then reconcile against `type_mapping.md` before writing the final scripts. See `wire/platform_pairs/snowflake_to_bigquery/bqms_first_pass.md`. BQMS gets the bulk of the column/type translation right; the type mapping catches the lossless-conversion flags (e.g. `NUMBER` precision, `VARIANT` → `JSON` vs `STRING`) and partition/cluster carry-over. Read its translation report — every warning is a candidate `-- TODO: manual review required`. Do not skip the reconciliation: BQMS output is a draft, not the final DDL.

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/02_tables.sql`

### Step 4: Generate view DDL (stubs)

For each view with `migration_approach: translate_view`:

- Generate a stub `CREATE VIEW` with the original SQL as a comment
- Add a `-- TODO: translate using dbt-migration or manual review` marker
- The actual view translation happens during dbt migration or manual translation

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/03_views_stub.sql`

### Step 5: Generate role and permission DDL

Based on the security audit:

- `GRANT` statements for each role on each schema/table
- Row-level security policy creation
- Column masking policy creation (where directly translatable)
- Service account permissions

Write to: `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql`

### Step 6: Generate execution manifest

Write a manifest file listing all scripts with descriptions and recommended execution order:

`.wire/releases/$ARGUMENTS/migration/target_setup_scripts/MANIFEST.md`

### Step 7: Update status

```yaml
artifacts:
  target_setup:
    generate: complete
    file: migration/target_setup_scripts/MANIFEST.md
    generated_date: "{{TODAY}}"
    scripts_count: N
    tables_in_ddl: N
```

### Step 8: Emit dbt profiles.yml block

Read the following fields from status.md:

| status.md field | profiles.yml key |
|-----------------|-----------------|
| `migration.target_platform` | type (bigquery / snowflake) |
| `migration.target_project` (BigQuery) or `migration.target_account` (Snowflake) | project / account |
| `migration.target_dataset` (BigQuery) or `migration.target_database` + `migration.target_schema` (Snowflake) | dataset / database + schema |
| `migration.target_location` (BigQuery, default: `EU`) | location |
| `migration.service_account_key_path` (BigQuery) or `migration.snowflake_user` + `migration.snowflake_private_key_path` (Snowflake) | keyfile / user + private_key_path |

If `target_platform` is `bigquery`, emit:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add this to ~/.dbt/profiles.yml to connect to the target BigQuery environment:

[profile_name]:
  target: bigquery
  outputs:
    bigquery:
      type: bigquery
      method: service-account
      project: [target_project]
      dataset: [target_dataset]
      location: [target_location, default EU]
      keyfile: [service_account_key_path]
      threads: 4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Where `[profile_name]` is the engagement_name from status.md with `_target` appended (e.g. `carwow_target`).

If `target_platform` is `snowflake`, emit the equivalent Snowflake block using `method: private-key` or `method: password` depending on which credentials are present in status.md.

If any required field is missing from status.md, emit a placeholder (`[FILL IN: ...]`) rather than omitting the block. This ensures the consultant has a complete template to fill in rather than having to construct the format from scratch.

Do not write this block to the file system — output it to the console only.

### Step 9: Output summary and safety reminder

```
Target setup scripts generated. These scripts have NOT been executed.

Scripts written to: .wire/releases/$ARGUMENTS/migration/target_setup_scripts/

Review the scripts carefully before the review step. The review gate requires
explicit approval before any script is executed against the target platform.

/wire:target-setup-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/01_schemas.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/02_tables.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/03_views_stub.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql`
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/MANIFEST.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `target_setup` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `target_setup` as artifact_id, `Target Setup` as artifact_name, and the `file` value from `artifacts.target_setup` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `target_setup` as artifact, `generate` as action.

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
