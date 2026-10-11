# Metabase to Omni: property mapping

Experimental.

| Source expression | Omni filter object |
|---|---|
| `NULL`, `-NULL` | `{type: null, is_negative}` |
| `EMPTY`, `-EMPTY` | `{kind: IS_EMPTY, type: string}` |
| `a,b`, `-a` | `{kind: EQUALS, type: string, values, is_negative}` |
| `%x%`, `x%`, `%x` | `CONTAINS`, `STARTS_WITH`, `ENDS_WITH` |
| `>5`, `>=5`, `<5`, `<=5` | `{kind: GREATER_THAN or LESS_THAN, type: number, values, is_inclusive}` (Omni has no `_OR_EQUAL` kinds) |
| `[1, 9]`, `5`, `1,2` | `BETWEEN` (inclusive), `EQUALS` |
| `Yes`, `No` on a yes/no field | `{type: boolean, is_negative}` |
| `N units ago for N units` | `{kind: TIME_FOR_INTERVAL_DURATION, left_side: "N complete units ago", right_side: "N units", ui_type: PAST}` |
| `N units` (including the current one) | the same, `left_side: "N-1 complete units ago"` |
| `this unit`, `last unit`, `today`, `yesterday` | the same, one unit |
| `after D`, `before D`, `D1 to D2` | `ON_OR_AFTER`, `BEFORE`, `BETWEEN` |
| anything else | Not mapped: the tile is skipped (`unmapped_filter`) and listed |

Measure filters in the model use Omni's operator objects (`is`, `is_not`, `greater_than` and so on), never a bare scalar.

| Source aggregation | Omni `aggregate_type` |
|---|---|
| sum, count, count distinct, average, min, max, median, percentile | `sum`, `count`, `count_distinct`, `average`, `min`, `max`, `median`, `percentile` |
| a formula over aggregations | none: a measure with `sql` over other measures |
