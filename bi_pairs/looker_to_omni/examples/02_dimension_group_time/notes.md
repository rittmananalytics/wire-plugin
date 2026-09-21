# 02 Time and duration dimension groups

- A `type: time` group becomes one Omni dimension named after the group, with `timeframes`. `time` is dropped (`raw` covers it), `day_of_week` becomes `day_of_week_name`, `day_of_week_index` becomes `day_of_week_num`, and `week_of_year` has no Omni value, so it is dropped from the list and recorded in `needs_human.json` as `assisted`.
- `convert_tz: no` becomes `convert_tz: false`.
- A LookML timeframe reference in another field, `${occurred_month}`, becomes Omni's `${occurred[month]}`.
- A `type: duration` group becomes Omni's `duration` parameter. It is classed `assisted`: the converter emits `start`, `end` and `intervals`, and the agent confirms the shape against the Omni docs before the batch is validated.
