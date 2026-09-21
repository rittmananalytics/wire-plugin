# 05 Tier and case dimensions

- `type: tier` with `tiers: [0, 10000, 50000, 250000]` becomes `bin_boundaries: [0, 10000, 50000, 250000]` on a dimension whose `sql` is the tiered field. Mechanical.
- `plan_family` is a `case` where every `when` is an equality or `IN` list on the same field. It becomes Omni `groups` on `sql: ${plan}`, one group per `when` with `filter: {is: [...]}` and `name`, plus `else`. Classed `assisted`: the agent confirms labels and the else bucket.
- `health` is a `case` with a compound condition. There is no mechanical Omni form, so nothing is emitted and it is recorded as `assisted` for a hand-written `sql`.
