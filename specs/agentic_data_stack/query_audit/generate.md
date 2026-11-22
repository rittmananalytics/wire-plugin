---
wire_schema: "1.0"
command: generate
artifact: query_audit
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Analyse warehouse query history to extract high-frequency question patterns and classify by semantic-layer answerability
argument-hint: <release-folder>

---

# Agentic Data Stack — Query Audit Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Mine the warehouse query logs to find the real questions the business is asking — not what stakeholders say they need, but what they actually run. Classify each pattern by whether the semantic layer can answer it today, needs extension, or requires raw SQL. This drives the semantic_layer_design phase toward the highest-value metric additions.

## Usage

```bash
/wire:ads_query-audit-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `.wire/<release-folder>/status.md` with `project_type: agentic_data_stack`
- Query history access (INFORMATION_SCHEMA.JOBS for BigQuery, QUERY_HISTORY for Snowflake) OR a query log export

## Workflow

### Step 1: Read Context

1. Read status.md for `warehouse`, `query_history_access`, `dbt_project_path`
2. If dataset_audit and metric_audit are complete, read their artifacts for domain and metric context

### Step 2: Extract Query History

**BigQuery (last 90 days):**
```sql
SELECT
  user_email,
  query,
  creation_time,
  total_bytes_billed,
  total_slot_ms,
  referenced_tables
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE
  creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
  AND error_result IS NULL
  AND total_bytes_billed > 0
ORDER BY creation_time DESC
LIMIT 10000
```

**Snowflake (last 90 days):**
```sql
SELECT
  user_name, query_text, start_time,
  bytes_scanned, execution_time,
  database_name, schema_name
FROM snowflake.account_usage.query_history
WHERE
  start_time >= DATEADD(day, -90, CURRENT_TIMESTAMP())
  AND query_type = 'SELECT'
  AND execution_status = 'SUCCESS'
ORDER BY start_time DESC
LIMIT 10000
```

If query history access is unavailable (`query_history_access: false`), skip to Step 4 and derive patterns from the SOW, engagement context, and metric audit coverage gap questions instead.

### Step 3: Cluster into Question Patterns

Group the raw query log into question patterns. A question pattern is a recurring analytical intent, regardless of the exact SQL. Common clustering signals:

- **Table targets**: queries hitting the same tables with similar GROUP BY / WHERE patterns
- **Metric references**: column names that correspond to metrics (revenue, orders, users, conversions)
- **Time dimensions**: queries with date filters of the same granularity (daily, weekly, monthly)
- **User segments**: queries from the same user group (finance team queries cluster differently to marketing)

For each pattern, record:
- Pattern name (human-readable: "Monthly revenue by channel")
- Approximate frequency (queries/month)
- Tables referenced
- Semantic layer classification (see Step 4)
- Example query (anonymised if needed)

### Step 4: Classify by Semantic Layer Answerability

| Class | Definition | Action |
|---|---|---|
| **SL-covered** | A current semantic layer metric answers this directly | No action needed |
| **SL-extendable** | A metric exists but needs an additional dimension or time grain | Add to semantic_layer_design backlog |
| **SL-gap** | No semantic metric covers this — raw SQL required today | High-priority addition in semantic_layer_design |
| **Raw-only** | Requires complex multi-step logic unlikely to be encapsulated in a single metric | Document as raw-SQL pattern; add to knowledge_skill reference |

### Step 5: Write Query Audit Document

Write `.wire/<release-folder>/artifacts/query_audit.md`:

```markdown
---
artifact: query_audit
generated: YYYY-MM-DD
source: query_history  # or: sow_derived | stakeholder_input
---

# Query Audit

## Summary

| Metric | Value |
|---|---|
| Queries analysed | N |
| Distinct question patterns identified | N |
| SL-covered | N (X%) |
| SL-extendable | N (X%) |
| SL-gap (high priority additions) | N |
| Raw-only (complex patterns) | N |

## Top 20 Question Patterns

| Pattern | Frequency/month | Tables | SL Class | Priority |
|---|---|---|---|---|
| Monthly revenue by channel | 47 | fct_orders, dim_channels | SL-gap | High |
| Active customers last 30 days | 31 | dim_customers, fct_orders | SL-extendable | High |
| Marketing spend vs revenue by campaign | 28 | fct_ad_spend, fct_orders | SL-gap | High |

## High-Priority Semantic Layer Additions

[Ordered by frequency — input to semantic_layer_design]

## Raw-SQL Patterns (knowledge_skill candidates)

[Complex patterns that won't fit a single metric — document for knowledge skill reference files]

## Domain Distribution

| Domain | % of queries | SL coverage |
|---|---|---|
| orders/revenue | 42% | 35% |
| marketing | 28% | 12% |
```

### Step 6: Update Status

```yaml
query_audit:
  generate: complete
  generated_date: YYYY-MM-DD
  queries_analysed: N
  patterns_found: N
  sl_coverage_pct: X
  source: query_history
```

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `query_audit`
- `artifact_name`: `Query Audit`
- `file_path`: `.wire/[release_folder]/artifacts/query_audit.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Edge Cases

### No Query History Access

Derive question patterns from:
1. SOW KPIs and reporting requirements
2. Metric audit coverage gaps
3. Direct stakeholder input — ask: "List the ten questions you ask most often in Slack or on dashboards"

Mark `source: stakeholder_input` in the audit document. Note this in the review: stakeholder-derived patterns are less reliable than query log patterns and may miss the long tail.

### Very High Query Volume (>100k queries/day)

Sample the last 30 days at 10% rather than 90 days at full volume. Filter to queries >1MB scanned to exclude trivial lookups. Note the sampling approach in the audit.

## Output

- `.wire/<release-folder>/artifacts/query_audit.md`
- Updated `status.md`
