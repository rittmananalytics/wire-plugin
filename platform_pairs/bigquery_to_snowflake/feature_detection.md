# BigQuery Feature Detection Patterns

## Purpose

These regex and grep patterns identify BigQuery-specific SQL features in dbt model `.sql` files. Apply these patterns during the dbt audit to tag each model. Each tag maps to a translation pattern in `translation_guide.md`.

## Patterns

| Tag | Pattern | Description |
|-----|---------|-------------|
| `unnest` | `\bUNNEST\s*\(` | Array expansion using UNNEST |
| `in_unnest` | `\bIN\s+UNNEST\s*\(` | Array-membership join/filter — translates to Snowflake `ARRAY_CONTAINS(value::variant, array)`, args reversed (see example 05) |
| `struct_literal` | `\bSTRUCT\s*\(` | Struct constructor |
| `struct_dot_access` | `[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_]` | Multi-level dot notation (potential struct path access — review context) |
| `array_agg` | `\bARRAY_AGG\s*\(` | ARRAY_AGG — on Snowflake drop `IGNORE NULLS` (no-op); a `STRUCT` array becomes `ARRAY_AGG(OBJECT_CONSTRUCT(...))` (see example 06) |
| `array_agg_ordered` | `ARRAY_AGG\s*\([^)]+\)\s+WITHIN\|ARRAY_AGG\s*\([^)]+ORDER\s+BY` | Ordered ARRAY_AGG |
| `json_extract` | `\bJSON_EXTRACT\s*\(\|JSON_EXTRACT_SCALAR\s*\(` | JSON extraction functions |
| `json_value` | `\bJSON_VALUE\s*\(\|JSON_QUERY\s*\(` | JSON value/query functions |
| `timestamp_diff` | `\bTIMESTAMP_DIFF\s*\(` | Timestamp difference |
| `timestamp_add` | `\bTIMESTAMP_ADD\s*\(` | Timestamp addition |
| `timestamp_trunc` | `\bTIMESTAMP_TRUNC\s*\(` | Timestamp truncation |
| `date_trunc` | `\bDATE_TRUNC\s*\(` | Date truncation |
| `date_diff` | `\bDATE_DIFF\s*\(` | Date difference |
| `date_add` | `\bDATE_ADD\s*\(` | Date addition |
| `date_sub` | `\bDATE_SUB\s*\(` | Date subtraction |
| `qualify` | `\bQUALIFY\b` | QUALIFY clause (supported in both BQ and SF — but flag for review) |
| `column_except` | `\bEXCEPT\s*\(\s*[a-zA-Z]` | Column exclusion syntax (SELECT * EXCEPT) |
| `pivot` | `\bPIVOT\s*\(` | PIVOT transformation |
| `unpivot` | `\bUNPIVOT\s*\(` | UNPIVOT transformation |
| `ml_predict` | `\bML\.PREDICT\s*\(` | BigQuery ML prediction — no SF equivalent |
| `ml_functions` | `\bML\.[A-Z_]+\s*\(` | Any BigQuery ML function |
| `bignumeric` | `\bBIGNUMERIC\b` | BIGNUMERIC type usage |
| `geography` | `\bGEOGRAPHY\b\|ST_[A-Z_]+\s*\(' | Geography type or spatial functions |
| `generate_date_array` | `\bGENERATE_DATE_ARRAY\s*\(` | Date range generation |
| `generate_array` | `\bGENERATE_ARRAY\s*\(` | Integer range generation |
| `generate_uuid` | `\bGENERATE_UUID\s*\(\)` | UUID generation |
| `parse_date` | `\bPARSE_DATE\s*\(` | String-to-date parsing |
| `parse_timestamp` | `\bPARSE_TIMESTAMP\s*\(` | String-to-timestamp parsing |
| `format_date` | `\bFORMAT_DATE\s*\(` | Date formatting |
| `format_timestamp` | `\bFORMAT_TIMESTAMP\s*\(` | Timestamp formatting |
| `safe_cast` | `\bSAFE_CAST\s*\(` | Safe (non-erroring) type cast |
| `information_schema_bq` | `region-[a-z].*INFORMATION_SCHEMA\|`[a-z].*INFORMATION_SCHEMA` | BQ-style regional INFORMATION_SCHEMA queries |
| `partition_config` | `partition_by\s*=` | dbt partition_by config (BQ-style) |
| `cluster_config` | `cluster_by\s*=` | dbt cluster_by config |
| `backtick_ref` | `` `[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+` `` | Backtick fully-qualified references (BQ style) |
| `interval_literal` | `\bINTERVAL\s+[0-9]` | INTERVAL literal in arithmetic |

## Usage

To scan a model file and detect features, apply each pattern as a case-insensitive grep:

```bash
for pattern_tag in unnest struct_literal json_extract ...; do
  if grep -qi "<pattern>" "$model_file"; then
    echo "$pattern_tag"
  fi
done
```

During the dbt audit, the detected tags for each model are stored in the `feature_tags` column of `dbt_audit.csv`. The migration generate command uses these tags to select the appropriate translation patterns from `translation_guide.md`.

## Complexity Contribution

A model's complexity rating increases with the number and type of features detected:

- `ml_predict`, `ml_functions`: immediately Complex (requires architectural decision)
- `geography`: immediately Complex (spatial function equivalence requires manual review)
- `unnest`, `struct_literal`, `generate_date_array`, `generate_array`: contribute to Moderate → Complex threshold
- `bignumeric`: review for precision loss
- All others: contribute to Simple → Moderate threshold (see dbt_audit complexity rules)
