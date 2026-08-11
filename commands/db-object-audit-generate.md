---
description: Enumerate all databases, schemas, tables, views on source platform
argument-hint: <release-folder>
---

# Enumerate all databases, schemas, tables, views on source platform

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
description: Enumerate all databases, schemas, tables, views on source platform
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: db_object_audit` and `artifact_file_path: audit/db_object_audit.md` before proceeding.

---

# DB Object Audit — Generate

## Purpose

Catalogs every database object on the source platform — databases, schemas, tables, views, materialized views, external tables, and stored procedures. Classifies each object by type, owner, row volume tier, and migration approach. The output feeds into the migration inventory and target setup DDL generation.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- Source platform credentials or MCP server access configured
- For Snowflake: the Snowflake MCP server (`mcp__claude_ai_Snowflake__sql_exec`) connected and reachable — verify with `/mcp` before starting

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — source platform (`bigquery` or `snowflake`)
- Source platform MCP or direct SQL access

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration`. Read `migration.source_platform`.

If the audit file already exists at `audit/db_object_audit.md`, ask whether to re-generate or update.

### Step 2: Query source platform object catalog

**If source is BigQuery**:

```sql
-- All tables and views across all datasets
SELECT
  table_catalog AS project,
  table_schema AS dataset,
  table_name,
  table_type,
  row_count,
  size_bytes,
  creation_time,
  last_modified_time,
  ddl
FROM `region-us`.INFORMATION_SCHEMA.TABLES
ORDER BY table_catalog, table_schema, table_name;
```

Also query:
- `INFORMATION_SCHEMA.ROUTINES` for stored procedures and UDFs
- `INFORMATION_SCHEMA.VIEWS` for view definitions
- `INFORMATION_SCHEMA.PARTITIONS` to identify partitioned tables

**If source is Snowflake**:

All queries below run via `mcp__claude_ai_Snowflake__sql_exec`. `ACCOUNT_USAGE` has up to 45-minute latency — use it for full-estate counts. Use `INFORMATION_SCHEMA` for precise, real-time DDL on specific objects. Always pair `LIMIT` with `ORDER BY` on `ACCOUNT_USAGE` queries.

```sql
-- All tables, views, materialized views, external tables
SELECT
  TABLE_CATALOG,
  TABLE_SCHEMA,
  TABLE_NAME,
  TABLE_TYPE,
  ROW_COUNT,
  BYTES,
  CREATED,
  LAST_ALTERED,
  COMMENT
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
WHERE DELETED IS NULL
ORDER BY TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME;
```

```sql
-- Stored procedures
SELECT
  PROCEDURE_CATALOG,
  PROCEDURE_SCHEMA,
  PROCEDURE_NAME,
  ARGUMENT_SIGNATURE,
  PROCEDURE_LANGUAGE,
  PROCEDURE_DEFINITION,
  CREATED,
  LAST_ALTERED
FROM SNOWFLAKE.ACCOUNT_USAGE.PROCEDURES
WHERE DELETED IS NULL
ORDER BY PROCEDURE_CATALOG, PROCEDURE_SCHEMA, PROCEDURE_NAME;
```

```sql
-- UDFs and UDTFs
SELECT
  FUNCTION_CATALOG,
  FUNCTION_SCHEMA,
  FUNCTION_NAME,
  ARGUMENT_SIGNATURE,
  DATA_TYPE AS RETURN_TYPE,
  FUNCTION_LANGUAGE,
  FUNCTION_DEFINITION,
  IS_TABLE_FUNCTION,
  CREATED,
  LAST_ALTERED
FROM SNOWFLAKE.ACCOUNT_USAGE.FUNCTIONS
WHERE DELETED IS NULL
ORDER BY FUNCTION_CATALOG, FUNCTION_SCHEMA, FUNCTION_NAME;
```

```sql
-- Stages (internal, named external, user)
SELECT
  STAGE_CATALOG,
  STAGE_SCHEMA,
  STAGE_NAME,
  STAGE_URL,
  STAGE_REGION,
  STAGE_TYPE,
  CREATED,
  LAST_ALTERED,
  COMMENT
FROM SNOWFLAKE.ACCOUNT_USAGE.STAGES
WHERE DELETED IS NULL
ORDER BY STAGE_CATALOG, STAGE_SCHEMA, STAGE_NAME;
```

```sql
-- Dynamic tables (incremental refresh, no direct BigQuery equivalent)
SELECT
  NAME,
  DATABASE_NAME,
  SCHEMA_NAME,
  TARGET_LAG,
  SCHEDULING_STATE,
  REFRESH_MODE,
  ROWS,
  BYTES,
  CREATED,
  LAST_ALTERED
FROM SNOWFLAKE.ACCOUNT_USAGE.DYNAMIC_TABLES
WHERE DELETED IS NULL
ORDER BY DATABASE_NAME, SCHEMA_NAME, NAME;
```

```sql
-- Streams (CDC changelog — no direct BigQuery equivalent)
SELECT
  STREAM_NAME,
  STREAM_SCHEMA_NAME,
  STREAM_DATABASE_NAME,
  TABLE_NAME,
  STALE,
  MODE,
  STALE_AFTER,
  CREATED
FROM SNOWFLAKE.ACCOUNT_USAGE.STREAMS
WHERE DELETED IS NULL
ORDER BY STREAM_DATABASE_NAME, STREAM_SCHEMA_NAME, STREAM_NAME;
```

```sql
-- Tasks (scheduled SQL / stored procedure calls — replace with Cloud Scheduler / Airflow on target)
SELECT
  NAME,
  DATABASE_NAME,
  SCHEMA_NAME,
  SCHEDULE,
  STATE,
  DEFINITION,
  CONDITION,
  LAST_COMMITTED_ON,
  LAST_SUSPENDED_ON
FROM SNOWFLAKE.ACCOUNT_USAGE.TASKS
WHERE DELETED IS NULL
ORDER BY DATABASE_NAME, SCHEMA_NAME, NAME;
```

```sql
-- Pipes (Snowpipe continuous ingest — replace with target-platform streaming ingestion)
SELECT
  PIPE_CATALOG,
  PIPE_SCHEMA,
  PIPE_NAME,
  DEFINITION,
  CREATED,
  LAST_ALTERED
FROM SNOWFLAKE.ACCOUNT_USAGE.PIPES
WHERE DELETED IS NULL
ORDER BY PIPE_CATALOG, PIPE_SCHEMA, PIPE_NAME;
```

```sql
-- Row access policies (security — must be recreated on target)
SELECT
  POLICY_CATALOG,
  POLICY_SCHEMA,
  POLICY_NAME,
  POLICY_BODY,
  CREATED,
  LAST_ALTERED
FROM SNOWFLAKE.ACCOUNT_USAGE.ROW_ACCESS_POLICIES
WHERE DELETED IS NULL;
```

```sql
-- Masking policies (column-level security — must be recreated on target)
SELECT
  POLICY_CATALOG,
  POLICY_SCHEMA,
  POLICY_NAME,
  POLICY_BODY,
  CREATED,
  LAST_ALTERED
FROM SNOWFLAKE.ACCOUNT_USAGE.MASKING_POLICIES
WHERE DELETED IS NULL;
```

```sql
-- Outbound data shares (note: cannot be migrated — must be rebuilt on target)
SHOW SHARES;
```

For each view and stored procedure, retrieve the full DDL via `INFORMATION_SCHEMA` (lower latency than `ACCOUNT_USAGE`):

```sql
SELECT GET_DDL('VIEW', 'my_db.my_schema.my_view');
SELECT GET_DDL('PROCEDURE', 'my_db.my_schema.my_proc(NUMBER, VARCHAR)');
SELECT GET_DDL('FUNCTION', 'my_db.my_schema.my_udf(VARCHAR)');
```

To identify semantic views (Cortex Analyst layer — if present, these require special handling):

```sql
SHOW SEMANTIC VIEWS IN DATABASE my_db;
```

If any semantic views are found, tag them as a separate object type (`semantic_view`) in the audit. The semantic layer definition must be re-authored on the target platform — it cannot be translated directly.

### Step 3: Classify each object

For each object, assign:

**Object type classification**:
- `table` — standard managed table
- `view` — non-materialised view
- `materialized_view` — materialised/precomputed view
- `external_table` — table backed by external storage
- `udf` — user-defined function (scalar or table-valued)
- `stored_procedure` — stored procedure
- `stage` — Snowflake internal or external stage (no direct target equivalent)
- `dynamic_table` — Snowflake incremental refresh table (no direct BigQuery equivalent; evaluate per case)
- `stream` — Snowflake CDC stream (replace with target streaming ingestion)
- `task` — Snowflake scheduled SQL/procedure (replace with Airflow, Cloud Scheduler, or dbt Cloud)
- `pipe` — Snowpipe continuous ingest definition (replace with target ingestion service)
- `semantic_view` — Cortex Analyst semantic layer view (must be re-authored on target; not translatable)
- `row_access_policy` — row-level security policy (must be recreated on target)
- `masking_policy` — column-level masking policy (must be recreated on target)
- `share` — outbound Snowflake data share (cannot be migrated; note for stakeholder decision)

**Row volume tier**:
- `xs` — <1M rows
- `s` — 1M–100M rows
- `m` — 100M–1B rows
- `l` — 1B–10B rows
- `xl` — >10B rows

**Migration approach**:
- `recreate_ddl` — re-create DDL on target, load data via Fivetran or COPY
- `translate_view` — translate view SQL to target dialect
- `evaluate` — requires manual assessment before a migration approach can be assigned; applies to: external tables, UDFs, stored procedures, dynamic tables, streams, tasks, pipes, semantic views, masking/row-access policies, shares
- `exclude` — staging/temp tables, scratch schemas, system objects, transient tables used only for intermediate processing

Default approach by Snowflake object type when source is Snowflake:

| Object type | Default approach | Notes |
|---|---|---|
| `table` | `recreate_ddl` | Standard tables; data load via Fivetran or COPY |
| `view` | `translate_view` | SQL requires dialect translation |
| `materialized_view` | `evaluate` | Target-platform MV capabilities differ |
| `external_table` | `evaluate` | Stage location, format, and IAM must be assessed |
| `udf` | `evaluate` | Language-specific (JS/Python/Java/SQL); assess portability |
| `stored_procedure` | `evaluate` | High complexity; often needs rewrite |
| `stage` | `evaluate` | Cloud storage paths and credentials need remapping |
| `dynamic_table` | `evaluate` | No direct BigQuery equivalent; consider dbt incremental |
| `stream` | `evaluate` | Replace with target CDC service |
| `task` | `evaluate` | Replace with Airflow/Cloud Scheduler DAGs |
| `pipe` | `evaluate` | Replace with target ingestion connector |
| `semantic_view` | `evaluate` | Must be re-authored as BigQuery/Looker semantic layer |
| `row_access_policy` | `evaluate` | Translate to BigQuery row-level security or equivalent |
| `masking_policy` | `evaluate` | Translate to BigQuery policy tags or equivalent |
| `share` | `evaluate` | Snowflake-specific; stakeholder decision required |

### Step 4: Identify platform-specific features requiring translation

For each view and procedure, scan the definition for features that require dialect translation. Load the feature detection file for the source platform:

- BigQuery source: read `wire/platform_pairs/bigquery_to_snowflake/feature_detection.md`
- Snowflake source: read `wire/platform_pairs/snowflake_to_bigquery/feature_detection.md`

Tag each object with the features detected. These tags drive complexity scoring in the dbt audit and migration strategy.

### Step 5: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/db_object_audit.md`

Use the template at `TEMPLATES/migration/db_object_audit.md`. Include:
- Summary counts by object type and volume tier
- Full object catalog table
- Platform-specific feature tags
- Objects flagged as `evaluate` or `exclude` with reasons
- Schema/database inventory (distinct list)

### Step 6: Update status

```yaml
artifacts:
  db_object_audit:
    generate: complete
    file: audit/db_object_audit.md
    generated_date: "{{TODAY}}"
    total_objects: N
    tables: N
    views: N
    materialized_views: N
    external_tables: N
    dynamic_tables: N     # Snowflake only
    streams: N            # Snowflake only
    tasks: N              # Snowflake only
    pipes: N              # Snowflake only
    semantic_views: N     # Snowflake only
    udfs: N
    stored_procedures: N
    stages: N             # Snowflake only
    security_policies: N  # Snowflake row access + masking policies
    shares: N             # Snowflake only
    evaluate_count: N
    exclude_count: N
```

### Step 7: Output summary

Print: total objects cataloged, breakdown by type, count flagged for evaluation or exclusion, and next command:

```
/wire:db-object-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/db_object_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `db_object_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `db_object_audit` as artifact_id, `DB Object Audit` as artifact_name, and the `file` value from `artifacts.db_object_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `db_object_audit` as artifact, `generate` as action.

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
