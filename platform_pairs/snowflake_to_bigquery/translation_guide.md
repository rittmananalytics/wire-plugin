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
| `PARSE_JSON(json_string)` | `PARSE_JSON(json_string, wide_number_mode => 'round')` or `SAFE.PARSE_JSON(...)` | BigQuery does have PARSE_JSON; use `SAFE.` to null-on-error. For extraction from a STRING column without parsing, use `JSON_VALUE`/`JSON_QUERY`. When the JSON contains large integers (IDs, epoch timestamps), add `wide_number_mode => 'round'` to avoid silent precision loss — BigQuery's default JSON number handling truncates large integers that exceed float64 precision. | See `translation_reference.md` §6 |
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
| `DIV0(a, b)` | `IF(b = 0, 0, SAFE_DIVIDE(a, b))` | Snowflake `DIV0(a, b) = IFF(b = 0, 0, a / b)`: it zeroes a zero **divisor** but **propagates NULL inputs** (NULL numerator or divisor → NULL, not 0). `IF(b = 0, 0, SAFE_DIVIDE(a, b))` matches both. Do **not** use `IFNULL(SAFE_DIVIDE(a, b), 0)` **or** the semantically identical `COALESCE(SAFE_DIVIDE(a, b), 0)` — both also coerce NULL inputs to 0, silently corrupting NULL-sensitive downstream logic; nor bare `SAFE_DIVIDE(a, b)` — it returns NULL on a zero divisor. | Pattern replacement |
| `DIV0NULL(a, b)` | `IF(b = 0 OR b IS NULL, 0, SAFE_DIVIDE(a, b))` | Snowflake `DIV0NULL(a, b)` returns 0 on a zero **or NULL** divisor; a NULL **numerator** still propagates. `IF(b = 0 OR b IS NULL, 0, SAFE_DIVIDE(a, b))` matches. Do **not** use `IFNULL(SAFE_DIVIDE(a, b), 0)` or `COALESCE(SAFE_DIVIDE(a, b), 0)` — they coerce a propagated NULL numerator to 0, which `DIV0NULL` never does; nor bare `SAFE_DIVIDE(a, b)` — it returns NULL on a zero divisor rather than 0. | Pattern replacement |
| `REGEXP_LIKE(x, p)` / `x RLIKE p` | `REGEXP_CONTAINS(x, r'^(?:p)$')` | Snowflake `REGEXP_LIKE`/`RLIKE` match the **whole** string; BigQuery `REGEXP_CONTAINS` matches a **substring**. Re-anchor the full pattern as `^(?:...)$` or a value merely *containing* a match passes where Snowflake returned false/NULL. Watch top-level alternation: `^a|b$` anchors only the outer branches — wrap as `^(?:a|b)$`. | Pattern replacement |
| `DECODE(x, v1, r1, v2, r2, default)` | `CASE WHEN x=v1 THEN r1 WHEN x=v2 THEN r2 ELSE default END` | BQ uses CASE — no DECODE | Regex/pattern replacement |
| `DATEADD(DAY, n, date_col)` | `DATE_ADD(date_col, INTERVAL n DAY)` | Argument order and syntax differ | `{{ sf_to_bq.dateadd('DAY', n, date_col) }}` |
| `DATEDIFF(DAY, date1, date2)` | `DATE_DIFF(date2, date1, DAY)` | Argument order differs — target minus source in BQ | `{{ sf_to_bq.datediff('DAY', date1, date2) }}` |
| `DATE_PART(MONTH, date_col)` | `EXTRACT(MONTH FROM date_col)` | Different syntax | Regex replacement |
| `DATE_TRUNC('MONTH', date_col)` | `DATE_TRUNC(date_col, MONTH)` | Argument order differs | Regex replacement |
| `TIMESTAMPDIFF(SECOND, ts1, ts2)` | `TIMESTAMP_DIFF(ts2, ts1, SECOND)` | Function name and argument order differ | `{{ sf_to_bq.timestampdiff('SECOND', ts1, ts2) }}` |
| `TRY_CAST(x AS INTEGER)` | `SAFE_CAST(x AS INT64)` | BQ uses SAFE_CAST for non-erroring casts | Simple replacement (with type translation) |
| `TRY_TO_DATE(x)` | `SAFE_CAST(x AS DATE)` | BQ equivalent | Simple replacement |
| `TRY_TO_TIMESTAMP(x)` | `SAFE_CAST(x AS TIMESTAMP)` | BQ equivalent | Simple replacement |
| `CAST(x AS NUMBER)` / `x::NUMBER` | `CAST(CAST(x AS NUMERIC) AS INT64)` | Snowflake `CAST(x AS NUMBER)` and the `::NUMBER` shorthand use scale 0 by default and **round** to the nearest integer. BigQuery's `CAST(x AS INT64)` **truncates** — producing different results on 0.5 boundaries. Use the two-step form to reproduce rounding. Do not use bare `CAST AS INT64` on a column that was `::NUMBER` in Snowflake. | Pattern replacement |
| `a = b` join predicate where types differ (e.g. STRING = INT64) | `CAST(a AS <matching_type>) = b` | Snowflake implicitly coerces STRING to NUMBER in join predicates; BigQuery does not — the join silently returns no rows or errors. For every join predicate, confirm both sides share the same BigQuery type and emit an explicit `CAST` where Snowflake relied on implicit coercion. Common case: `legacy_id` (INT64) joined to a substring expression (STRING). | Manual per join |
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

## Deployment type-divergence patterns

Consumed by `specs/utils/deployment_type_preflight.md` (the W3 pre-flight shared by `dbt-migration-generate` and `equivalency-validate`). These are the constructs that build clean against a scratch/sample validation warehouse and error against the **real deployment warehouse** because its column *types* differ. Each fires only when the deployment column's actual type triggers it — the pre-flight reads the deployment `INFORMATION_SCHEMA`, never the validation warehouse's types.

| id | fires when (against deployment column types) | failure at deploy | fix hint | ref |
|---|---|---|---|---|
| `TS_WRAP_ALREADY_TS` | `TIMESTAMP(col)` / `DATETIME(col)` wraps a column that is **already** `TIMESTAMP`/`DATETIME` at deployment | redundant or erroring cast — validation warehouse had it as STRING so the wrap was needed there; deployment has it typed, so the wrap errors or double-converts | drop the wrap when the deployment column is already the target temporal type | type_mapping.md "Timestamp Handling" |
| `JSON_FN_ON_STRING` | `PARSE_JSON`/`JSON_VALUE`/`JSON_QUERY`/`JSON_TYPE` applied to a column that is `STRING` at deployment (or a native-`JSON` accessor used where the column landed `STRING`) | JSON function rejects a STRING argument, or extracts nothing, depending on direction | align the accessor to the deployment column: `JSON_VALUE`/`JSON_QUERY` for STRING-stored JSON, native JSON functions only for a `JSON` column | translation_reference.md §6 |
| `JSON_FN_ON_JSON` | a STRING-oriented extraction (`JSON_VALUE`) applied to a column that is native `JSON` at deployment when a typed accessor was intended | silent type/precision surprise or wrong extraction | use the native-`JSON` accessor for a `JSON` column | translation_reference.md §6 |
| `IMPLICIT_JOIN_COERCION` | a join predicate compares two columns whose deployment types differ (e.g. `STRING = INT64`) where Snowflake implicitly coerced them | BigQuery does not coerce — the join errors or silently returns no rows | emit an explicit `CAST` so both sides share the deployment type (see the join-coercion row in "SQL Construct Translations") | translation_guide.md (join coercion row) |
| `STRING_FN_ON_NONSTRING` | a string function (`TRIM`, `UPPER`, `LOWER`, `LENGTH`, `SUBSTR`, `REGEXP_*`, `SPLIT`, `CONCAT` of a bare column) applied to a column that is **not** `STRING` at deployment — e.g. a bare `TRIM(id)` on an id that landed `INT64` | BigQuery has no signature for the string function on the deployment type and errors at first run; only type-verified columns (`_fivetran_synced`-style) are safe to assume | `CAST(col AS STRING)` first, or confirm the deployment column type — do not assume STRING for an id/numeric-looking column | translation_reference.md §5.3 |

## Edge-case runtime-failure patterns

Consumed by the W5 pre-PR faithfulness review (`dbt-migration-pre-pr-review`). These compile clean and pass a default-path full-refresh build, then hard-fail or silently diverge at runtime **only when a triggering row is present** — a blank string, a malformed JSON blob, a boundary value — which the equivalency sample often doesn't contain. Each names the offending translated construct and its runtime fix; several overlap with a `dbt-migration-lint` rule id and are cross-referenced so the two stay in lockstep.

| id | detect (on translated BigQuery SQL) | runtime failure | fix hint | lint rule |
|---|---|---|---|---|
| `CAST_BLANK_STRING_NUMERIC` | `CAST(<string expr> AS NUMERIC/INT64/FLOAT64)` where the source used a tolerant cast on a column that can be `''` | BigQuery `CAST('' AS NUMERIC)` errors at runtime the first time a blank/empty row is scanned; Snowflake tolerated it | use `SAFE_CAST` (NULL on failure) and handle the NULL, matching the source's tolerance | — |
| `UNGUARDED_JSON_PARSE` | any unguarded JSON accessor with no `SAFE.` prefix on a value that can be malformed or NULL — `PARSE_JSON(x)`, `JSON_VALUE(x, ...)`, `JSON_QUERY(x, ...)`, `JSON_EXTRACT*(x, ...)` | errors at runtime on the first malformed/NULL row, failing the whole (incremental) build where Snowflake yielded NULL | prefix `SAFE.` (`SAFE.PARSE_JSON`, `SAFE.JSON_VALUE`, …) to null-on-error; add `wide_number_mode => 'round'` on `PARSE_JSON` for large integers | — |
| `UNANCHORED_REGEX` | `REGEXP_CONTAINS(...)` translated from an anchored `REGEXP_LIKE`/`RLIKE` without `^(?:...)$` | over-matches — returns extra rows the source never matched | wrap the pattern `^(?:...)$` to restore whole-string anchoring | `REGEXP_ANCHOR` |
| `DIV0_NULL_COERCION` | a `DIV0`/`DIV0NULL` translation emitted as bare `SAFE_DIVIDE(a, b)`, `IFNULL(SAFE_DIVIDE(a, b), 0)`, or `COALESCE(SAFE_DIVIDE(a, b), 0)` rather than the faithful `IF(...)` form | silent divergence, severity **`error`** (not `warn`): the wrappers coerce NULL inputs to 0 and bare `SAFE_DIVIDE` returns NULL on a zero divisor, so NULL-sensitive downstream logic — data-quality / checksum guards — is corrupted with no runtime error and no divergent row in a sample that lacks a NULL/zero-divisor case | rewrite to `IF(b = 0, 0, SAFE_DIVIDE(a, b))` for `DIV0`, and `IF(b = 0 OR b IS NULL, 0, SAFE_DIVIDE(a, b))` for `DIV0NULL` | — |

## Deployment-integration / provenance defect patterns

Consumed by `dbt-migration-generate`'s inline deterministic-defect pass (Step 3.1 "Proactive deterministic-defect pass"), the `dbt-migration-lint` catalogue (rules 1–3), and `migration-drift-generate` (rule 4). These are the deploy-time defects a translated model can carry that compile clean and pass sampled equivalency in a **co-located validation warehouse**, yet break — or silently under-deliver — once the model runs under the **real deployment project split** and against the **live, moving source**. Each is deterministic to detect; the auto/propose/decision policy follows the `dbt-migration-fix` classifier. The pattern is declared here (pair); each command enforces it. The check itself is dialect-agnostic — only the marker names (the target-project reference shape, the CDC soft-delete column, the soft-delete filter form) are per-pair.

| id | detect (on translated BigQuery SQL / model config) | breaks at deploy | fix | policy | where |
|---|---|---|---|---|---|
| `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` | a new model whose dataset/folder is absent from the deployment orchestrator's model-selection manifest (pointer below) | the model translates, compiles, and passes equivalency, but the deployment orchestrator never builds it — it silently does not exist in production | add the model's dataset/folder to the deployment model-selection manifest | auto (only when the manifest pointer resolves; a **no-op** otherwise — never a false pass) | lint + generate |
| `HARDCODED_TARGET_DATABASE_XPROJECT` | a cross-project relation reference assembled from `{{ target.database }}` or a hardcoded target-project literal (e.g. `` `my-prod-project`.raw.orders ``) that should be a `source()` call | resolves in a co-located validation warehouse where everything shares one project; under the real deployment split the referenced data lives in another project, so the reference reads the wrong or an empty relation | rewrite the reference to `source('<source_name>', '<table>')` resolving to the correct pair source database | auto (downgrades to `propose` when the referenced relation cannot be mapped to a declared source) | lint + generate |
| `CDC_SOURCE_NO_SOFT_DELETE_FILTER` | a read of a CDC source carrying the pair's soft-delete marker (`_fivetran_deleted`) with no soft-delete filter | the validation sample rarely contains a soft-deleted row, so it passes; against the live source the model silently returns hard-deleted rows the source system has removed | inject the pair's soft-delete filter (`{{ filter_soft_deletes() }}` macro, or `WHERE NOT COALESCE(_fivetran_deleted, FALSE)`) | auto | lint + generate |
| `STALE_NULL_PAD_BRONZE_PRESENT` | a `CAST(NULL AS <type>)` column carrying a `-- MARKET GAP:` marker (generate Step 3.1 item b) whose named source column is now PRESENT and populated in the live source warehouse for the previously-missing market(s) | the model keeps synthesizing NULL for a column that now carries real data — a silent data gap that widens the longer the connector has been caught up | flag for restore — re-map to the now-present source column and re-translate | **flag only** (`decision` — restoring needs the real column mapping and type; never auto-rewritten) | migration-drift |

**Deployment model-selection manifest pointer (rule 1).** The manifest that decides which models the deployment orchestrator actually builds is engagement-specific — its location and shape depend on the orchestrator. Read a configurable pointer from `status.md`:

```yaml
migration:
  deployment_manifest:
    type: airflow_dataset_list | dbt_cloud_selector | dagster_selection   # the orchestrator flavour
    path: <engagement-relative path to the manifest / selector / DAG dataset-list file>
    selection_key: <the key or list within that file that enumerates the built datasets/folders>   # optional, type-dependent
```

When `deployment_manifest` is unset, or its `path` does not resolve, `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` is a documented **no-op** — recorded as an explicit coverage gap (`deployment manifest not configured — MODEL_NOT_REGISTERED_FOR_DEPLOYMENT not checked`), **never** a PASS. Detection when configured: a newly-translated model whose dataset/folder is not present in the resolved selection. Auto-fix: add the folder to the selection (a deterministic edit to the manifest file); if the manifest resolves but cannot be written (read-only path), downgrade to `propose` with the exact line to add.

**Cross-project reference detection (rule 2).** In snowflake→bigquery, the defect shape is a relation reference assembled from `{{ target.database }}` (or a hardcoded target-project literal) qualifying a table in another project. In a co-located validation warehouse the project resolves fine; under the real deployment split the source data lives in a different project, so the reference reads the wrong — or an empty — relation. The faithful form is a `source()` call whose `sources.yml` entry names the correct deployment source database. When the referenced relation cannot be mapped to a declared source, the fix downgrades from `auto` to `propose` (the source mapping is a judgment).

**CDC soft-delete marker + filter (rule 3).** Fivetran-landed CDC sources carry a soft-delete marker column `_fivetran_deleted` (BOOLEAN): a hard-deleted upstream row is retained with `_fivetran_deleted = TRUE`, not physically removed. A staging read of such a source with no soft-delete filter silently includes deleted rows. The pair's soft-delete filter is the dispatched `{{ filter_soft_deletes() }}` macro where the project defines one, else `WHERE NOT COALESCE(_fivetran_deleted, FALSE)`. Detection: a `source(...)`/`ref(...)` read of a relation whose schema carries `_fivetran_deleted` with no such filter in the model. The fix is deterministic and behaviour-restoring → `auto`.

**Stale NULL-pad marker (rule 4, migration-drift only).** generate Step 3.1 item b substitutes `CAST(NULL AS <type>) /* -- MARKET GAP: <col> not present in <markets> ... */` for a source column absent in one or more markets at translation time. That column can later land in the source (the connector catches up). `migration-drift` — which already runs against a moving source and knows each model's `last_migrated_commit` from the register — detects a `-- MARKET GAP:` NULL-pad whose named source column is now PRESENT and populated in the live source warehouse for the previously-missing market(s), and flags it for restore. It is **never auto-rewritten**: restoring needs the real column mapping and type, a human/re-translate decision.

## Column governance / masking mechanisms

Consumed by the W4 governance equivalence check (`equivalency-validate`). Row-level equivalency cannot see column-level security: a column masked at source but landing unprotected at target produces identical rows, so equivalency passes while the security posture regresses. The check compares each translated column's protection at **target** against its protection at **source** and fails when a column protected at source is unprotected at target. These are the per-platform mechanisms it reads — the check itself is dialect-agnostic; only the mechanism names are per-pair.

| side | protection expressed as | where the check reads it |
|---|---|---|
| Source (Snowflake) | `CREATE MASKING POLICY` applied per column (`ALTER TABLE ... ALTER COLUMN ... SET MASKING POLICY`); named in dbt as `meta.masking_policy` on the column | source column metadata: dbt `meta.masking_policy`, or `INFORMATION_SCHEMA`/`ACCOUNT_USAGE` policy references |
| Target (BigQuery) | Policy tags (Data Catalog taxonomy + data policies); masking attaches to the tag, expressed in dbt as the column's `policy_tags` list | translated companion YAML `policy_tags`, or the deployed column's policy-tag binding via `INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` / catalog |

**Expected protection** is derived from the source column's `meta.masking_policy` (the same value `dbt-migration-generate` Step 3b item 4 maps to a target policy tag via the PII tag map). A source column carrying a `meta.masking_policy` is *expected protected*; the target column satisfies it when it carries a `policy_tags` binding (or an equivalent target masking mechanism). A source column with no masking policy is not expected protected — the check does not demand tags it never had. See `translation_reference.md` §16 for the full mechanism mapping and why `CURRENT_ROLE()`-branching policies need a rebuild rather than a mechanical translation.

## Schema-parity / column-order

Consumed by the W6b column-order comparison in the schema-equivalence check (`equivalency-validate` check type 2 and `dbt-migration-generate` Check B) and surfaced by `dbt-migration-pre-pr-review`. Row-level equivalency proves the same rows come out; it cannot see that the **columns are in the same ordinal order** as the source. A reordered projection — or an unpinned `SELECT *` (see `UNPINNED_SELECT_STAR` in the lint catalogue and §11.27) that gains, loses, or reorders columns as the upstream evolves — passes a set-based schema check while breaking positional consumers: UNION/INSERT by position, CSV/SAR exports, BI and reverse-ETL pinned to column order. A lift-and-shift's schema-parity contract includes order.

**The comparison.** Read `SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.COLUMNS ... ORDER BY ordinal_position` on both platforms and compare the **sequences**, not just set membership. Source columns must appear first, in source ordinal order; any migration-added columns follow, at the tail, in the order below. A positional mismatch — the set matches (all source columns present, every tail column allow-listed) but the order differs — is an `error`, reason `column_order_drift`. Because it is a pure reorder, it is deterministic and parity-restoring, so `dbt-migration-fix` applies it automatically.

**Migration-appended tail allow-list.** These are the column categories a migration legitimately adds after the source columns; they are allowed at the tail (in this category order) before the sequence is compared. The categories are pair-declared and generalise; the concrete column names are supplied by the engagement override (`.wire/engagement/platform_pair_overrides/snowflake_to_bigquery/`), since they are client-specific:

| order | category | what it is | name source |
|---|---|---|---|
| 1 | audit / load-timestamp columns | columns the target loader/ELT stamps on every row (e.g. a `_<loader>_loaded_at` / `_<loader>_synced_at` pair) | engagement override — exact names per client loader |
| 2 | region / surrogate globalize keys | keys added when a per-region source is globalised into one target table (e.g. a `country`/region column, then a globalised surrogate `<entity>_id`) | engagement override — per multi-region model |

A column that is neither a source column nor an allow-listed tail column (an unexpected column), or a missing source column, is the schema check's existing extra/missing-columns FAIL — a set mismatch, escalated because adding or dropping a column is intent-dependent — not `column_order_drift`.

**Per-model waiver.** An intentional, data-owner-signed-off reorder is recorded per model as `column_order_waived: <reason>` in the migration register (or the model's `meta`). A waiver suppresses `column_order_drift` for that model only. It is mandatory by default and waivable per model — never globally disabled, so a reorder is always either parity-verified or explicitly on the record.

## Snapshot SCD mechanisms

Consumed by the snapshot object-type handling in `dbt-audit-generate` / `migration-inventory-generate` (catalog), `migration-strategy-generate` / `migration-register-generate` (strategy), `bulk-copy-migration-generate` (history copy), `dbt-migration-generate` (translate + continue), and `dbt-migration-validate` / `equivalency-validate` (test gate). A dbt snapshot is not a model — it is an SCD-2 history table whose rows accrete over time, so a lift-and-shift must move the *built history*, not just re-run the snapshot from empty (which would lose every closed version). The check itself is dialect-agnostic; only the meta-column *types* and the `dbt_scd_id` computation come from the pair. **Never hardcode these types in a command — read them here and from `type_mapping.md`.**

**SCD meta-column set (dbt-fixed names, pair-declared types).** dbt writes four meta columns onto every snapshot relation. The names are constants across every adapter — `dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to` — and must be preserved byte-for-byte, in this ordinal order, at the tail of the copied relation after the payload columns. Their types are pair-declared (resolved through `type_mapping.md`):

| meta column | meaning | source type (Snowflake) | target type (BigQuery) | nullable |
|---|---|---|---|---|
| `dbt_scd_id` | surrogate hash identifying a version row | `VARCHAR` (32-char MD5 hex) | `STRING` | no |
| `dbt_updated_at` | the version's updated-at value at snapshot time | mirrors the snapshot's `updated_at` column type (`TIMESTAMP_NTZ` → `DATETIME`, `TIMESTAMP_TZ`/`TIMESTAMP_LTZ` → `TIMESTAMP`) | per `type_mapping.md` temporal row | no |
| `dbt_valid_from` | when this version became current | same temporal type as `dbt_updated_at` | same | no |
| `dbt_valid_to` | when this version was superseded (`NULL` = current/open) | same temporal type as `dbt_updated_at` | same | yes |

**`dbt_scd_id` computation (the continuation-critical invariant).** dbt computes `dbt_scd_id` in the snapshot macro via `dbt.snapshot_hash_arguments` — an `MD5` over the concatenation of the resolved `unique_key` expression and, for the `timestamp` strategy, the `updated_at` value, or for the `check` strategy, the `check_cols` values. Both the `dbt-snowflake` and `dbt-bigquery` adapters use the same `MD5(coalesce(cast(<arg> as string/varchar), '') || '|' || …)` shape, so a row's `dbt_scd_id` recomputed at target equals the copied source value **only when every hash input casts to the identical string on both platforms**. Confirm before copying history that the `unique_key` and `updated_at`/`check_cols` inputs stringify identically under the pair's type translations (watch `NUMBER`-scale rounding, `TIMESTAMP_NTZ → DATETIME` precision, and NULL-vs-empty-string). A changed strategy, `updated_at`, `unique_key`, or `check_cols` re-hashes `dbt_scd_id` and orphans the copied history — the snapshot config must stay byte-identical across the migration (enforced in `dbt-migration-generate`).

**Strategy inputs to catalog.** Each snapshot declares a `strategy` (`timestamp` or `check`), a `unique_key`, and either `updated_at` (timestamp) or `check_cols` (check), plus `invalidate_hard_deletes`. These are the inputs the catalog records and the copy/continue steps must preserve unchanged — they are the same inputs `dbt_scd_id` is hashed from, so any drift in them is a re-hash.

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
