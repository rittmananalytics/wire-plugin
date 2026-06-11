# Snowflake SQL to BigQuery SQL: Canonical Translation Guide

> **Wire framework role.** This is the deep reference for the `snowflake → bigquery` platform pair. It complements the other files in this directory rather than replacing them:
> - [`translation_guide.md`](./translation_guide.md) — the quick pattern table (one row per construct) and the macro-first strategy. Start there.
> - [`type_mapping.md`](./type_mapping.md) — the data-type lookup.
> - [`examples/`](./examples/) — worked before/after models used as few-shot context.
> - **this file** — the exhaustive treatment, organised for the cases where a naive translation compiles cleanly and returns the wrong answer. Section 11 is a 25-item gotcha checklist; sections 5, 6 and 13 carry the silent-behaviour-change detail the pattern table can only summarise.
>
> `dbt_migration-generate` and `migration_strategy-generate` read the quick guide and examples first, and reach into this reference when a model trips one of the ⚠ cases or uses a construct the pattern table doesn't cover. The reverse direction lives in `bigquery_to_snowflake/`.

A practitioner's reference for translating Snowflake SQL to BigQuery Standard SQL (GoogleSQL). Written for warehouse migration work where correctness matters more than line-by-line equivalence: every section flags the places where a naive translation compiles fine but returns different results.

Conventions used throughout: Snowflake syntax appears first, BigQuery second. Where behaviour differs silently (same syntax, different answer) the entry is marked **⚠ silent behaviour change**. UK English, BigQuery examples assume GoogleSQL (not legacy SQL).

---

## 1. Dialect fundamentals

These differences underpin everything else. Get these wrong and the function mappings won't save you.

### 1.1 Identifier case sensitivity

| Aspect | Snowflake | BigQuery |
|---|---|---|
| Unquoted identifiers | Case-insensitive, stored and resolved as UPPERCASE | Case-insensitive for column names; **case-sensitive for dataset and table names** by default |
| Quoted identifiers | `"MixedCase"` is case-sensitive | Backticks `` `MixedCase` `` quote reserved words and special characters; table name case still matters |
| Quote character | Double quotes `"col name"` | Backticks `` `col name` `` |

**⚠ silent behaviour change:** a Snowflake table created as `create table orders` is really `ORDERS`. In BigQuery, `orders` and `Orders` are two different tables (unless the dataset was created with case-insensitivity enabled, which is rare). Standardise on lowercase snake_case during migration and the problem disappears.

Double-quoted string literals do not exist in BigQuery's default mode the way people sometimes abuse them in Snowflake. In BigQuery, `"text"` and `'text'` are both string literals; identifiers must use backticks.

### 1.2 Object naming and qualification

| Snowflake | BigQuery |
|---|---|
| `database.schema.table` | `project.dataset.table` |
| `use database analytics;` | No equivalent; default project comes from connection/job config |
| `use schema staging;` | No equivalent; qualify with dataset or set default dataset on the job |
| `use warehouse transforming;` | No equivalent; compute is serverless (on-demand or slot reservations) |

Fully qualified references need backticks if the project ID contains hyphens: `` `ra-development.analytics.orders` ``.

### 1.3 Session state and timezone defaults

This is the single most common source of silently wrong numbers in a Snowflake to BigQuery migration.

| Aspect | Snowflake | BigQuery |
|---|---|---|
| Default timezone | Session parameter `TIMEZONE`, **defaults to America/Los_Angeles** | Always UTC; no session timezone |
| `CURRENT_TIMESTAMP` | `TIMESTAMP_LTZ` in session timezone | `TIMESTAMP` (UTC instant) |
| `CURRENT_DATE` | Date in session timezone | **Date in UTC** unless you pass a zone: `CURRENT_DATE('Europe/London')` |
| Session variables | `SET my_var = 5;` then `$my_var` | `DECLARE my_var INT64 DEFAULT 5;` in scripts; no session-scoped variables across statements outside scripting |

**⚠ silent behaviour change:** any Snowflake logic relying on the session timezone (daily partitioning by `CURRENT_DATE`, "today's orders" filters, `DATE(created_at)` casts on `TIMESTAMP_LTZ`) will shift by the UTC offset after migration. Audit every `CURRENT_DATE`, `CURRENT_TIMESTAMP` and timestamp-to-date cast, and make the timezone explicit: `DATE(created_at, 'Europe/London')`.

### 1.4 Set operators and SELECT modifiers

| Snowflake | BigQuery | Notes |
|---|---|---|
| `UNION` (implies DISTINCT) | `UNION DISTINCT` | **BigQuery requires the keyword.** Bare `UNION` is a syntax error |
| `UNION ALL` | `UNION ALL` | Identical |
| `MINUS` or `EXCEPT` | `EXCEPT DISTINCT` | |
| `INTERSECT` | `INTERSECT DISTINCT` | |
| `SELECT TOP 10 ...` | `SELECT ... LIMIT 10` | |
| `SELECT * EXCLUDE (a, b)` | `SELECT * EXCEPT (a, b)` | Same idea, different keyword |
| `SELECT * RENAME (a AS x)` | `SELECT * REPLACE (expr AS a)` | REPLACE substitutes an expression for a column; there is no direct rename, so use `EXCEPT` plus an aliased column |
| `SELECT * ILIKE 'order_%'` | No equivalent | Enumerate columns or restructure |
| `GROUP BY ALL` | `GROUP BY ALL` | Both supported |
| `GROUP BY 1, 2` | `GROUP BY 1, 2` | Both supported |
| `QUALIFY row_number() over (...) = 1` | `QUALIFY ... ` | Supported, **but BigQuery requires a WHERE, GROUP BY or HAVING clause in the same query**. Idiom: add `WHERE TRUE` |

```sql
-- Snowflake
select *
from orders
qualify row_number() over (partition by customer_id order by created_at desc) = 1;

-- BigQuery
select *
from orders
where true
qualify row_number() over (partition by customer_id order by created_at desc) = 1;
```

### 1.5 Casting syntax

| Snowflake | BigQuery |
|---|---|
| `col::varchar` | `CAST(col AS STRING)` — **no `::` operator in BigQuery** |
| `CAST(col AS NUMBER)` | `CAST(col AS NUMERIC)` or `INT64` depending on scale |
| `TRY_CAST(col AS DATE)` | `SAFE_CAST(col AS DATE)` |
| `TRY_TO_NUMBER(s)` | `SAFE_CAST(s AS NUMERIC)` |
| `TRY_TO_DATE(s, 'YYYY-MM-DD')` | `SAFE.PARSE_DATE('%Y-%m-%d', s)` |

The `SAFE.` prefix in BigQuery generalises: it works on most scalar functions and turns errors into NULL, e.g. `SAFE.PARSE_TIMESTAMP`, `SAFE.SUBSTR`, `SAFE_DIVIDE`.

**⚠ silent behaviour change:** boolean casting. Snowflake accepts `'yes'`, `'y'`, `'t'`, `'on'`, `'1'` as TRUE when casting strings to BOOLEAN. BigQuery accepts only `'true'` and `'false'` (case-insensitive). `CAST('yes' AS BOOL)` errors in BigQuery; `SAFE_CAST` returns NULL.

---

## 2. Data type mapping

| Snowflake | BigQuery | Notes |
|---|---|---|
| `NUMBER(38,0)`, `INT`, `BIGINT` | `INT64` | All Snowflake integer aliases are NUMBER(38,0) underneath. INT64 is 8 bytes; values beyond ±9.2 quintillion need NUMERIC |
| `NUMBER(p,s)` with s > 0 | `NUMERIC` (38 digits, 9 decimal places) or `BIGNUMERIC` (~76 digits, 38 dp) | NUMERIC is fixed at scale 9. Parameterised `NUMERIC(p,s)` exists but constrains, it doesn't change storage. Money: NUMERIC is fine |
| `FLOAT`, `DOUBLE` | `FLOAT64` | Both IEEE 754 double |
| `VARCHAR(n)`, `STRING`, `TEXT` | `STRING` | BigQuery STRING is unbounded; `STRING(n)` exists as a parameterised type enforced on write. Snowflake VARCHAR length is rarely worth carrying over |
| `BINARY` | `BYTES` | |
| `BOOLEAN` | `BOOL` | |
| `DATE` | `DATE` | |
| `TIME` | `TIME` | |
| `TIMESTAMP_NTZ` / `DATETIME` | `DATETIME` | Wall-clock time, no zone. The natural pairing |
| `TIMESTAMP_LTZ` | `TIMESTAMP` | Both represent an absolute instant. Display differs: Snowflake renders in session tz, BigQuery in UTC |
| `TIMESTAMP_TZ` | No equivalent | BigQuery TIMESTAMP does not store the original offset. If the offset itself matters, store it in a separate column |
| `VARIANT` | `JSON` | See section 6. Historically migrated as STRING; native JSON type is now the right target |
| `OBJECT` | `JSON` or `STRUCT<...>` | STRUCT if the shape is fixed and known; JSON if not |
| `ARRAY` | `ARRAY<T>` or `JSON` | **Snowflake arrays are heterogeneous (elements are VARIANT); BigQuery arrays are typed and homogeneous.** Mixed-type arrays must land as JSON |
| `GEOGRAPHY` | `GEOGRAPHY` | Both planet-scale geodesic types; function coverage differs at the edges |
| `GEOMETRY` | No equivalent | BigQuery has no planar geometry type |

Two array gotchas worth pinning:

1. **BigQuery arrays cannot contain NULL elements** in a stored table (query results can produce them transiently, but writing them errors). Snowflake arrays can. Filter or coalesce nulls when building arrays: `ARRAY_AGG(x IGNORE NULLS)`.
2. **Snowflake `TIMESTAMP` is an alias** whose meaning depends on the `TIMESTAMP_TYPE_MAPPING` session parameter (default NTZ). Check what the column actually is before mapping; assuming LTZ when it's NTZ shifts every value by the UTC offset.

---

## 3. DDL translation

### 3.1 CREATE TABLE

```sql
-- Snowflake
create or replace table analytics.orders (
    order_id      number(38,0)    not null,
    customer_id   number(38,0),
    order_status  varchar(50),
    total_amount  number(10,2),
    created_at    timestamp_ntz   default current_timestamp(),
    constraint pk_orders primary key (order_id)
)
cluster by (created_at);

-- BigQuery
create or replace table `analytics.orders` (
    order_id      int64 not null,
    customer_id   int64,
    order_status  string,
    total_amount  numeric,
    created_at    datetime default current_datetime(),
    primary key (order_id) not enforced
)
partition by date(created_at)
cluster by customer_id;
```

Key differences:

| Feature | Snowflake | BigQuery |
|---|---|---|
| Primary/foreign keys | Declared, not enforced (metadata only) | Declared with mandatory `NOT ENFORCED`; used by the optimiser for join elimination |
| `CLUSTER BY` | Background automatic clustering service, billed separately | Free; tables re-cluster automatically on write. Up to 4 clustering columns, order matters |
| Partitioning | None (micro-partitions are automatic) | Explicit: one column, `PARTITION BY` on DATE/TIMESTAMP/DATETIME (or integer range). 10,000 partition limit, so daily not hourly for long-lived tables |
| `TRANSIENT` tables | No fail-safe, cheaper | No equivalent; closest is a table with short expiry |
| `TEMPORARY` tables | Session-scoped | `CREATE TEMP TABLE` only inside scripts/sessions; expires with the session |
| Table expiry | Via retention parameters | `OPTIONS (expiration_timestamp = ...)` or partition expiry, both first-class |
| `CREATE TABLE ... AS SELECT` | Supported | Supported, including `PARTITION BY` and `CLUSTER BY` on the CTAS |

The structural shift: Snowflake clustering keys are an optimisation hint over automatic micro-partitions, whereas BigQuery partitioning is a hard physical layout decision that drives both cost (bytes scanned) and the 10,000 partition ceiling. The standard pattern for a Snowflake table clustered on a timestamp is `PARTITION BY DATE(ts)` plus `CLUSTER BY` on the next most selective filter columns (customer_id, status and so on).

`require_partition_filter = true` is worth setting on very large partitioned tables; it turns accidental full scans into errors rather than invoices.

### 3.2 Views and materialized views

```sql
-- Both support standard views with near-identical syntax
create or replace view analytics.v_orders as select ...;
```

Materialized views differ substantially:

| Aspect | Snowflake | BigQuery |
|---|---|---|
| Refresh | Automatic, background service, billed | Automatic and incremental, free refresh within limits; optional max_staleness |
| Query support | Single table, no joins (Enterprise edition feature) | Aggregations and some joins supported; restrictions on non-deterministic functions, UNNEST quirks |
| Edition gating | Enterprise+ | All editions |

In practice most Snowflake materialized views translate better to dbt incremental models or BigQuery scheduled queries than to BigQuery materialized views, because the workloads that motivated them differ.

### 3.3 Cloning, time travel and snapshots

| Snowflake | BigQuery | Notes |
|---|---|---|
| `create table t2 clone t1;` | `create table t2 clone t1;` | Both zero-copy. BigQuery also has `CREATE SNAPSHOT TABLE` for read-only point-in-time copies |
| `select * from t at(offset => -3600);` | `select * from t for system_time as of timestamp_sub(current_timestamp(), interval 1 hour);` | |
| `select * from t at(timestamp => '...'::timestamp);` | `select * from t for system_time as of timestamp '...';` | |
| Time travel window | Default 1 day; configurable up to 90 days on Enterprise+ | **7 days maximum**, configurable 2–7 days per dataset |
| `undrop table t;` | `create table t clone t for system_time as of ...` before expiry, or restore via snapshot | No direct UNDROP for tables past the time travel window |

**⚠ operational change:** any recovery runbook assuming 90-day time travel needs rewriting. For longer retention in BigQuery, schedule snapshot tables.

### 3.4 Stages, file loading and external data

| Snowflake | BigQuery |
|---|---|
| `create stage`, `PUT`, `COPY INTO table FROM @stage` | `LOAD DATA INTO`, `bq load`, or load jobs via API from GCS |
| `COPY INTO @stage FROM table` (unload) | `EXPORT DATA OPTIONS(uri='gs://...') AS SELECT ...` |
| External tables over S3/GCS/Azure | External tables / BigLake tables over GCS (and S3/Azure via Omni) |
| Snowpipe (auto-ingest) | Storage Write API, Pub/Sub + Dataflow, or BigQuery Data Transfer Service |
| File formats: CSV, JSON, Avro, ORC, Parquet, XML | CSV, JSON (newline-delimited), Avro, ORC, Parquet; no XML |

---

## 4. DML translation

### 4.1 MERGE

Both dialects support ANSI-style MERGE and it translates almost mechanically:

```sql
-- Snowflake
merge into target t
using source s on t.id = s.id
when matched and s.is_deleted then delete
when matched then update set t.amount = s.amount, t.updated_at = s.updated_at
when not matched then insert (id, amount, updated_at) values (s.id, s.amount, s.updated_at);

-- BigQuery: identical apart from boolean predicates needing explicit form
merge into `analytics.target` t
using `staging.source` s on t.id = s.id
when matched and s.is_deleted = true then delete
when matched then update set amount = s.amount, updated_at = s.updated_at
when not matched then insert (id, amount, updated_at) values (s.id, s.amount, s.updated_at);
```

Differences that matter:

- Snowflake's `ERROR_ON_NONDETERMINISTIC_MERGE` parameter (default true) errors when a target row matches multiple source rows. **BigQuery always errors** in that case. Deduplicate the source first in both.
- BigQuery MERGE on partitioned tables can prune partitions if the ON clause or a `when matched and t.partition_col >= ...` predicate constrains them. Without this you scan the whole target on every merge, which is the classic cost surprise on incremental models.

### 4.2 UPDATE and DELETE with joins

```sql
-- Snowflake
update orders o
set o.status = s.status
from order_updates s
where o.id = s.id;

delete from orders o
using cancelled c
where o.id = c.order_id;

-- BigQuery
update `analytics.orders` o
set o.status = s.status
from `staging.order_updates` s
where o.id = s.id;

delete from `analytics.orders` o
where o.id in (select order_id from `staging.cancelled`);
-- or: where exists (select 1 from `staging.cancelled` c where c.order_id = o.id)
```

BigQuery UPDATE...FROM works the same way. DELETE has no USING clause; rewrite as IN or EXISTS.

### 4.3 Multi-table INSERT

Snowflake's `INSERT ALL / INSERT FIRST` into multiple tables has no BigQuery equivalent. Decompose into separate INSERT statements, or restructure as a single table with a discriminator column.

### 4.4 TRUNCATE and DML quotas

`TRUNCATE TABLE` exists in both. One operational note: BigQuery DML is no longer meaningfully quota-limited per table per day (the old 1,000 statement limit is gone), but each DML statement is a job with seconds of latency. OLTP-style row-at-a-time writes that limp along in Snowflake will not survive in BigQuery; batch them or use the Storage Write API.


---

## 5. Function translation

### 5.1 Conditional and null-handling functions

| Snowflake | BigQuery | Notes |
|---|---|---|
| `IFF(cond, a, b)` | `IF(cond, a, b)` | |
| `NVL(a, b)` | `IFNULL(a, b)` or `COALESCE(a, b)` | |
| `NVL2(x, a, b)` | `IF(x IS NOT NULL, a, b)` | |
| `ZEROIFNULL(x)` | `IFNULL(x, 0)` | |
| `NULLIFZERO(x)` | `NULLIF(x, 0)` | |
| `DECODE(x, a, r1, b, r2, dflt)` | `CASE x WHEN a THEN r1 WHEN b THEN r2 ELSE dflt END` | **⚠** DECODE treats NULL = NULL as a match; CASE does not. If the DECODE branches on NULL, add an explicit `WHEN x IS NULL` via searched CASE |
| `EQUAL_NULL(a, b)` | `a IS NOT DISTINCT FROM b` | Null-safe equality |
| `BOOLOR_AGG(x)` / `BOOLAND_AGG(x)` | `LOGICAL_OR(x)` / `LOGICAL_AND(x)` | |
| `GREATEST(a, b, c)` | `GREATEST(a, b, c)` | Both return NULL if any argument is NULL. Snowflake's `GREATEST_IGNORE_NULLS` maps to a COALESCE-wrapped GREATEST or a manual CASE |

### 5.2 Numeric functions and division

| Snowflake | BigQuery | Notes |
|---|---|---|
| `a / b` | `a / b` | Snowflake returns NUMBER with extended scale; BigQuery integer division returns FLOAT64. **⚠** downstream NUMERIC vs FLOAT64 typing can change rounding; cast explicitly where money is involved |
| `DIV0(a, b)` | `IFNULL(SAFE_DIVIDE(a, b), 0)` | SAFE_DIVIDE returns NULL on divide-by-zero |
| `DIV0NULL(a, b)` | `SAFE_DIVIDE(a, b)` | Also handles NULL divisor the same way |
| `MOD(a, b)` / `a % b` | `MOD(a, b)` | No `%` operator in BigQuery |
| `ROUND(x, n)` | `ROUND(x, n)` | **⚠** both round halves away from zero for NUMERIC, but FLOAT64 rounding in BigQuery follows IEEE and Snowflake FLOAT behaves similarly; differences appear at the representation edge. For financial rounding keep values NUMERIC throughout |
| `TRUNC(x, n)` (numeric) | `TRUNC(x, n)` | |
| `CEIL(x, n)` / `FLOOR(x, n)` with scale | `CEIL(x * POW(10,n)) / POW(10,n)` | BigQuery CEIL/FLOOR take no scale argument |
| `SQUARE(x)` | `POW(x, 2)` | |
| `LOG(base, x)` | `LOG(x, base)` | **⚠ argument order is reversed** |
| `RANDOM()` | `RAND()` | Snowflake returns a 64-bit integer; BigQuery returns FLOAT64 in [0,1). `UNIFORM(0,1,RANDOM())` → `RAND()` |
| `SEQ4()` | `ROW_NUMBER() OVER ()` or `GENERATE_ARRAY` | See section 7.4 on generators |

### 5.3 String functions

| Snowflake | BigQuery | Notes |
|---|---|---|
| `CONCAT(a, b)` / `a \|\| b` | Same | **⚠** Snowflake CONCAT returns NULL if any argument is NULL; BigQuery CONCAT does too. But Snowflake's `CONCAT_WS` skips NULLs while joining; BigQuery has no CONCAT_WS — use `ARRAY_TO_STRING([a, b, c], ',')` which also skips NULLs |
| `LEN(s)` / `LENGTH(s)` | `LENGTH(s)` | Both count characters for STRING |
| `SUBSTR(s, pos, len)` | `SUBSTR(s, pos, len)` | Both 1-based. Both treat negative pos as from-the-end |
| `LEFT(s, n)` / `RIGHT(s, n)` | `LEFT(s, n)` / `RIGHT(s, n)` | |
| `LPAD` / `RPAD` / `TRIM` / `LTRIM` / `RTRIM` | Same names | Snowflake LTRIM/RTRIM take a character set; BigQuery's do as well |
| `SPLIT_PART(s, ',', 2)` | `SPLIT(s, ',')[SAFE_OFFSET(1)]` | **⚠ index base changes**: SPLIT_PART is 1-based, OFFSET is 0-based. SAFE_OFFSET returns NULL out of range, matching SPLIT_PART returning empty string only loosely — SPLIT_PART returns '' for missing parts, SAFE_OFFSET returns NULL |
| `STRTOK(s, delim, n)` | Same SPLIT pattern | STRTOK treats consecutive delimiters differently (skips empties); add `ARRAY(SELECT x FROM UNNEST(SPLIT(...)) x WHERE x != '')` if that matters |
| `CHARINDEX(sub, s)` / `POSITION(sub IN s)` | `STRPOS(s, sub)` | **⚠ argument order swaps** between CHARINDEX and STRPOS |
| `INSERT(s, pos, len, repl)` | Compose with SUBSTR/CONCAT | |
| `REPLACE` / `REVERSE` / `REPEAT` / `INITCAP` | Same names | INITCAP exists in both |
| `TRANSLATE(s, from, to)` | `TRANSLATE(s, from, to)` | Exists in both, despite some migration guides claiming otherwise |
| `STARTSWITH(s, p)` / `ENDSWITH(s, p)` | `STARTS_WITH(s, p)` / `ENDS_WITH(s, p)` | Underscore appears |
| `CONTAINS(s, sub)` | `CONTAINS_SUBSTR(s, sub)` | **⚠** CONTAINS_SUBSTR is case-insensitive and normalises; for an exact case-sensitive match use `STRPOS(s, sub) > 0` |
| `CHARINDEX(sub, s, start)` | `INSTR(s, sub, start)` | INSTR also takes an occurrence argument |
| `ILIKE` | No ILIKE | `LOWER(a) LIKE LOWER('pattern')` or `REGEXP_CONTAINS(a, r'(?i)pattern')`. For equality, a `COLLATE 'und:ci'` column also works |
| `LIKE ANY ('a%', 'b%')` | `REGEXP_CONTAINS(s, r'^(a\|b)')` or OR-chain | |
| `RLIKE(s, pat)` / `REGEXP_LIKE` | `REGEXP_CONTAINS(s, r'pat')` | See regex engine note below |
| `REGEXP_SUBSTR(s, pat)` | `REGEXP_EXTRACT(s, r'pat')` | REGEXP_SUBSTR's occurrence/position/group arguments need REGEXP_EXTRACT_ALL plus OFFSET to replicate |
| `REGEXP_REPLACE(s, pat, repl)` | `REGEXP_REPLACE(s, r'pat', repl)` | Backreferences: Snowflake `\\1`, BigQuery `\\1` in raw strings or `\\\\1` otherwise |
| `REGEXP_COUNT(s, pat)` | `ARRAY_LENGTH(REGEXP_EXTRACT_ALL(s, r'pat'))` | |
| `UUID_STRING()` | `GENERATE_UUID()` | |
| `BASE64_ENCODE(s)` | `TO_BASE64(CAST(s AS BYTES))` | BigQuery base64 functions operate on BYTES |

**Regex engine — ⚠ silent behaviour change.** Snowflake implements POSIX ERE (with extensions); BigQuery uses RE2. Some published guides claim both use RE2; that's wrong, although the practical gap is narrower than the engine names suggest because **neither supports backreferences or lookarounds in patterns** (Snowflake does allow backreferences in the REGEXP_REPLACE replacement string, as does BigQuery via `\\1`). The differences that actually bite:

- **Default anchoring**: Snowflake `REGEXP_LIKE`/`RLIKE` and `REGEXP_SUBSTR`'s 'e' behaviour implicitly anchor the whole string for the LIKE variants (acts like `^pattern$`); `REGEXP_CONTAINS` matches anywhere. Translate `REGEXP_LIKE(s, p)` as `REGEXP_CONTAINS(s, r'^(?:p)$')`.
- **Escaping**: Snowflake patterns in single-quoted strings need doubled backslashes (`'\\d+'`); BigQuery raw strings don't (`r'\d+'`). When porting, convert to raw strings and halve the backslashes. Snowflake code written with `$$...$$` dollar-quoting already has single backslashes.
- **Flags**: Snowflake passes match parameters as a function argument (`REGEXP_SUBSTR(s, p, 1, 1, 'i')` for case-insensitive, `'s'` for dotall, `'m'` for multiline). RE2 takes them inline at the start of the pattern: `r'(?i)pattern'`, `r'(?s)...'`, `r'(?m)...'`.
- **Occurrence and group arguments**: `REGEXP_SUBSTR(s, p, position, occurrence, params, group)` has no single-call equivalent; replicate with `REGEXP_EXTRACT_ALL(s, p)[SAFE_OFFSET(occurrence - 1)]` and capture groups in the pattern. `REGEXP_INSTR` has no equivalent at all; combine `REGEXP_EXTRACT` with `STRPOS`.

### 5.4 Hash functions

| Snowflake | BigQuery | Notes |
|---|---|---|
| `MD5(s)` (returns hex string) | `TO_HEX(MD5(s))` | **⚠** BigQuery MD5 returns BYTES. dbt surrogate keys built on MD5 match across platforms once wrapped in TO_HEX with lowercase hex, which is what dbt_utils handles per-adapter |
| `SHA1(s)` / `SHA2(s, 256)` | `TO_HEX(SHA1(s))` / `TO_HEX(SHA256(s))` | Same BYTES caveat |
| `HASH(a, b)` | `FARM_FINGERPRINT(CONCAT(...))` | **⚠ different algorithms, different values.** Snowflake HASH is proprietary 64-bit; FARM_FINGERPRINT is FarmHash. Never compare hashes computed on different platforms; rebuild hash-based keys from source columns during migration |

### 5.5 Date and time functions

The mechanical mappings first, then the traps.

| Snowflake | BigQuery |
|---|---|
| `CURRENT_DATE()` | `CURRENT_DATE('Europe/London')` (be explicit; bare form is UTC) |
| `CURRENT_TIMESTAMP()` | `CURRENT_TIMESTAMP()` (UTC instant) or `CURRENT_DATETIME('Europe/London')` for wall clock |
| `SYSDATE()` (always UTC) | `CURRENT_TIMESTAMP()` |
| `DATEADD(day, 7, d)` | `DATE_ADD(d, INTERVAL 7 DAY)` |
| `DATEADD(hour, -3, ts)` | `TIMESTAMP_SUB(ts, INTERVAL 3 HOUR)` / `DATETIME_SUB` |
| `DATEDIFF(day, d1, d2)` | `DATE_DIFF(d2, d1, DAY)` — **⚠ argument order reverses** |
| `DATEDIFF(hour, t1, t2)` | `TIMESTAMP_DIFF(t2, t1, HOUR)` — see boundary semantics below |
| `DATE_TRUNC('month', d)` | `DATE_TRUNC(d, MONTH)` / `TIMESTAMP_TRUNC(ts, MONTH)` |
| `LAST_DAY(d)` / `LAST_DAY(d, 'month')` | `LAST_DAY(d)` / `LAST_DAY(d, MONTH)` |
| `DAYNAME(d)` | `FORMAT_DATE('%a', d)` |
| `MONTHNAME(d)` | `FORMAT_DATE('%b', d)` |
| `YEAR(d)`, `MONTH(d)`, `DAY(d)` | `EXTRACT(YEAR FROM d)` etc |
| `DAYOFWEEK(d)` | `EXTRACT(DAYOFWEEK FROM d)` — **⚠ numbering differs**, see below |
| `WEEK(d)` / `WEEKISO(d)` | `EXTRACT(WEEK FROM d)` / `EXTRACT(ISOWEEK FROM d)` |
| `TO_DATE(s, 'YYYY-MM-DD')` | `PARSE_DATE('%Y-%m-%d', s)` |
| `TO_TIMESTAMP(s, 'YYYY-MM-DD HH24:MI:SS')` | `PARSE_TIMESTAMP('%Y-%m-%d %H:%M:%S', s)` (assumes UTC unless %Z/%Ez present) |
| `TO_CHAR(d, 'YYYY-MM-DD')` / `TO_VARCHAR` | `FORMAT_DATE('%Y-%m-%d', d)` / `FORMAT_TIMESTAMP` / `FORMAT_DATETIME` |
| `TO_TIMESTAMP(epoch_seconds)` | `TIMESTAMP_SECONDS(n)` / `TIMESTAMP_MILLIS(n)` / `TIMESTAMP_MICROS(n)` |
| `DATE_PART(epoch_second, ts)` | `UNIX_SECONDS(ts)` / `UNIX_MILLIS` / `UNIX_MICROS` |
| `CONVERT_TIMEZONE('Europe/London', ts)` | `DATETIME(ts, 'Europe/London')` (TIMESTAMP → local DATETIME) |
| `CONVERT_TIMEZONE('UTC', 'Europe/London', ntz)` | `DATETIME(TIMESTAMP(ntz, 'UTC'), 'Europe/London')` |
| `TIMESTAMP_NTZ_FROM_PARTS(y,m,d,h,mi,s)` | `DATETIME(y, m, d, h, mi, s)` |
| `MONTHS_BETWEEN(d1, d2)` | `DATE_DIFF(d1, d2, MONTH)` approximates; MONTHS_BETWEEN returns fractional months, so replicate with day arithmetic if the fraction is used |

**Format strings are a different language.** Snowflake uses Oracle-style elements; BigQuery uses strftime-style. Every TO_CHAR/TO_DATE/TO_TIMESTAMP call needs its format string rewritten. The common elements:

| Concept | Snowflake | BigQuery |
|---|---|---|
| 4-digit year | `YYYY` | `%Y` |
| 2-digit year | `YY` | `%y` |
| 2-digit month | `MM` | `%m` |
| Abbrev / full month name | `MON` / `MMMM` | `%b` / `%B` |
| 2-digit day | `DD` | `%d` |
| Abbrev / full day name | `DY` / `DAY` | `%a` / `%A` |
| 24-hour / 12-hour | `HH24` / `HH12` | `%H` / `%I` |
| Minute | `MI` | `%M` |
| Second | `SS` | `%S` |
| Fractional seconds | `FF3` / `FF6` / `FF9` | `%E3S` / `%E6S` (includes the seconds; no nanosecond element) |
| AM/PM | `AM` | `%p` |
| Timezone offset | `TZH:TZM` | `%Ez` |
| Timezone name | — | `%Z` |
| ISO date shortcut | `YYYY-MM-DD` | `%F` |
| Time shortcut | `HH24:MI:SS` | `%T` |

Two traps inside the trap: BigQuery's `%E3S` element renders **seconds plus fraction** (`05.123`), so `SS.FF3` maps to `%E3S` alone, not `%S.%E3S`. And `MI` means minute in Snowflake but `%M` is minute and `%m` is month in BigQuery, which is exactly the kind of single-character slip that survives code review; diff actual rendered output during validation rather than eyeballing format strings.

**Boundary semantics — ⚠ silent behaviour change.** Snowflake `DATEDIFF` counts **date-part boundaries crossed**: `DATEDIFF(year, '2025-12-31', '2026-01-01') = 1` despite being one day apart. BigQuery `DATE_DIFF` also counts boundaries, so date-level translations agree. But `TIMESTAMP_DIFF` and `DATETIME_DIFF` count **whole elapsed units**: `TIMESTAMP_DIFF('2026-01-01 00:00:01', '2025-12-31 23:59:59', HOUR) = 0`, whereas Snowflake `DATEDIFF(hour, ...)` on the same inputs returns 1 (boundary crossed). Any SLA, ageing or duration logic on timestamps needs reviewing case by case. To replicate Snowflake's boundary counting on timestamps, truncate both sides first: `TIMESTAMP_DIFF(TIMESTAMP_TRUNC(t2, HOUR), TIMESTAMP_TRUNC(t1, HOUR), HOUR)`.

**Day-of-week numbering — ⚠.** Snowflake `DAYOFWEEK` returns 0–6 or 1–7 depending on the `WEEK_START` session parameter (default: Sunday = 0 with WEEK_START 0... in practice default returns 1=Monday under ISO settings, 0=Sunday otherwise). BigQuery `EXTRACT(DAYOFWEEK ...)` is fixed: 1 = Sunday, 7 = Saturday. Don't translate day-of-week arithmetic without checking what the Snowflake account's `WEEK_START` actually was; safest is to compare day names during validation.

**DATE_TRUNC week start.** Snowflake `DATE_TRUNC('week', d)` honours `WEEK_START` (default Monday under ISO semantics). BigQuery `DATE_TRUNC(d, WEEK)` starts weeks on **Sunday**; use `DATE_TRUNC(d, WEEK(MONDAY))` or `ISOWEEK` to match Monday-start weeks.


### 5.6 Aggregate functions

| Snowflake | BigQuery | Notes |
|---|---|---|
| `LISTAGG(x, ',')` | `STRING_AGG(x, ',')` | |
| `LISTAGG(x, ',') WITHIN GROUP (ORDER BY y)` | `STRING_AGG(x, ',' ORDER BY y)` | BigQuery puts ORDER BY inside the call |
| `LISTAGG(DISTINCT x, ',')` | `STRING_AGG(DISTINCT x, ',')` | DISTINCT + ORDER BY: BigQuery requires ordering by the aggregated expression itself |
| `ARRAY_AGG(x)` | `ARRAY_AGG(x)` | **⚠** Snowflake silently drops NULLs from ARRAY_AGG; BigQuery includes them and then errors if the array is stored. Use `ARRAY_AGG(x IGNORE NULLS)` for like-for-like |
| `ARRAY_AGG(x) WITHIN GROUP (ORDER BY y)` | `ARRAY_AGG(x ORDER BY y)` | |
| `MEDIAN(x)` | No direct aggregate | `APPROX_QUANTILES(x, 2)[OFFSET(1)]` (approximate) or exact via `PERCENTILE_CONT(x, 0.5) OVER ()` with `ANY_VALUE`/`MAX` per group: `SELECT grp, MAX(med) FROM (SELECT grp, PERCENTILE_CONT(x, 0.5) OVER (PARTITION BY grp) med FROM t) GROUP BY grp` |
| `PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY x)` | `PERCENTILE_CONT(x, 0.5) OVER (...)` | **⚠** BigQuery's version is window-only, not a true aggregate; use the wrap-and-group pattern above |
| `MODE(x)` | `APPROX_TOP_COUNT(x, 1)[OFFSET(0)].value` | Approximate |
| `APPROX_COUNT_DISTINCT(x)` / `HLL(x)` | `APPROX_COUNT_DISTINCT(x)` | HLL sketch import/export exists in both (`HLL_EXPORT`/`HLL_COUNT.*`) but the sketch formats are incompatible |
| `COUNT_IF(cond)` | `COUNTIF(cond)` | No underscore |
| `SUM(IFF(cond, 1, 0))` | `COUNTIF(cond)` | Tidier idiom |
| `MIN_BY(x, y)` / `MAX_BY(x, y)` | `MIN_BY(x, y)` / `MAX_BY(x, y)` | Now native in BigQuery; older guides say ARRAY_AGG ORDER BY LIMIT 1, no longer needed |
| `ANY_VALUE(x)` | `ANY_VALUE(x)` | |
| `OBJECT_AGG(k, v)` | `JSON_OBJECT` built from `ARRAY_AGG(STRUCT(k, v))`, or aggregate into JSON | No direct equivalent; usually restructured |
| `CORR`, `COVAR_POP`, `COVAR_SAMP`, `STDDEV`, `VARIANCE` | Same names | Direct |

### 5.7 Window functions

| Snowflake | BigQuery | Notes |
|---|---|---|
| `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `NTILE`, `LEAD`, `LAG`, `FIRST_VALUE`, `LAST_VALUE`, `NTH_VALUE` | Identical | `IGNORE NULLS` supported in both for navigation functions |
| `RATIO_TO_REPORT(x) OVER (PARTITION BY g)` | `SAFE_DIVIDE(x, SUM(x) OVER (PARTITION BY g))` | |
| `CONDITIONAL_TRUE_EVENT(cond) OVER (...)` | `SUM(IF(cond, 1, 0)) OVER (... ROWS UNBOUNDED PRECEDING)` | Sessionisation idiom |
| `CONDITIONAL_CHANGE_EVENT(x) OVER (...)` | `SUM(IF(x != LAG(x) OVER w, 1, 0)) OVER w` nested via subquery | BigQuery doesn't allow nesting window functions; two-step subquery needed |

Frame defaults match: with an ORDER BY and no explicit frame, both use `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, which makes `LAST_VALUE` misbehave identically in both dialects (add `ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING`).

One Snowflake leniency to watch: Snowflake permits window functions in more clause positions and tolerates some implicit ordering. BigQuery is stricter about where analytic functions can appear (not in WHERE/GROUP BY/HAVING; use QUALIFY or a subquery).

---

## 6. Semi-structured data: VARIANT to JSON

This is usually the largest single chunk of manual work in a Snowflake migration, because Snowflake's colon-path syntax is pervasive and terse.

### 6.1 Path access and extraction

```sql
-- Snowflake
select
    payload:customer.id::number          as customer_id,
    payload:customer.name::varchar       as customer_name,
    payload:items[0].sku::varchar        as first_sku,
    payload:"weird key"::varchar         as weird_key
from raw_events;

-- BigQuery (payload is JSON type)
select
    int64(payload.customer.id)                       as customer_id,
    json_value(payload.customer.name)                as customer_name,
    json_value(payload.items[0].sku)                 as first_sku,
    json_value(payload['weird key'])                 as weird_key
from `raw.events`;
```

Mapping table:

| Snowflake | BigQuery (JSON type) | BigQuery (STRING column) |
|---|---|---|
| `col:a.b` | `col.a.b` | `JSON_QUERY(col, '$.a.b')` |
| `col:a.b::varchar` | `JSON_VALUE(col.a.b)` or `STRING(col.a.b)` | `JSON_VALUE(col, '$.a.b')` |
| `col:a.b::number` | `INT64(col.a.b)` / `FLOAT64(...)` / `LAX_INT64(...)` | `SAFE_CAST(JSON_VALUE(col, '$.a.b') AS INT64)` |
| `col:a.b::boolean` | `BOOL(col.a.b)` / `LAX_BOOL(...)` | `SAFE_CAST(JSON_VALUE(...) AS BOOL)` |
| `GET_PATH(col, 'a.b')` | `JSON_QUERY(col, '$.a.b')` | Same |
| `col['a']` | `col['a']` | |
| `PARSE_JSON(s)` | `PARSE_JSON(s)` / `SAFE.PARSE_JSON(s)` | |
| `TO_JSON(v)` | `TO_JSON_STRING(v)` | |
| `OBJECT_CONSTRUCT('k', v, ...)` | `JSON_OBJECT('k', v, ...)` or `TO_JSON(STRUCT(v AS k))` | |
| `OBJECT_CONSTRUCT(*)` | `TO_JSON(t)` for the whole row alias | |
| `ARRAY_CONSTRUCT(a, b)` | `[a, b]` (typed) or `JSON_ARRAY(a, b)` | |
| `IS_NULL_VALUE(v)` | `v = JSON 'null'` or check `JSON_TYPE(v) = 'null'` | JSON null vs SQL NULL exists in both |
| `TYPEOF(v)` | `JSON_TYPE(v)` | |
| `OBJECT_KEYS(v)` | No direct equivalent | `JSON_KEYS(v)` now exists in BigQuery for this |
| `CHECK_JSON(s)` | `SAFE.PARSE_JSON(s) IS NULL` test | |

The `LAX_` family (`LAX_INT64`, `LAX_STRING`, `LAX_BOOL`, `LAX_FLOAT64`) is the closest match to Snowflake's forgiving `::` casting from VARIANT, coercing across JSON types ("42" → 42) where the strict converters error.

**⚠ key behaviour:** Snowflake path access on a missing key returns SQL NULL silently. BigQuery JSON dot access also returns NULL for missing keys. But strict converters (`INT64(json)`) **error** on type mismatch where Snowflake's `::` cast would often coerce or where `TRY_CAST` would null. Default to `LAX_` or `SAFE_CAST(JSON_VALUE(...))` when porting, then tighten.

### 6.2 FLATTEN to UNNEST

```sql
-- Snowflake
select
    e.event_id,
    f.value:sku::varchar    as sku,
    f.value:qty::number     as qty,
    f.index                 as item_index
from events e,
lateral flatten(input => e.payload:items) f;

-- BigQuery
select
    e.event_id,
    json_value(item.sku)            as sku,
    lax_int64(item.qty)             as qty,
    item_index
from `raw.events` e,
unnest(json_query_array(e.payload.items)) as item with offset as item_index;
```

| FLATTEN feature | BigQuery equivalent |
|---|---|
| `f.value` | The unnested element itself |
| `f.index` | `WITH OFFSET` |
| `f.key` (flattening objects) | No direct object-flatten; restructure or use `JSON_KEYS` + access |
| `outer => true` | `LEFT JOIN UNNEST(...)` — **⚠** default comma-join UNNEST is an implicit CROSS JOIN and **drops rows where the array is NULL or empty**, exactly like FLATTEN's default `outer => false`. So default-to-default matches, but check every `outer => true` |
| `recursive => true` | No equivalent; restructure with explicit nested UNNESTs |
| `path => 'a.b'` | Apply the path in `JSON_QUERY_ARRAY(col, '$.a.b')` |

Where the array's element shape is known and stable, the better long-term BigQuery target is a typed `ARRAY<STRUCT<...>>` column rather than JSON, which makes UNNEST direct (`UNNEST(e.items)`) and far cheaper to query.

### 6.3 Structural difference worth internalising

Snowflake's model: everything semi-structured is VARIANT, schema-on-read, columnarised automatically behind the scenes. BigQuery's model: prefer explicit nested and repeated STRUCT/ARRAY types in the schema, fall back to the JSON type for genuinely variable shapes. A faithful migration keeps JSON; a good migration promotes stable paths to typed columns, because typed columns cluster, partition-prune and cost less to scan.

---

## 7. Query patterns and constructs

### 7.1 PIVOT and UNPIVOT

```sql
-- Snowflake
select * from monthly_sales
pivot (sum(amount) for month in ('JAN', 'FEB', 'MAR'));

-- BigQuery
select * from monthly_sales
pivot (sum(amount) for month in ('JAN', 'FEB', 'MAR'));
```

Near-identical. Differences: Snowflake supports `ANY` and subqueries in the IN list (dynamic pivot); BigQuery requires a literal list, so dynamic pivots need `EXECUTE IMMEDIATE` with a generated statement. UNPIVOT translates directly in both.

### 7.2 Hierarchical queries

Snowflake `CONNECT BY` has no BigQuery equivalent. Both support standard recursive CTEs, which is the translation target:

```sql
-- Snowflake
select id, parent_id, sys_connect_by_path(name, ' > ') as path
from org
start with parent_id is null
connect by parent_id = prior id;

-- BigQuery
with recursive org_tree as (
    select id, parent_id, name, name as path
    from org
    where parent_id is null
    union all
    select o.id, o.parent_id, o.name, concat(t.path, ' > ', o.name)
    from org o
    join org_tree t on o.parent_id = t.id
)
select * from org_tree;
```

Snowflake also supports `WITH RECURSIVE`, so if the codebase already uses recursive CTEs they port directly.

### 7.3 Sampling

| Snowflake | BigQuery |
|---|---|
| `select * from t sample (10);` (10% row sample) | `select * from t tablesample system (10 percent);` |
| `select * from t sample (100 rows);` | `order by rand() limit 100` or qualify on `rand()` |
| `sample block (10)` | `tablesample system` is already block-based |

BigQuery TABLESAMPLE is block-sampled and not repeatable; Snowflake's `seed` option has no equivalent. For deterministic samples in BigQuery use `WHERE MOD(ABS(FARM_FINGERPRINT(CAST(id AS STRING))), 100) < 10`.

### 7.4 Row generators

```sql
-- Snowflake
select seq4() as n
from table(generator(rowcount => 1000));

select dateadd(day, seq4(), '2026-01-01'::date) as d
from table(generator(rowcount => 365));

-- BigQuery
select n from unnest(generate_array(0, 999)) as n;

select d from unnest(generate_date_array('2026-01-01', '2026-12-31')) as d;
```

`GENERATE_DATE_ARRAY` and `GENERATE_TIMESTAMP_ARRAY` cover the date-spine pattern more cleanly than Snowflake's generator. dbt_utils.date_spine handles both via the adapter.

### 7.5 Sequences and identity columns

| Snowflake | BigQuery |
|---|---|
| `CREATE SEQUENCE` / `seq.nextval` | No sequences |
| `IDENTITY` / `AUTOINCREMENT` columns | No identity columns |

Translation options, in order of preference: a natural or hashed surrogate key (`TO_HEX(MD5(...))`, dbt_utils `generate_surrogate_key`); `GENERATE_UUID()` where global uniqueness suffices; `ROW_NUMBER()` over a stable ordering plus a max-key offset for load-time sequencing. Monotonic gap-free sequences are an anti-pattern in BigQuery; if the requirement survives scrutiny, it belongs upstream of the warehouse.


---

## 8. Procedural code: scripting, procedures and UDFs

### 8.1 Scripting blocks

```sql
-- Snowflake Scripting
declare
    cutoff date default dateadd(day, -30, current_date());
    row_count integer;
begin
    delete from events where event_date < :cutoff;
    row_count := sqlrowcount;
    return row_count;
end;

-- BigQuery procedural language
declare cutoff date default date_sub(current_date('Europe/London'), interval 30 day);
declare row_count int64;

delete from `analytics.events` where event_date < cutoff;
set row_count = @@row_count;
select row_count;
```

| Concept | Snowflake Scripting | BigQuery scripting |
|---|---|---|
| Block structure | `DECLARE ... BEGIN ... EXCEPTION ... END` | Flat statements; `BEGIN ... EXCEPTION WHEN ERROR THEN ... END` blocks available |
| Variable reference in SQL | `:var` bind syntax inside block SQL | Bare variable name |
| Affected rows | `SQLROWCOUNT` | `@@row_count` |
| Loops, IF, WHILE, CASE | Supported | Supported (`IF/ELSEIF`, `LOOP`, `WHILE`, `FOR ... IN`) |
| Cursors | Supported | `FOR rec IN (SELECT ...) DO ... END FOR` covers most cursor use |
| Dynamic SQL | `EXECUTE IMMEDIATE :stmt` | `EXECUTE IMMEDIATE stmt [USING ...]` |
| Exceptions | Named exceptions, `RAISE` | `RAISE USING MESSAGE = ...`, `@@error.message` |
| Transactions in scripts | `BEGIN/COMMIT/ROLLBACK` | `BEGIN TRANSACTION; ... COMMIT TRANSACTION;` supported with restrictions (no DDL inside, one at a time per session) |

### 8.2 Stored procedures

Snowflake procedures come in SQL (Snowflake Scripting), JavaScript, Python, Java and Scala flavours. BigQuery stored procedures are SQL-only (plus Apache Spark stored procedures for the Python/Scala cases, which run on serverless Spark and are a different cost and latency profile).

Translation guidance: SQL-scripting procedures port to BigQuery procedures fairly directly. JavaScript procedures doing orchestration (loops over tables, dynamic DDL) port to BigQuery SQL scripting with EXECUTE IMMEDIATE. Python/Snowpark procedures doing real computation usually belong outside the warehouse in BigQuery's world: Dataform/dbt for transformation logic, Cloud Run or Composer for orchestration. Resist translating them literally.

### 8.3 UDFs

| Snowflake | BigQuery |
|---|---|
| SQL UDF (scalar) | `CREATE FUNCTION ... AS (expression)` — direct port |
| SQL UDTF (table function) | `CREATE TABLE FUNCTION ... AS SELECT ...` — direct port |
| JavaScript UDF | JavaScript UDF — supported, similar but slower than SQL; check library availability |
| Python UDF / vectorised UDF | No in-warehouse Python UDF; use remote functions (Cloud Functions/Cloud Run) or BigQuery DataFrames |
| External functions (API Gateway) | Remote functions over Cloud Functions |
| `MEMOIZABLE` functions | No equivalent |

BigQuery UDFs can be temporary (script-scoped) or persistent in a dataset; persistent UDFs are referenced as `dataset.function_name`, which affects how shared utility functions are organised compared with Snowflake's schema-level function namespaces.

---

## 9. Architecture and cost model: what changes operationally

Not strictly SQL translation, but these shape how translated SQL should be written.

| Dimension | Snowflake | BigQuery |
|---|---|---|
| Compute | Named virtual warehouses, per-second credit billing while running | Serverless: on-demand (per TiB scanned) or capacity (slot reservations, autoscaling) |
| Cost lever in SQL | Mostly runtime: faster query = fewer credits | **On-demand: bytes scanned.** `SELECT *` and unpartitioned scans cost real money regardless of runtime |
| Tuning unit | Warehouse size, clustering keys, query profile | Partition pruning, clustering, materialisation, avoiding SELECT * |
| Result cache | 24h result cache | Result cache (free re-runs of identical queries on unchanged tables) |
| Local disk spill | Warehouse-size dependent | Slot memory; shuffle handled by the service |
| Concurrency control | Multi-cluster warehouses | Slot scheduler; on-demand has per-project slot fairness |
| Query limits worth knowing | Few practical ones | 6-hour max query runtime; interactive concurrency quotas; 10,000 partitions per table |

Consequences for translated SQL:

- **Prune or pay.** Every incremental model, MERGE and reporting query against a large table should filter on the partition column with a constant-foldable predicate. Predicates wrapped in functions of the partition column (`WHERE DATE(ts) = ...` against a TIMESTAMP-partitioned table) do still prune in current BigQuery for common cases, but the safe idiom is to filter directly on the partitioning expression.
- **Column pruning is the cost model.** BigQuery charges for columns read, so wide `SELECT *` staging patterns that were merely untidy on Snowflake become billable on-demand. dbt's standard "import CTEs with explicit columns" convention pays for itself here.
- **No warehouse to size.** Performance problems shift from "bump the warehouse" to query shape: reduce shuffled bytes, pre-aggregate, avoid exploding joins before aggregation.

---

## 10. dbt migration notes

For codebases managed in dbt (the common case for this kind of migration), the adapter absorbs a lot, but not everything.

### What the adapter handles

- `{{ ref() }}` / `{{ source() }}` resolution and quoting
- Cross-database macros: `dbt.date_trunc`, `dbt.dateadd`, `dbt.datediff`, `dbt.concat`, `dbt.split_part`, `dbt.safe_cast`, `dbt_utils.generate_surrogate_key`, `dbt_utils.date_spine` and friends all compile to the correct dialect. **Audit which models bypass these with raw SQL; those are your manual translation backlog.**
- Incremental materialisation plumbing (BigQuery default strategy is `merge`)

### What it does not handle

| Concern | Snowflake (dbt-snowflake) | BigQuery (dbt-bigquery) |
|---|---|---|
| Model config | `snowflake_warehouse`, `cluster_by`, `transient`, `query_tag` | `partition_by` (dict: field, data_type, granularity), `cluster_by`, `require_partition_filter`, `hours_to_expiration`, `labels` |
| Incremental strategies | `merge`, `delete+insert`, `append`, `microbatch` | `merge`, `insert_overwrite`, `microbatch` |
| Cheap full-partition refresh | n/a | `insert_overwrite` with `copy_partitions: true` uses the free copy API instead of a billed MERGE — the single biggest cost win on large incremental models |
| Incremental pruning | Less critical | Add a partition filter on the **target** side of the merge predicate (`incremental_predicates` or static partition selection) or every run scans the full target |
| Case handling | dbt objects resolve to uppercase in the warehouse | Names preserved as written; check any `quoting:` config carried over from Snowflake |
| Dev environments | Zero-copy clone of prod schemas | Table clones exist; common alternative is dataset-per-developer with deferral (`--defer`) |

A `partition_by` worth copying as the default shape:

```yaml
{{ config(
    materialized = 'incremental',
    incremental_strategy = 'insert_overwrite',
    partition_by = { 'field': 'event_date', 'data_type': 'date', 'granularity': 'day' },
    cluster_by = ['customer_id'],
    partitions = dbt.partition_range(var('start_date'), var('end_date')) if var('start_date', none) else none
) }}
```

### Validation approach that works

1. Run both warehouses in parallel for the cutover window with the same sources.
2. Compare at three levels per model: row counts, column-level aggregates (SUM/MIN/MAX/COUNT DISTINCT per column) and full-row hash diffs on a deterministic sample. dbt's `audit_helper` package or a thin `EXCEPT DISTINCT` harness both work.
3. Expect and triage classes of difference rather than rows: timezone shifts (section 1.3), boundary-count datediffs (5.5), regex behaviour (5.3), float formatting and hash-key mismatches (5.4). Almost every real discrepancy lands in one of those buckets.

---

## 11. Quick-reference gotcha checklist

The compressed list to pin next to the code review checklist. Everything here compiles cleanly after a naive translation and returns wrong answers anyway.

1. **Timezones.** Snowflake session timezone (often America/Los_Angeles by default) vs BigQuery UTC-everywhere. Audit `CURRENT_DATE`, `CURRENT_TIMESTAMP` and every TIMESTAMP→DATE cast.
2. **DATEDIFF argument order reverses** (`DATEDIFF(part, from, to)` → `DATE_DIFF(to, from, part)`) and **timestamp diffs count whole units, not boundaries**.
3. **DATE_TRUNC week starts Sunday** in BigQuery; use `WEEK(MONDAY)` or `ISOWEEK`.
4. **DAYOFWEEK numbering** depends on Snowflake's `WEEK_START`; BigQuery is fixed 1=Sunday.
5. **Bare UNION is a syntax error**; Snowflake's plain UNION means UNION DISTINCT.
6. **No `::` casts, no ILIKE, no `%` modulo, no CONCAT_WS, no DECODE, no SPLIT_PART** — all have idiomatic rewrites (section 5).
7. **Array indexing is 0-based via OFFSET, 1-based via ORDINAL**; SPLIT_PART is 1-based. Off-by-one factory.
8. **ARRAY_AGG keeps NULLs** in BigQuery and storing them errors; Snowflake drops them. Add `IGNORE NULLS`.
9. **Regex: RE2, no backreferences or lookarounds**, REGEXP_LIKE anchors but REGEXP_CONTAINS doesn't, backslash escaping changes.
10. **HASH() values will never match FARM_FINGERPRINT**; rebuild hash keys from source columns, and wrap MD5/SHA in TO_HEX.
11. **Format strings rewrite by hand** (Oracle-style → strftime-style); no mechanical mapping.
12. **QUALIFY needs a WHERE clause** (use `WHERE TRUE`).
13. **UNNEST drops empty/NULL arrays** like default FLATTEN; `outer => true` needs LEFT JOIN UNNEST.
14. **MERGE without partition pruning scans the whole target every run.** Add target-side partition predicates; prefer `insert_overwrite` + `copy_partitions` in dbt where the grain allows.
15. **Time travel drops from up to 90 days to 7.** Update recovery runbooks; schedule snapshots if longer retention matters.
16. **Boolean string casts**: 'yes'/'t'/'1' no longer cast to TRUE.
17. **LOG(base, x) becomes LOG(x, base).**
18. **PERCENTILE_CONT/MEDIAN are window-only**; group via the wrap-and-MAX pattern or accept APPROX_QUANTILES.
19. **Dataset and table names are case-sensitive.** Standardise on lowercase during migration.
20. **Cost model inverts**: bytes scanned, not seconds run. SELECT * and unpartitioned scans go from untidy to expensive.
21. **NaN and NULL sort positions differ** (NaN largest in Snowflake, smallest in BigQuery; default NULL position flips). Make NULLS FIRST/LAST explicit on any float or nullable ORDER BY that feeds ranking.
22. **Nanosecond timestamps truncate to microseconds** on load; add a tiebreaker if event ordering relied on them.
23. **CONTAINS_SUBSTR is case-insensitive**; it is not a drop-in for Snowflake CONTAINS. Use STRPOS for exact matching.
24. **ARRAY_TO_STRING drops NULL elements** in BigQuery where Snowflake rendered empties; concatenated-key columns built this way will diverge.
25. **CURRENT_ROLE()-based masking and RLS logic doesn't translate**; rebuild on IAM principals and policy tags (section 16).

---

## 12. Tooling

For bulk translation, the BigQuery Migration Service includes a batch SQL translator with a Snowflake dialect mode, plus an interactive translator in the console. Snowflake's SnowConvert AI also targets BigQuery (and works in reverse), and sqlglot transpiles between the dialects programmatically, which suits building house rewrite rules into CI. All of them handle the mechanical 80% (casts, function renames, qualification) and reliably leave behind exactly the items in section 11, which is why this guide leads with them. Pair machine translation with the validation harness in section 10 rather than trusting either alone.

---

## 13. Array functions

Snowflake array functions operate on VARIANT arrays; BigQuery's on typed arrays. The names mostly differ.

| Snowflake | BigQuery | Notes |
|---|---|---|
| `ARRAY_SIZE(a)` | `ARRAY_LENGTH(a)` | |
| `ARRAY_CONTAINS(v::variant, a)` | `v IN UNNEST(a)` or `EXISTS(SELECT 1 FROM UNNEST(a) x WHERE x = v)` | **⚠ argument order**: Snowflake takes (value, array) |
| `ARRAY_CAT(a, b)` | `ARRAY_CONCAT(a, b)` | |
| `ARRAY_APPEND(a, v)` / `ARRAY_PREPEND(v, a)` | `ARRAY_CONCAT(a, [v])` / `ARRAY_CONCAT([v], a)` | |
| `ARRAY_SLICE(a, from, to)` | `(SELECT ARRAY_AGG(x) FROM UNNEST(a) x WITH OFFSET o WHERE o BETWEEN from AND to - 1)` | No direct function; 0-based half-open in Snowflake |
| `ARRAY_DISTINCT(a)` | `(SELECT ARRAY_AGG(DISTINCT x) FROM UNNEST(a) x)` | Order not preserved |
| `ARRAY_COMPACT(a)` | `(SELECT ARRAY_AGG(x) FROM UNNEST(a) x WHERE x IS NOT NULL)` | Removes NULLs |
| `ARRAY_POSITION(v, a)` | `(SELECT MIN(o) FROM UNNEST(a) x WITH OFFSET o WHERE x = v)` | Both 0-based |
| `ARRAYS_OVERLAP(a, b)` | `EXISTS(SELECT 1 FROM UNNEST(a) x WHERE x IN UNNEST(b))` | |
| `ARRAY_TO_STRING(a, sep)` | `ARRAY_TO_STRING(a, sep[, null_text])` | **⚠** Snowflake renders NULL elements as empty strings; BigQuery skips NULL elements entirely unless you pass null_text. Element counts in the output can differ |
| `ARRAY_INTERSECTION(a, b)` | `(SELECT ARRAY_AGG(x) FROM UNNEST(a) x WHERE x IN UNNEST(b))` | |
| `a[0]` (VARIANT array) | `a[OFFSET(0)]` / `a[SAFE_OFFSET(0)]` / `a[ORDINAL(1)]` | Both 0-based at heart, but BigQuery makes you say so; OFFSET errors out of range, SAFE_OFFSET nulls |

A structural reminder from section 2 that belongs here too: BigQuery arrays of arrays are illegal (`ARRAY<ARRAY<T>>` won't compile); nest a STRUCT in between (`ARRAY<STRUCT<arr ARRAY<T>>>`). Snowflake VARIANT arrays nest freely.

## 14. Bit operations and context functions

| Snowflake | BigQuery |
|---|---|
| `BITAND(a, b)` / `BITOR` / `BITXOR` / `BITNOT(a)` | `a & b`, `a \| b`, `a ^ b`, `~a` (operators on INT64) |
| `BITSHIFTLEFT(a, n)` / `BITSHIFTRIGHT(a, n)` | `a << n` / `a >> n` |
| `UNIFORM(lo, hi, RANDOM())` | `CAST(FLOOR(RAND() * (hi - lo + 1)) + lo AS INT64)` |

Context functions mostly have no equivalent because the concepts don't exist:

| Snowflake | BigQuery |
|---|---|
| `CURRENT_USER()` | `SESSION_USER()` |
| `CURRENT_ROLE()` | No equivalent (IAM, not roles); authorisation checks live outside SQL |
| `CURRENT_WAREHOUSE()` | No equivalent (serverless) |
| `CURRENT_DATABASE()` / `CURRENT_SCHEMA()` | `@@project_id` system variable; no default-dataset accessor |
| `CURRENT_ACCOUNT()` / `CURRENT_REGION()` | `@@project_id`; region is a dataset property, query via INFORMATION_SCHEMA |
| `LAST_QUERY_ID()` | `@@last_job_id` in scripts |

Audit any row-level security or audit-trail logic built on `CURRENT_ROLE()`; it needs redesigning around `SESSION_USER()` and IAM rather than translating.

## 15. Streams, tasks and dynamic tables

The Snowflake objects that carry pipeline behaviour rather than data need architectural mapping, not syntax mapping.

| Snowflake | Closest BigQuery equivalent | Notes |
|---|---|---|
| `STREAM` (CDC on a table) | `CHANGES` / `APPENDS` table-valued functions, or change history via time travel | BigQuery's `APPENDS(TABLE t, start, end)` TVF covers append-only CDC; full update/delete change tracking is narrower than Snowflake streams. dbt incremental models replace many stream+task patterns outright |
| `TASK` (scheduled SQL, DAGs of tasks) | Scheduled queries, or Dataform/dbt/Composer for DAGs | Scheduled queries have no inter-task dependencies; anything DAG-shaped belongs in an orchestrator |
| `DYNAMIC TABLE` (declarative incremental materialisation with target lag) | No direct equivalent | Choose per case: materialized view (if the query qualifies), dbt incremental model on a schedule, or a continuous query for streaming SQL. Treat each dynamic table as a small design decision |
| `ALERT` | Scheduled query + Cloud Monitoring/Logging, or assertions in Dataform/dbt tests | |
| Snowpipe | Storage Write API, Pub/Sub subscriptions to BigQuery, or DTS | Tooling, not SQL |

## 16. Security and governance objects

Both platforms cover the same ground; none of the DDL ports directly.

| Concern | Snowflake | BigQuery |
|---|---|---|
| Access model | Hierarchical RBAC roles, GRANT/REVOKE, role activation per session | IAM bindings at project/dataset/table/column level; no role switching |
| Row-level security | `CREATE ROW ACCESS POLICY` + `ALTER TABLE ... ADD ROW ACCESS POLICY` | `CREATE ROW ACCESS POLICY ... ON t GRANT TO (...) FILTER USING (...)` — similar name, different shape; policies grant to IAM principals |
| Column masking | `CREATE MASKING POLICY` applied per column, can branch on `CURRENT_ROLE()` | Dynamic data masking via policy tags (Data Catalog taxonomy + data policies); masking rules attach to tags, not columns |
| Secure views | `CREATE SECURE VIEW` | Authorized views (IAM grant of the view into the source dataset) |
| Tags | `CREATE TAG` / `ALTER ... SET TAG` | Policy tags (governed, drive masking/ACLs) and labels (free-form key-value, drive billing breakdown) |
| Sharing | Secure Data Sharing, listings | Analytics Hub listings; or plain cross-project IAM |

The migration shape: masking policies that branch on `CURRENT_ROLE()` have no mechanical translation because BigQuery masking is principal-and-tag based. Inventory each policy, map roles to IAM groups, then rebuild as taxonomy + data policies. Budget real time for this; it's design work.

## 17. Metadata and observability

| Snowflake | BigQuery |
|---|---|
| `db.INFORMATION_SCHEMA.TABLES/COLUMNS/VIEWS` | `project.dataset.INFORMATION_SCHEMA.TABLES/COLUMNS/VIEWS` (dataset-scoped) |
| `SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY` | `` `region-eu`.INFORMATION_SCHEMA.JOBS `` (region-scoped; also JOBS_BY_USER/_FOLDER/_ORGANIZATION) |
| `ACCOUNT_USAGE.ACCESS_HISTORY` | `INFORMATION_SCHEMA.JOBS` referenced_tables, plus Cloud Audit Logs for full lineage |
| `WAREHOUSE_METERING_HISTORY` (cost) | `JOBS.total_bytes_billed` / `total_slot_ms`; billing export to BigQuery for invoiced cost |
| `TABLE_STORAGE_METRICS` | `INFORMATION_SCHEMA.TABLE_STORAGE` |
| `SHOW TABLES` / `DESCRIBE TABLE` | `INFORMATION_SCHEMA` queries or `bq show`; no SHOW/DESCRIBE statements |
| `RESULT_SCAN(query_id)` | No equivalent in SQL; job results retrievable via API for 24h |

Worth knowing: ACCOUNT_USAGE views lag up to 45 minutes to 3 hours; `INFORMATION_SCHEMA.JOBS` is near-real-time but only retains 180 days. Cost-monitoring dashboards (the Looker block style) rebuild cleanly on JOBS plus the billing export.

## 18. Transactions

| | Snowflake | BigQuery |
|---|---|---|
| Model | READ COMMITTED; explicit `BEGIN`/`COMMIT`/`ROLLBACK` anywhere | Snapshot isolation; `BEGIN TRANSACTION`/`COMMIT TRANSACTION` inside scripts or sessions only |
| DDL in transaction | Autocommits immediately (cannot roll back) | Not allowed inside a transaction; each DDL statement is individually atomic |
| Concurrent writers | Locking on partitions being modified | Optimistic: conflicting concurrent transactions abort on commit; first writer wins |
| Cross-statement scope | Any session | BigQuery sessions feature scopes temp tables and transactions across separate requests |
| Autocommit | `AUTOCOMMIT` parameter | Always autocommit outside explicit transactions |

Snowflake procedures that wrap a dozen statements in one transaction usually port fine; patterns relying on long-held locks or read-your-uncommitted-sibling-statement behaviour need rethinking under optimistic concurrency, since a busy target table means commit-time aborts and retries rather than waiting.

## 19. Migration fidelity notes

Small physical differences that surface during data validation rather than SQL translation:

- **Timestamp precision**: Snowflake stores up to nanoseconds (TIMESTAMP_NTZ(9)); BigQuery TIMESTAMP/DATETIME are microsecond precision. Sub-microsecond digits truncate on load. If event ordering depends on nanosecond ties, add a tiebreaker column before migrating.
- **TIME precision**: same story, 9 digits vs 6.
- **NaN ordering**: in ORDER BY, Snowflake sorts NaN as larger than all values; BigQuery sorts NaN smaller than everything including negative infinity. Float columns ordered or window-ranked can change row order. (NULLs also differ in default sort position: Snowflake NULLS LAST on ASC, BigQuery NULLS FIRST on ASC; both accept explicit NULLS FIRST/LAST, so be explicit.)
- **FLOAT64 equality and grouping**: both group NaN values together; comparisons `NaN = NaN` are false in both. No action, just don't panic at validation time.
- **DATE literal strictness**: BigQuery parses only `YYYY-[M]M-[D]D` in date literals; Snowflake's AUTO detection accepts a wide family of formats. Any reliance on loose implicit parsing becomes a PARSE_DATE with an explicit format.
- **Numeric rounding**: NUMERIC in BigQuery rounds half away from zero at scale 9 on write; Snowflake honours the declared scale. A NUMBER(18,2) column that becomes bare NUMERIC keeps more decimal places than before; constrain with parameterised `NUMERIC(18,2)` if write-time rounding to 2dp was load-bearing.

## 20. MERGE refinements and corrections to common claims

Filling in MERGE detail prompted by claims seen in machine-generated guides, some of which are wrong:

- **Multiple `WHEN MATCHED` clauses with search conditions are legal in both** Snowflake and BigQuery; clauses evaluate in order and the first match wins. The claim that BigQuery permits only one WHEN MATCHED is false. What's true in both: a single source row matching is fine, but **multiple source rows matching one target row** errors in BigQuery and (by default, via ERROR_ON_NONDETERMINISTIC_MERGE) in Snowflake.
- **`WHEN NOT MATCHED BY SOURCE THEN DELETE/UPDATE` is supported in both**, and is the idiomatic full-sync pattern. In BigQuery, combine it with a partition predicate on the target inside the WHEN condition or you'll scan and rewrite everything.
- `GROUP BY ALL` is supported in both (claims that BigQuery lacks it are out of date).
- `TRANSLATE` exists in both (see section 5.3).
- Snowflake's regex engine is not RE2 (see section 5.3), though the practical pattern compatibility is higher than the engine difference implies.

## 21. UDF and procedure refinements

Additions to section 8 worth having on the record:

- BigQuery SQL UDF bodies are a single expression after `AS (...)`: no `$$` dollar-quoting, and `RETURNS` is optional (inferred). Scalar subqueries over tables are allowed in persistent SQL UDF bodies, with restrictions (not usable everywhere, e.g. inside materialized views).
- `CREATE TEMP FUNCTION` exists in BigQuery for script-scoped helpers; Snowflake has no temporary functions, so utility UDFs that were schema objects may shrink to temp functions co-located with the scripts that use them.
- Snowflake's `SECURE`, `IMMUTABLE`/`VOLATILE` and `MEMOIZABLE` function properties have no BigQuery equivalents; BigQuery treats SQL UDFs as deterministic by assumption.
- BigQuery procedures have **no RETURN value**; use `OUT`/`INOUT` parameters or write results to a table. Argument modes (`IN` default, `OUT`, `INOUT`) must be declared.
- No `EXECUTE AS OWNER`/`CALLER` toggle: BigQuery procedures always run as the caller. Snowflake owner's-rights procedures used as a privilege bridge need replacing with authorized routines or service-account-run scheduled queries.

## 22. Pipe syntax (BigQuery only)

BigQuery now supports pipe syntax (`FROM t |> WHERE ... |> AGGREGATE ...`) as an alternative query form. Nothing in Snowflake maps to it and nothing requires it; mentioning it only because machine translation output or newer team-written BigQuery may contain it, and it's valid GoogleSQL, not a syntax error to "fix". House style decision whether to allow it; for a migration, stick to standard form so diffs against the Snowflake original stay reviewable.
