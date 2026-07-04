---
name: cube
description: Cube.dev semantic-layer modeling — cubes, views, dimensions, measures, joins, segments, and pre-aggregations via YAML or JavaScript, plus Cube's MCP server for querying a live deployment. Activates for Cube data model development, Cube MCP server integration, or any engagement where the semantic layer is (or will be) Cube rather than LookML or Omni's model. Encodes Rittman Analytics' own Cube modeling conventions and coding standards — the canonical reference for how RA builds cubes, not just how Cube itself works.
---

# Cube

Cube is a semantic layer sitting between the warehouse and every downstream consumer — a BI tool, an embedded app, or an AI agent querying through Cube's MCP server. Used by `semantic_layer-generate` when the engagement's semantic layer is Cube rather than LookML, and by any work that reads, builds, or migrates a Cube data model.

This skill assumes dbt is doing the transformation work upstream (staging → intermediate → marts) and Cube reads from marts-layer tables or views. **Cube is not a transformation tool.** If a calculation needs a window function or a multi-step aggregation before it reaches Cube, it belongs in dbt, not in a `sql` parameter — this is the first thing to check when a cube's `sql` is doing more than a light per-row expression.

## Core concepts

Two object types matter: **cubes** and **views**.

- A **cube** wraps a single database table (via `sql_table`) or a query result, and defines dimensions, measures, joins, and segments on it. Cubes are the normalised, building-block layer.
- A **view** sits atop one or more cubes and presents a denormalised, consumption-ready dataset — what BI tools, analysts, and AI agents actually query. Views govern what's exposed and how it's named for a business audience.

Within a cube: **dimensions** are the categorical/groupable columns (cities, statuses, timestamps); **measures** are the aggregates (counts, sums, calculated ratios); **segments** are named, reusable filters; **joins** connect cubes to each other; **pre-aggregations** are materialized rollups that keep interactive queries fast. Cube supports both YAML and JavaScript for schema definition — they produce identical behaviour, and the choice is organisational (Wire's convention below defaults to YAML).

Full official reference: [docs.cube.dev/docs/data-modeling/overview](https://docs.cube.dev/docs/data-modeling/overview).

## Connecting to a live deployment — the Cube MCP server

Cube's MCP server (Premium/Enterprise plans, Viewer role or higher) lets an MCP-compatible agent query a Cube deployment directly, over HTTPS with OAuth 2.0 (Authorization Code + PKCE). The endpoint is `https://<cube-mcp-server-host>/api/mcp`; OAuth discovery is at `/.well-known/oauth` with `client_id = cube-mcp-client` and scope `mcp-agent-access`. An admin configures access under **Admin → MCP Server** — a default deployment (or "Automatic" routing to the user's first accessible one), optionally restricted to specific deployments, always intersected with the user's role-based permissions.

Three tools are exposed: **`listDeployments`** (discover reachable deployments and their agents), **`chat`** (send a query, optionally targeting a specific `deploymentId`/`agentId` — omit both for the session default and Auto agent), and **`loadQueryResults`** (page through prior results on the same deployment). A request against an excluded deployment returns `403 Forbidden`.

To register with Claude Code:

```bash
claude mcp add --transport http cube-mcp-server https://<host>/api/mcp
```

Authenticate via browser, select the server with `/mcp`, then query. Full reference: [docs.cube.dev/docs/integrations/mcp-server](https://docs.cube.dev/docs/integrations/mcp-server).

---

## Rittman Analytics Cube modeling conventions and coding standards

**Owner**: Rittman Analytics. **Applies to**: all Cube.dev data model development on client and internal engagements. The point of a semantic layer is that "revenue" means the same thing everywhere it's asked — that only holds if every consultant builds cubes the same way. This section is that shared way. It replaces personal judgement calls on naming, folder structure, and join direction with a fixed set of decisions, so a project can move between consultants without a rebuild.

### Project structure

```
cube_project
└── model
    ├── cubes
    │   ├── finance
    │   │   ├── stripe_invoices.yml
    │   │   └── stripe_payments.yml
    │   ├── sales
    │   │   ├── orders.yml
    │   │   └── order_line_items.yml
    │   └── customers
    │       └── customers.yml
    └── views
        ├── finance
        │   └── finance_view.yml
        └── sales
            └── orders_view.yml
```

- One cube per file. One file per dbt mart table, as a rule.
- Subfolder cubes and views by **business domain** (finance, sales, customers, product), not by client team or by data source. Domain folders survive a reorg; team folders don't.
- Mirror the domain folder structure between `cubes/` and `views/`. If there's a `sales/` cube folder there should be a `sales/` view folder.
- Default to YAML. Reach for JavaScript only when you need dynamic data model generation (looping over a set of similar cubes, `COMPILE_CONTEXT`-driven visibility) — and document why in a comment at the top of the file when you do.

### Naming conventions

- `snake_case` throughout, in both YAML and JavaScript syntax. No camelCase, no kebab-case.
- Cube names match the underlying table's own convention — if the mart is `fct_orders`, the cube is `orders`.
- View names take a `_view` suffix: `orders_view`, `finance_view`. This makes it unambiguous in the API explorer which objects are the public product and which are internal building blocks.
- Measure names describe what's counted, not how: `total_revenue`, not `revenue_sum`. `order_count`, not `count_of_orders`.
- Boolean dimensions read as a yes/no question: `is_cancelled`, `is_first_order`. Never `cancelled_flag` or `flag_first_order`.
- Date/time dimensions carry the grain in the name only where more than one grain of the same event exists on the same cube: `created_at` is fine alone; if a truncated version is also exposed, `created_month` is clearer than a second `created_at`.
- Foreign keys used only for joins, never exposed as dimensions, don't need public names — mark them `public: false`.

### Cube standards

Point every cube at a single dbt mart with `sql_table`, using the fully-qualified table reference:

```yaml
cubes:
  - name: orders
    sql_table: analytics.marts.fct_orders
    data_source: default
    description: >
      One row per order, at order-header grain. Joins to order_line_items
      for product-level detail.
```

- Use `sql_table` in preference to a raw `sql` query. Reach for `sql` only for a genuine one-off transformation that doesn't warrant a new dbt model — and treat that as a temporary state, with a ticket raised to move the logic into dbt.
- Every cube declares a `primary_key` dimension explicitly. Cube can't reliably de-duplicate join results without one, and a missing primary key is the single most common cause of silently inflated numbers in a semantic layer.
- Set `description` on every cube: what the row represents, and anything a consumer needs to know before joining to it (grain, known caveats, filters already baked in).
- Use `sql_alias` when the auto-generated table alias would be truncated by the target warehouse — this bites on Postgres and Redshift more than BigQuery or Snowflake, but check regardless.
- Set `data_source` explicitly whenever a project blends more than one warehouse or database. Don't rely on the default silently applying.
- Use `extends` for genuine specialisation (a `cancelled_orders` cube extending `orders` with a baked-in filter), not as a shortcut to avoid writing a join.

### Dimension standards

```yaml
dimensions:
  - name: id
    sql: id
    type: number
    primary_key: true
  - name: status
    sql: status
    type: string
  - name: is_cancelled
    sql: "{CUBE}.status = 'cancelled'"
    type: boolean
  - name: created_at
    sql: created_at
    type: time
```

- Prefix column references with `{CUBE}` (or the cube name) rather than leaving them bare, even though Cube will resolve unqualified references. It removes ambiguity the moment a join is added later, and it's what the Cube style guide itself recommends.
- One dimension per column as the default. Derived dimensions (concatenations, case statements) are acceptable for genuinely presentational needs — a full name from first/last — but any derived dimension carrying business logic belongs in dbt, where it can be tested.
- Every dimension gets a `type`. Don't let Cube infer it.
- Set `meta` or `description` on dimensions that a non-technical consumer will encounter through a view and that aren't self-explanatory from the name alone.
- Segments (named, reusable `WHERE` filters) go on the cube, not duplicated as a filter in every measure that needs them.

### Measure standards

```yaml
measures:
  - name: count
    type: count
  - name: total_revenue
    sql: amount
    type: sum
    format: currency
  - name: average_order_value
    sql: "{total_revenue} / NULLIF({count}, 0)"
    type: number
    format: currency
  - name: paying_customer_count
    sql: id
    type: count_distinct
    filters:
      - sql: "{CUBE}.is_paying = true"
```

- Every measure declares a `type`, matched to the correct SQL aggregate: `count` for row counts, `sum` for additive totals, `count_distinct` (or `count_distinct_approx` at genuine scale) for unique counts, `min`/`max` for extremes, `number` for anything calculated from other measures.
- **Know your additive measures.** Only `count`, `count_distinct_approx`, `min`, `max`, and `sum` are additive — this determines whether pre-aggregations can serve a query at a different grain than the one they were built for. If a measure isn't additive (a ratio, a percentage, an average), it must be built as a calculated measure referencing additive components, never pre-aggregated directly.
- Ratios and averages are always calculated measures over other measures, with `NULLIF` guarding the denominator. Never divide two raw columns inline inside a single measure's `sql`.
- Set `format` (`currency`, `percent`) wherever the value will be surfaced directly to a business user. Don't leave formatting to the BI tool to guess.
- Filtered measures (`paying_customer_count` above) are preferred over exposing a boolean dimension and asking every consumer to remember to filter on it correctly.
- Give every measure a `description` where the name alone doesn't make the definition obvious — particularly anything involving a filter, a `NULLIF` guard, or a business rule around what counts as "cancelled" or "active".

### Joins and relationships

```yaml
joins:
  - name: customers
    sql: "{CUBE}.customer_id = {customers.id}"
    relationship: many_to_one
```

- Use the current relationship vocabulary — `one_to_many`, `many_to_one`, `one_to_one` — not the older `belongsTo`/`hasMany` terms, which are deprecated.
- Define each join once, on the cube where it reads most naturally (usually the many side pointing at the one side). Don't redeclare the same join in both directions.
- Where a join path between two cubes is ambiguous (more than one route connects them), resolve it explicitly in the view with `join_path`, rather than leaving Cube to pick and hoping it picks correctly. An ambiguous join silently answered the wrong way is worse than a build error.
- Keep join keys as plain foreign-key dimensions, marked `public: false` if they have no analytical value beyond the join itself.

### View standards

Views are entity-oriented and denormalised by design. Build them around what a business user thinks of as one thing — "orders", not "orders joined to everything we might ever need."

```yaml
views:
  - name: orders_view
    description: >
      Order-level reporting view. Includes customer geography and product
      category via joins from the orders cube.
    cubes:
      - join_path: orders
        includes:
          - status
          - created_at
          - count
          - total_revenue
          - average_order_value
      - join_path: orders.line_items.products
        includes:
          - name
        prefix: true
      - join_path: orders.customers
        includes:
          - city
          - country
        prefix: true
```

- Always use the `cubes`/`join_path`/`includes` structure rather than hand-listing every member with full qualification. It's shorter, and the join path is explicit rather than inferred.
- Use `prefix: true` when pulling dimensions from a joined cube, so `customers.city` surfaces as `customers_city` rather than colliding with a same-named field elsewhere in the view.
- Use `includes: ["*"]` sparingly — only for a genuinely small, stable cube (a lookup or dimension table) where exposing everything is the intended behaviour. For fact-grain cubes, list members explicitly, so a new column added upstream doesn't appear in a client-facing view unreviewed.
- Order the view's `includes` as: dimensions first, then measures, matching the pattern a consumer will actually browse in when building a report.
- Set `public: false` on any view still under active development, and don't flip it to public until it's been checked against the Definition of Done below.

### Pre-aggregations

Pre-aggregations exist to keep interactive queries fast, not to work around a badly modelled cube. **Model correctly first.**

```yaml
pre_aggregations:
  - name: orders_by_day
    measures:
      - orders.count
      - orders.total_revenue
    dimensions:
      - orders.status
    time_dimension: orders.created_at
    granularity: day
    partition_granularity: month
    refresh_key:
      every: 1 hour
```

- Only additive measures belong in a pre-aggregation intended to serve multiple granularities (see Measure standards above).
- Partition by month for anything with meaningful history, so incremental refresh doesn't rebuild the whole table on every run.
- Set an explicit `refresh_key` rather than accepting the default. For OLTP-sourced marts, `MAX(updated_at)` on the source table is usually the right check; for append-only event data, a time-based `every` clause is simpler and cheaper.
- Name pre-aggregations for what they serve (`orders_by_day`, `orders_by_customer_month`), not `pre_agg_1`.
- Review pre-aggregation usage in Cube Cloud's monitoring (or the equivalent logs on self-hosted) before adding a new one. A pre-aggregation nobody's queries hit is dead weight on every refresh cycle.

### Security and access control

- Use `security_context` in `COMPILE_CONTEXT` for row-level, multi-tenant filtering — never bake a client-specific `WHERE tenant_id = '...'` into a cube's `sql`. The whole point of the semantic layer is that one model serves every tenant safely.
- Set `public: false` at cube, view, dimension, or measure level for anything that shouldn't be reachable through the API — internal join keys, deprecated fields kept temporarily for backward compatibility, anything containing data a given role shouldn't see.
- For member-level security beyond simple visibility (different measure definitions per role), use `queryRewrite` in the Cube configuration file rather than trying to encode role logic inside the data model itself.
- Any engagement with more than roughly 100 tenants should be flagged for a multi-cluster deployment conversation rather than assumed to scale on a single instance — raise this at scoping, not after go-live.

### SQL and YAML style

- Indent YAML with two spaces. No tabs.
- Use trailing commas in JavaScript syntax.
- SQL keywords and function names in upper case: `SELECT`, `SUM`, `CASE WHEN`.
- `!=` rather than `<>`.
- Always `AS` when aliasing a column, expression, or table — never rely on positional aliasing.
- Anything beyond a trivial one-liner starts SQL on a new line, formatted for readability rather than compactness.
- Prefer a CTE over a nested subquery once a query needs more than one logical step.
- Prefix every column with its table or alias once more than one table is in play, even where a database wouldn't require it.

### Version control and deployment

- Cube data models live in the same delivery repository as the rest of the project, under `wire/cube/` or the project's established convention — never as a standalone repo disconnected from the dbt project it reads from.
- Every change to a cube or view goes through a pull request, reviewed against the Naming, Cube, Dimension, Measure, Joins, and View standards above before merge. Treat the review the same way as a dbt model review — it's not optional because the change looks small.
- Run the Cube validation step (`cube validate` or the CI equivalent) before merge. A YAML syntax error caught in CI costs a minute; caught in production it costs a client-facing outage.
- Tag a data model change against the dbt commit it depends on where the two are tightly coupled (a renamed column, a new grain), so a rollback of one doesn't silently break the other.

### Testing and validation

- After any change to a cube's joins or measures, run the affected queries through the Cube Playground and compare totals against a known-good source — the dbt model directly, or a prior export — before merging.
- Check additive measures aren't double-counted through a join fan-out. This is the most common silent error in a semantic layer: a one-to-many join multiplying a sum measure because the primary key wasn't declared, or because the join direction is backwards.
- New pre-aggregations get validated for both correctness (does the rolled-up number match the non-aggregated query) and refresh behaviour (does it actually refresh on the cadence set, and does it partition as expected) before being marked as serving production traffic.

### Documentation requirements

Every cube and view needs, at minimum: a `description` at the cube/view level covering grain and any caveats, and a `description` on any measure whose definition isn't obvious from its name alone — anything involving a filter, an exclusion, or a business rule that isn't universal (what counts as "active", what's excluded from "revenue"). No requirement to document self-evident dimensions (`status`, `created_at`) beyond a `type`.

### Definition of done

Before a cube or view is marked ready for client-facing use:

- [ ] Cube points at a single dbt mart via `sql_table`, not a raw `sql` query, unless a ticket exists to migrate it
- [ ] `primary_key` declared explicitly
- [ ] All column references prefixed with `{CUBE}` or the cube name
- [ ] Every measure has an explicit `type`, matched correctly to the underlying aggregate
- [ ] Non-additive measures built as calculated measures over additive components, with `NULLIF` guarding any division
- [ ] Joins use current relationship terms (`one_to_many` / `many_to_one` / `one_to_one`) and ambiguous paths are resolved explicitly in views
- [ ] View built with `cubes`/`join_path`/`includes`, not hand-listed members
- [ ] `public: false` set on internal join keys and anything not intended for API exposure
- [ ] Descriptions present per Documentation requirements
- [ ] Pre-aggregations (if any) cover only additive measures at the grains actually queried, with an explicit `refresh_key`
- [ ] Totals checked against source in the Playground, including a join fan-out check
- [ ] Changes reviewed via pull request against these standards before merge
