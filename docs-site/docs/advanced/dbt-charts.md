---
sidebar_position: 16
title: "dbt Charts Boards"
---

# dbt Charts Boards

**Since v4.0.0.** [dbt Charts](https://dbtcharts.com) is a dashboard layer written as YAML files that live in the dbt project next to the models. Each file is a **board**: named SQL queries that read models through `ref()`, charts that map a query's columns to a chart type, optional filter variables, and a layout. The `dct` command-line tool validates, renders and serves the boards, and dbtcharts.com can host them from the repository. Because a board is a text file, it gets the same pull-request review as the models it reads, which is the property Wire wants from a dashboard layer.

Wire adds one optional artifact, `dbtcharts`, to the `full_platform`, `dbt_development` and `dashboard_first` release types. It sits in the development phase after the dbt models and depends on `dbt` passing validation. It is optional: a release director asks for it ("and give me dbt Charts boards for the warehouse"), and it stays out of the way otherwise. A release can have both `dashboards` (Looker, Omni, Metabase or OAC content) and `dbtcharts`; the boards need no BI tool.

## What the command produces

`/wire:dbtcharts-generate <release>` writes one board per **subject area**, where a subject area is a folder under the warehouse layer (`models/warehouse/w_sales/`, `models/warehouse/w_finance/`). That is how Wire's dbt conventions and most client projects already group facts and dimensions, so the boards land where a reader would look for them. A board covers every fact model in its folder plus the dimensions those facts join to, wherever those dimensions live: the scaffold follows the fact's `ref()` dependencies in the manifest and matches `<x>_fk` columns to a dimension's `<x>_pk` in the catalog. `--subject-area w_sales` builds that one board.

The command has two halves with a fixed line between them.

**The scaffold is a script.** `scripts/dbtcharts_scaffold.py` reads dbt's own artifacts, `target/manifest.json` and `target/catalog.json`, and writes the boards without an AI call. It classifies each model as a fact or a dimension from its name, and each column from Wire's naming conventions and the catalog's types: `_dt` and `_ts` are dates, `_amount`, `_count` and `_hours` are measures summed, `_rate`, `_pct` and `_score` are averaged, `_pk`, `_fk` and `_id` are never charted, and `is_`, `has_` and `was_` flags are never summed. For each fact it writes a KPI row (record count and up to three measures), a monthly trend of the first measure and a top-10 breakdown by the first categorical column; for each dimension a record count and a breakdown. The same manifest and catalog always produce the same boards, and a test in `wire/tests/development/` holds that to be true. Everything the script could not decide goes to `needs_human.json` with a reason: a model that matches neither convention, a model with no column metadata, a fact with no date, no measure or no categorical column, a nested `STRUCT` field.

**The design is judgement.** The scaffold's board is an inventory: one KPI per numeric column, one line per month, one bar per category, for every table. The agent rebuilds each into a dashboard to the brief shipped with the `dbtcharts` skill (`board-design-brief.md`): it profiles the models first so nothing charts a mostly-null column or a stopped feed, keeps the tables that matter, writes a KPI row with prior-period deltas from one query, one hero trend over the last 24 months, a few ranked breakdowns and a detail table, in the business language the release already uses (the business rules register, the requirements, the viz catalog), and decides every `needs_human` item. `--auto` runs this for every subject area at once, one lane each, without pausing; `--subject-area w_sales` designs one area, its facts and the dimensions they join. Each decision is a row in the generation report, so the reviewer sees what the scaffold proposed and what changed.

![The Marketing board produced by dbtcharts-generate: a KPI row with prior-period deltas, a stacked 24-month conversions trend, attribution and email breakdowns, LinkedIn engagement, and a paid-campaigns table](/img/dbt-charts/dbt_charts_example_dashboard.png)

*One board as the command leaves it: the Marketing subject area of a live BigQuery warehouse. Six KPIs with deltas against the prior period, a hero trend over the last 24 months, four breakdowns, one detail table, GBP shown as a prefix and named in the subtitles.*

The scaffold also writes two project files once: `charts/meta.yml`, which sets the theme every board inherits (`vivid` by default; `--theme` changes it), and `charts/index.yml`, the landing page `dct serve` shows at `/` in place of a file listing, one card per board with an optional logo (`--logo`, embedded as a data URI because dct serves no static files). `--currency '£'` switches money formats to a prefix for a non-dollar client, since dbt Charts' currency presets print `$` and its axis formats take no other symbol.

![The landing page dct serve shows at /: a heading with the engagement's logo top-right and twelve bordered cards, one per board, grouped into Commercial, Delivery and finance, People and Technology](/img/dbt-charts/dbt_charts_homepage.png)

*The generated landing page for the same warehouse, with the engagement's logo embedded and one card per subject-area board.*

## Validation

`/wire:dbtcharts-validate <release>` runs ten checks. Three are `dct`'s own: `dct validate charts/` for structure and, with the manifest present, `ref()` names and model columns; `dct validate charts/ --warehouse`, a per-query dry run (unbilled on BigQuery, `EXPLAIN` on Snowflake, Postgres and Redshift); and `dct render` of every board, which must print no warning other than the expected `WARN-DBT-MODEL-COLUMNS-UNRESOLVED` (the render warnings name truncated labels, money without a currency format, mostly-null measures and empty queries, which is what a reviewer sees first). The rest are Wire's: queries read models only through `ref()`; no inline or external data in a board; every KPI has a label, every other chart a title, every query and chart a note; every model in a scaffolded subject area is charted or has a recorded decision; the anchor holds no credentials; every viz-catalog row is mapped or listed as unmapped; one board per subject area with `meta.yml` and `index.yml` present. A check that cannot run records `unverified`, which is not a pass.

Generate does not auto-validate, for the same reason `dbt-generate` does not: the validate step touches the warehouse, so it is a separate command and a separate decision.

## Reviewing and publishing

`/wire:dbtcharts-review <release>` presents the rendered boards (`dct render --format png`, written under the release's `dev/dbtcharts/`) and the generation report, gathers meeting and document-store context as every review does, and records approval or change requests. Change requests are applied by editing the board YAML, never by regenerating with `--force`, which would discard the curation.

Once approved, `dct init ci` in the dbt project adds a GitHub Actions workflow that validates every board on every pull request, and `dct skills cloud-setup` walks the dbtcharts.com connection if the client wants the boards hosted.

## Design conventions

How a board should look is a **convention**, the same mechanism as Wire's dbt, LookML and Cube coding standards: a YAML file in the process registry (`conventions/dbtcharts.yml`, mirrored to `wire/conventions/dbtcharts.yml`) that an engagement overrides by placing its own copy at `.wire/conventions/dbtcharts.yml`. The engagement file wins when present; otherwise the framework default applies. Copy the framework file and change the values; the whole file is read.

The file has two kinds of section.

| Section | What it holds | Who reads it |
|---|---|---|
| `presentation` | theme (`vivid` by default), frame width, currency symbol, landing-page title and logo | `dbtcharts-generate`, passed to the scaffold as `--theme`, `--currency`, `--frame-width`, `--title`, `--logo` |
| `windows` | KPI period (12 months vs the prior 12), event period (30 days), trend length (24 months), how a stopped feed anchors its window | the design step and the scaffold (`--trend-months`) |
| `board_shape` | 4 to 6 KPIs, 4 to 6 charts, one table, about 8 visualisations, KPI row height, no section headings, the layout row splits | the design step, the scaffold (`--kpi-row-height`) |
| `chart_defaults` | trend as bar with month labels and a left axis, composition as a stacked bar, mixed units on a right-hand axis, rankings horizontal and top 10, tables of 15 rows, no pie over three slices | the design step, the scaffold (`--breakdown-limit`) |
| `formats` | which slot a format lives in per chart family, the presets for counts, percents and deltas, and how a non-dollar currency is shown (KPI prefix, plain axes, currency named in the subtitle) | the design step |
| `render`, `profiling` | which `dct render` warning codes must be cleared, and the null-share and point-count thresholds below which a column is not charted | the design step, validate Check 10 |
| `naming`, `layout`, `sql`, `project_files` | rules with an id and a severity: KPI labels of at most 4 words and no table-name prefix; every chart titled and noted; every KPI formatted; trends with `time_unit`; no hidden endpoint labels; no `## Section` rows on a dashboard; no board-level `theme:`; BigQuery forms the dct static checker rejects; `dbt_charts.yml` holding `sources:` only | `lint_conventions.py --domain dbtcharts`, run by generate Step 6 and validate Check 11 |

An engagement that bills in pounds, for example, sets `presentation.currency: "£"` and a landing-page title and logo, and every board generated for it carries `£` on its KPIs and tables, plain numbers on its axes with "GBP" in the subtitles, and the client's logo top-right on the home page. Nothing in the commands or the skill changes.

## Notes on the dct CLI (0.8)

Things found the hard way and recorded in the `dbtcharts` skill so nobody rediscovers them:

- Build the manifest with `dbt compile`, not `dbt parse`. `dct` derives model columns from `compiled_code`; without it every Jinja-wrapped model reads as "contains no SELECT statement".
- `dbt_charts.yml` holds `sources:` only. A `serve:` or `theme:` key there is rejected; the dialect comes from the profile target and the theme from `charts/meta.yml`.
- The static column check misreads `DATE_TRUNC(d, MONTH)`, `WEEK(MONDAY)` and `r'...'` raw strings. The scaffold writes `DATE(EXTRACT(YEAR FROM d), EXTRACT(MONTH FROM d), 1)`; the skill lists the other substitutes.
- `dct validate --warehouse` needs the warehouse adapter inside the tool environment (`uv tool install dbt-charts --with dbt-bigquery`), and on Apple silicon an arm64 Python named explicitly.
- Currency presets print `$` and axis formats accept no other symbol; non-dollar money uses a KPI prefix and plain axes with the currency in the subtitle.
- `dbt show` on dbt Fusion rewrites `target/manifest.json`, which `dct` reads. Design lanes profile with `--target-path <scratch>` so a concurrent render never reads a half-written manifest, and the orchestrator compiles once before the whole-set validate.
- `--auto` lanes follow the director model's lane contract: the orchestrating session dispatches them, each writes a state file under `lanes/` after every completed item, and a lane silent for 30 minutes is re-dispatched. The generation report is assembled from those files.

## Where the rules live

| What | Where |
|---|---|
| The three commands | `wire/specs/development/dbtcharts/{generate,validate,review}.md` |
| The scaffold | `wire/scripts/dbtcharts_scaffold.py`, shipped in the plugin under `scripts/` |
| The skill and the design brief | `wire/skills/dbtcharts/SKILL.md`, `wire/skills/dbtcharts/board-design-brief.md` |
| The design convention | `conventions/dbtcharts.yml` in the process registry, mirrored to `wire/conventions/dbtcharts.yml`; engagement override at `.wire/conventions/dbtcharts.yml`; linted by `wire/scripts/lint_conventions.py --domain dbtcharts` |
| The graph entries | `dbtcharts` in `full_platform.yaml`, `dbt_development.yaml`, `dashboard_first.yaml` (optional, after `dbt` validate PASS) |
| The tests | `wire/tests/development/validate_dbtcharts_scaffold.py` (a fixture manifest and catalog round-tripped byte for byte) and `validate_dbtcharts_conventions.py` (the convention's sections present, the scaffold's output lint-clean, every mechanical rule firing on a bad board) |

## See also

- [Tutorial: dbt Charts Boards](../tutorials/dbt-charts): the three commands on a worked example, the convention override, and publishing to dbt Charts Cloud
- [Wire Agents](./wire-agents) (the `semantic-layer-developer` agent runs the generate and validate commands)
- [Full Platform Build](../release-types/full-platform), [dbt Development](../release-types/dbt-development), [Dashboard-First](../release-types/dashboard-first)
- [Command Reference](../reference/commands)
