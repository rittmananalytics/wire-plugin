# Looker to Omni: property mappings

Value tables the converter applies. An engagement extends or overrides them with `.wire/engagement/bi_pair_overrides/looker_to_omni/property_mapping.yml` (see the README).

## `value_format_name` to `format`

| LookML | Omni |
|---|---|
| `usd`, `usd_2` | `currency_2` |
| `usd_0` | `currency_0` |
| `eur` | `eurcurrency_2` |
| `eur_0` | `eurcurrency_0` |
| `gbp` | `gbpcurrency_2` |
| `gbp_0` | `gbpcurrency_0` |
| `decimal_0` to `decimal_4` | `number_0` to `number_4` |
| `percent_0` to `percent_4` | `percent_0` to `percent_4` |
| `id` | `id` |

Any other name: emitted without `format`, recorded in `needs_human.json`. Omni also offers `thousands_N`, `millions_N`, `billions_N`, `big`, `bigcurrency`, accounting formats and D3 date strings; pick one by hand.

## `value_format` string to `format`

| LookML | Omni |
|---|---|
| `#,##0`, `0` | `number_0` |
| `#,##0.0`, `0.0` | `number_1` |
| `#,##0.00`, `0.00` | `number_2` |
| `0%` | `percent_0` |
| `0.0%` | `percent_1` |
| `0.00%` | `percent_2` |
| `$#,##0` | `currency_0` |
| `$#,##0.00` | `currency_2` |
| `£#,##0`, `£#,##0.00` | `gbpcurrency_0`, `gbpcurrency_2` |
| `€#,##0`, `€#,##0.00` | `eurcurrency_0`, `eurcurrency_2` |

## Timeframes

| LookML | Omni |
|---|---|
| `raw` | `raw` |
| `time` | dropped (`raw` covers it) |
| `date` | `date` |
| `week` | `week` |
| `month` | `month` |
| `quarter` | `quarter` |
| `year` | `year` |
| `hour`, `minute`, `second`, `millisecond` | same |
| `day_of_week` | `day_of_week_name` |
| `day_of_week_index` | `day_of_week_num` |
| `day_of_month` | `day_of_month` |
| `day_of_year` | `day_of_year` |
| `hour_of_day` | `hour_of_day` |
| `month_name` | `month_name` |
| `month_num` | `month_num` |
| `quarter_of_year` | `quarter_of_year` |
| `fiscal_quarter`, `fiscal_year` | same (Omni needs `fiscal_month_offset` on the model) |
| `week_of_year`, `time_of_day`, `day_of_quarter`, others | dropped, `needs_human` |

Default when LookML lists none: `raw, date, week, month, quarter, year`.

## Measure types to `aggregate_type`

| LookML `type` | Omni `aggregate_type` |
|---|---|
| `sum` | `sum` |
| `count` | `count` |
| `count_distinct` | `count_distinct` |
| `average` | `average` |
| `min` | `min` |
| `max` | `max` |
| `median` | `median` |
| `list` | `list` |
| `percentile` (+ `percentile: N`) | `percentile` (+ `percentile: N`) |
| `sum_distinct` (+ `sql_distinct_key`) | `sum_distinct_on` (+ `custom_primary_key_sql`) |
| `average_distinct` | `average_distinct_on` |
| `median_distinct` | `median_distinct_on` |
| `percentile_distinct` | `percentile_distinct_on` |
| `number` | none (derived measure; `assisted`) |
| `running_total`, `percent_of_total`, `percent_of_previous`, `date`, `string`, `yesno` | none (`redesign`) |

## Joins

| LookML `relationship` | Omni `relationship_type` |
|---|---|
| `many_to_one` | `many_to_one` |
| `one_to_one` | `one_to_one` |
| `one_to_many` | `one_to_many` |
| `many_to_many` | `many_to_many` |

| LookML `type` | Omni `join_type` |
|---|---|
| `left_outer` | `always_left` |
| `inner` | `inner` |
| `full_outer` | `full_outer` |
| `cross` | `cross` |
| (no LookML equivalent) | `right_left`, `left_right` |

## LookML filter expressions to Omni operators

Applies to measure `filters` and to explore `always_filter` / `conditionally_filter`.

| LookML expression | Omni |
|---|---|
| `value` | `{is: value}` |
| `a,b` | `{is: [a, b]}` |
| `-value` | `{is_not: value}` |
| `-a,b` | `{is_not: [a, b]}` |
| `NULL` | `{is: null}` |
| `-NULL` | `{not: null}` |
| `>n`, `>=n`, `<n`, `<=n` | `{greater_than: n}`, `{greater_than_or_equal_to: n}`, `{less_than: n}`, `{less_than_or_equal_to: n}` |
| `[a,b]` | `{between: [a, b]}` |
| `%x%` | `{contains: x}` |
| `x%` | `{starts_with: x}` |
| `%x` | `{ends_with: x}` |
| `Yes` / `No` on a `yesno` dimension in the same view | `{is: true}` / `{is: false}` |
| `Yes` / `No` on any other field | `{is: Yes}` / `{is: No}` (strings) |
| Date expressions: `30 days`, `last month`, `before 2024-01-01`, `today`, ISO dates | not mechanical: `needs_human` |
| Mixed include and exclude (`a,-b`), wildcards inside a value, anything else | not mechanical: `needs_human` |

When any expression on a construct is not mechanical, the converter withholds the whole construct rather than emit it unfiltered.
