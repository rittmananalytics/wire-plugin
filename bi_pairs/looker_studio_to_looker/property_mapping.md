# Looker Studio to Looker: property mapping

Experimental. The tables in `ls_to_lookml.py` are the executable form. Codes were confirmed against captured fields, recorded chart ranges and the SQL Looker Studio sent to BigQuery (October 2026).

## Data type codes

| Code | LookML |
|---|---|
| 0 | `type: string` |
| 1 | `type: yesno` |
| 2, 3 | `type: number` |
| 8 | `dimension_group`, `datatype: date` |
| 9 | `dimension_group`, `datatype: timestamp` |

Other codes are emitted as strings and listed.

## Aggregation, sort and date range codes

| Field | Code | Meaning |
|---|---|---|
| `aggregation` | 6 | SUM |
| Record Count | (system field) | `COUNT(1)` |
| `sort.direction_code` | 1 | descending; others ascending |
| `date_duration` offset unit | 3 | day (offset 0 is today) |
| `date_duration` offset unit | 6 | month, counted from the start of a month |

## Formula functions

| Looker Studio | BigQuery SQL |
|---|---|
| `a / b` | `SAFE_DIVIDE(a, b)` |
| `COUNT_DISTINCT(x)` | `COUNT(DISTINCT x)` |
| `NARY_MAX`, `NARY_MIN` | `GREATEST`, `LEAST` |
| `TODAY()` | `CURRENT_DATE()` |
| `SUM`, `AVG`, `MIN`, `MAX`, `COUNT`, `IF`, `CASE`, `IFNULL`, `COALESCE`, `CONCAT`, `UPPER`, `LOWER`, `TRIM`, `SUBSTR`, `REPLACE`, `ROUND`, `ABS`, `CAST`, `DATE_TRUNC`, `DATETIME_TRUNC`, `EXTRACT`, `REGEXP_CONTAINS`, `SAFE_DIVIDE` | same |
| Anything else (`CONTAINS_TEXT` and others) | not translated |

Field references in a formula are `t0.<field name>`: a source column, or another calculated field (inlined).
