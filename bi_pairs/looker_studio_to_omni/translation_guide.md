# Looker Studio to Omni: translation guide

## Evidence routes

| Route | Source | Gives | Access | Supported by Google |
|---|---|---|---|---|
| B | Editor calls `getReport`, `getSchema`, `getBlockDatasource` | Pages, layout, components, fields, formulas, filters, blends, parameters; data source connections and calculated fields | View on report; Edit on each data source | No (undocumented) |
| C | Chart data calls `batchedDataV2` | Each chart's query specification and the values it showed, for every connector; BigQuery job link | View on report | No (undocumented) |
| A | `INFORMATION_SCHEMA.JOBS`, jobs labelled `looker_studio_report_id` | SQL per BigQuery chart; usage over 180 days | BigQuery Resource Viewer on the billing project | Yes |

Route A cannot cover non-BigQuery connectors (Funnel.io and other community connectors, GA4, Google Ads, Search Console, Sheets): none of them keeps a query log a consultant can read. Route C covers them, because it records what the chart showed rather than how it was queried.

## Data source classes

Applied by `looker_studio_catalog.py`.

| Connector | Class | What happens |
|---|---|---|
| BigQuery table or view | `map` | The Omni model reads the same table, or its modelled successor |
| BigQuery custom SQL | `assisted` | The SQL becomes a dbt model (preferred) or an Omni SQL view |
| Community connector (Apps Script), Google product connector, Sheets, other | `pipeline` | No known warehouse copy. The plan raises a pipeline task: land the data in the warehouse first (the product's BigQuery export, a pipeline tool, or the partner's warehouse export) |
| Definition not read | `blocked` | Edit access refused, or not captured. Request access and re-capture |

A community connector that runs its own SQL against another warehouse (for example a Snowflake connector with a `query` setting) is still `pipeline`; its reason names the query to reproduce.

## Component classes

| Class | Rule |
|---|---|
| `mechanical` | Chart type in the supported list of `content_mapping.md`, no chart-level formula, no comparison period, not on a blend |
| `assisted` | Supported type that needs a decision: chart-level calculated field, comparison period, blend, combo or bullet chart; every control |
| `redesign` | Chart type with no Omni mapping (community visualisations and any unlisted type) |
| `drop` | Decorative shapes, lines and images; text boxes (recreated from `report.json` text) |

`blocked_by` records `pipeline` or `blocked` when the chart's data source (or any input of its blend) has that class. The chart's own class still describes the chart.

## Calculated fields

A data source field is a calculation when `createdBy` is 2, or its formula is something other than a bare `t0.<column>` reference or the system `COUNT(1)` record count. Chart-level calculated fields are concept definitions with a `textFormula`.

## Formula normalisation

Applied by `looker_studio_metrics.py` before grouping:

1. Drop table namespaces (`t0.`, `t1.`).
2. Lower-case field names; upper-case function names and keywords.
3. `IFNULL(x, 0)` and `COALESCE(x, 0)` inside `SUM`, `AVG`, `MIN` or `MAX` become `x`. Those aggregates ignore nulls, so the result differs only when every row is null.
4. Collapse whitespace to one space, and remove it around operators, commas and brackets.
5. String literals are left exactly as written.

The **shape** of a formula is its normalised text with every field name replaced by `f` and every number by `n`.

## Metric catalogue classes

Definitions are grouped by metric name (label, lower case, letters and digits only).

| Class | Rule | Review decides |
|---|---|---|
| `same_definition` | One normalised formula | Merge |
| `same_shape_different_fields` | Several formulas, one shape | Alias (merge) or different things (rename) |
| `conflict` | Several shapes | Which is right, or keep both under new names |

Finding `sum_of_ratio`: a chart applies `SUM` (code 6) to a data source field whose formula divides with no aggregate function. The total is a sum of row ratios, not a ratio of totals.

## What the model is built from

Never from the data sources. The Omni model reads warehouse tables (existing, or from a linked `dbt_development` release), and each ruled metric becomes one measure. See `specs/migration/bi_migration_plan/generate.md`, section "Pair: looker_studio_to_omni", for the model route rule.
