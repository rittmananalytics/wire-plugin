# 03 Measure filters and aggregate types

Omni measure filters are operator objects, never bare scalars.

| Looker filter | Omni |
|---|---|
| `status: "complete"` | `status: {is: complete}` |
| `amount: ">=100"` | `amount: {greater_than_or_equal_to: 100}` |
| `is_gift: "Yes"` on a `yesno` dimension | `is_gift: {is: true}` |
| `status: "open,pending"` | `status: {is: [open, pending]}` |
| `status: "-cancelled"` | `status: {is_not: cancelled}` |
| `status: "-NULL"` | `status: {not: null}` |
| `status: "%pend%"` | `status: {contains: pend}` |

Two measures are withheld and recorded as `assisted`:

- `recent_orders` filters on a date expression (`"30 days"`). Omni's date filter grammar differs from Looker's, so the converter never guesses it.
- `mixed_filter` mixes include and exclude in one expression (`"open,-pending"`).

A withheld measure is safer than an unfiltered one: an unfiltered `count` where Looker had a filtered one changes the number silently.

Also here: `percentile` keeps its `percentile: 90`; `average` stays `average`; the custom `value_format: "#,##0.00"` maps to `number_2`; `aov` (`type: number`) is emitted with `sql` and no `aggregate_type`, classed `assisted` so validate confirms it resolves on the branch.
