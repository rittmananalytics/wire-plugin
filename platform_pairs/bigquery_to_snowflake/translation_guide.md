# BigQuery → Snowflake Translation Guide

## Overview

This guide defines the canonical translation decisions for migrating SQL from BigQuery to Snowflake. Each entry covers: the source construct, the target equivalent, the decision rationale, and the macro or approach to use during dbt model translation.

## SQL Construct Translations

| Source (BigQuery) | Target (Snowflake) | Decision | Macro / Approach |
|-------------------|-------------------|----------|-----------------|
| `UNNEST(array_col)` with `CROSS JOIN` | `LATERAL FLATTEN(input => array_col)` | Snowflake uses FLATTEN for array expansion | `{{ bq_to_sf.unnest(array_col) }}` macro |
| `UNNEST(array_col) AS element` | `f.value AS element` (from FLATTEN alias `f`) | Alias syntax differs | Manual per model |
| `STRUCT(a, b, c)` | `OBJECT_CONSTRUCT('a', a, 'b', b, 'c', c)` | Snowflake uses OBJECT_CONSTRUCT for named structs | `{{ bq_to_sf.struct(...) }}` |
| `struct_col.field` (dot notation) | `struct_col:field` (colon path notation) | Snowflake uses colon for VARIANT path access | Find/replace with care around table refs |
| `ARRAY_AGG(x)` | `ARRAY_AGG(x)` | Same function name — no change needed | None |
| `ARRAY_AGG(x ORDER BY y)` | `ARRAY_AGG(x) WITHIN GROUP (ORDER BY y)` | ORDER BY clause position differs | Regex replacement |
| `JSON_EXTRACT(json_col, '$.field')` | `json_col:field::STRING` | Snowflake uses path notation for VARIANT | Manual review — structure-dependent |
| `JSON_EXTRACT_SCALAR(json_col, '$.field')` | `json_col:field::STRING` | Same as above | Manual review |
| `TIMESTAMP_DIFF(ts1, ts2, SECOND)` | `TIMESTAMPDIFF(SECOND, ts2, ts1)` | Argument order and function name differ | `{{ bq_to_sf.timestamp_diff(ts1, ts2, 'SECOND') }}` |
| `TIMESTAMP_ADD(ts, INTERVAL n SECOND)` | `DATEADD(SECOND, n, ts)` | BQ uses INTERVAL syntax, SF uses DATEADD | `{{ bq_to_sf.timestamp_add(ts, n, 'SECOND') }}` |
| `DATE_TRUNC(date_col, MONTH)` | `DATE_TRUNC('MONTH', date_col)` | Argument order differs | Regex replacement |
| `DATE_DIFF(date1, date2, DAY)` | `DATEDIFF(DAY, date2, date1)` | Argument order and name differ | Regex replacement |
| `DATE_ADD(date_col, INTERVAL n DAY)` | `DATEADD(DAY, n, date_col)` | BQ uses INTERVAL, SF uses DATEADD | Regex replacement |
| `GENERATE_DATE_ARRAY(start, end, INTERVAL 1 DAY)` | `(SELECT DATEADD(DAY, seq4(), start) FROM TABLE(GENERATOR(ROWCOUNT => DATEDIFF(DAY, start, end)+1)))` | No direct equivalent — generator table approach | `{{ bq_to_sf.generate_date_array(start, end) }}` macro |
| `GENERATE_ARRAY(0, 9)` | `(SELECT seq4() FROM TABLE(GENERATOR(ROWCOUNT => 10)))` | Similar generator approach | `{{ bq_to_sf.generate_array(start, stop) }}` macro |
| `GENERATE_UUID()` | `UUID_STRING()` | Different function name | Simple replacement |
| `PARSE_DATE('%Y-%m-%d', date_str)` | `TO_DATE(date_str, 'YYYY-MM-DD')` | Function name and format specifier syntax differ | Manual — format string must be translated |
| `PARSE_TIMESTAMP('%Y-%m-%dT%H:%M:%S', ts_str)` | `TO_TIMESTAMP(ts_str, 'YYYY-MM-DD"T"HH24:MI:SS')` | Similar — format string translation required | Manual |
| `FORMAT_DATE('%Y-%m', date_col)` | `TO_CHAR(date_col, 'YYYY-MM')` | Function and format specifier differ | Manual |
| `QUALIFY ROW_NUMBER() OVER (...) = 1` | `QUALIFY ROW_NUMBER() OVER (...) = 1` | QUALIFY supported in both — no change needed | None |
| `EXCEPT(col1, col2)` in SELECT | Not natively supported — must list columns explicitly | Snowflake lacks column exclusion syntax | Generate explicit column list from schema |
| `PIVOT(agg FOR col IN (val1, val2))` | `PIVOT(agg(x) FOR col IN (val1, val2))` | Minor syntax difference | Manual review |
| `UNPIVOT(value FOR col IN (col1, col2))` | `UNPIVOT(value FOR col IN (col1, col2))` | Same — no change | None |
| `ML.PREDICT(MODEL \`project.model\`, ...)` | No equivalent — must use Snowflake Cortex or external function | Requires architectural decision | Flag for manual replacement — document in migration_strategy |
| `INFORMATION_SCHEMA.TABLES` (BQ-style with backtick region prefix) | `INFORMATION_SCHEMA.TABLES` (Snowflake ACCOUNT_USAGE or per-database) | Context and catalog differ | Manual — these are meta-queries, likely test/utility models |
| `{{ config(partition_by=...) }}` | `{{ config(snowflake_warehouse=...) }}` + cluster_by | BQ partition → Snowflake clustering | dbt config block update |
| `{{ config(cluster_by=...) }}` | `{{ config(cluster_by=...) }}` | Same key — supported in both | Usually no change |

## dbt Profile Changes

The target dbt profile must use the Snowflake adapter:

```yaml
# profiles.yml
target_snowflake:
  type: snowflake
  account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
  user: "{{ env_var('SNOWFLAKE_USER') }}"
  private_key_path: "{{ env_var('SNOWFLAKE_PRIVATE_KEY_PATH') }}"
  database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
  warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
  schema: "{{ env_var('SNOWFLAKE_SCHEMA') }}"
  role: "{{ env_var('SNOWFLAKE_ROLE') }}"
  threads: 8
```

## Dispatch Overrides

Add to `dbt_project.yml` to override dbt_utils macros for Snowflake:

```yaml
dispatch:
  - macro_namespace: dbt_utils
    search_order: ['my_project', 'dbt_utils']
```

## Known Limitations

- **ML.PREDICT**: No Snowflake equivalent in standard SQL. Models using ML.PREDICT must be redesigned using Snowflake Cortex ML functions or removed from the dbt project.
- **GEOGRAPHY**: Coordinate systems differ between BigQuery (WGS84 spherical) and Snowflake (WGS84 planar for some functions). Spatial queries require validation.
- **BIGNUMERIC**: Translates to `NUMBER(38, 18)` — confirm precision is sufficient for the data.
- **Policy tags (column-level security)**: BigQuery policy tags have no direct Snowflake equivalent — translate to Snowflake dynamic data masking policies.
