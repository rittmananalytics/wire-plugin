# SQL Dialect Differences: BigQuery, Snowflake, Databricks

Comprehensive reference for translating SQL between the three platforms supported by Rittman Analytics. Organized by function category.

---

## Date and Time Functions

### Date Arithmetic

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Add days to date | `DATE_ADD(d, INTERVAL 7 DAY)` | `DATEADD(day, 7, d)` | `date_add(d, 7)` |
| Subtract days from date | `DATE_SUB(d, INTERVAL 7 DAY)` | `DATEADD(day, -7, d)` | `date_sub(d, 7)` |
| Add months | `DATE_ADD(d, INTERVAL 3 MONTH)` | `DATEADD(month, 3, d)` | `add_months(d, 3)` |
| Add years | `DATE_ADD(d, INTERVAL 1 YEAR)` | `DATEADD(year, 1, d)` | `add_months(d, 12)` |
| Add hours to timestamp | `TIMESTAMP_ADD(ts, INTERVAL 2 HOUR)` | `DATEADD(hour, 2, ts)` | `ts + INTERVAL 2 HOURS` |
| Date difference (days) | `DATE_DIFF(d1, d2, DAY)` | `DATEDIFF(day, d2, d1)` | `datediff(d1, d2)` |
| Date difference (months) | `DATE_DIFF(d1, d2, MONTH)` | `DATEDIFF(month, d2, d1)` | `months_between(d1, d2)` |
| Timestamp difference (seconds) | `TIMESTAMP_DIFF(ts1, ts2, SECOND)` | `DATEDIFF(second, ts2, ts1)` | `unix_timestamp(ts1) - unix_timestamp(ts2)` |

**Note on argument order:**
- BigQuery `DATE_DIFF`: `(end_date, start_date, part)` — end first
- Snowflake `DATEDIFF`: `(part, start_date, end_date)` — start first
- Databricks `datediff`: `(end_date, start_date)` — end first, days only

### Date Truncation

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Truncate to day | `DATE_TRUNC(d, DAY)` | `DATE_TRUNC('day', d)` | `date_trunc('day', d)` |
| Truncate to week | `DATE_TRUNC(d, WEEK)` | `DATE_TRUNC('week', d)` | `date_trunc('week', d)` |
| Truncate to month | `DATE_TRUNC(d, MONTH)` | `DATE_TRUNC('month', d)` | `date_trunc('month', d)` |
| Truncate to quarter | `DATE_TRUNC(d, QUARTER)` | `DATE_TRUNC('quarter', d)` | `date_trunc('quarter', d)` |
| Truncate to year | `DATE_TRUNC(d, YEAR)` | `DATE_TRUNC('year', d)` | `date_trunc('year', d)` |

**Key difference:** BigQuery uses bare keywords (`MONTH`), Snowflake and Databricks use quoted strings (`'month'`).

### Date Extraction

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Year | `EXTRACT(YEAR FROM d)` | `EXTRACT(YEAR FROM d)` or `YEAR(d)` | `year(d)` or `extract(YEAR FROM d)` |
| Month | `EXTRACT(MONTH FROM d)` | `EXTRACT(MONTH FROM d)` or `MONTH(d)` | `month(d)` |
| Day | `EXTRACT(DAY FROM d)` | `EXTRACT(DAY FROM d)` or `DAY(d)` | `day(d)` |
| Day of week | `EXTRACT(DAYOFWEEK FROM d)` | `DAYOFWEEK(d)` | `dayofweek(d)` |
| Day of year | `EXTRACT(DAYOFYEAR FROM d)` | `DAYOFYEAR(d)` | `dayofyear(d)` |
| Week number | `EXTRACT(WEEK FROM d)` | `WEEKOFYEAR(d)` | `weekofyear(d)` |
| Hour | `EXTRACT(HOUR FROM ts)` | `EXTRACT(HOUR FROM ts)` or `HOUR(ts)` | `hour(ts)` |

**Warning:** Day-of-week numbering differs:
- BigQuery: Sunday = 1, Saturday = 7
- Snowflake: Depends on `WEEK_START` parameter (default: Monday = 0)
- Databricks: Sunday = 1, Saturday = 7

### Date Formatting and Parsing

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Format date | `FORMAT_DATE('%Y-%m-%d', d)` | `TO_CHAR(d, 'YYYY-MM-DD')` | `date_format(d, 'yyyy-MM-dd')` |
| Format timestamp | `FORMAT_TIMESTAMP('%Y-%m-%d %H:%M:%S', ts)` | `TO_CHAR(ts, 'YYYY-MM-DD HH24:MI:SS')` | `date_format(ts, 'yyyy-MM-dd HH:mm:ss')` |
| Parse date from string | `PARSE_DATE('%Y-%m-%d', s)` | `TO_DATE(s, 'YYYY-MM-DD')` | `to_date(s, 'yyyy-MM-dd')` |
| Parse timestamp | `PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', s)` | `TO_TIMESTAMP(s, 'YYYY-MM-DD HH24:MI:SS')` | `to_timestamp(s, 'yyyy-MM-dd HH:mm:ss')` |
| String to date (auto) | `CAST(s AS DATE)` | `CAST(s AS DATE)` | `CAST(s AS DATE)` |

**Format code differences:**

| Meaning | BigQuery | Snowflake | Databricks |
|---------|----------|-----------|------------|
| 4-digit year | `%Y` | `YYYY` | `yyyy` |
| 2-digit month | `%m` | `MM` | `MM` |
| 2-digit day | `%d` | `DD` | `dd` |
| 24-hour | `%H` | `HH24` | `HH` |
| Minute | `%M` | `MI` | `mm` |
| Second | `%S` | `SS` | `ss` |
| Month name | `%B` | `MMMM` | `MMMM` |
| Abbreviated month | `%b` | `MON` | `MMM` |

### Date Construction

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Date from parts | `DATE(2024, 1, 15)` | `DATE_FROM_PARTS(2024, 1, 15)` | `make_date(2024, 1, 15)` |
| Timestamp from parts | `TIMESTAMP(DATE(2024,1,15))` | `TIMESTAMP_FROM_PARTS(2024,1,15,0,0,0)` | `make_timestamp(2024,1,15,0,0,0)` |
| Last day of month | `LAST_DAY(d, MONTH)` | `LAST_DAY(d)` | `last_day(d)` |
| Generate date array | `GENERATE_DATE_ARRAY(start, end, INTERVAL 1 DAY)` | Use `GENERATOR` with `ROW_NUMBER` | `sequence(start, end, INTERVAL 1 DAY)` |

---

## String Functions

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Concatenate | `CONCAT(a, b, c)` | `CONCAT(a, b, c)` | `concat(a, b, c)` |
| Concat with separator | `ARRAY_TO_STRING([a,b,c], ',')` | `CONCAT_WS(',', a, b, c)` | `concat_ws(',', a, b, c)` |
| Substring | `SUBSTR(s, pos, len)` | `SUBSTR(s, pos, len)` | `substring(s, pos, len)` |
| Left N chars | `LEFT(s, n)` | `LEFT(s, n)` | `left(s, n)` |
| Right N chars | `RIGHT(s, n)` | `RIGHT(s, n)` | `right(s, n)` |
| Character length | `LENGTH(s)` | `LENGTH(s)` | `length(s)` |
| Byte length | `BYTE_LENGTH(s)` | `OCTET_LENGTH(s)` | `octet_length(s)` |
| Upper case | `UPPER(s)` | `UPPER(s)` | `upper(s)` |
| Lower case | `LOWER(s)` | `LOWER(s)` | `lower(s)` |
| Title case | `INITCAP(s)` | `INITCAP(s)` | `initcap(s)` |
| Trim both | `TRIM(s)` | `TRIM(s)` | `trim(s)` |
| Trim leading | `LTRIM(s)` | `LTRIM(s)` | `ltrim(s)` |
| Trim trailing | `RTRIM(s)` | `RTRIM(s)` | `rtrim(s)` |
| Pad left | `LPAD(s, len, pad)` | `LPAD(s, len, pad)` | `lpad(s, len, pad)` |
| Pad right | `RPAD(s, len, pad)` | `RPAD(s, len, pad)` | `rpad(s, len, pad)` |
| Replace | `REPLACE(s, old, new)` | `REPLACE(s, old, new)` | `replace(s, old, new)` |
| Reverse | `REVERSE(s)` | `REVERSE(s)` | `reverse(s)` |
| Repeat | `REPEAT(s, n)` | `REPEAT(s, n)` | `repeat(s, n)` |
| Find position | `STRPOS(s, substr)` | `POSITION(substr IN s)` or `CHARINDEX(substr, s)` | `locate(substr, s)` or `instr(s, substr)` |
| Regex extract | `REGEXP_EXTRACT(s, r)` | `REGEXP_SUBSTR(s, r)` | `regexp_extract(s, r, 0)` |
| Regex extract group | `REGEXP_EXTRACT(s, r'group(pattern)')` | `REGEXP_SUBSTR(s, 'pattern', 1, 1, 'e')` | `regexp_extract(s, 'group(pattern)', 1)` |
| Regex match | `REGEXP_CONTAINS(s, r)` | `REGEXP_LIKE(s, r)` or `s RLIKE r` | `s RLIKE r` |
| Regex replace | `REGEXP_REPLACE(s, r, repl)` | `REGEXP_REPLACE(s, r, repl)` | `regexp_replace(s, r, repl)` |
| Split to array | `SPLIT(s, delim)` | `SPLIT(s, delim)` | `split(s, delim)` |
| Split and get part | `SPLIT(s, delim)[OFFSET(n)]` | `SPLIT_PART(s, delim, n+1)` | `split(s, delim)[n]` |
| MD5 hash | `MD5(s)` | `MD5(s)` | `md5(s)` |
| SHA256 hash | `SHA256(s)` | `SHA2(s, 256)` | `sha2(s, 256)` |

**Note on BigQuery regex:** BigQuery uses `r'pattern'` syntax (raw string) for regex patterns. Snowflake and Databricks use regular strings.

---

## Data Type Casting

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Cast | `CAST(x AS INT64)` | `CAST(x AS INTEGER)` | `CAST(x AS BIGINT)` |
| Safe cast | `SAFE_CAST(x AS INT64)` | `TRY_CAST(x AS INTEGER)` | `try_cast(x AS BIGINT)` |
| To string | `CAST(x AS STRING)` | `CAST(x AS VARCHAR)` or `TO_CHAR(x)` | `CAST(x AS STRING)` |
| To integer | `CAST(x AS INT64)` | `CAST(x AS INTEGER)` | `CAST(x AS BIGINT)` |
| To float | `CAST(x AS FLOAT64)` | `CAST(x AS FLOAT)` | `CAST(x AS DOUBLE)` |
| To decimal | `CAST(x AS NUMERIC)` | `CAST(x AS NUMBER(38,2))` | `CAST(x AS DECIMAL(38,2))` |
| To boolean | `CAST(x AS BOOL)` | `CAST(x AS BOOLEAN)` | `CAST(x AS BOOLEAN)` |
| To date | `CAST(x AS DATE)` | `CAST(x AS DATE)` | `CAST(x AS DATE)` |
| To timestamp | `CAST(x AS TIMESTAMP)` | `CAST(x AS TIMESTAMP_NTZ)` | `CAST(x AS TIMESTAMP)` |

---

## Aggregation Functions

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Count | `COUNT(*)` | `COUNT(*)` | `count(*)` |
| Count distinct | `COUNT(DISTINCT x)` | `COUNT(DISTINCT x)` | `count(DISTINCT x)` |
| Approx count | `APPROX_COUNT_DISTINCT(x)` | `APPROX_COUNT_DISTINCT(x)` | `approx_count_distinct(x)` |
| Sum | `SUM(x)` | `SUM(x)` | `sum(x)` |
| Average | `AVG(x)` | `AVG(x)` | `avg(x)` |
| Min / Max | `MIN(x)` / `MAX(x)` | `MIN(x)` / `MAX(x)` | `min(x)` / `max(x)` |
| Median | `PERCENTILE_CONT(x, 0.5) OVER()` | `MEDIAN(x)` | `percentile_approx(x, 0.5)` |
| Percentile | `PERCENTILE_CONT(x, p) OVER()` | `PERCENTILE_CONT(p) WITHIN GROUP (ORDER BY x)` | `percentile_approx(x, p)` |
| String agg | `STRING_AGG(x, ',')` | `LISTAGG(x, ',')` | `concat_ws(',', collect_list(x))` |
| Array agg | `ARRAY_AGG(x)` | `ARRAY_AGG(x)` | `collect_list(x)` |
| Array agg distinct | `ARRAY_AGG(DISTINCT x)` | `ARRAY_AGG(DISTINCT x)` | `collect_set(x)` |
| Boolean AND | `LOGICAL_AND(x)` | `BOOLAND_AGG(x)` | `bool_and(x)` |
| Boolean OR | `LOGICAL_OR(x)` | `BOOLOR_AGG(x)` | `bool_or(x)` |
| Conditional count | `COUNTIF(condition)` | `COUNT_IF(condition)` | `count_if(condition)` |
| Conditional sum | `SUM(IF(cond, val, 0))` | `SUM(IFF(cond, val, 0))` | `sum(IF(cond, val, 0))` |

---

## Window Functions

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Row number | `ROW_NUMBER() OVER(...)` | `ROW_NUMBER() OVER(...)` | `row_number() OVER(...)` |
| Rank | `RANK() OVER(...)` | `RANK() OVER(...)` | `rank() OVER(...)` |
| Dense rank | `DENSE_RANK() OVER(...)` | `DENSE_RANK() OVER(...)` | `dense_rank() OVER(...)` |
| Lead | `LEAD(x, n) OVER(...)` | `LEAD(x, n) OVER(...)` | `lead(x, n) OVER(...)` |
| Lag | `LAG(x, n) OVER(...)` | `LAG(x, n) OVER(...)` | `lag(x, n) OVER(...)` |
| First value | `FIRST_VALUE(x) OVER(...)` | `FIRST_VALUE(x) OVER(...)` | `first_value(x) OVER(...)` |
| Last value | `LAST_VALUE(x) OVER(...)` | `LAST_VALUE(x) OVER(...)` | `last_value(x) OVER(...)` |
| Ntile | `NTILE(n) OVER(...)` | `NTILE(n) OVER(...)` | `ntile(n) OVER(...)` |
| Running sum | `SUM(x) OVER(ORDER BY y ROWS UNBOUNDED PRECEDING)` | Same | Same |
| Moving avg | `AVG(x) OVER(ORDER BY y ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)` | Same | Same |

**Window functions are largely compatible across all three platforms.** The main differences are in frame specification edge cases and NULL handling within windows.

---

## JSON Handling

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Access field | `JSON_VALUE(j, '$.field')` | `j:field` or `GET_PATH(j, 'field')` | `get_json_object(j, '$.field')` or `j.field` |
| Access nested | `JSON_VALUE(j, '$.a.b')` | `j:a.b` | `get_json_object(j, '$.a.b')` |
| Access array element | `JSON_VALUE(j, '$.arr[0]')` | `j:arr[0]` | `get_json_object(j, '$.arr[0]')` |
| Extract as string | `JSON_VALUE(j, '$.field')` | `j:field::VARCHAR` | `get_json_object(j, '$.field')` |
| Extract as object | `JSON_QUERY(j, '$.obj')` | `j:obj` | `get_json_object(j, '$.obj')` |
| Parse JSON string | `PARSE_JSON(s)` (or `JSON s`) | `PARSE_JSON(s)` | `from_json(s, schema)` |
| To JSON string | `TO_JSON_STRING(x)` | `TO_JSON(x)` | `to_json(x)` |
| JSON keys | `-- not directly supported` | `OBJECT_KEYS(j)` | `json_object_keys(j)` |
| Build JSON object | `JSON_OBJECT(k1, v1, k2, v2)` | `OBJECT_CONSTRUCT(k1, v1, k2, v2)` | `named_struct(k1, v1, k2, v2)` |

**BigQuery note:** BigQuery has both `JSON` type (native) and string-based JSON functions. Use `JSON_VALUE` for scalar extraction from both. For BigQuery `STRING` columns containing JSON, the same functions work.

**Snowflake note:** Snowflake's `VARIANT` type supports direct path notation (`j:field`), which is the most ergonomic syntax but has no equivalent on other platforms.

---

## Array Handling

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Create array | `[1, 2, 3]` or `ARRAY<INT64>[1,2,3]` | `ARRAY_CONSTRUCT(1, 2, 3)` | `array(1, 2, 3)` |
| Array length | `ARRAY_LENGTH(arr)` | `ARRAY_SIZE(arr)` | `size(arr)` |
| Access element | `arr[OFFSET(0)]` | `arr[0]` | `arr[0]` or `element_at(arr, 1)` |
| Contains | `x IN UNNEST(arr)` | `ARRAY_CONTAINS(x, arr)` | `array_contains(arr, x)` |
| Flatten/unnest | `UNNEST(arr) AS elem` | `LATERAL FLATTEN(input => arr)` | `explode(arr)` |
| Array concat | `ARRAY_CONCAT(a, b)` | `ARRAY_CAT(a, b)` | `concat(a, b)` |
| Array distinct | `ARRAY(SELECT DISTINCT x FROM UNNEST(arr) x)` | `ARRAY_DISTINCT(arr)` | `array_distinct(arr)` |
| Array sort | `ARRAY(SELECT x FROM UNNEST(arr) x ORDER BY x)` | `ARRAY_SORT(arr)` | `array_sort(arr)` |
| Array to string | `ARRAY_TO_STRING(arr, ',')` | `ARRAY_TO_STRING(arr, ',')` | `concat_ws(',', arr)` |

**Unnesting pattern differences:**

BigQuery:
```sql
SELECT t.id, elem
FROM my_table t, UNNEST(t.tags) AS elem
```

Snowflake:
```sql
SELECT t.id, f.value::VARCHAR AS elem
FROM my_table t, LATERAL FLATTEN(input => t.tags) f
```

Databricks:
```sql
SELECT t.id, elem
FROM my_table t LATERAL VIEW explode(t.tags) AS elem
```

---

## Conditional Logic

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| If/else | `IF(cond, then, else)` | `IFF(cond, then, else)` | `IF(cond, then, else)` |
| Coalesce | `COALESCE(a, b, c)` | `COALESCE(a, b, c)` | `coalesce(a, b, c)` |
| Null if equal | `NULLIF(a, b)` | `NULLIF(a, b)` | `nullif(a, b)` |
| If null | `IFNULL(a, default)` | `NVL(a, default)` | `nvl(a, default)` or `ifnull(a, default)` |
| If null 2-arg | `--` | `NVL2(a, if_not_null, if_null)` | `nvl2(a, if_not_null, if_null)` |
| Decode | `-- use CASE` | `DECODE(expr, val1, res1, val2, res2, default)` | `-- use CASE` |
| Greatest | `GREATEST(a, b, c)` | `GREATEST(a, b, c)` | `greatest(a, b, c)` |
| Least | `LEAST(a, b, c)` | `LEAST(a, b, c)` | `least(a, b, c)` |
| Safe divide | `SAFE_DIVIDE(a, b)` | `DIV0NULL(a, b)` | `a / nullif(b, 0)` |

---

## DDL Differences

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Create table | `CREATE TABLE ds.t (...)` | `CREATE TABLE db.schema.t (...)` | `CREATE TABLE catalog.schema.t (...)` |
| Create or replace | `CREATE OR REPLACE TABLE` | `CREATE OR REPLACE TABLE` | `CREATE OR REPLACE TABLE` |
| Create if not exists | `CREATE TABLE IF NOT EXISTS` | `CREATE TABLE IF NOT EXISTS` | `CREATE TABLE IF NOT EXISTS` |
| Drop table | `DROP TABLE IF EXISTS ds.t` | `DROP TABLE IF EXISTS db.schema.t` | `DROP TABLE IF EXISTS catalog.schema.t` |
| Add column | `ALTER TABLE t ADD COLUMN c TYPE` | `ALTER TABLE t ADD COLUMN c TYPE` | `ALTER TABLE t ADD COLUMN c TYPE` |
| Rename column | `ALTER TABLE t RENAME COLUMN a TO b` | `ALTER TABLE t RENAME COLUMN a TO b` | `ALTER TABLE t RENAME COLUMN a TO b` |
| Table comment | `-- in OPTIONS(description='...')` | `COMMENT ON TABLE t IS '...'` | `COMMENT ON TABLE t IS '...'` |
| Column comment | `-- in schema definition` | `COMMENT ON COLUMN t.c IS '...'` | `COMMENT ON COLUMN t.c IS '...'` |

---

## Miscellaneous

| Operation | BigQuery | Snowflake | Databricks |
|-----------|----------|-----------|------------|
| Generate UUID | `GENERATE_UUID()` | `UUID_STRING()` | `uuid()` |
| Hash multiple cols | `FARM_FINGERPRINT(CONCAT(a,b))` | `HASH(a, b)` | `hash(a, b)` |
| Type of expression | `-- no direct function` | `TYPEOF(x)` | `typeof(x)` |
| Table sampling | `TABLESAMPLE SYSTEM (10 PERCENT)` | `SAMPLE (10)` | `TABLESAMPLE (10 PERCENT)` |
| Pivot | `PIVOT(...)` (limited) | `PIVOT(...)` | `PIVOT(...)` |
| Unpivot | `UNPIVOT(...)` | `UNPIVOT(...)` | `UNPIVOT(...)` or `stack()` |
| CTE syntax | `WITH cte AS (...)` | `WITH cte AS (...)` | `WITH cte AS (...)` |
| Recursive CTE | `WITH RECURSIVE cte AS (...)` | `WITH RECURSIVE cte AS (...)` | Not supported (use loops) |
| MERGE | `MERGE INTO t USING s ON ...` | `MERGE INTO t USING s ON ...` | `MERGE INTO t USING s ON ...` |
| Qualify | `QUALIFY ROW_NUMBER() OVER(...) = 1` | `QUALIFY ROW_NUMBER() OVER(...) = 1` | `-- use subquery/CTE` |

**QUALIFY note:** BigQuery and Snowflake support `QUALIFY` natively. Databricks does not — use a subquery or CTE with a window function instead.
