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

## Deployment type-divergence patterns

Consumed by `specs/utils/deployment_type_preflight.md` (the W3 pre-flight shared by `dbt-migration-generate` and `equivalency-validate`). These are the constructs that build clean against a scratch/sample validation warehouse and error against the **real deployment warehouse** because its column *types* differ. Each fires only when the deployment column's actual type triggers it — the pre-flight reads the deployment `INFORMATION_SCHEMA`, never the validation warehouse's types.

| id | fires when (against deployment column types) | failure at deploy | fix hint | ref |
|---|---|---|---|---|
| `JSON_FN_ON_VARIANT` | a STRING-parse construct (`PARSE_JSON`, `TRY_PARSE_JSON`) applied to a column already `VARIANT`/`OBJECT` at deployment | redundant/erroring re-parse — validation warehouse stored it as STRING so the parse was needed there; deployment has it typed | drop the parse when the deployment column is already `VARIANT`/`OBJECT`; use path notation (`col:field`) directly | type_mapping.md |
| `VARIANT_ACCESS_ON_STRING` | colon path (`col:field`) or `:variant` access applied to a column that is `STRING`/`VARCHAR` at deployment | Snowflake cannot path-access a plain string — errors or returns NULL | `PARSE_JSON(col):field` (or `TRY_PARSE_JSON`) to parse the STRING first | type_mapping.md |
| `TZ_TYPE_MISMATCH` | a `TIMESTAMP_NTZ`/`TIMESTAMP_TZ`/`TIMESTAMP_LTZ` construct applied to a column whose deployment timestamp variant differs (e.g. BigQuery `DATETIME`→`TIMESTAMP_NTZ` vs `TIMESTAMP`→`TIMESTAMP_LTZ`) | wrong wall-clock/UTC interpretation, or a comparison across incompatible variants | pin the Snowflake timestamp variant to the deployment column's actual variant | type_mapping.md "Timestamp Handling" |
| `IMPLICIT_JOIN_COERCION` | a join predicate compares two columns whose deployment types differ where BigQuery coerced them | Snowflake's coercion rules differ — join errors or changes result set | emit an explicit `CAST` so both sides share the deployment type | translation_guide.md |
| `STRING_FN_ON_NONSTRING` | a string function (`TRIM`, `UPPER`, `LOWER`, `SUBSTR`, `SPLIT`, etc.) applied to a column that is **not** `VARCHAR`/`STRING` at deployment | Snowflake errors or implicitly coerces differently than BigQuery did | `CAST(col AS VARCHAR)` first, or confirm the deployment column type before assuming it is string | type_mapping.md |

## Edge-case runtime-failure patterns

Consumed by the W5 pre-PR faithfulness review (`dbt-migration-pre-pr-review`). These compile clean and pass a default-path full-refresh build, then hard-fail or silently diverge at runtime **only when a triggering row is present** — a blank string, a malformed JSON blob, a boundary value — which the equivalency sample often doesn't contain. Each names the offending translated construct and its runtime fix.

| id | detect (on translated Snowflake SQL) | runtime failure | fix hint |
|---|---|---|---|
| `CAST_BLANK_STRING_NUMERIC` | `CAST(<string expr> AS NUMBER/INT/FLOAT)` where the source (BigQuery `SAFE_CAST`) tolerated failure on a column that can be `''` | Snowflake `CAST('' AS NUMBER)` errors at runtime on the first blank row | use `TRY_CAST` / `TRY_TO_NUMBER` and handle the NULL, matching the source's tolerance |
| `UNGUARDED_JSON_PARSE` | `PARSE_JSON(x)` on a column that can hold malformed JSON, translated from `SAFE.PARSE_JSON` | errors at runtime on the first malformed row | `TRY_PARSE_JSON(...)` to null-on-error |
| `REGEX_ANCHOR_DRIFT` | `RLIKE`/`REGEXP_LIKE(...)` translated from BigQuery `REGEXP_CONTAINS` without loosening anchoring | under-matches — Snowflake `RLIKE` anchors the whole string, BigQuery `REGEXP_CONTAINS` is a substring search | drop the implicit full-string anchor (or add `.*...*.`) to restore substring semantics |

## Column governance / masking mechanisms

Consumed by the W4 governance equivalence check (`equivalency-validate`). Row-level equivalency cannot see column-level security: a column masked at source but landing unprotected at target produces identical rows, so equivalency passes while the security posture regresses. The check compares each translated column's protection at **target** against its protection at **source** and fails when a column protected at source is unprotected at target. These are the per-platform mechanisms it reads — the check itself is dialect-agnostic; only the mechanism names are per-pair.

| side | protection expressed as | where the check reads it |
|---|---|---|
| Source (BigQuery) | Policy tags (Data Catalog taxonomy + data policies); masking attaches to the tag, expressed in dbt as the column's `policy_tags` list | source column metadata: dbt `policy_tags`, or the deployed column's policy-tag binding via catalog |
| Target (Snowflake) | `CREATE MASKING POLICY` applied per column (`ALTER TABLE ... ALTER COLUMN ... SET MASKING POLICY`); expressed in dbt as `meta.masking_policy` on the column | translated companion YAML `meta.masking_policy`, or `INFORMATION_SCHEMA`/`ACCOUNT_USAGE` policy references |

**Expected protection** is derived from the source column's `policy_tags` binding. A source column carrying a policy tag is *expected protected*; the target column satisfies it when it carries a `meta.masking_policy` (or an equivalent target masking mechanism). A source column with no policy tag is not expected protected — the check does not demand masking it never had. BigQuery policy tags have no direct Snowflake equivalent, so the target-side mechanism is a dynamic data masking policy (see Known Limitations).

## Snapshot SCD mechanisms

Consumed by the snapshot object-type handling in `dbt-audit-generate` / `migration-inventory-generate` (catalog), `migration-strategy-generate` / `migration-register-generate` (strategy), `bulk-copy-migration-generate` (history copy), `dbt-migration-generate` (translate + continue), and `dbt-migration-validate` / `equivalency-validate` (test gate). A dbt snapshot is not a model — it is an SCD-2 history table whose rows accrete over time, so a lift-and-shift must move the *built history*, not just re-run the snapshot from empty (which would lose every closed version). The check itself is dialect-agnostic; only the meta-column *types* and the `dbt_scd_id` computation come from the pair. **Never hardcode these types in a command — read them here and from `type_mapping.md`.**

**SCD meta-column set (dbt-fixed names, pair-declared types).** dbt writes four meta columns onto every snapshot relation. The names are constants across every adapter — `dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to` — and must be preserved byte-for-byte, in this ordinal order, at the tail of the copied relation after the payload columns. Their types are pair-declared (resolved through `type_mapping.md`):

| meta column | meaning | source type (BigQuery) | target type (Snowflake) | nullable |
|---|---|---|---|---|
| `dbt_scd_id` | surrogate hash identifying a version row | `STRING` (32-char MD5 hex) | `VARCHAR` | no |
| `dbt_updated_at` | the version's updated-at value at snapshot time | mirrors the snapshot's `updated_at` column type (`DATETIME` → `TIMESTAMP_NTZ`, `TIMESTAMP` → `TIMESTAMP_TZ`) | per `type_mapping.md` temporal row | no |
| `dbt_valid_from` | when this version became current | same temporal type as `dbt_updated_at` | same | no |
| `dbt_valid_to` | when this version was superseded (`NULL` = current/open) | same temporal type as `dbt_updated_at` | same | yes |

**`dbt_scd_id` computation (the continuation-critical invariant).** dbt computes `dbt_scd_id` in the snapshot macro via `dbt.snapshot_hash_arguments` — an `MD5` over the concatenation of the resolved `unique_key` expression and, for the `timestamp` strategy, the `updated_at` value, or for the `check` strategy, the `check_cols` values. Both the `dbt-bigquery` and `dbt-snowflake` adapters use the same `MD5(coalesce(cast(<arg> as string/varchar), '') || '|' || …)` shape, so a row's `dbt_scd_id` recomputed at target equals the copied source value **only when every hash input casts to the identical string on both platforms**. Confirm before copying history that the `unique_key` and `updated_at`/`check_cols` inputs stringify identically under the pair's type translations. A changed strategy, `updated_at`, `unique_key`, or `check_cols` re-hashes `dbt_scd_id` and orphans the copied history — the snapshot config must stay byte-identical across the migration (enforced in `dbt-migration-generate`).

**Strategy inputs to catalog.** Each snapshot declares a `strategy` (`timestamp` or `check`), a `unique_key`, and either `updated_at` (timestamp) or `check_cols` (check), plus `invalidate_hard_deletes`. These are the inputs the catalog records and the copy/continue steps must preserve unchanged — they are the same inputs `dbt_scd_id` is hashed from, so any drift in them is a re-hash.

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
