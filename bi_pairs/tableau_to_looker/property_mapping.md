# Tableau to Looker: property mapping

Experimental. The tables in `twb_to_lookml.py` are the executable form.

## Data types

| Tableau `datatype` | LookML |
|---|---|
| `string` | `type: string` |
| `integer`, `real` | `type: number` |
| `boolean` | `type: yesno` |
| `date` | `dimension_group: type: time`, `datatype: date` |
| `datetime` | `dimension_group: type: time`, `datatype: timestamp` |

## Default aggregation

| Tableau `aggregation` | LookML measure | Name |
|---|---|---|
| `Sum` | `type: sum` | `total_<field>` |
| `Avg` | `type: average` | `average_<field>` |
| `Min` | `type: min` | `min_<field>` |
| `Max` | `type: max` | `max_<field>` |
| `CountD` | `type: count_distinct` | `count_distinct_<field>` |
| `Count`, `Year` | no measure (dimension) | |

## Column instance derivations (worksheet fields)

| Prefix | Meaning | LookML field |
|---|---|---|
| `none` | dimension | `<view>.<field>` (dates: `<field>_date`) |
| `sum`, `avg`, `min`, `max`, `ctd` | aggregate | the matching measure |
| `usr` | calculated field as written | `<view>.<calc>` |
| `tyr`, `tqr`, `tmn`, `twk`, `tdy` | date truncation | `<field>_year`, `_quarter`, `_month`, `_week`, `_date` |
| `cnt`, `attr`, others | not mapped | tile skipped, needs_human |

## Formats

| Tableau `default-format` | LookML `value_format_name` |
|---|---|
| starts `p`, with `.0` | `percent_1` |
| starts `p` | `percent_0` |
| starts `c` with £ | `gbp` |
| starts `c` with € | `eur` |
| starts `c` | `usd` |
| anything else | none (hand-finished) |

## Calculation language

Row-level functions with a SQL form. Anything else is not emitted (needs_human).

| Tableau | BigQuery | Snowflake |
|---|---|---|
| `IFNULL(a, b)` | `COALESCE(a, b)` | same |
| `ZN(a)` | `COALESCE(a, 0)` | same |
| `ISNULL(a)` | `(a IS NULL)` | same |
| `IIF(c, a, b)` | `CASE WHEN c THEN a ELSE b END` | same |
| `IF ... THEN ... ELSEIF ... ELSE ... END` | `CASE WHEN ... END` | same |
| `CASE x WHEN v THEN r ... END` | `CASE WHEN x = v THEN r ... END` | same |
| `CONTAINS(s, t)` | `(STRPOS(s, t) > 0)` | `CONTAINS(s, t)` |
| `STARTSWITH`, `ENDSWITH` | `STARTS_WITH`, `ENDS_WITH` | same as Tableau |
| `UPPER`, `LOWER`, `TRIM`, `LTRIM`, `RTRIM`, `ABS`, `SQRT`, `FLOOR`, `LEFT`, `RIGHT`, `REPLACE`, `POWER`, `ROUND` | same | same |
| `CEILING(x)` | `CEIL(x)` | same |
| `LEN(s)` | `LENGTH(s)` | same |
| `DATETRUNC('month', d)` | `DATE_TRUNC(d, MONTH)` (`TIMESTAMP_TRUNC` for datetimes) | `DATE_TRUNC('month', d)` |
| `DATEDIFF('day', a, b)` | `DATE_DIFF(b, a, DAY)` (`TIMESTAMP_DIFF` for datetimes) | `DATEDIFF('day', a, b)` |
| `DATEPART('year', d)`, `YEAR(d)`, `MONTH(d)`, `DAY(d)` | `EXTRACT(YEAR FROM d)` | same |
| `STR(x)`, `INT(x)`, `FLOAT(x)` | `CAST(x AS STRING / INT64 / FLOAT64)` | `CAST(x AS VARCHAR / INTEGER / FLOAT)` |
| `a / b` | `(a) / NULLIF(b, 0)` | same |
| `a % b` | `MOD(a, b)` | same |
| `'x' + s` (string) | `CONCAT('x', s)` | same |
| `==`, `!=` | `=`, `<>` | same |
| `[Parameters].[p]` | `{% parameter p %}` | same |

Aggregates `SUM`, `AVG`, `MIN`, `MAX`, `COUNTD` over a single field become references to the matching measure. `COUNT`, `MEDIAN`, `ATTR`, `STDEV`, `VAR`, `PERCENTILE`, and any aggregate over an expression, are not emitted.
