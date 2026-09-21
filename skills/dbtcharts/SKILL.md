---
name: dbtcharts
description: Author, validate and render dbt Charts boards (dashboards as YAML in a dbt project, rendered by the dct CLI). Activates when the user mentions dbt Charts, dbtcharts, dct, a board file under charts/, or asks for a dashboard over dbt models where the release's reporting tool is dbt Charts. Used by /wire:dbtcharts-generate, -validate and -review, and for ad-hoc board work.
---

# dbt Charts

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | dbtcharts | activated | dbt Charts board work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

---

## What dbt Charts is

[dbt Charts](https://dbtcharts.com) is a dashboard layer written as YAML **boards** that live in a dbt project next to the models. A board holds named SQL **queries** (which reference models through `{{ ref('model') }}`), **charts** that map a query's columns to a chart type and its channels, optional **variables** for filters, and one **layout** (`rows`, `cols`, `grid` or `tabs`). The `dct` CLI validates, renders (SVG, PNG, HTML, PDF) and serves boards; dbtcharts.com hosts the same files from Git with a warehouse connection. Boards are diffable and reviewable in a pull request, which is why Wire uses them: the dashboard layer gets the same review path as the models.

The offline reference is bundled with the CLI and is the source of truth for every field name. Never guess a key:

```bash
dct docs cheatsheet          # one screen of essentials
dct docs charts              # the 16 chart types and every channel and style field
dct docs queries | board | layout | variables | sources
dct docs -s "<query>"        # search
dct skills                   # workflow skills (board-build, board-design, board-review) and layout patterns
dct examples                 # complete boards to copy from
```

## Install

```bash
dct --version || uv tool install dbt-charts      # or: pip install dbt-charts
```

`dct` reads the dbt project it is run in: `dbt_project.yml`, `profiles.yml`, and `target/manifest.json` when present (which is what lets `dct validate` check `ref()` names and model columns without a warehouse). Produce the manifest with `dbt compile`, not `dbt parse`: `dct` derives a model's columns from `compiled_code`, and a bare parse writes none, so every model wrapped in Jinja (`{% if var(...) %} ... {% endif %}`, the Wire pattern) comes back as "contains no SELECT statement". A model that ends in `SELECT *` stays `WARN-DBT-MODEL-COLUMNS-UNRESOLVED` whatever you do; that warning is expected and the `--warehouse` run is what checks those columns.

`dct validate --warehouse` needs the warehouse adapter inside the `dct` tool environment: `uv tool install dbt-charts --with dbt-bigquery` (or the Snowflake/Postgres package). On an Apple-silicon Mac, name an arm64 Python (`--python cpython-3.12-macos-aarch64-none`); uv picks an Intel build when an Intel Homebrew is on the path, and `cryptography` then has to compile from source and fails.

## Project layout Wire expects

```
<dbt project>/
  dbt_charts.yml            # anchor: the sources registry only (type: dbt_profile → the dbt profile)
  charts/
    meta.yml                # project defaults every board inherits: theme, frame width
    index.yml               # the landing page dct serves at /: one card per board, optional logo
    <subject_area>.yml      # one board per warehouse folder: sales.yml, finance.yml, ...
    scaffold_summary.json   # written by the scaffold: what it chose for each model
    needs_human.json        # written by the scaffold: what it could not decide, and why
```

`dbt_charts.yml` names sources; a board picks one with `source: <name>` and never defines a connection inline. Credentials stay in `profiles.yml` or `env_var()`. Nothing else goes in the anchor: dct 0.8 rejects `serve:`, `theme:` or `style:` there ("Extra inputs are not permitted") and infers the SQL dialect from the profile target. Presentation defaults live in `charts/meta.yml` (`theme: vivid` is the Wire default; the built-ins are `clarity`, `paper`, `stark`, `vivid`, `neon`).

`charts/index.yml` replaces dct's default file listing at `/`. Keep it text-only (no queries) so it loads at once. To show a logo, embed the file as a `data:` URI in a markdown image (`![Logo](data:image/svg+xml;base64,...)`, the scaffold's `--logo` does this); dct serves no static files and a relative image path renders as blank space. Put the page heading in the first row as `# Title` beside the logo column rather than in `title:`, so the two top-align.

## Step 0: resolve the design convention

Before designing or reviewing a board, resolve which convention applies (client override wins, as for dbt):

1. `.wire/conventions/dbtcharts.yml` in the client project, if present (the client's house style: currency, theme, windows, board shape, landing-page title and logo).
2. `wire/conventions/dbtcharts.yml` next to this skill's framework installation (synced from the private `wire-process-registry`; see `wire/schemas/convention-schema.md`).

The settings sections (`presentation`, `windows`, `board_shape`, `chart_defaults`, `formats`, `render`, `profiling`) give the numbers the design rules below refer to; the rule sections (`naming`, `layout`, `sql`, `project_files`) are checked mechanically:

```bash
python3 <plugin>/scripts/lint_conventions.py --domain dbtcharts \
    --convention <resolved file> --path charts/          # and again with --path dbt_charts.yml
```

Errors fail a board (missing title, label or notes; a `serve:` key in the anchor; a raw-string regex). Warnings are the design nudges (KPI label length, a `## Section` row, a hidden endpoint label, a trend without `time_unit`); fix them or record why not. To change house style for one engagement, copy the framework file to `.wire/conventions/dbtcharts.yml` and edit the values; the whole file is read, so keep it complete.

## The Wire rules for a board

These are what `/wire:dbtcharts-validate` checks. Keep them in ad-hoc work too.

1. **Queries read models through `ref()`.** `FROM {{ ref('wh_deals_fact') }}`, never `project.dataset.table`. `dct validate` then checks the model exists and, with the manifest, that the columns do.
2. **No inline data.** No `type: values`, no `columns:`/`values:` blocks, no `type: http` in a delivered board. A board reads the warehouse.
3. **Metadata on everything.** Every query and chart has `notes:` (one factual sentence; dbt Charts' AI search reads it). Every `type: kpi` has `label:`; every other chart has `title:`. `title:` on a KPI is rejected.
4. **Business names.** Titles and labels read as a person would say them, taken from the business rules register or the requirements where those exist.
5. **One board per subject area**, the warehouse folder the models sit in. Split a board into `tabs:` by fact before it passes about twelve charts.
6. **Validate before handing over.** `dct validate charts/` (structure), then `dct validate charts/ --warehouse` (BigQuery dry-run, unbilled; `EXPLAIN` on Snowflake, Postgres and Redshift) unless the release budget says `warehouse_spend: none`.
7. **dbt Charts is the renderer.** Do not fall back to a plotting library, an HTML canvas or another BI tool for a chart that was asked for as a board. If dbt Charts cannot draw the shape (funnel, gauge, waterfall, sankey, treemap are not drawable), say so and record it.
8. **Render clean.** `dct render` runs the same checks a reviewer's eyes would and prints `WARN-*` codes: truncated KPI labels, titles and series labels, money or percent fields without a `$`/`%` format, mostly-null measures, zero-row queries, a one-point time axis. A delivered board renders with none of them; the only tolerated code is `WARN-DBT-MODEL-COLUMNS-UNRESOLVED`, which the `--warehouse` run clears.

## Designing the board (what curation means)

The scaffold's output is an inventory, not a dashboard: one KPI per numeric column, one line per month, one bar per category, for every table, under a `## Table` heading each. Curating it means rebuilding each board to the shape in `dct skills board-design`, with the numbers (KPI count, windows, limits, layout splits, formats, currency) taken from the resolved convention (Step 0). The working checklist is `board-design-brief.md` next to this file; `/wire:dbtcharts-generate --auto` hands it to one lane per subject area and runs them all at once. This is the shape Wire hands over:

- **One board, one screen.** 4 to 6 KPIs on top (`- height: 120` then `cols:`), 4 to 6 charts, one detail table. Pick the tables that matter to the subject area and drop the rest; record what was dropped and why. No `## Section` text rows and no row titles: chart titles carry the meaning.
- **Every KPI has context.** One `kpis` query returns one row with the current period and deltas vs the prior period (last 12 months vs the 12 before; last 30 days vs the prior 30 for event data). Deltas are ratios (`current / prior - 1`) shown with `support: {value, label, format: percent_delta}`. Leave `glyph:`/`tone:` off a delta whose sign is not known in advance. When a feed has stopped loading, anchor the windows on its last loaded month and say so in the board `notes:`, or the KPIs read zero.
- **Trends show the last 24 complete months**, never the full history, with `style.axis_x.time_unit: yearmonth` and `style.axis_y.position: left` (without an end-of-line label the theme puts the axis on the right). Composition over time is a bar with `color:` and `style.stack: zero`. Two measures in different units go on `layers:` with `axis_y.position: right`, not on one `y: [a, b]` list.
- **Rankings** are horizontal bars with `sort:` and `LIMIT 8` to `10`; **precise rows** are a `table` with column labels, formats, right-aligned numbers, `pagination.enabled: false`, `LIMIT 15`. No pie or donut over three slices.
- **Formats live in the family slot.** KPI: `style.value.format`; cartesian chart: `style.number_format`; table: `style.columns.<col>.format`. Presets: `integer`, `number`, `percent_whole`, `percent` (ratio in), `currency_whole`. The currency presets print `$`, and axis tick formats accept only preset names or D3 strings, so for a GBP (or any non-dollar) project the KPI and table formats take `{ spec: ",.0f", prefix: "£" }` and chart axes use `number` with the currency named in the `subtitle:`. Divide 0-100 percent columns by 100 in SQL before a percent format.
- **Titles say what the chart answers; subtitles say unit and window.** KPI labels are 2 to 4 words without the table name (the truncation warning fires at about 40 characters). Alias long column names in SQL (`projected_amount`, not `projected_home_currency_amount`) so end-of-line series labels fit; do not switch `endpoint_labels.visible` off, which reflows the chart badly in PNG renders.
- **Profile the data first.** Run `dbt show --inline` over the model before designing: a chart on a column that is 90% null, all zero, or a single snapshot is worse than no chart. The render warnings `WARN-Y-ENCODING-MOSTLY-NULL`, `WARN-QUERY-RETURNED-ZERO-ROWS` and `WARN-TEMPORAL-SINGLE-POINT` name exactly these.
- **Keep the heuristics quiet by naming things well.** `dct render` guesses a field is money from a `_amount`/`_revenue`/`_cost`/`_price`/`_value`/`_spend` suffix and percent from `_pct`/`_rate`/`_share`, and warns when the axis format has no `$` or `%`. A generic `kpi_value` column that is not money will be flagged; alias it (`kpi_reading`) rather than give it a currency format it does not have.

### Things the static checker gets wrong

`dct validate` reads SQL without a warehouse and trips on a few BigQuery forms. Each has a form it accepts:

| It rejects | Write instead |
|---|---|
| `DATE_TRUNC(d, MONTH)`, `WEEK(MONDAY)`, `ISOWEEK` as date parts (read as columns) | `DATE(EXTRACT(YEAR FROM d), EXTRACT(MONTH FROM d), 1)`; filter on a `week_commencing` column; compute month anchors with `LAST_DAY` |
| `r'...'` raw-string regex literals | `ENDS_WITH`, `STARTS_WITH`, or a plain-string regex |
| A query named like one of its own columns, reused as `{{ queries.name }}` | `{{ queries.x }}` expands to `(...) AS x`, so the alias shadows the column; name base queries differently (`time_off`, not `days_off`) |

### Two rules for running lanes in parallel

- **`dbt show` rewrites `target/manifest.json` on dbt Fusion**, and `dct validate` and `dct render` read that file. A lane profiling while another renders makes the render fail with `ERR-DBT-MANIFEST-UNREADABLE`. Every `dbt show` in a lane takes `--target-path <its own scratch dir>`; the orchestrator runs `dbt compile` once before the whole-set validate and render.
- **A lane's work lives in its state file, not its conversation.** `--auto` lanes follow the lane contract in `specs/utils/director_operating_model.md`: `.wire/releases/<release>/lanes/dbtcharts-<area>.md`, rewritten after each completed item, ending with the report rows. The orchestrating session dispatches the lanes itself (the specialist-agent delegate wrapper does not apply to `--auto`), watches the state files, and re-dispatches a lane with no writes for 30 minutes. The first real run lost two of twelve boards' designs and every lane's report rows when the wrapping agent stalled; this is the rule that prevents that.

## The scaffold

`scripts/dbtcharts_scaffold.py` (shipped with the plugin; source at `wire/scripts/dbtcharts_scaffold.py`) turns a dbt manifest and catalog into one board per subject area, deterministically:

```bash
python3 <plugin>/scripts/dbtcharts_scaffold.py \
  --manifest target/manifest.json --catalog target/catalog.json \
  --out charts --layer-path models/warehouse --dialect bigquery \
  --write-anchor dbt_charts.yml --profile <profile> --target <target> \
  --theme vivid --currency '£' --title "<Client> Warehouse" --logo <path/to/logo.svg>
```

Per fact: a KPI row (record count plus up to three measures, each formatted), a trend of the first measure over the last 24 months by the first date column, a top-10 breakdown by the first categorical column. A subject area's board covers the facts in its folder plus the dimensions they join to, wherever those live: a dimension the fact `ref()`s, or whose `<x>_pk` matches a fact `<x>_fk`. `--subject-area w_sales` builds that one board; the summary marks each linked dimension with the fact and the link that brought it in. Per dimension: a record count and a breakdown. Column roles come from Wire's dbt conventions (`_dt`/`_ts` dates, `_amount`/`_count`/`_hours` measures with `SUM`, `_rate`/`_pct`/`_score` with `AVG`, `_pk`/`_fk`/`_id` never charted, `is_`/`has_`/`was_` flags never summed) and from the catalog's types. Nested `STRUCT` fields, models that match neither `_fact` nor `_dim`, and models with no column metadata go to `needs_human.json`.

The scaffold proposes; you decide. Rename, prune, add what the requirements ask for, and resolve every `needs_human` item with a recorded reason. Never hand-write what the scaffold emits before it has run, and never regenerate with `--force` over a board someone has curated.

The scaffold also writes `charts/meta.yml` (theme, frame width) and `charts/index.yml` (the landing page) once each, and never over an existing file without `--force`. `--theme` picks the built-in theme (default `vivid`), `--currency £` switches money formats to a prefix, `--title` and `--logo` name and brand the landing page. On BigQuery it writes month buckets as `DATE(EXTRACT(YEAR FROM d), EXTRACT(MONTH FROM d), 1)`, not `DATE_TRUNC(d, MONTH)` (see the table above).

## Rendering for a review

```bash
dct render charts/sales.yml --format png --output .wire/releases/<release>/dev/dbtcharts/sales.png
dct serve            # live preview at the URL it prints; leave it running while iterating
```

Renders run the queries. Under `warehouse_spend: estimate_required` or a cap, the cost governance rules in `specs/utils/director_operating_model.md` apply.

## Publishing

`dct init ci` scaffolds a GitHub Actions workflow that runs `dct validate` on every pull request. `dct skills cloud-setup` walks the dbtcharts.com connection (Cloud connects to BigQuery, Postgres, Redshift and Snowflake). Record a published URL in `status.md` under `dbtcharts.published_url`.

## Relationship to the Wire commands

| Command | What it does with this skill |
|---|---|
| `/wire:dbtcharts-generate <release> [--auto] [--subject-area <area>]` | Runs the scaffold over the release's dbt project, then designs each board to the brief (one lane per subject area with `--auto`), validates and renders them |
| `/wire:dbtcharts-validate <release>` | Ten checks: dct structure, warehouse dry-run, `ref()`-only, no inline data, labels and notes, coverage and `needs_human` decisions, no credentials, viz-catalog mapping, one board per subject area with meta and index, renders clean |
| `/wire:dbtcharts-review <release>` | Presents the renders and the generation report for sign-off |
| `/wire:dashboards-generate <release>` | The BI-tool dashboards (Looker, Omni, Metabase, OAC). A release can have both; dbt Charts boards sit with the dbt models and need no BI tool |
