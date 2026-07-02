# Snowflake Feature Detection Patterns

## Purpose

These regex and grep patterns identify Snowflake-specific SQL features in dbt model `.sql` files. Apply during the dbt audit to tag each model. Each tag maps to a translation pattern in `translation_guide.md`.

## Patterns

| Tag | Pattern | Description |
|-----|---------|-------------|
| `flatten` | `\bFLATTEN\s*\(` | FLATTEN function for array expansion |
| `lateral_flatten` | `LATERAL\s+FLATTEN\s*\(` | LATERAL FLATTEN (most common form) |
| `flatten_join` | `TABLE\s*\(\s*FLATTEN\s*\(` | FLATTEN table-function form — commonly a pre-flatten CTE for an array-membership join (becomes `IN UNNEST`; see example 04) |
| `array_agg` | `\bARRAY_AGG\s*\(` | ARRAY_AGG — review NULL handling; BigQuery needs `IGNORE NULLS` to match Snowflake's default and avoid a runtime error (see example 05) |
| `parse_json` | `\bPARSE_JSON\s*\(` | JSON string parsing |
| `get_path` | `\bGET_PATH\s*\(\|::VARIANT\b` | VARIANT path access via GET_PATH |
| `colon_path` | `[a-zA-Z_][a-zA-Z0-9_]*:[a-zA-Z_]` | Colon path notation for VARIANT/OBJECT access |
| `object_construct` | `\bOBJECT_CONSTRUCT\s*\(` | Object literal construction |
| `array_construct` | `\bARRAY_CONSTRUCT\s*\(` | Array literal construction |
| `variant_type` | `\bVARIANT\b` | VARIANT type usage |
| `object_type` | `\bOBJECT\b` | OBJECT type usage |
| `iff` | `\bIFF\s*\(` | IFF conditional function |
| `zeroifnull` | `\bZEROIFNULL\s*\(` | ZEROIFNULL null replacement |
| `nullifzero` | `\bNULLIFZERO\s*\(` | NULLIFZERO null conversion |
| `nvl` | `\bNVL\s*\(` | NVL null replacement |
| `nvl2` | `\bNVL2\s*\(` | NVL2 conditional null |
| `decode` | `\bDECODE\s*\(` | DECODE conditional |
| `dateadd` | `\bDATEADD\s*\(` | Date/timestamp addition |
| `datediff` | `\bDATEDIFF\s*\(` | Date/timestamp difference |
| `date_part` | `\bDATE_PART\s*\(` | Date part extraction |
| `date_trunc_sf` | `DATE_TRUNC\s*\(\s*'` | Snowflake DATE_TRUNC (string as first arg) |
| `timestampdiff` | `\bTIMESTAMPDIFF\s*\(` | Timestamp difference (SECOND/MINUTE/etc.) |
| `try_cast` | `\bTRY_CAST\s*\(` | Safe casting |
| `try_to_date` | `\bTRY_TO_DATE\s*\(` | Safe date conversion |
| `try_to_timestamp` | `\bTRY_TO_TIMESTAMP\s*\(` | Safe timestamp conversion |
| `listagg` | `\bLISTAGG\s*\(` | List aggregation |
| `median` | `\bMEDIAN\s*\(` | Median aggregation |
| `qualify` | `\bQUALIFY\b` | QUALIFY clause |
| `pivot` | `\bPIVOT\s*\(` | PIVOT transformation |
| `unpivot` | `\bUNPIVOT\s*\(` | UNPIVOT transformation |
| `copy_into` | `\bCOPY\s+INTO\b` | COPY INTO data load statement |
| `stage_ref` | `@[a-zA-Z_][a-zA-Z0-9_./]*` | Stage reference (@stage_name) |
| `dynamic_table` | `\bDYNAMIC\s+TABLE\b` | Dynamic table creation/reference |
| `search_optimization` | `SEARCH\s+OPTIMIZATION` | Search optimization table property |
| `account_usage` | `SNOWFLAKE\.ACCOUNT_USAGE` | Snowflake ACCOUNT_USAGE schema queries |
| `uuid_string` | `\bUUID_STRING\s*\(\)` | UUID generation |
| `within_group` | `\bWITHIN\s+GROUP\s*\(` | WITHIN GROUP aggregate clause |
| `timestamp_ntz` | `\bTIMESTAMP_NTZ\b` | NTZ timestamp type |
| `timestamp_ltz` | `\bTIMESTAMP_LTZ\b` | LTZ timestamp type |
| `timestamp_tz` | `\bTIMESTAMP_TZ\b` | TZ timestamp type |
| `show_command` | `^\s*SHOW\s+` | SHOW metadata commands |
| `sample_clause` | `\bSAMPLE\s*\(\|TABLESAMPLE\s*\(` | Table sampling |
| `ilike` | `\bILIKE\b` | Case-insensitive LIKE — BigQuery needs LOWER()/REGEXP_CONTAINS rewrite |
| `ilike_any` | `\bILIKE\s+ANY\b` | ILIKE against a list of patterns — no direct BigQuery equivalent |
| `like_all` | `\bLIKE\s+ALL\b` | LIKE against all of a list of patterns — no direct BigQuery equivalent |
| `rlike` | `\bRLIKE\b` | Regex match operator — becomes REGEXP_CONTAINS |
| `regexp_substr_multiarg` | `\bREGEXP_SUBSTR\s*\(([^,()]*(\([^()]*\))?[^,()]*,){3,}` | REGEXP_SUBSTR with 4+ arguments (position/occurrence/parameters) — Snowflake's multi-arg form has no direct BigQuery equivalent |
| `object_agg` | `\bOBJECT_AGG\s*\(` | Key-value aggregation into OBJECT — needs JSON/STRUCT rewrite |
| `create_function_udf` | `CREATE\s+(OR\s+REPLACE\s+)?FUNCTION[\s\S]*?LANGUAGE\s+(JAVASCRIPT\|PYTHON\|SQL)` | UDF DDL (`CREATE FUNCTION ... LANGUAGE JAVASCRIPT/PYTHON/SQL`) — JS/Snowpark UDFs need redesign, not translation |

## Usage

Apply each pattern as a case-insensitive grep against each model's SQL file. Store results as comma-separated tags in `dbt_audit.csv` `feature_tags` column.

Each pattern is a single-construct, line-based match — they do not span lines (exception: `create_function_udf`, which spans from the `CREATE FUNCTION` to its `LANGUAGE` clause). Some patterns are only meaningful in combination: a model tagged both `array_agg` and `parse_json` is building a record array as JSON (`ARRAY_AGG(PARSE_JSON(...))`), which translates to a native BigQuery `ARRAY_AGG(STRUCT(...))` — see example 05. Read co-occurring tags together when selecting translation patterns.

## Macro-Layer Usage

These same patterns apply to macro bodies (`macros/**/*.sql`), not only model files. They are the basis for the dbt audit's macro-flagging step (`specs/migration/dbt_audit/generate.md` Step 5): any macro with at least one hit joins the NEEDS-translation set and is then classified by action (`translate` / `redesign` / `manual-review-out-of-scope`). Categories a model-only scan misses live almost entirely in the macro layer: the `fn_*` UDF-DDL layer (`create_function_udf`), key-value aggregation (`object_agg`, `within_group`, VARIANT colon-path access), and the pattern-matching family (`ilike`, `ilike_any`, `like_all`, `rlike`, `regexp_substr_multiarg`).

## Complexity Contribution

- `copy_into`, `stage_ref`, `dynamic_table`: immediately Complex (requires architectural decision — no SQL equivalent in BQ)
- `lateral_flatten`, `flatten`, `parse_json`, `colon_path`: contribute to Moderate → Complex threshold
- `object_construct`, `array_construct`, `variant_type`, `object_type`: Moderate (semi-structured data requires type decision)
- `iff`, `zeroifnull`, `nullifzero`, `nvl`, `dateadd`, `datediff`, `listagg`: Simple → Moderate (mechanical replacements)
- `flatten_join`: Moderate (structural rewrite — the join shape changes, not just function names; see example 04)
- `array_agg` co-occurring with `parse_json`: Moderate — a record array built as JSON (`ARRAY_AGG(PARSE_JSON(...))`) that becomes a native `ARRAY_AGG(STRUCT(...))` on BigQuery (see example 05)
- `array_agg`: Simple, but a silent-failure flag — a bare port drops `IGNORE NULLS` and fails at runtime on the first NULL
- `account_usage`, `show_command`: flag separately — these are meta-queries, not data transformation models
