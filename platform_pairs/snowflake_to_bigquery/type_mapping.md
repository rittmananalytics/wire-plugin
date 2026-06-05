# Snowflake → BigQuery Data Type Mapping

## Standard Type Mappings

| Snowflake Type | BigQuery Type | Notes |
|----------------|--------------|-------|
| `NUMBER(p, 0)` | `INT64` | Integer — use INT64 when scale is 0 and precision ≤ 18 |
| `NUMBER(p, 0)` (p > 18) | `NUMERIC` or `BIGNUMERIC` | For large integers, use NUMERIC or BIGNUMERIC |
| `NUMBER(p, s)` | `NUMERIC(p, s)` | BQ NUMERIC supports up to 29 total digits |
| `NUMBER(p, s)` (p > 29) | `BIGNUMERIC` | BQ BIGNUMERIC supports 76 digits |
| `DECIMAL(p, s)` | `NUMERIC(p, s)` | Alias for NUMBER |
| `INTEGER` | `INT64` | |
| `INT` | `INT64` | |
| `BIGINT` | `INT64` | |
| `SMALLINT` | `INT64` | BQ has no small integer type — use INT64 |
| `TINYINT` | `INT64` | Same |
| `BYTEINT` | `INT64` | Same |
| `FLOAT` | `FLOAT64` | IEEE 754 double |
| `FLOAT4` | `FLOAT64` | |
| `FLOAT8` | `FLOAT64` | |
| `DOUBLE` | `FLOAT64` | |
| `DOUBLE PRECISION` | `FLOAT64` | |
| `REAL` | `FLOAT64` | |
| `VARCHAR` | `STRING` | BQ STRING is UTF-8, unlimited length |
| `VARCHAR(n)` | `STRING` | BQ STRING does not enforce length — remove constraint |
| `CHAR(n)` | `STRING` | |
| `CHARACTER(n)` | `STRING` | |
| `NVARCHAR(n)` | `STRING` | |
| `TEXT` | `STRING` | |
| `STRING` | `STRING` | Direct equivalent |
| `BINARY` | `BYTES` | |
| `VARBINARY` | `BYTES` | |
| `BOOLEAN` | `BOOL` | |
| `DATE` | `DATE` | Direct equivalent |
| `TIME` | `TIME` | Direct equivalent |
| `TIMESTAMP_NTZ` | `DATETIME` | No timezone — maps to BQ DATETIME |
| `TIMESTAMP_LTZ` | `TIMESTAMP` | Local timezone — maps to BQ TIMESTAMP (UTC) |
| `TIMESTAMP_TZ` | `TIMESTAMP` | With timezone — maps to BQ TIMESTAMP |
| `TIMESTAMP` | `TIMESTAMP` | Snowflake TIMESTAMP default is TIMESTAMP_NTZ in most configs — verify |
| `DATETIME` | `DATETIME` | |
| `VARIANT` | `JSON` | BQ JSON type (BQ 2023+ Enterprise) or `STRING` |
| `OBJECT` | `JSON` or `STRUCT` | Fixed schema → STRUCT; dynamic → JSON |
| `ARRAY` | `ARRAY<...>` | BQ ARRAYs are typed — specify element type |
| `GEOGRAPHY` | `GEOGRAPHY` | Available in both — verify spatial function equivalence |

## Notes on Timestamp Handling

Snowflake has three timestamp types:
- `TIMESTAMP_NTZ`: No timezone (stores datetime as-is)
- `TIMESTAMP_LTZ`: Local timezone (stored as UTC, displayed in session timezone)
- `TIMESTAMP_TZ`: With timezone offset stored

BigQuery has two:
- `DATETIME`: No timezone
- `TIMESTAMP`: Always UTC

The safest mapping is `TIMESTAMP_NTZ → DATETIME` and `TIMESTAMP_LTZ / TIMESTAMP_TZ → TIMESTAMP`. Confirm the actual timezone handling in the source data before applying at scale.

## CAST Expression Translation

| Snowflake | BigQuery |
|----------|---------|
| `CAST(x AS VARCHAR)` | `CAST(x AS STRING)` |
| `CAST(x AS NUMBER)` | `CAST(x AS NUMERIC)` |
| `CAST(x AS INTEGER)` | `CAST(x AS INT64)` |
| `CAST(x AS FLOAT)` | `CAST(x AS FLOAT64)` |
| `CAST(x AS TIMESTAMP_NTZ)` | `CAST(x AS DATETIME)` |
| `CAST(x AS TIMESTAMP_TZ)` | `CAST(x AS TIMESTAMP)` |
| `TRY_CAST(x AS INTEGER)` | `SAFE_CAST(x AS INT64)` |
| `TRY_CAST(x AS VARCHAR)` | `SAFE_CAST(x AS STRING)` |
| `TO_VARCHAR(x)` | `CAST(x AS STRING)` |
| `TO_NUMBER(x)` | `CAST(x AS NUMERIC)` |
| `TO_DATE(x, fmt)` | `PARSE_DATE(bq_fmt, x)` (format string must be translated) |
| `TO_TIMESTAMP(x, fmt)` | `PARSE_TIMESTAMP(bq_fmt, x)` |
