# Snowflake Feature Detection Patterns

## Purpose

These regex and grep patterns identify Snowflake-specific SQL features in dbt model `.sql` files. Apply during the dbt audit to tag each model. Each tag maps to a translation pattern in `translation_guide.md`.

## Patterns

| Tag | Pattern | Description |
|-----|---------|-------------|
| `flatten` | `\bFLATTEN\s*\(` | FLATTEN function for array expansion |
| `lateral_flatten` | `LATERAL\s+FLATTEN\s*\(` | LATERAL FLATTEN (most common form) |
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

## Usage

Apply each pattern as a case-insensitive grep against each model's SQL file. Store results as comma-separated tags in `dbt_audit.csv` `feature_tags` column.

## Complexity Contribution

- `copy_into`, `stage_ref`, `dynamic_table`: immediately Complex (requires architectural decision — no SQL equivalent in BQ)
- `lateral_flatten`, `flatten`, `parse_json`, `colon_path`: contribute to Moderate → Complex threshold
- `object_construct`, `array_construct`, `variant_type`, `object_type`: Moderate (semi-structured data requires type decision)
- `iff`, `zeroifnull`, `nullifzero`, `nvl`, `dateadd`, `datediff`, `listagg`: Simple → Moderate (mechanical replacements)
- `account_usage`, `show_command`: flag separately — these are meta-queries, not data transformation models
