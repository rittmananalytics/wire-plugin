# 04 Explore to topic

- The explore becomes `orders.topic` with `base_view: orders`. `fields: [ALL_FIELDS*, -customers.email]` expands to one `view.*` entry per view in the explore plus the exclusion, because Omni's `fields` lists views explicitly.
- Each plain join becomes an entry in `relationships.yaml` (`join_from_view`, `join_to_view`, `on_sql`, `relationship_type`, `join_type`), and the topic's `joins:` tree records the join path: `skus` hangs under `order_lines` because its `sql_on` references `order_lines`.
- `reps` is an aliased join (`from: customers`). Omni's `join_to_view_as` is built for joining the same view twice: the relationship targets `customers`, names the alias `reps`, and the topic's `joins:` and the `on_sql` use the alias. It is emitted as a topic-scoped relationship so alias names cannot collide across topics.
- `order_lines` is `one_to_many` from orders. Omni supports fan-out joins natively (`relationship_type: one_to_many`), so it is emitted as written. Correct aggregation over a fan-out needs `primary_key: true` on the joined views; `omni-model-lint` rule L6 checks that.
- `sql_always_where` becomes `always_where_sql`; `access_filter` becomes `access_filters`. Both are `assisted`: the field references and the user attribute must exist on the Omni side (`omni-target-setup` creates the attribute).
