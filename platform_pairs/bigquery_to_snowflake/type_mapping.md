# BigQuery → Snowflake Data Type Mapping

## Standard Type Mappings

| BigQuery Type | Snowflake Type | Notes |
|---------------|---------------|-------|
| `INT64` | `NUMBER(38, 0)` | BQ INT64 is 64-bit signed integer |
| `INTEGER` | `NUMBER(38, 0)` | Alias for INT64 |
| `INT` | `NUMBER(38, 0)` | Alias for INT64 |
| `SMALLINT` | `NUMBER(5, 0)` | |
| `BIGINT` | `NUMBER(38, 0)` | |
| `TINYINT` | `NUMBER(3, 0)` | |
| `BYTEINT` | `NUMBER(3, 0)` | |
| `FLOAT64` | `FLOAT` | IEEE 754 double — equivalent |
| `FLOAT` | `FLOAT` | Alias for FLOAT64 |
| `NUMERIC` | `NUMBER(38, 9)` | BQ default precision/scale |
| `NUMERIC(p, s)` | `NUMBER(p, s)` | Explicit precision/scale — preserve |
| `BIGNUMERIC` | `NUMBER(38, 18)` | BQ BIGNUMERIC: 76 digits, 38 fractional. Snowflake max is 38,18 — confirm no precision loss |
| `BIGNUMERIC(p, s)` | `NUMBER(p, s)` | Explicit — preserve but cap at Snowflake max (38) |
| `BOOL` | `BOOLEAN` | Direct equivalent |
| `BOOLEAN` | `BOOLEAN` | Same |
| `STRING` | `VARCHAR` | Snowflake VARCHAR is unlimited length by default |
| `STRING(n)` | `VARCHAR(n)` | Explicit length — preserve |
| `BYTES` | `BINARY` | Raw binary data |
| `BYTES(n)` | `BINARY(n)` | With length |
| `DATE` | `DATE` | Direct equivalent |
| `TIME` | `TIME` | Direct equivalent |
| `DATETIME` | `TIMESTAMP_NTZ` | BQ DATETIME has no timezone — maps to NTZ (no time zone) |
| `TIMESTAMP` | `TIMESTAMP_TZ` | BQ TIMESTAMP is UTC with timezone awareness — maps to TZ |
| `ARRAY<T>` | `ARRAY` | Snowflake ARRAY is semi-structured — type parameter is dropped |
| `STRUCT<fields>` | `OBJECT` or `VARIANT` | Simple named structs → OBJECT; nested/complex structs → VARIANT |
| `JSON` | `VARIANT` | Snowflake VARIANT handles arbitrary semi-structured data |
| `GEOGRAPHY` | `GEOGRAPHY` | Available in both. Verify spatial function equivalence separately |
| `INTERVAL` | Not directly supported | BQ INTERVAL literals in arithmetic must be converted to DATEADD/DATEDIFF |

## Precision and Scale Notes

- **BIGNUMERIC**: BigQuery supports up to 76 digits with 38 fractional digits. Snowflake's `NUMBER` type caps at 38 total digits. If your data uses the full BQ BIGNUMERIC range, Snowflake `FLOAT` may be required with an accepted precision loss. Flag these columns for manual review.
- **NUMERIC default**: BigQuery NUMERIC without explicit precision defaults to `NUMBER(29, 9)`. Snowflake equivalent is `NUMBER(38, 9)` (wider total digits, same scale).

## CAST Expression Translation

BigQuery `CAST` and `SAFE_CAST` translate as follows:

| BigQuery | Snowflake |
|----------|----------|
| `CAST(x AS INT64)` | `CAST(x AS NUMBER)` |
| `CAST(x AS STRING)` | `CAST(x AS VARCHAR)` |
| `CAST(x AS TIMESTAMP)` | `CAST(x AS TIMESTAMP_TZ)` |
| `CAST(x AS DATETIME)` | `CAST(x AS TIMESTAMP_NTZ)` |
| `SAFE_CAST(x AS INT64)` | `TRY_CAST(x AS NUMBER)` |
| `SAFE_CAST(x AS FLOAT64)` | `TRY_TO_DOUBLE(x)` |
| `SAFE_CAST(x AS DATE)` | `TRY_TO_DATE(x)` |
| `SAFE_CAST(x AS TIMESTAMP)` | `TRY_TO_TIMESTAMP_TZ(x)` |
