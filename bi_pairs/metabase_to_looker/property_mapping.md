# Metabase to Looker: property mapping

Experimental. The tables in `mb_to_lookml.py` are the executable form.

## Types (field effective type)

| Metabase | LookML |
|---|---|
| `type/Text`, `type/UUID` and other text types | `type: string` |
| `type/Integer`, `type/BigInteger`, `type/Float`, `type/Decimal`, `type/Number`, currency, percentage | `type: number` |
| `type/Boolean` | `type: yesno` |
| `type/Date` | `dimension_group: type: time`, `datatype: date` |
| `type/DateTime`, `...WithTZ`, `...WithLocalTZ`, `...WithZoneOffset`, `...WithZoneID`, `type/Instant` | `dimension_group: type: time`, `datatype: timestamp` |

## Date units

| Metabase `temporal-unit` | Looker timeframe |
|---|---|
| `minute`, `hour` | `minute`, `hour` |
| `day` | `date` |
| `week`, `month`, `quarter`, `year` | same |
| `day-of-week`, `day-of-month`, `day-of-year`, `week-of-year` | `day_of_week`, `day_of_month`, `day_of_year`, `week_of_year` |
| `month-of-year`, `quarter-of-year`, `hour-of-day` | `month_num`, `quarter_of_year`, `hour_of_day` |

A Metabase result returns a bucket as the timestamp of its first day (`2026-10-01T00:00:00Z`); Looker returns the bucket's label (`2026-10`). Parity contracts declare the grain (`comparison.dates.grain`).

## Relative date filters (`time-interval`)

| Metabase | Looker | Checked on a live instance |
|---|---|---|
| Previous N units | `N units ago for N units` | Yes (12 months) |
| Previous N units, including the current one | `N+1 units` | Yes (11 months, including this one: `12 months`) |
| Current unit | `this unit` | |
| Next N units | not converted | |
| Dashboard default `pastNunits` | `N units ago for N units` | |
| Dashboard default `pastNunits~` | `N+1 units` | |
| `thisweek`, `lastmonth` and similar | `this week`, `last month` | |
| `YYYY-MM-DD~YYYY-MM-DD` | `YYYY-MM-DD to <end + 1 day>` | |

## Filter operators

| Metabase | Looker filter expression |
|---|---|
| `=`, `in` (one or more values) | `a,b` (commas, `%`, `_` and a leading `-` escaped with `^`) |
| `!=`, `not-in` | `-a,-b` |
| `<`, `>`, `<=`, `>=` | `<n` and so on; on dates `before d` or `after d` |
| `between` | `[a, b]`; on dates `a to <b + 1 day>` |
| `is-null`, `not-null` | `NULL`, `-NULL` |
| `is-empty`, `not-empty` | `EMPTY`, `-EMPTY` |
| `contains`, `starts-with`, `ends-with`, `does-not-contain` | `%x%`, `x%`, `%x`, `-%x%` |
| Boolean `= true` | `Yes` |
| `or` on one field with `=` | `a,b` |
| `or` across fields, segments, `inside`, relative intervals with an offset | not converted |

## Custom-column functions

`+ - * /` (division with `NULLIF`), comparisons, `and`, `or`, `not`, `is-null`, `not-null`, `contains`, `starts-with`, `ends-with`, `does-not-contain`, `case`, `if`, `coalesce`, `concat`, `lower`, `upper`, `trim`, `ltrim`, `rtrim`, `length`, `abs`, `round`, `floor`, `ceil`, `sqrt`, `power`, `log` (`LOG10`), `exp`, `substring` (`SUBSTR`), `replace`. Anything else (for example `datetime-diff`, whose meaning differs from BigQuery's `DATE_DIFF`) is not translated.
