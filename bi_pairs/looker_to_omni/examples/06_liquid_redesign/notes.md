# 06 Redesign: Liquid, parameters, filter fields, running totals, PDTs

Nothing in this file's redesign rows is emitted. Each one lands in `needs_human.json` with the Omni alternative:

| Construct | Why not mechanical | Omni alternative |
|---|---|---|
| `dynamic_label` with `{% if %}` Liquid | Omni has no Liquid | Two dimensions plus a templated filter, or a dashboard control |
| `sku_link` with `html:` | Looker `html` is Liquid; Omni `markdown` is Mustache | Omni `markdown` on the dimension, written by hand |
| `parameter: measure_picker` | No parameter fields in Omni | Templated filter or a `FIELD_SELECTION` dashboard control |
| `filter: warehouse_filter` | No filter-only fields in Omni | Dashboard filter control |
| `units_running_total` | Omni does running totals as table calculations | Table calculation on the tile |
| `inventory_daily_pdt` (`sql_trigger_value`) | Persistence is a warehouse concern | dbt model, or an Omni query view; the plan rules which |

`inventory` itself is still emitted: `sku_id`, `sku_link` (as a plain dimension, its `html` withheld) and `units_on_hand` are mechanical. The `sku_link` dimension keeps its `sql` because `html` is the only part that fails.
