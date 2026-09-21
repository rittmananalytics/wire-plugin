# Looker to Omni: Omni-side patterns for `needs_human` and `redesign` items

Documented Omni idioms for the constructs the converter refuses or emits with a note. Each entry names the LookML construct it replaces, the Omni recipe, and the community post that documents it (all under community.omni.co, category Patterns, read 2026-09-06). The converter never implements these; they are the agent's reference when it works a `needs_human.json` item or applies a plan ruling. An idiom used on an engagement is confirmed against the live Omni instance, not assumed from this file.

## Model-layer patterns

| LookML construct (class) | Omni idiom | Recipe | Source |
|---|---|---|---|
| Liquid `{% condition %}` with a default filter (redesign) | Mustache conditional templated filter | `{{# view.field.filter }}` applies the user's filter; `{{^ view.field.filter }}` supplies the default when none is set. Layered override filters chain the two. | /t/creating-an-override-style-filter/137 |
| `_in_query` Liquid (redesign) | `in_query` mustache | `case when {{ view.field.in_query }} then <calc> else ' ' end` blanks a measure at aggregation levels where it has no meaning (e.g. QoQ change grouped by year). | /t/how-to-create-a-measure-that-is-blank-for-certain-levels-of-aggregation/194 |
| Liquid parameter driving date grain (redesign) | CASE dimension on filter range | A dimension whose CASE reads `{{ filters.view.field.range_start }}` / `range_end`, returning hourly formatting under 48h and daily above. Dialect functions per warehouse (`TIMESTAMP_DIFF` on BigQuery, `TIMESTAMPDIFF` on Snowflake). | /t/dynamically-change-date-granularity-based-on-filter-timeframe/367 |
| Liquid parameter in derived-table SQL, rolling windows (redesign) | Templated filter injected into join SQL | Self-join with `make_interval(days => {{ filters.view.rolling_window.value }}::integer)` (Postgres form; adapt per dialect); filter carries a `suggestion_list` and single-select. | /t/rolling-fact-table-with-dynamic-look-back-window/201 |
| User attributes in `sql_table_name` per tenant (redesign) | Dynamic schemas | Declare a dynamic schema in the model file; a user attribute picks the physical schema; views reference `<dynamic_schema_name>__table`. For identical per-tenant schemas, not row-level filtering. | /t/working-with-dynamic-schemas/99 |
| LookML `extends` across projects / hub-and-spoke (assisted) | `template: true` + `extends` | Hub model marks reusable views `template: true`; spoke models `extends: [view_template]`. Already the converter's mapping for `extension: required`; this post covers the cross-model form. | /t/how-can-i-share-logic-across-multiple-models-hub-and-spoke/150 |
| Date-comparison parameters, arbitrary periods (redesign) | Filter-only fields + filtered measures | Two filter-only timestamp fields capture the periods; templated filters bind them to the date column; one filtered measure per period. Replaces Looker patterns that compare non-sequential windows (Black Friday vs Memorial Day). | /t/comparing-metrics-over-arbitrary-periods/280 |
| Localised labels via Looker locale files (redesign) | `dynamic_shared_extensions` | A language user attribute selects a shared extension overriding `label`/`description` per field. Feature-flagged; confirm on the instance. | /t/configuring-model-level-localization/345 |

## Content-layer patterns

| Looker construct (class) | Omni idiom | Recipe | Source |
|---|---|---|---|
| Merged results (redesign) | XLOOKUP calc or saved-view join | XLOOKUP for one-to-one merges (first match only); saved views joined through relationships for one-to-many. | /t/merging-queries/151 |
| Parameter-driven YTD/QTD/MTD single-value tiles (redesign) | Parent control + filtered measures | Filtered measures per period using time-part dimensions (`day_of_year` etc.) and `between_dates: this year`; a parent control wires a timeframe selector to a measure selector. | /t/how-can-i-dynamically-show-ytd-qtd-mtd-metrics-in-the-kpi-tiles-on-my-dashboard/124 |
| KPI comparison breaking on comparison-period change | Transpose the results table | Swap Rows & Measures so the KPI references the stable `Measure Value` column instead of a period-named column. | /t/how-do-i-stop-comparison-period-changes-from-breaking-my-kpi-tile-comparisons/143 |
| Top-N filters on pivots, merged-result rankers | Filter by query | A helper tab ranks and limits the dimension; the main query filters with "is from another query". Also the idiom for long ID/email lists. | /t/tricks-for-filtering-dimensions-that-youre-pivoting-on/100, /t/how-do-i-filter-on-a-long-list-of-emails-or-ids/187 |
| `pivot_where()` / offset ranking calcs (`unsupported_calc`) | In-group ranking calc | Sort by group then metric; `=IF((ROW() = 1), 0, IF((A2 = A1), COUNTIF(A$1:A1, A2), 0)) + 1` ranks within group for top-N-per-category. | /t/rank-sub-category-using-calcs-to-get-things-like-top-10-subcategories/316 |
| Dashboard navigation (Looker nav tiles; no tabs in either tool) | Anchor links or filter-carrying tab links | Text tile with an HTML `id` (Omni prepends `user-content-`) plus markdown links; for cross-dashboard tabs, links embed live filter values with `filters.FIELD.json` mustache. Embedded: markdown POST messages swap the iframe URL. | /t/link-to-sections-on-an-omni-dashboard/230, /t/dashboard-tabs-preserving-filter-selection/221, /t/creating-a-tabbed-experience-in-an-embedded-dashboard/132 |
| Subtotals with XLOOKUP calcs blank | Align lookup with GROUP BY | XLOOKUP's lookup value and range must include every grouped dimension or the subtotal row returns blank. | /t/subtotals-and-xlookup/415 |

## Dashboard themes

Omni dashboards theme through a JSON imported in the dashboard editor (`dashboard-key-color`, `dashboard-background`, `dashboard-tile-border-radius`, font families, tile margins and shadows). Six worked themes (tile accent, control accent, subtle blue/orange, dawn, matrix, and a user-contributed gradient pair) are at /t/can-you-provide-some-example-dashboard-themes/180. `omni-target-setup` derives one theme JSON from the client's brand at setup so every migrated document styles consistently; per-dashboard fidelity work stays in the content batches' `hand_finish` list.

## Not in scope here

Analytical patterns with no Looker-construct counterpart (sessionization SQL, date spines, LoD cohorting, XmR charts, binning, EAV custom-field flattening) live in `wire/skills/omni/patterns.md`; this file only maps Looker constructs the converter refuses to their Omni replacements.
