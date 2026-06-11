# Snowflake → BigQuery Translation Guide

## Overview

This guide defines the canonical translation decisions for migrating SQL from Snowflake to BigQuery. Each entry covers: the source construct, the target equivalent, the decision rationale, and the macro or approach to use during dbt model translation.

This table is the quick reference. For the exhaustive treatment — dialect fundamentals, the silent-behaviour-change cases, semi-structured/JSON, array functions, security and metadata objects, and a 25-item gotcha checklist — see [`translation_reference.md`](./translation_reference.md). When a model trips a ⚠ case (timezone defaults, `DATEDIFF` boundary vs elapsed semantics, day-of-week numbering, regex engine, hash-key mismatch, NaN/NULL sort order), the reference is authoritative.

## SQL Construct Translations

| Source (Snowflake) | Target (BigQuery) | Decision | Macro / Approach |
|-------------------|------------------|----------|-----------------|
| `LATERAL FLATTEN(input => array_col)` | `CROSS JOIN UNNEST(array_col) AS element` | BQ uses UNNEST for array expansion | `{{ sf_to_bq.flatten(array_col) }}` macro |
| `f.value` (FLATTEN alias value) | element alias from UNNEST | Alias semantics differ | Manual per model |
| `f.index` (FLATTEN position) | `WITH OFFSET` clause | Position access differs | Manual |
| `PARSE_JSON(json_string)` | `PARSE_JSON(json_string)` or `SAFE.PARSE_JSON(...)` | BigQuery does have PARSE_JSON; use `SAFE.` to null-on-error. For extraction from a STRING column without parsing, use `JSON_VALUE`/`JSON_QUERY` | See `translation_reference.md` §6 |
| `col:field` (colon path notation) | `JSON_VALUE(col, '$.field')` or struct dot notation | BQ uses JSON function or struct access depending on column type | Type-dependent — manual review |
| `col:field::STRING` | `JSON_VALUE(col, '$.field')` | Snowflake path extract + cast | `{{ sf_to_bq.path_extract(col, 'field', 'STRING') }}` |
| `OBJECT_CONSTRUCT('a', a, 'b', b)` | `STRUCT(a AS a, b AS b)` | BQ uses STRUCT literal | `{{ sf_to_bq.object_construct(...) }}` |
| `ARRAY_CONSTRUCT(a, b, c)` | `[a, b, c]` | BQ uses array literal syntax | Simple replacement |
| `VARIANT` column type | `JSON` type | Snowflake VARIANT → BQ JSON (BQ 2023+) or `STRING` with JSON extraction | Prefer `JSON` type if target is BQ Enterprise |
| `OBJECT` column type | `STRUCT` or `JSON` | Depends on whether schema is fixed | Manual review — fixed schema → STRUCT, dynamic → JSON |
| `IFF(condition, true_val, false_val)` | `IF(condition, true_val, false_val)` | Different function name — same semantics | Simple replacement |
| `ZEROIFNULL(x)` | `IFNULL(x, 0)` | BQ equivalent | Simple replacement |
| `NULLIFZERO(x)` | `NULLIF(x, 0)` | BQ equivalent | Simple replacement |
| `NVL(x, y)` | `IFNULL(x, y)` | BQ equivalent | Simple replacement |
| `DECODE(x, v1, r1, v2, r2, default)` | `CASE WHEN x=v1 THEN r1 WHEN x=v2 THEN r2 ELSE default END` | BQ uses CASE — no DECODE | Regex/pattern replacement |
| `DATEADD(DAY, n, date_col)` | `DATE_ADD(date_col, INTERVAL n DAY)` | Argument order and syntax differ | `{{ sf_to_bq.dateadd('DAY', n, date_col) }}` |
| `DATEDIFF(DAY, date1, date2)` | `DATE_DIFF(date2, date1, DAY)` | Argument order differs — target minus source in BQ | `{{ sf_to_bq.datediff('DAY', date1, date2) }}` |
| `DATE_PART(MONTH, date_col)` | `EXTRACT(MONTH FROM date_col)` | Different syntax | Regex replacement |
| `DATE_TRUNC('MONTH', date_col)` | `DATE_TRUNC(date_col, MONTH)` | Argument order differs | Regex replacement |
| `TIMESTAMPDIFF(SECOND, ts1, ts2)` | `TIMESTAMP_DIFF(ts2, ts1, SECOND)` | Function name and argument order differ | `{{ sf_to_bq.timestampdiff('SECOND', ts1, ts2) }}` |
| `TRY_CAST(x AS INTEGER)` | `SAFE_CAST(x AS INT64)` | BQ uses SAFE_CAST for non-erroring casts | Simple replacement (with type translation) |
| `TRY_TO_DATE(x)` | `SAFE_CAST(x AS DATE)` | BQ equivalent | Simple replacement |
| `TRY_TO_TIMESTAMP(x)` | `SAFE_CAST(x AS TIMESTAMP)` | BQ equivalent | Simple replacement |
| `LISTAGG(col, ', ')` | `STRING_AGG(col, ', ')` | Different function name | Simple replacement |
| `LISTAGG(col, ', ') WITHIN GROUP (ORDER BY x)` | `STRING_AGG(col, ', ' ORDER BY x)` | BQ supports ORDER BY inside STRING_AGG | Pattern replacement |
| `MEDIAN(x)` | `PERCENTILE_CONT(x, 0.5) OVER ()` or `APPROX_QUANTILES(x, 2)[OFFSET(1)]` | BQ has no MEDIAN — use percentile approach | `{{ sf_to_bq.median(x) }}` macro |
| `QUALIFY ROW_NUMBER() OVER (...) = 1` | `... WHERE TRUE QUALIFY ROW_NUMBER() OVER (...) = 1` | QUALIFY is supported in BQ but requires a WHERE, GROUP BY or HAVING in the same query — add `WHERE TRUE` when there's no other filter | Pattern replacement |
| `PIVOT(SUM(x) FOR col IN (v1, v2))` | `PIVOT(SUM(x) FOR col IN (v1, v2))` | PIVOT syntax largely compatible | Minor syntax review |
| `UNPIVOT(val FOR col IN (c1, c2))` | `UNPIVOT(val FOR col IN (c1, c2))` | Compatible | Usually no change |
| `COPY INTO table FROM @stage` | Cannot replicate in dbt — this is a DML statement | COPY INTO is a Snowflake data loading command, not a SELECT | Remove from dbt models; document as a loading pattern |
| `@stage_name` (stage reference) | GCS/BQ External table or transfer service | Snowflake stages have no BQ equivalent in SQL | Requires architectural decision |
| `CREATE DYNAMIC TABLE ... TARGET_LAG = '1 minute'` | BQ materialized views with refresh | Dynamic tables are a Snowflake-specific feature | Evaluate per use case — BQ MVs may be equivalent |
| `SEARCH OPTIMIZATION` (table property) | No equivalent — BQ uses clustering | Snowflake SEARCH OPTIMIZATION is a table property | Document in target_setup; no SQL translation needed |
| `SNOWFLAKE.ACCOUNT_USAGE.*` queries | `region-us.INFORMATION_SCHEMA.*` | Different catalog for metadata queries | Manual — these are meta-queries, likely test/utility models |
| `UUID_STRING()` | `GENERATE_UUID()` | Different function name | Simple replacement |
| `TABLE(FLATTEN(arr))` in a CTE, then equi-join on `f.value` | `JOIN … ON x IN UNNEST(arr)` | BQ tests array membership inline in the join; SF must pre-flatten the array to a row set first | See example 04 — collapse the pre-flatten CTE; or dispatched `array_contains` macro for dual-target |
| `ARRAY_AGG(x)` | `ARRAY_AGG(x IGNORE NULLS)` | SF omits NULLs by default; BQ defaults to RESPECT NULLS and then errors (`Array cannot have a null element`) | See example 05 — always add `IGNORE NULLS` when porting an `ARRAY_AGG` |
| `ARRAY_AGG(PARSE_JSON(CONCAT('{"k":"', v, '"}')))` | `ARRAY_AGG(STRUCT(v AS k) IGNORE NULLS)` | SF builds record arrays as JSON strings; BQ has a native typed STRUCT array | See example 05 — prefer the native STRUCT; retire the JSON workaround |

## Macro-First Translation Strategy

Before translating a construct inline, decide *where the difference should live*. For a project that must run on both platforms during a parallel-run window, dialect logic belongs in macros, not scattered through model bodies behind `target.type` branches. The hierarchy — dbt built-in cross-database macro → `dbt_utils` → your own `adapter.dispatch` macro → `target.type` in a macro → `target.type` in a model (last resort) — and the full `dbt.*` built-in reference live in the shared [`../dbt_neutral_translation.md`](../dbt_neutral_translation.md). The array-membership join (example 04) and NULL-safe `ARRAY_AGG` (example 05) have no built-in equivalent, so each example's `notes.md` shows the dispatched-macro form.

## dbt Profile Changes

The target dbt profile must use the BigQuery adapter:

```yaml
# profiles.yml
target_bigquery:
  type: bigquery
  method: oauth
  project: "{{ env_var('BQ_PROJECT') }}"
  dataset: "{{ env_var('BQ_DATASET') }}"
  threads: 8
  timeout_seconds: 300
  location: US
  priority: interactive
```

## Known Limitations

- **COPY INTO / STAGE references**: No SQL equivalent in BigQuery. Models using COPY INTO must be redesigned as external table references or load procedures.
- **DYNAMIC TABLES**: BigQuery materialized views are not equivalent. Evaluate each dynamic table use case individually.
- **VARIANT/OBJECT columns**: Translation depends heavily on whether the schema is fixed or dynamic. Fixed schemas should use STRUCT; dynamic schemas should use BQ JSON type (Enterprise only) or STRING with JSON extraction.
- **Row access policies**: Snowflake row access policies translate to BigQuery row-level security filters, but the policy SQL must be rewritten in BigQuery dialect.
