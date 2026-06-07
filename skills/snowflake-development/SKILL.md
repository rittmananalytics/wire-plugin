---
name: snowflake-development
description: Proactive skill for working with Snowflake. Auto-activates when querying, designing, or auditing Snowflake objects, running migrations, assessing AI-readiness, or using the Snowflake MCP server. Covers SQL conventions, object management, performance patterns, dynamic tables, streams, tasks, and data quality assessment.
---

# Snowflake Development Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | snowflake-development | activated | Snowflake work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first. If no `.wire/` directory exists in the current repo, skip this step.

## Purpose

This skill activates when working directly with Snowflake — writing queries, designing objects, running audits, assessing data quality, or executing migration tasks. It standardises how we connect via the MCP server, enforces SQL conventions appropriate for Snowflake's dialect, and provides structured patterns for each major Snowflake capability.

For semantic view work specifically, see `skills/snowflake-semantic-views/SKILL.md`.

## When This Skill Activates

### User-Triggered

- "Query Snowflake for..."
- "Create a Snowflake table / view / stage / dynamic table / stream / task..."
- "Audit our Snowflake account..."
- "Run this SQL against Snowflake..."
- "Check AI-readiness of this Snowflake dataset..."
- "Assess data quality in Snowflake..."
- Working with `.sql` files that contain Snowflake-specific constructs (`VARIANT`, `LATERAL FLATTEN`, `QUALIFY`, `IFF`, `DYNAMIC TABLE`, `STREAM`, `TASK`, `COPY INTO`, `$stage_name`, `TRY_CAST`, `LISTAGG`, `WITHIN GROUP`)

### Self-Triggered (Proactive)

Activate BEFORE writing any Snowflake SQL when:
- The platform context is Snowflake (from `status.md`, environment config, or user statement)
- A `db_object_audit` or `target_setup` step targets Snowflake
- The dbt project adapter is `snowflake`
- You are about to execute queries against a Snowflake endpoint

---

## Instructions

### 0. Establish MCP Connection

The Snowflake MCP server is registered and available as `mcp__claude_ai_Snowflake__sql_exec`.

Before running any query:
1. Confirm the MCP tool is available in the current session
2. If not available, tell the user: "The Snowflake MCP server is not connected in this session. Please ensure it is added in Claude Code settings and run `/mcp` to verify."
3. If available, proceed — all SQL below runs via `mcp__claude_ai_Snowflake__sql_exec`

All `INFORMATION_SCHEMA` filters must use `UPPER(...)` on both sides to avoid case-sensitivity misses:

```sql
WHERE UPPER(table_schema) = UPPER('my_schema')
```

When querying `SNOWFLAKE.ACCOUNT_USAGE` views, always pair `LIMIT` with a stable `ORDER BY` to get deterministic results. `ACCOUNT_USAGE` has up to 45-minute latency — prefer `INFORMATION_SCHEMA` for real-time metadata.

---

### 1. Context Discovery

Run these orientation queries before substantive work on an unfamiliar account:

```sql
-- Current session context
SELECT CURRENT_ACCOUNT(), CURRENT_ROLE(), CURRENT_WAREHOUSE(),
       CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_USER();
```

```sql
-- Available databases
SHOW DATABASES;
```

```sql
-- Roles available to current user
SHOW ROLES;
```

If the wrong database/schema/role is active, ask the user to set the correct context before proceeding. Never assume default context is correct.

---

### 2. SQL Conventions for Snowflake

Follow these conventions when writing or reviewing Snowflake SQL.

**Dialect rules:**
- Use `IFF(cond, true_val, false_val)` instead of `IF(cond, true_val, false_val)` — Snowflake supports both but `IFF` is idiomatic
- Use `NVL(a, b)` or `COALESCE(a, b)` — both work; `COALESCE` is more portable
- Use `ZEROIFNULL(expr)` and `NULLIFZERO(expr)` for common numeric null patterns
- Use `TRY_CAST` / `TRY_TO_DATE` / `TRY_TO_TIMESTAMP` for safe type conversion — never let bad data crash a load
- Prefer `QUALIFY` for window function filtering rather than a wrapping subquery
- Use `LISTAGG(col, ',') WITHIN GROUP (ORDER BY col)` for string aggregation
- `FLATTEN` and `LATERAL FLATTEN` for VARIANT array expansion — always alias the value column explicitly: `f.value::STRING AS item`
- Use `GET_PATH(col, 'key')` or colon notation `col:key::STRING` for semi-structured access — be explicit about the cast
- Prefer `OBJECT_CONSTRUCT(...)` over ad-hoc JSON building; prefer `ARRAY_CONSTRUCT(...)` over array literals

**Timestamp types:**
- `TIMESTAMP_NTZ` — no timezone, pure wall-clock; use for business events
- `TIMESTAMP_LTZ` — stores UTC, displays in session timezone; use for system events
- `TIMESTAMP_TZ` — stores offset with value; use when source data carries timezone
- Default `TIMESTAMP` maps to `TIMESTAMP_NTZ` unless the account has changed `TIMESTAMP_TYPE_MAPPING` — always be explicit

**Performance patterns:**
- Cluster large tables on the most common filter/join columns: `CLUSTER BY (date_trunc('day', created_at), customer_id)`
- `SEARCH OPTIMIZATION` on tables with selective equality or substring filters — add via `ALTER TABLE ... ADD SEARCH OPTIMIZATION`
- Avoid `SELECT *` on wide VARIANT-heavy tables — project only needed columns
- Use `LIMIT` and `SAMPLE` during exploration; remove before production
- Warehouse sizing: start with `X-SMALL` for audits and metadata queries; scale up for full-table scans only when needed

---

### 3. Object Type Reference

When cataloging, auditing, or migrating, recognise these Snowflake-specific object types that have no direct BigQuery or Databricks equivalent:

| Object Type | ACCOUNT_USAGE / INFORMATION_SCHEMA View | Notes |
|---|---|---|
| Table | `ACCOUNT_USAGE.TABLES` | Includes transient and temporary |
| View | `ACCOUNT_USAGE.VIEWS` | Standard views |
| Materialized View | `ACCOUNT_USAGE.TABLES` (TABLE_TYPE = 'MATERIALIZED VIEW') | Requires enterprise edition |
| Dynamic Table | `ACCOUNT_USAGE.DYNAMIC_TABLES` | Incremental refresh, target lag setting |
| External Table | `ACCOUNT_USAGE.TABLES` (TABLE_TYPE = 'EXTERNAL TABLE') | References external stage |
| Stage | `ACCOUNT_USAGE.STAGES` | Internal, external (S3/GCS/Azure), user |
| Stream | `ACCOUNT_USAGE.STREAMS` | CDC on tables/views/external tables |
| Task | `ACCOUNT_USAGE.TASKS` | Scheduled SQL or stored procedure calls |
| Pipe | `ACCOUNT_USAGE.PIPES` | Snowpipe continuous ingest |
| Stored Procedure | `ACCOUNT_USAGE.PROCEDURES` | JS, Python, Java, Scala, SQL |
| UDF / UDTF | `ACCOUNT_USAGE.FUNCTIONS` | Scalar and table-valued |
| Semantic View | `ACCOUNT_USAGE.VIEWS` (COMMENT contains semantic metadata) | Cortex Analyst semantic layer |
| Row Access Policy | `ACCOUNT_USAGE.ROW_ACCESS_POLICIES` | Row-level security |
| Masking Policy | `ACCOUNT_USAGE.MASKING_POLICIES` | Column-level masking |
| Network Rule / Policy | `ACCOUNT_USAGE.NETWORK_POLICIES` | IP allow/deny |
| Share | `ACCOUNT_USAGE.SHARES` | Data Sharing outbound/inbound |
| Replication Group | `ACCOUNT_USAGE.REPLICATION_GROUPS` | Cross-region replication |

---

### 4. AI-Ready Data Assessment

When a user asks to assess AI-readiness of a Snowflake dataset, run the following structured assessment. This is adapted from the Snowflake Labs ai-ready-data framework and scored 0–1 per factor (1 = fully ready; NULL = not applicable — neither pass nor fail).

**Factor: Clean** — is the data structurally sound?

```sql
-- Completeness: ratio of non-null values per column
SELECT
  column_name,
  ROUND(1 - (null_count / row_count), 4) AS completeness_score
FROM (
  SELECT
    column_name,
    COUNT(*) AS row_count,
    SUM(CASE WHEN column_value IS NULL THEN 1 ELSE 0 END) AS null_count
  FROM (
    SELECT column_name, column_value
    FROM your_table
    UNPIVOT (column_value FOR column_name IN (col1, col2, col3))
  )
  GROUP BY column_name
);
```

```sql
-- Uniqueness: duplicate rate on candidate key
SELECT
  ROUND(1 - (COUNT(*) - COUNT(DISTINCT key_column)) / NULLIF(COUNT(*), 0), 4) AS uniqueness_score
FROM your_table;
```

**Factor: Contextual** — does the data have sufficient metadata for AI consumption?

Check for:
- Column comments: `SELECT column_name, comment FROM information_schema.columns WHERE UPPER(table_name) = UPPER('YOUR_TABLE') AND comment IS NOT NULL`
- Table comments: `SHOW TABLES LIKE 'your_table'` — inspect the `comment` column
- Primary/unique key constraints: `SHOW PRIMARY KEYS IN TABLE your_table`

Score: (columns with non-empty comment) / (total columns). Flag tables with zero column comments as failing.

**Factor: Consumable** — is it structured for retrieval?

- Column count: tables with >200 columns are poor retrieval targets; recommend splitting or projecting
- VARIANT column ratio: high VARIANT ratios need semi-structured documentation
- Availability of clustered/search-optimised access paths

```sql
-- Check search optimization status
SELECT table_name, search_optimization
FROM information_schema.tables
WHERE UPPER(table_schema) = UPPER('YOUR_SCHEMA');
```

**Factor: Current** — is the data fresh?

```sql
-- Last DML timestamp from ACCOUNT_USAGE
SELECT table_name, last_altered
FROM snowflake.account_usage.tables
WHERE UPPER(table_schema) = UPPER('YOUR_SCHEMA')
  AND deleted IS NULL
ORDER BY last_altered DESC;
```

Flag tables with `last_altered` > 48h old for RAG or agent use cases; > 7 days for training data.

**Factor: Compliant** — are access controls appropriate for AI use?

```sql
-- Masking policy coverage
SELECT
  a.table_name,
  a.column_name,
  b.policy_name
FROM information_schema.columns a
LEFT JOIN snowflake.account_usage.policy_references b
  ON UPPER(a.table_name) = UPPER(b.ref_entity_name)
  AND UPPER(a.column_name) = UPPER(b.ref_column_name)
WHERE UPPER(a.table_schema) = UPPER('YOUR_SCHEMA')
ORDER BY a.table_name, a.column_name;
```

PII columns without a masking policy are a compliance risk before AI feature serving.

**Scoring summary output format:**

```
## AI-Readiness Report — {DATABASE}.{SCHEMA}
Assessed: {TODAY}

| Factor      | Score | Status | Notes |
|-------------|-------|--------|-------|
| Clean       | 0.92  | PASS   | Low null rates; 2 columns >5% null |
| Contextual  | 0.41  | FAIL   | 59% of columns lack comments |
| Consumable  | 0.80  | PASS   | Search optimization on 4/5 key tables |
| Current     | 1.00  | PASS   | All tables refreshed within 24h |
| Compliant   | 0.65  | WARN   | 3 PII columns lack masking policies |

Overall: CONDITIONALLY READY — fix Contextual and Compliant before AI feature serving.

### Recommended Actions
1. Add column comments to: ... (list tables with 0 comments)
2. Apply masking policies to: ... (list unmasked PII columns)
3. Consider SEARCH OPTIMIZATION on: ... (tables used as RAG targets)
```

---

### 5. Dynamic Tables

Dynamic tables are Snowflake's declarative incremental materialisation — closer to dbt's incremental models than to standard materialized views.

**Key concepts:**
- `TARGET LAG` — how stale the DT can be before Snowflake refreshes it (`'1 minute'`, `'1 hour'`, `DOWNSTREAM`)
- `DOWNSTREAM` lag means "refresh when a downstream DT needs me" — use for pipeline chains
- Refresh is automatic; no task or cron needed
- DTs participate in lineage via `DYNAMIC_TABLE_GRAPH`

**Create pattern:**
```sql
CREATE OR REPLACE DYNAMIC TABLE my_schema.customer_summary
  TARGET_LAG = '1 hour'
  WAREHOUSE = COMPUTE_WH
AS
SELECT
  customer_id,
  COUNT(DISTINCT order_id)  AS order_count,
  SUM(order_total)          AS lifetime_value
FROM my_schema.orders
GROUP BY customer_id;
```

**Audit pattern:**
```sql
SELECT
  name,
  database_name,
  schema_name,
  target_lag,
  scheduling_state,
  last_suspended_on,
  rows,
  bytes,
  refresh_mode
FROM snowflake.account_usage.dynamic_tables
WHERE deleted IS NULL
ORDER BY database_name, schema_name, name;
```

Migration note: Dynamic tables have no direct equivalent in BigQuery. The nearest approximations are BigQuery materialized views (limited refresh control) or scheduled dbt runs. Flag all dynamic tables as `evaluate` in `db_object_audit`.

---

### 6. Streams and Tasks

**Streams** capture incremental changes (INSERT / UPDATE / DELETE) as a changelog on top of a table, view, or directory stage.

```sql
-- Create stream
CREATE OR REPLACE STREAM my_schema.orders_stream ON TABLE my_schema.orders;

-- Consume stream in a DML (marks records as consumed once transaction commits)
INSERT INTO my_schema.orders_processed
SELECT order_id, customer_id, order_total, METADATA$ACTION, METADATA$ISUPDATE
FROM my_schema.orders_stream;
```

**Tasks** are scheduled SQL or stored procedure calls. They can be chained into DAGs using `AFTER` syntax.

```sql
-- Root task (cron-scheduled)
CREATE OR REPLACE TASK my_schema.process_orders_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = 'USING CRON 0 * * * * UTC'
AS
  CALL my_schema.process_new_orders();

-- Child task (triggers after parent)
CREATE OR REPLACE TASK my_schema.aggregate_orders_task
  WAREHOUSE = COMPUTE_WH
  AFTER my_schema.process_orders_task
AS
  INSERT INTO my_schema.order_summary SELECT ...;
```

Audit queries:
```sql
-- All streams
SELECT stream_name, stale, mode, stale_after
FROM snowflake.account_usage.streams
WHERE deleted IS NULL;

-- All tasks
SELECT name, state, schedule, last_committed_on, last_suspended_on
FROM snowflake.account_usage.tasks
WHERE deleted IS NULL;
```

Migration note: Streams + Tasks form Snowflake's native CDC and orchestration layer. Neither maps to BigQuery directly. In a Snowflake-to-BigQuery migration, replace with:
- Streams → BigQuery Change Data Capture or Datastream
- Tasks → Cloud Scheduler + Cloud Run, or Airflow DAGs

---

### 7. Read-Only vs Write Operations

This skill defaults to read-only operations (queries, `SHOW`, `DESCRIBE`). Before any DDL or DML via the MCP server:

1. Present the full statement to the user
2. State what it will create, alter, or delete
3. Get explicit approval
4. Execute
5. Verify with a follow-up query

Never batch-execute DDL without per-statement consent. Never drop objects without a confirmed `SHOW` that verifies the object exists and is the intended target.

---

### 8. Deactivation

Do NOT activate this skill when:
- Working purely with dbt model SQL (the dbt-development skill handles that)
- The warehouse context is BigQuery, Databricks, or Redshift
- The user is asking about Snowflake billing/procurement (not engineering)
- Working with Snowflake semantic views specifically — defer to `snowflake-semantic-views` skill
