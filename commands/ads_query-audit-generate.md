---
description: Analyse query history to extract patterns and classify by semantic-layer answerability
argument-hint: <release-folder>
---

# Analyse query history to extract patterns and classify by semantic-layer answerability

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.7.8\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ads_query-audit-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.7.8\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Analyse warehouse query history to extract high-frequency question patterns and classify by semantic-layer answerability
argument-hint: <release-folder>
---

# Agentic Data Stack — Query Audit Generate

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
