# Translation notes — date and timestamp arithmetic

This is the highest-frequency translation in any dbt migration. The vast majority of "weird BQ syntax that doesn't compile" errors during a Snowflake build come from date functions.

## What changed (cheat sheet)

| BigQuery | Snowflake | Watch out for |
|---|---|---|
| `date_diff(end, start, day)` | `datediff(day, start, end)` | **Argument order reverses** — end-start in BQ, start-end in SF |
| `timestamp_diff(end, start, second)` | `datediff(second, start, end)` | Same reversal; also note `timestamp_diff` → `datediff` (no separate timestamp variant) |
| `date_add(d, interval 30 day)` | `dateadd(day, 30, d)` | INTERVAL literal disappears; unit becomes positional first arg |
| `date_sub(d, interval 30 day)` | `dateadd(day, -30, d)` | No `date_sub`; use negative interval |
| `date_trunc(d, month)` | `date_trunc('month', d)` | Argument order reversed AND unit becomes a quoted string |
| `format_date('%Y-%m', d)` | `to_char(d, 'YYYY-MM')` | Function name AND format string syntax differ |
| `parse_date('%Y-%m-%d', s)` | `to_date(s, 'YYYY-MM-DD')` | Function name AND format string syntax differ |
| `current_date()` | `current_date()` (also `current_date`) | Same; safe |
| `current_timestamp()` | `current_timestamp()` | Same; safe |
| `unix_seconds(ts)` | `date_part(epoch_second, ts)` | Different function entirely |

## Why argument order is the trap

Both `datediff` flavours read left-to-right as "the unit, then the smaller value, then the larger value, giving you the difference". The BigQuery version reads "from end, back to start, in this unit". They produce opposite signs for the same inputs. Code that compiles successfully but returns negative values for a "duration" calculation is almost always a missed argument-order swap.

The Wire `dbt_migration-validate` step catches this by spot-checking sign conventions on duration columns — if a not-null-positive value becomes negative after migration, it's flagged for review.

## Format string conversion

BigQuery uses strftime-style format specifiers (`%Y`, `%m`, `%d`, `%H`, `%M`, `%S`). Snowflake uses Oracle-style specifiers (`YYYY`, `MM`, `DD`, `HH24`, `MI`, `SS`). The full mapping:

| BQ specifier | Snowflake specifier |
|---|---|
| `%Y` | `YYYY` |
| `%m` | `MM` |
| `%d` | `DD` |
| `%H` | `HH24` |
| `%I` | `HH12` |
| `%M` | `MI` |
| `%S` | `SS` |
| `%j` | `DDD` |
| `%U` | `WW` |
| `%a` | `DY` |
| `%A` | `DAY` |
| `%b` | `MON` |
| `%B` | `MONTH` |

Wire's `dbt_migration-generate` translates format strings automatically when it sees them inside `format_date` / `parse_date` / `format_timestamp` / `parse_timestamp` calls.

## Wire macro equivalents

The translation guide lists these for common cases:

- `{{ bq_to_sf.date_diff(end, start, 'day') }}` — swaps order
- `{{ bq_to_sf.date_add(d, n, 'day') }}` — drops INTERVAL literal
- `{{ bq_to_sf.timestamp_diff(t1, t2, 'second') }}` — same swap, timestamp aware

Use macros where the source code is going to keep evolving (so the translation is reusable). For one-shot migrations the inline rewrite shown in `after.sql` is fine.
