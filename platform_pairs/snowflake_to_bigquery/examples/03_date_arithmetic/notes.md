# Translation notes — date and timestamp arithmetic (Snowflake → BigQuery)

Mirror of `bigquery_to_snowflake/examples/03_date_arithmetic/notes.md` — read that file for the full cheat sheet and watch-outs. The same argument-order traps apply in reverse.

## Quick reference

| Snowflake | BigQuery |
|---|---|
| `datediff(unit, start, end)` | `date_diff(end, start, unit)` (or `timestamp_diff` for ts) |
| `dateadd(unit, n, d)` | `date_add(d, interval n unit)` |
| `dateadd(unit, -n, d)` | `date_sub(d, interval n unit)` |
| `date_trunc('unit', d)` | `date_trunc(d, unit)` |
| `to_char(d, 'YYYY-MM-DD')` | `format_date('%Y-%m-%d', d)` |
| `to_date(s, 'YYYY-MM-DD')` | `parse_date('%Y-%m-%d', s)` |
| `date_part(epoch_second, ts)` | `unix_seconds(ts)` |

## Argument order trap

BigQuery's `date_diff(end, start, unit)` reads as "the difference, from end back to start". Code translated from Snowflake's `datediff(unit, start, end)` form will compile but return values of the opposite sign if the order isn't reversed. `dbt_migration-validate` spot-checks sign conventions on duration columns.

## Format string conversion

Same mapping as the forward direction, reversed. Snowflake uses Oracle-style (`YYYY`, `MM`, `DD`, `HH24`); BigQuery uses strftime-style (`%Y`, `%m`, `%d`, `%H`). Wire's `dbt_migration-generate` translates format strings automatically inside `to_char` / `to_date` / `to_timestamp` calls.
