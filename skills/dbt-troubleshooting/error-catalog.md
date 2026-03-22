# dbt Error Catalog

Quick-reference catalog of common dbt errors organized by class, with symptoms, likely causes, and resolution patterns. Use this as a lookup table when diagnosing failures.

---

## Infrastructure Errors (Category A)

| Error Message / Pattern | Likely Cause | Resolution | BigQuery-Specific? |
|---|---|---|---|
| `Connection refused` | Warehouse service down or unreachable | Check warehouse status dashboard; verify network/firewall rules | No |
| `Connection timed out` | Network issue or warehouse overloaded | Retry; check VPC/firewall; verify service account permissions | No |
| `Authentication failed` / `Invalid credentials` | Expired token or misconfigured service account | Refresh OAuth token; re-generate service account key; check `profiles.yml` | No |
| `Permission denied` on dataset/table | Service account lacks required IAM role | Grant `roles/bigquery.dataEditor` on target dataset | Yes |
| `Access Denied: Project [id]: User does not have bigquery.jobs.create` | Missing job creation permission | Grant `roles/bigquery.jobUser` at project level | Yes |
| `Quota exceeded: Your project exceeded quota for concurrent queries` | Too many simultaneous queries | Reduce thread count in `profiles.yml`; stagger job schedules | Yes |
| `Resources exceeded during query execution` | Query requires more memory than available slots | Optimize query; break into smaller models; request slot increase | Yes |
| `Query timed out` / `Job exceeded maximum execution time` | Query running too long (default 6h in BQ) | Optimize query; add partition filters; use incremental materialization | Yes |
| `Rate limit exceeded: Too many API requests` | API call throttling | Add retry logic; reduce `threads` setting; batch operations | Yes |
| `Disk space exceeded` | Local disk full (dbt Core) or temp storage exceeded | Clean `target/` and `dbt_packages/`; increase disk; reduce `--threads` | No |
| `SSL: CERTIFICATE_VERIFY_FAILED` | SSL certificate issue | Update CA certificates; check proxy settings; verify `--no-ssl` flag | No |
| `Could not connect to dbt Cloud` | dbt Cloud API unreachable | Check dbt Cloud status page; verify API token; check network | No |

---

## Code / Compilation Errors (Category B)

| Error Message / Pattern | Likely Cause | Resolution | Prevention |
|---|---|---|---|
| `Compilation Error in model X: 'ref' ... not found` | Misspelled model name in `ref()` | Check exact model filename; run `dbt ls` to list models | Use IDE autocomplete; add CI check with `dbt parse` |
| `Compilation Error: source ... not found` | Missing source definition in YAML | Add source to `sources.yml`; check schema/table name | Run `dbt parse` in CI |
| `Parsing Error: ... expected a key` | Invalid YAML syntax (bad indentation, missing colon) | Lint YAML; check indentation (2 spaces, no tabs) | Use YAML linter in pre-commit |
| `Circular dependency detected` | Model A -> B -> A (direct or indirect) | Refactor to break the cycle; introduce intermediate model | Review DAG with `dbt docs generate` regularly |
| `Duplicate model name: X` | Two models share the same name in different paths | Rename one model; use `alias` config if needed | Enforce unique names in CI |
| `Macro 'X' is undefined` | Missing macro package or wrong path | Run `dbt deps`; check macro file location; verify import | Pin package versions in `packages.yml` |
| `Jinja Error: 'undefined' has no attribute 'X'` | Variable or config not set | Check `dbt_project.yml` vars; verify `var()` default values | Always provide defaults: `var('x', 'default')` |
| `SQL compilation error: Syntax error` | Invalid SQL for target warehouse | Check BigQuery SQL dialect; review compiled SQL in `target/compiled/` | Test with `dbt compile --select model` |
| `Snapshot has no unique_key configured` | Missing required snapshot config | Add `unique_key` to snapshot config block | Use snapshot template with required fields |
| `Contract violation: column X has type Y, expected Z` | Model output doesn't match declared contract | Fix model SQL to match contract; or update contract | Run `dbt build` (not just `dbt run`) to catch early |
| `dbt_project.yml is invalid: ...` | Project config syntax error | Validate YAML; check for deprecated config keys | Keep `dbt_project.yml` minimal and well-structured |
| `Env var required but not provided: DBT_...` | Missing environment variable | Set the env var; check `.env` file; verify CI secrets | Document required env vars in project README |
| `Could not find profile named 'X'` | Profile missing from `profiles.yml` | Add profile; check `DBT_PROFILES_DIR` env var | Use `--profiles-dir` flag explicitly |
| `Seed file too large` | CSV seed exceeds size limit | Move large data to warehouse load; seeds are for small reference data | Set `seed-paths` config; document seed size limits |

---

## Data / Test Failures (Category C)

| Test Type | Failure Message Pattern | Common Causes | Investigation Query | Resolution Pattern |
|---|---|---|---|---|
| `not_null` | `Got X results, configured to fail if != 0` | Source sends NULLs; join produces NULLs; upstream bug | `SELECT COUNT(*) FROM model WHERE col IS NULL` | Fix upstream; add `coalesce()` in staging; or relax test with `where` config |
| `unique` | `Got X results, configured to fail if != 0` | Join fanout; missing dedup; source duplicates | `SELECT col, COUNT(*) FROM model GROUP BY 1 HAVING COUNT(*) > 1` | Add dedup logic; fix join; add `unique` test on source |
| `relationships` | `Got X results, configured to fail if != 0` | Orphan FKs; parent records deleted; late-arriving dimensions | `SELECT child.fk FROM child LEFT JOIN parent ON ... WHERE parent.pk IS NULL` | Fix data load order; add defensive join; use `relationships` with `where` |
| `accepted_values` | `Got X results, configured to fail if != 0` | New category in source data; typo in mapping | `SELECT col, COUNT(*) FROM model GROUP BY 1 ORDER BY 2 DESC` | Add new value to accepted list; or fix source mapping |
| `dbt_expectations.expect_column_values_to_be_between` | `Got X results, configured to fail if != 0` | Outlier data; unit change; currency conversion error | `SELECT col FROM model WHERE col NOT BETWEEN min AND max` | Adjust bounds; investigate outliers; fix conversion logic |
| `dbt_utils.expression_is_true` | `Got X results, configured to fail if != 0` | Business rule violation | `SELECT * FROM model WHERE NOT (expression)` | Fix the data/model to satisfy the business rule |
| `unit_test` | `Got 1 result, configured to fail if != 0` + diff output | Model logic changed; expected output wrong; mock data incomplete | Compare actual vs expected in diff output | Fix model logic or update test expectations |
| Row count | Custom macro: unexpected row count | Data volume spike/drop; filter change; source issue | `SELECT DATE(ts), COUNT(*) FROM model GROUP BY 1 ORDER BY 1 DESC` | Investigate source; check filters; verify incremental logic |

---

## BigQuery-Specific Errors (Category D)

| Error Message / Pattern | Cause | Resolution | Example Fix |
|---|---|---|---|
| `Cannot query over table without a filter over column(s) '_PARTITIONTIME'` | Table requires partition filter | Add partition filter in WHERE clause | `WHERE _PARTITIONTIME >= '2024-01-01'` |
| `UPDATE/MERGE must match at most one source row for each target row` | Duplicate keys in merge source | Add deduplication before merge | `QUALIFY ROW_NUMBER() OVER (PARTITION BY key ORDER BY updated_at DESC) = 1` |
| `No matching signature for operator = for argument types: BYTES, STRING` | Type mismatch between BYTES and STRING | Explicit cast | `SAFE_CONVERT_BYTES_TO_STRING(col)` |
| `Cannot access field on a value with type ARRAY<STRUCT<...>>` | Trying to access array element without UNNEST | Use UNNEST for arrays | `SELECT param.value FROM t, UNNEST(params) AS param` |
| `Exceeded rate limits: too many table update operations` | DML rate limit (max 1500/table/day) | Reduce incremental frequency; batch operations | Run incrementals less frequently or use larger batches |
| `Not found: Table project.dataset.table was not found` | Table doesn't exist yet or wrong reference | Check dataset/table exists; run upstream models first | `dbt run --select +model_name` to build dependencies |
| `STRUCT type mismatch in UNION ALL` | STRUCT schemas differ across UNION branches | Ensure all branches have identical STRUCT definitions | Explicitly cast STRUCT fields in each branch |
| `Array element access is not allowed for type STRUCT` | Wrong syntax for nested data access | Use dot notation for STRUCT, UNNEST for ARRAY | Review BigQuery nested data documentation |
| `Invalid table name` / `Dataset not found` | Wrong project/dataset in source config | Verify `database` and `schema` in source YAML | Check `generate_database_name` / `generate_schema_name` macros |
| `The user does not have permission to query table` | Row-level or column-level security | Grant appropriate access; check authorized views | Review IAM and authorized dataset settings |
| `Query exceeded resource limits: Not enough resources for query planning` | Query too complex for planner | Simplify query; break into intermediate models | Create CTEs as separate models |
| `Memory limit exceeded during query execution` | Single query exceeds slot memory | Reduce data scanned; add filters; use approximate functions | `APPROX_COUNT_DISTINCT()` instead of `COUNT(DISTINCT ...)` |

---

## Resolution Decision Tree

When a test fails, follow this decision tree:

```
TEST FAILS
    |
    v
Is the test correct? (Does it test a valid business rule?)
    |
    +-- NO --> Fix or remove the test. Document why.
    |
    +-- YES
         |
         v
    Is the data correct? (Does the source data match expectations?)
         |
         +-- NO --> Fix the data pipeline. Add source tests.
         |
         +-- YES
              |
              v
         Is the model correct? (Does the transformation logic work?)
              |
              +-- NO --> Fix the model SQL. Add unit test.
              |
              +-- YES
                   |
                   v
              Is the test too strict? (Are the thresholds reasonable?)
                   |
                   +-- NO --> Investigate deeper. Something else changed.
                   |
                   +-- YES --> Adjust thresholds. Document the change. Add warn threshold.
```

---

## Severity and Response Guide

| Severity | Criteria | Response Time | Action |
|---|---|---|---|
| **P0 - Critical** | Production data pipeline fully blocked | Immediate | All hands; escalate to platform team; communicate to stakeholders |
| **P1 - High** | Production data delayed or partially incorrect | Within 2 hours | Investigate and fix; communicate expected resolution time |
| **P2 - Medium** | Non-critical test failure; data mostly correct | Within 1 business day | Investigate root cause; create fix PR; add preventive test |
| **P3 - Low** | Warning-level issue; no data impact | Within 1 week | Create ticket; fix in next sprint; update documentation |

---

## Attribution

Adapted from [dbt-labs/dbt-agent-skills](https://github.com/dbt-labs/dbt-agent-skills) (Apache-2.0 License). Expanded with BigQuery-specific errors and Rittman Analytics conventions.
