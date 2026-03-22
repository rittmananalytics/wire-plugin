---
name: dbt-troubleshooting
description: Proactive skill for diagnosing dbt job failures and test errors. Auto-activates when encountering dbt errors, failed jobs, compilation issues, or test failures. Provides systematic diagnosis workflow with error classification, investigation steps, and resolution patterns.
---

# dbt Troubleshooting Skill

## Purpose

This skill automatically activates when diagnosing dbt job failures, test errors, compilation issues, or runtime problems. It provides a systematic methodology for classifying errors, investigating root causes, and implementing fixes with preventive measures.

The goal is not just to fix the immediate error but to understand **why** it happened, fix the root cause, and add safeguards to prevent recurrence.

## When This Skill Activates

### User-Triggered Activation

This skill should activate when users:
- **Report job failures:** "My dbt job failed last night"
- **Share error messages:** "I'm getting this error: ..."
- **Ask about test failures:** "Why is my not_null test failing?"
- **Debug compilation issues:** "My model won't compile"
- **Investigate timeouts:** "The job timed out after 3 hours"
- **Troubleshoot data issues:** "The numbers don't match the source"

**Keywords to watch for:**
- "dbt error", "job failed", "test failure", "compilation error"
- "timeout", "dbt run failed", "model error", "build failed"
- "not_null failed", "unique failed", "relationships failed"
- "syntax error", "missing ref", "circular dependency"
- "quota exceeded", "slot contention", "connection failed"

### Self-Triggered Activation (Proactive)

**Activate when:**
- You see dbt error output in a terminal or log
- A `dbt build` or `dbt run` command returns errors
- You're reviewing `run_results.json` or dbt Cloud run artifacts
- You encounter a failing CI check related to dbt
- A Wire validate command (`/wire:dbt-validate`) reports failures

**Example internal triggers:**
- dbt command returns non-zero exit code -> Activate skill
- User pastes error traceback -> Classify and investigate
- Test results show failures -> Begin diagnostic workflow

---

## Core Principle

> **Never modify a test to make it pass without understanding why it is failing.**

This is the iron rule of dbt troubleshooting. A failing test is a signal. Before changing anything:

1. **Understand** what the test is checking
2. **Investigate** why the data violates the test expectation
3. **Determine** whether the bug is in the data, the model, or the test
4. **Fix** the actual root cause
5. **Document** the finding

Tests that are "fixed" by loosening constraints, adding exceptions, or disabling them entirely create a false sense of data quality. Every suppressed test is a future production incident.

---

## Instructions

### 1. Error Classification

When encountering a dbt error, first classify it into one of three categories. This determines the investigation approach:

#### Category A: Infrastructure Errors

Errors caused by the execution environment, not the dbt code itself.

| Error Pattern | Likely Cause | Urgency |
|---|---|---|
| `Connection refused` / `Connection timed out` | Warehouse unreachable | High -- check warehouse status |
| `Quota exceeded` / `Resources exceeded` | BigQuery slot/billing limits | High -- may need quota increase |
| `Slot contention` / `Query timed out` | Concurrent query pressure | Medium -- reschedule or optimize |
| `Authentication failed` / `Permission denied` | Credentials expired or role missing | High -- check service account |
| `Disk space` / `Memory exceeded` | Worker resource limits | Medium -- optimize query or increase resources |
| `Rate limit exceeded` | API throttling | Low -- add retry logic or reduce concurrency |
| `Network error` / `DNS resolution failed` | Network connectivity | High -- infrastructure issue |

**Resolution approach:** Infrastructure errors are not code bugs. Fix the environment, then re-run.

#### Category B: Code/Compilation Errors

Errors in dbt project code that prevent compilation or execution.

| Error Pattern | Likely Cause | Urgency |
|---|---|---|
| `Compilation Error` + `ref('...')` | Missing or misspelled model reference | Medium -- fix the ref |
| `Compilation Error` + `source('...')` | Missing source definition | Medium -- add to sources.yml |
| `Parsing Error` + YAML | Invalid YAML syntax | Low -- fix indentation/syntax |
| `Circular dependency detected` | Model A refs B which refs A | High -- refactor model DAG |
| `Duplicate model name` | Two models share a name | Medium -- rename one |
| `Undefined macro` | Missing macro or wrong package | Medium -- check macro path |
| `SQL syntax error` | Invalid SQL for target warehouse | Low -- fix SQL |
| `Jinja rendering error` | Template syntax issue | Medium -- check Jinja logic |
| `Schema/contract violation` | Model output doesn't match contract | Medium -- fix model or update contract |

**Resolution approach:** Read the error message carefully. The fix is almost always in the file referenced in the error.

#### Category C: Data/Test Failures

The code compiles and runs, but tests detect data quality issues.

| Error Pattern | Likely Cause | Investigation |
|---|---|---|
| `not_null` failure | NULL values in a required column | Profile the NULLs -- are they from a specific source or time range? |
| `unique` failure | Duplicate values in a PK column | Find the duplicates -- is it a join fanout or source issue? |
| `relationships` failure | Orphan foreign keys | Check if referenced records were deleted or never loaded |
| `accepted_values` failure | Unexpected value in a categorical column | Check source for new values not yet mapped |
| `custom test` failure | Business rule violation | Understand the rule, then investigate the data |
| `unit test` failure | Transformation logic mismatch | Compare actual vs expected -- is the model or the test wrong? |
| Row count anomaly | Unexpected increase/decrease | Check source loads, dedup logic, join conditions |

**Resolution approach:** Always investigate the data first. The test may be correct and the data genuinely broken.

---

### 2. Diagnostic Workflow

Follow these steps in order for any dbt failure:

#### Step 1: Gather Information

Collect all available context before investigating:

```bash
# What exactly failed?
# Read the error message completely -- don't skim

# Check recent changes to the model
git log --oneline -10 -- models/path/to/failing_model.sql

# Check recent changes to the schema/tests
git log --oneline -10 -- models/path/to/failing_model.yml

# Check if the model's upstream dependencies changed
git log --oneline -10 -- models/path/to/upstream_model.sql

# Review the compiled SQL (for compilation issues)
cat target/compiled/project_name/models/path/to/failing_model.sql

# Review run results for timing and status
cat target/run_results.json | python3 -m json.tool
```

**Information checklist:**
- [ ] Full error message (not truncated)
- [ ] Model name and file path
- [ ] When the failure started (first failure vs recurring)
- [ ] What changed recently (code, data, infrastructure)
- [ ] Upstream model status (did they succeed?)
- [ ] Run timing (longer than usual?)

#### Step 2: Classify the Error

Using the tables in Section 1, determine:
- **Category:** Infrastructure (A), Code (B), or Data (C)?
- **Urgency:** Is this blocking production? Blocking development? Informational?
- **Scope:** One model? Multiple models? Entire project?

#### Step 3: Investigate Root Cause

**For Infrastructure Errors (A):**
1. Check warehouse status/health dashboard
2. Verify credentials and permissions
3. Check resource quotas and usage
4. Review network connectivity
5. Check for maintenance windows or outages

**For Code Errors (B):**
1. Read the full error message -- dbt usually tells you exactly what is wrong
2. Open the referenced file at the referenced line
3. Check the compiled SQL in `target/compiled/`
4. Validate YAML syntax with a linter
5. Run `dbt parse` to check for structural issues
6. Run `dbt compile --select model_name` to isolate compilation
7. Check `dbt_project.yml` for configuration issues

**For Data/Test Failures (C):**
1. **Profile the failure** -- Quantify the scope:
   ```sql
   -- For not_null failures
   SELECT COUNT(*) AS total_rows,
          COUNT(*) - COUNT(column_name) AS null_count,
          ROUND((COUNT(*) - COUNT(column_name)) / COUNT(*) * 100, 2) AS null_pct
   FROM {{ ref('model_name') }}

   -- For unique failures
   SELECT column_name, COUNT(*) AS occurrences
   FROM {{ ref('model_name') }}
   GROUP BY column_name
   HAVING COUNT(*) > 1
   ORDER BY occurrences DESC
   LIMIT 20

   -- For relationships failures
   SELECT child.fk_column, COUNT(*) AS orphan_count
   FROM {{ ref('child_model') }} child
   LEFT JOIN {{ ref('parent_model') }} parent
     ON child.fk_column = parent.pk_column
   WHERE parent.pk_column IS NULL
   GROUP BY 1
   ORDER BY 2 DESC
   LIMIT 20
   ```

2. **Identify the source** -- Where do the bad records come from?
   ```sql
   -- Check if NULLs correlate with a specific source or time range
   SELECT _source_system, DATE(loaded_at) AS load_date, COUNT(*) AS null_records
   FROM {{ ref('model_name') }}
   WHERE column_name IS NULL
   GROUP BY 1, 2
   ORDER BY 3 DESC
   ```

3. **Check upstream models** -- Did the problem originate upstream?
   ```sql
   -- Trace back through the DAG
   SELECT COUNT(*) AS upstream_nulls
   FROM {{ ref('upstream_model') }}
   WHERE relevant_column IS NULL
   ```

4. **Review recent data loads** -- Did source data change?
   ```sql
   -- Check for unusual load patterns
   SELECT DATE(_loaded_at) AS load_date, COUNT(*) AS row_count
   FROM {{ source('schema', 'table') }}
   GROUP BY 1
   ORDER BY 1 DESC
   LIMIT 14
   ```

5. **Check for schema drift** -- Did source columns change type or meaning?

#### Step 4: Resolve

Once you understand the root cause:

1. **Create a fix branch:**
   ```bash
   git checkout -b fix/model-name-error-description
   ```

2. **Implement the fix** in the correct location:
   - Data issue in source -> Fix the pipeline or add defensive logic in staging
   - Logic error in model -> Fix the SQL
   - Missing test -> Add the test
   - Configuration issue -> Fix `dbt_project.yml` or model config

3. **Add a preventive test** if one doesn't exist:
   ```yaml
   # If the failure revealed a gap in test coverage, add a test
   models:
     - name: model_name
       columns:
         - name: column_that_broke
           tests:
             - not_null
             - unique
   ```

4. **Validate the fix:**
   ```bash
   # Run the specific model
   dbt run --select model_name

   # Run the model's tests
   dbt test --select model_name

   # Run the model with its upstream dependencies
   dbt build --select +model_name
   ```

5. **Run regression** to ensure the fix doesn't break other models:
   ```bash
   # Check downstream models
   dbt build --select model_name+
   ```

#### Step 5: Document

After resolution, document the finding:

1. **Update `execution_log.md`** (if using Wire workflow):
   ```markdown
   ## [Date] - [Model Name] - [Error Type]
   - **Error:** [Brief description]
   - **Root Cause:** [What actually went wrong]
   - **Fix:** [What was changed]
   - **Prevention:** [Test or safeguard added]
   ```

2. **Create a Jira ticket** if the issue is recurring or systemic

3. **Update team documentation** if this reveals a pattern others should know about

---

### 3. BigQuery-Specific Errors

#### Quota Exceeded / Resources Exceeded

```
Resources exceeded during query execution: The query could not be executed in the allotted memory.
```

**Investigation:**
1. Check the query's bytes processed: Is it scanning too much data?
2. Check partition pruning: Is the model filtering on the partition column?
3. Check for cross-joins or exploding joins

**Resolution patterns:**
- Add `WHERE` clauses to filter by partition column (usually `_PARTITIONTIME` or a date column)
- Add `require_partition_filter: true` to the model config
- Break large queries into CTEs or intermediate models
- Use `APPROX_COUNT_DISTINCT()` instead of `COUNT(DISTINCT ...)` where precision is acceptable

#### Partition Filter Required

```
Cannot query over table 'project.dataset.table' without a filter over column(s) '_PARTITIONTIME'
```

**Resolution:** Add a partition filter in the model's `WHERE` clause. For incremental models:
```sql
{% if is_incremental() %}
WHERE _PARTITIONTIME >= (SELECT MAX(_PARTITIONTIME) FROM {{ this }})
{% endif %}
```

#### Slot Contention / Query Timeout

```
Query timed out. Job exceeded maximum execution time.
```

**Investigation:**
1. Check BigQuery admin console for concurrent query load
2. Review query execution plan for expensive operations
3. Check if the model's data volume grew unexpectedly

**Resolution patterns:**
- Schedule the job during off-peak hours
- Optimize the query (reduce joins, add filters)
- Request additional slot capacity
- Break into smaller incremental runs

#### BYTES vs STRING Confusion

```
No matching signature for operator = for argument types: BYTES, STRING
```

**Resolution:** Cast explicitly:
```sql
SAFE_CONVERT_BYTES_TO_STRING(bytes_column) = 'expected_value'
-- or
CAST(string_column AS BYTES) = bytes_column
```

#### STRUCT/ARRAY Handling Errors

```
Cannot access field 'name' on a value with type ARRAY<STRUCT<...>>
```

**Resolution:** Use `UNNEST()` for arrays, dot notation for structs:
```sql
-- Accessing STRUCT field
SELECT event.event_name.value AS event_name FROM events

-- Unnesting ARRAY of STRUCT
SELECT event_id, param.key, param.value.string_value
FROM events, UNNEST(event_params) AS param
```

#### Incremental Merge Failures

```
UPDATE/MERGE must match at most one source row for each target row
```

**Investigation:** The unique key has duplicates in the source query.

**Resolution:**
1. Add deduplication in the model's source CTE
2. Ensure the `unique_key` in model config truly identifies unique rows
3. Add a `unique` test on the unique key columns

#### DML Statement Limits

```
Exceeded rate limits: too many table update operations for this table
```

**Resolution:**
- Reduce the frequency of incremental runs
- Batch multiple operations
- Use `merge_update_columns` to limit the update scope

---

### 4. dbt Cloud Job Debugging

#### Checking Run Artifacts

After a dbt Cloud job fails, examine the artifacts:

```bash
# Run results contain timing and status for each node
# Available at: target/run_results.json
# Key fields: status, execution_time, message, failures

# Manifest contains the full project graph
# Available at: target/manifest.json
# Useful for checking compiled SQL and dependencies

# Check compiled SQL for a specific model
cat target/compiled/<project_name>/models/<path>/<model>.sql
```

#### Reading Compile Logs

dbt Cloud logs show the full execution sequence. Look for:

1. **First error** -- Earlier errors often cause cascading failures. Fix the first one.
2. **Timing anomalies** -- A model that usually takes 30s but took 30min indicates data volume or query plan issues.
3. **Skip markers** -- `SKIP` status means the model was skipped due to an upstream failure.
4. **Warning messages** -- Warnings often predict future failures.

#### Useful dbt Cloud CLI Commands

```bash
# Check job status
dbt cloud job list

# Re-run from failure point
dbt retry

# Run with debug logging
dbt --debug run --select model_name
```

#### API Endpoints for Job Status

For programmatic access to dbt Cloud job information:
- **List runs:** `GET /api/v2/accounts/{account_id}/runs/`
- **Get run:** `GET /api/v2/accounts/{account_id}/runs/{run_id}/`
- **Get run artifacts:** `GET /api/v2/accounts/{account_id}/runs/{run_id}/artifacts/{path}`

---

### 5. Common dbt CLI Error Patterns

#### `dbt deps` Failures

```
ERROR: Could not find a version that satisfies the requirement
```

**Resolution:**
- Check `packages.yml` for version constraints
- Run `dbt clean` then `dbt deps` to refresh packages
- Verify package registry availability

#### `dbt seed` Failures

```
Runtime Error: maximum recursion depth exceeded
```

**Resolution:**
- Check CSV file size (seeds should be small reference data, not large datasets)
- Verify CSV encoding (UTF-8 without BOM)
- Check for special characters in CSV headers

#### `dbt snapshot` Failures

```
Compilation Error: Snapshot 'model' has no 'unique_key' configured
```

**Resolution:**
- Add `unique_key` to snapshot config
- Verify the unique key column exists in the source query
- Check `strategy` is set (timestamp or check)

---

### 6. Anti-Patterns to Avoid

#### Sunk Time Bias

**Anti-pattern:** "I've spent 3 hours on this approach, I'll keep trying."

**Better:** If an approach isn't working after reasonable effort, step back:
1. Re-read the error message from scratch
2. Question your assumptions
3. Try a completely different approach
4. Ask for help

#### Accepting Flaky Tests

**Anti-pattern:** "This test fails sometimes but usually passes. I'll just re-run."

**Better:** Flaky tests indicate a real problem:
1. Non-deterministic query results (missing `ORDER BY` in window functions)
2. Race conditions in data loading
3. Timezone-dependent logic
4. Tests that depend on "current" data that changes

Always investigate and fix the root cause of flaky tests.

#### Tight-Deadline Shortcuts

**Anti-pattern:** "We need this deployed today, I'll disable the failing test."

**Better:**
1. Understand the test failure
2. If the test is wrong, fix the test
3. If the data is wrong, fix the data
4. If the model is wrong, fix the model
5. If none of the above is possible in the timeline, **document the risk** and create a ticket with a deadline

Never silently disable a test. At minimum, add a comment explaining why and a ticket reference.

#### Fixing Symptoms Instead of Causes

**Anti-pattern:** Adding `WHERE column IS NOT NULL` to fix a `not_null` test failure.

**Better:** Ask "why is this column NULL?" The answer determines the fix:
- Source system doesn't always provide it -> Add `coalesce()` in staging with a documented default
- Join is failing -> Fix the join condition
- Upstream model has a bug -> Fix the upstream model
- The column genuinely can be NULL -> Remove the `not_null` test and update documentation

---

### 7. Integration with Wire Workflow

#### After `/wire:dbt-validate` Failures

When Wire's validate command reports failures:

1. **Read the validation report** in `.wire/{project}/testing/` to understand what failed
2. **Apply this skill's diagnostic workflow** (Section 2) to investigate each failure
3. **Document findings** in the appropriate Wire artifact:
   - Data model issues -> `.wire/{project}/dev/data_model_*`
   - Test failures -> `.wire/{project}/testing/test_results_*`
   - Configuration issues -> `.wire/{project}/dev/dbt_project_config_*`

#### Creating Fix Artifacts

When troubleshooting reveals issues that need tracking:

1. **Log the issue** in the project's execution log
2. **Update the relevant Wire artifact** with findings
3. **Create a Jira sub-task** if the project uses Atlassian integration
4. **Re-run validation** after fixes: `/wire:dbt-validate {project_id}`

#### Escalation Path

If troubleshooting does not resolve the issue within a reasonable timeframe:

1. Document everything investigated so far
2. Capture the full error message, investigation queries, and findings
3. Create a detailed Jira ticket with:
   - Error classification (A/B/C)
   - Steps already taken
   - Hypotheses tested and ruled out
   - Recommended next steps
4. Escalate to the appropriate team member

---

### 8. Diagnostic Query Templates

#### Profiling a Failing Column

```sql
-- Comprehensive column profile for investigation
SELECT
  COUNT(*) AS total_rows,
  COUNT({{ column_name }}) AS non_null_count,
  COUNT(*) - COUNT({{ column_name }}) AS null_count,
  ROUND((COUNT(*) - COUNT({{ column_name }})) / COUNT(*) * 100, 2) AS null_pct,
  COUNT(DISTINCT {{ column_name }}) AS distinct_count,
  MIN({{ column_name }}) AS min_value,
  MAX({{ column_name }}) AS max_value
FROM {{ ref('model_name') }}
```

#### Finding Duplicate Keys

```sql
-- Identify duplicates with context
WITH duplicates AS (
  SELECT
    {{ unique_key }},
    COUNT(*) AS occurrence_count
  FROM {{ ref('model_name') }}
  GROUP BY {{ unique_key }}
  HAVING COUNT(*) > 1
)
SELECT
  m.*,
  d.occurrence_count
FROM {{ ref('model_name') }} m
INNER JOIN duplicates d ON m.{{ unique_key }} = d.{{ unique_key }}
ORDER BY d.occurrence_count DESC, m.{{ unique_key }}
LIMIT 100
```

#### Checking Row Count Trends

```sql
-- Daily row count trend for anomaly detection
SELECT
  DATE({{ timestamp_column }}) AS record_date,
  COUNT(*) AS row_count,
  LAG(COUNT(*)) OVER (ORDER BY DATE({{ timestamp_column }})) AS prev_day_count,
  ROUND(
    (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY DATE({{ timestamp_column }})))
    / NULLIF(LAG(COUNT(*)) OVER (ORDER BY DATE({{ timestamp_column }})), 0) * 100,
    1
  ) AS pct_change
FROM {{ ref('model_name') }}
WHERE {{ timestamp_column }} >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1
ORDER BY 1 DESC
```

#### Tracing Data Lineage for an Error

```sql
-- Trace a specific record through the DAG
-- Start from the failing model and work backward

-- Step 1: Find the problematic record in the failing model
SELECT * FROM {{ ref('failing_model') }}
WHERE {{ problem_condition }}
LIMIT 10;

-- Step 2: Check the same record in the upstream model
SELECT * FROM {{ ref('upstream_model') }}
WHERE {{ join_key }} IN (
  SELECT {{ join_key }} FROM {{ ref('failing_model') }}
  WHERE {{ problem_condition }}
);

-- Step 3: Check the source
SELECT * FROM {{ source('schema', 'table') }}
WHERE {{ source_key }} IN (
  SELECT {{ source_key }} FROM {{ ref('staging_model') }}
  WHERE {{ join_key }} IN (
    SELECT {{ join_key }} FROM {{ ref('failing_model') }}
    WHERE {{ problem_condition }}
  )
);
```

---

## Additional Resources

- **Error Catalog:** See `error-catalog.md` for a quick-reference table of common errors by class with resolution patterns
- **dbt-development skill:** For model coding conventions and schema test coverage guidelines
- **dbt-unit-testing skill:** For unit test creation when troubleshooting reveals logic errors
- **testing-reference.md** (in dbt-development): For overall test strategy and coverage requirements

---

## Attribution

Adapted from [dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) (Apache-2.0 License). Original skill: `troubleshooting-dbt-job-errors`. Modified for Rittman Analytics conventions, BigQuery focus, Wire Framework integration, and expanded error catalog.
