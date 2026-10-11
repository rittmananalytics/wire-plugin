# Omni to Looker: property mappings

Experimental. The value tables the converter applies (`wire/scripts/omni_to_lookml.py`). Engagement overrides go in `.wire/engagement/bi_pair_overrides/omni_to_looker/`.

## Formats

| Omni `format` | LookML |
|---|---|
| `currency`, `currency_2`, `usdcurrency`, `usdcurrency_2` | `value_format_name: usd` |
| `currency_0`, `usdcurrency_0` | `value_format_name: usd_0` |
| `gbpcurrency`, `gbpcurrency_2` / `gbpcurrency_0` | `gbp` / `gbp_0` |
| `eurcurrency`, `eurcurrency_2` / `eurcurrency_0` | `eur` / `eur_0` |
| `number_0` to `number_4` | `decimal_0` to `decimal_4` |
| `percent_0` to `percent_4` | `percent_0` to `percent_4` |
| `id` | `id` |
| `thousands_N`, `millions_N`, `billions_N` (N 0 to 2) | `value_format: "#,##0.0,\"K\""` and the like |
| `big`, `bigcurrency`, `accounting`, date formats, anything else | listed, emitted without a format |

Formats in table calculations are upper case (`GBPCURRENCY_2`) and map the same way.

## Timeframes

| Omni | LookML |
|---|---|
| `raw`, `time`, `date`, `week`, `month`, `quarter`, `year` | same |
| `hour`, `minute`, `second`, `millisecond` | same |
| `day_of_week_name` | `day_of_week` |
| `day_of_week_num` | `day_of_week_index` |
| `day_of_month`, `day_of_year`, `hour_of_day`, `month_name`, `month_num`, `quarter_of_year`, `week_of_year` | same |
| `fiscal_quarter`, `fiscal_year`, `fiscal_month_num`, `fiscal_quarter_of_year` | same (the model needs `fiscal_month_offset`) |
| `day_of_quarter` | none: dropped, listed |

A dimension group always carries `raw`, and `date` when it has neither `date` nor `time`. A timeframe a tile or filter uses is added if the Omni field did not declare it. A bare time field selected in a tile becomes `_time` (`_date` for a DATE column); in a filter it becomes `_date`.

## Aggregate types

| Omni `aggregate_type` | LookML `type` |
|---|---|
| `sum`, `count_distinct`, `average`, `min`, `max`, `median`, `list`, `percentile` | same |
| `count` | `count` (no `sql`), else `number` with `COUNT(...)` |
| `sum_distinct_on`, `average_distinct_on`, `median_distinct_on`, `percentile_distinct_on` | `sum_distinct`, `average_distinct`, `median_distinct`, `percentile_distinct`, with `sql_distinct_key` from `custom_primary_key_sql` |
| none | `number` |

## Joins

| Omni | LookML |
|---|---|
| `join_type: always_left` | `type: left_outer` |
| `inner`, `full_outer`, `cross` | same |
| `right_left`, `left_right` | `left_outer`, listed |
| `relationship_type` | `relationship`, reversed when the relationship is declared from the joined view |

## Measure and topic filter operators

| Omni | Looker filter expression |
|---|---|
| `{is: x}`, `{is: [a, b]}` | `x`, `a,b` |
| `{is_not: x}`, `{is_not: [a, b]}` | `-x`, `-a,-b` |
| `{is: true}` / `{is: false}` | `Yes` / `No` |
| `{is: null}`, `{not: null}` | `NULL`, `-NULL` |
| `{greater_than: n}`, `greater_than_or_equal_to`, `less_than`, `less_than_or_equal_to` | `>n`, `>=n`, `<n`, `<=n` |
| `{between: [a, b]}` | `[a,b]` |
| `{contains: x}`, `starts_with`, `ends_with` (and `does_not_...`) | `%x%`, `x%`, `%x` (with `-`) |
| `{time_for_duration: [left, right]}` | the date window rule below |
| anything else (`matches_regex`, nested conditions) | not translated: the measure is withheld, listed |

Commas and carets in values are escaped with a caret (`North^, East`).

## Document filters

| Omni filter object | Looker filter expression |
|---|---|
| `type: string`, `kind: EQUALS`, `values` | `a,b`; with `is_negative`, `-a,-b` |
| `kind: IS_EMPTY` | `EMPTY`; negated `-EMPTY` |
| `kind: CONTAINS`, `STARTS_WITH`, `ENDS_WITH` | `%x%`, `x%`, `%x` |
| `type: number`, `GREATER_THAN` / `LESS_THAN` | `>n` / `<n`; with `is_inclusive`, `>=n` / `<=n` |
| `type: number`, `EQUALS`, `BETWEEN` | `n`, `[a,b]` (`(a,b)` when not inclusive) |
| `type: boolean` | `Yes`; negated `No` |
| `type: null` | `NULL`; negated `-NULL` |
| `type: composite`, `AND` of negated parts | the parts joined with commas |
| `type: date`, `TIME_FOR_INTERVAL_DURATION` | the date window rule below |
| `type: date`, `BEFORE` / `ON_OR_AFTER` a date or `today` | `before <date>` / `after <date>` (Looker's `after` includes the date) |
| `type: date`, `BETWEEN` two dates | `<a> to <b>`, listed: Looker's end is exclusive |
| negated numbers or dates, composite `OR`, anything else | not translated: the tile is withheld, listed |

## Date windows

Omni stores a relative window as a start (`left_side`) and a length (`right_side`).

| Omni | Looker | Class |
|---|---|---|
| `N complete <unit>s ago` + `N+1 <unit>s` | `N+1 <unit>s` (includes the current unit) | mechanical |
| `N complete <unit>s ago` + `N <unit>s` | `N <unit>s ago for N <unit>s` | mechanical |
| `N complete <unit>s ago` + `M <unit>s` | `N <unit>s ago for M <unit>s` | mechanical |
| days without `complete` | as above | mechanical |
| other units without `complete`, or start and length in different units (`1 day ago` + `30 years`) | `N <unit>s ago for M <unit>s` | assisted: confirm the window |

## Table calculations

| Omni operator | Looker expression |
|---|---|
| `SqlStdOperatorTable.PLUS`, `MINUS`, `MULTIPLY`, `DIVIDE` | `(a + b)` and so on |
| `Omni.OMNI_FX_SAFE_DIVIDE` | `if(b = 0, null, a / b)` |
| field | `${view.field}` (timeframes rewritten) |
| literal | the value |
| `_omni_*` helper calculations | skipped |
| any other operator | the calculation is listed; the tile is emitted without it |
