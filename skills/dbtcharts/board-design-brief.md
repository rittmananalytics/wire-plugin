# Board design brief

The brief `/wire:dbtcharts-generate` hands to whoever (or whichever lane) designs one board. It turns the scaffold's inventory for one subject area into a finished dbt Charts dashboard. Read `SKILL.md` first; this file is the working checklist. The numbers below (4 to 6 KPIs, 12-month periods, 24-month trends, top 10, 15 rows, 60/40 splits, `$` presets) are the framework defaults in `wire/conventions/dbtcharts.yml`; an engagement's `.wire/conventions/dbtcharts.yml` overrides them and wins.

## Inputs

- The scaffold's board for the subject area (`charts/<area>.yml`): the inventory of models and the columns the scaffold picked. A starting list, not a design.
- `charts/scaffold_summary.json` and `charts/needs_human.json` for that area.
- The dbt project: `dbt show --inline` for profiling, `target/manifest.json` for `ref()` names.
- Where they exist: the business rules register (measure names and definitions), the requirements' dashboards section, the viz catalog.
- A reference board already curated in the project, when one exists, for house style.

## Profile before you design

Run `dbt show --inline` over each candidate model. Record, per column you intend to chart: null rate, distinct count, min and max date, whether the feed is still loading. Drop or replace anything that is mostly null, all zero, a single snapshot, or a technical id. Note stopped feeds: windows then anchor on the last loaded month, and the board `notes:` says so.

```bash
SCRATCH=$(mktemp -d)   # your own target dir: dbt show rewrites target/manifest.json, which dct reads while other lanes render
dbt show --target-path "$SCRATCH" --inline "select column_name, data_type from {{ ref('M').database }}.{{ ref('M').schema }}.INFORMATION_SCHEMA.COLUMNS where table_name = '{{ ref('M').identifier }}' order by ordinal_position" --limit 200
dbt show --target-path "$SCRATCH" --inline "select count(*) n, countif(x is null) x_nulls, min(d) first_d, max(d) last_d from {{ ref('M') }}"
```

Never run `dbt show` without `--target-path` while boards are being validated or rendered: on dbt Fusion it rewrites the project's `target/manifest.json`, and a concurrent `dct render` then fails with `ERR-DBT-MANIFEST-UNREADABLE`.

## The shape

1. **KPI row.** 4 to 6 KPIs from one `kpis` query returning one row: the current period and deltas vs the prior period (last 12 months vs the 12 before; last 30 days vs the prior 30 for event data). Deltas are ratios (`current / prior - 1`) shown with `support: {value, label, format: percent_delta}`; no `glyph:`/`tone:` on a delta whose sign is unknown; `tone: info` on a plain count. Row: `- height: 120` then `cols: [...]`.
2. **Hero trend.** Last 24 complete months. `bar` or `line`, `style.axis_x.time_unit: yearmonth`, `style.axis_y.position: left`. Composition = bar with `color:` and `style.stack: zero`. Two units = `layers:` with `axis_y.position: right`. Never `y: [a, b]` for measures in different units.
3. **Two to four breakdowns.** Horizontal bars (`style.orientation: horizontal`) with `sort:` and `LIMIT 8` to `10`; a second trend where the area needs one. No pie or donut over three slices.
4. **One detail table.** `type: table`, `style.columns` with labels, formats and right-aligned numbers, `pagination.enabled: false`, `LIMIT 15`.
5. **Layout.** KPI row; a 60/40 row (hero, side chart); a 40/60 or 50/50 row; the table full width. No `## Section` text rows, no row titles. About 8 visualisations plus the KPIs. If the subject area cannot be told in one screen, split by fact into `tabs:` or a second board, and say so in the report.

## Formats

| Slot | Field |
|---|---|
| KPI value | `style.value.format` |
| Cartesian chart measure | `style.number_format` |
| Table column | `style.columns.<col>.format` |

Presets: `integer`, `number`, `percent_whole`, `percent` (ratio in; divide 0-100 columns by 100 in SQL), `currency_whole`. The currency presets print `$`. For any other currency, KPIs and table columns take `{ spec: ",.0f", prefix: "£" }` and chart axes take `number` with the currency named in the `subtitle:`, because axis tick formats accept only preset names or D3 strings.

## Names

- `title:` says what the chart answers; `subtitle:` gives unit and window ("GBP, last 24 months").
- KPI `label:` is 2 to 4 words, without the table name.
- Alias long columns in SQL so end-of-line series labels fit (`projected_amount`, not `projected_home_currency_amount`). Do not hide the labels with `endpoint_labels.visible: false`; the PNG render reflows badly.
- Alias measures so the render heuristics stay quiet: a name ending `_amount`, `_revenue`, `_cost`, `_price`, `_value`, `_spend`, `_pct`, `_rate` or `_share` on a chart axis needs a `$` or `%` format, so a non-money `kpi_value` becomes `kpi_reading`.
- `COALESCE(dim, 'Unknown')` on categorical breakdowns; filter out rows with an `is_deleted` flag.
- Every query and chart has one factual `notes:` line.

## SQL (BigQuery forms the static checker accepts)

- `DATE(EXTRACT(YEAR FROM d), EXTRACT(MONTH FROM d), 1)` for month buckets, not `DATE_TRUNC(d, MONTH)`; filter weeks on a `week_commencing` column, not `WEEK(MONDAY)`.
- `ENDS_WITH`/`STARTS_WITH` or plain-string regex, not `r'...'` raw strings.
- `{{ ref('model') }}` for tables; `{{ queries.name }}` to reuse a base query, named unlike any of its columns.
- `SAFE_DIVIDE`, `COUNTIF`, `DATE_SUB(CURRENT_DATE(), INTERVAL n MONTH)`.

## Finish

```bash
dct validate charts/<area>.yml --warehouse     # only WARN-DBT-MODEL-COLUMNS-UNRESOLVED may remain
dct render charts/<area>.yml --output <release>/dev/dbtcharts/<area>.png
```

Look at the PNG. Fix overlaps, empty charts, unreadable labels, KPIs without formats, an axis on the wrong side. Zero render warnings other than `WARN-DBT-MODEL-COLUMNS-UNRESOLVED`.

When you run as a lane of `--auto`, write your state file (`.wire/releases/<release>/lanes/dbtcharts-<area>.md`) after each of these items, not at the end: profiled, designed, warehouse-validated, rendered and inspected, linted, complete. The final write holds your report: one row per scaffold chart (`kept | reshaped | dropped | added`, with a one-clause reason), the tables kept and dropped, the KPIs and charts built, the profiling findings (null columns, empty tables, stopped feeds, windows chosen), every `needs_human` item for the area with your decision, the validate and render warning counts, and the PNG path. The orchestrator assembles the generation report from these files; a row that exists only in your conversation is lost if the session dies.
