# Omni analytical patterns

Authoring idioms for Omni workbooks and models, collected from Omni's community Patterns category (community.omni.co/c/patterns/9, read 2026-09-06). Read this when building or reviewing Omni content; `SKILL.md` covers connection and object plumbing, this file covers analysis technique. Confirm any instance-dependent detail (feature flags, dialect functions) against the live instance before shipping it to a client.

For Looker-construct replacements during a `bi_migration` (Liquid to Mustache, parameters to controls, merged results), use `wire/bi_pairs/looker_to_omni/omni_patterns.md` instead; this file holds the tool-agnostic techniques.

## Table calculations (Excel-style calcs)

| Need | Idiom | Source (community.omni.co) |
|---|---|---|
| Top N within each group | Sort by group then metric desc; `=IF((ROW() = 1), 0, IF((A2 = A1), COUNTIF(A$1:A1, A2), 0)) + 1` ranks within group | /t/rank-sub-category-using-calcs-to-get-things-like-top-10-subcategories/316 |
| Top N rows overall | Helper tab ranks and limits; main query uses "filter by query"; or a duplicate tab with XLOOKUPs then a row limit | /t/how-to-filter-a-visualization-to-just-the-top-n-rows/127 |
| XLOOKUP beside subtotals | Lookup value and range must include every grouped dimension, or subtotal rows return blank | /t/subtotals-and-xlookup/415 |
| Hide repeated values in expanded tables | `=IF(ROW() = 1, A$1, IF(A2 <> A1, A2, ""))`, extended with `OR()` per parent dimension; hide the originals | /t/building-a-clean-pivot-table-by-hiding-repeated-values/404 |
| Sparse or single-point chart labels | `=IF(B1 = MAX(B:B), TEXT(B1, "#"), "")`; `TEXT()` keeps unlabeled points empty instead of 0; `MOD(ROW(), n)` for every-nth labels | /t/how-do-i-annotate-one-point-on-a-chart-are-there-ways-to-make-sparse-labels/126 |
| XmR (control) charts | Line chart plus eight calcs: moving range, MR average, value average, natural process limits, range limit, quartiles; duplicate per segment for before/after a change point | /t/xmr-charts-in-omni/258 |

## Query and model techniques

| Need | Idiom | Source |
|---|---|---|
| Cohorting without query views | Level-of-Detail field with Fixed grouping (field menu, Modeling, New Level of Detail field): aggregate one field by one dimension ignoring the rest of the query | /t/using-level-of-detail-functions-for-cohorting-analysis/368 |
| Date spine | Saved view generating sequential dates: `GENERATE_DATE_ARRAY` (BigQuery), `DATEADD` + `GENERATOR` (Snowflake), `SEQUENCE` + `EXPLODE` (Databricks) | /t/how-do-i-create-a-table-with-a-list-of-dates/49 |
| Sessionizing events | LAG per user for minutes since prior event; gaps over the threshold (typically 30 min) start sessions; join back and aggregate for session id, duration, event count | /t/sessionizing-your-events-data/48 |
| Histograms from aggregates | Aggregate to the grain, save as a view, apply the Bins UI to the numeric field, plot binned field against count | /t/binning-regrouping-aggregates-creating-a-histogram/152 |
| Long ID/email list filters | Build the list in one tab, filter with "is from another query"; or a boolean flag field in the model | /t/how-do-i-filter-on-a-long-list-of-emails-or-ids/187 |
| Filtering pivoted dimensions to top N | Same filter-by-query idiom against a ranked helper query | /t/tricks-for-filtering-dimensions-that-youre-pivoting-on/100 |
| Merging aggregate queries | XLOOKUP for one-to-one (first match only); saved views + relationships for one-to-many | /t/merging-queries/151 |
| Data-lag-aware date windows | Shift analysis windows by the pipeline's known lag instead of filtering on fixed relative dates | /t/shifting-dates-to-account-for-most-recent-data-not-being-current/429 |
| Stored procedures | `CALL` for DML or simple output; `SELECT * FROM TABLE(proc(...))` when results feed further querying; `omni_role` needs `GRANT USAGE` per procedure | /t/working-with-stored-procedures/329 |

## Multi-tenant and embedded

| Need | Idiom | Source |
|---|---|---|
| Identical per-tenant schemas | Dynamic schemas: user attribute picks the physical schema, views reference `<dynamic_schema>__table`; one model serves all tenants | /t/working-with-dynamic-schemas/99 |
| Customer-defined (EAV) custom fields | Typed CASE flattening in a hidden topic + query view; per-customer extension models generated via the YAML API; access filters bind tenant id | /t/embedding-custom-fields-eav-key-value-json-custom-fields-per-customer/339 |
| Localised labels | `dynamic_shared_extensions` keyed by a language user attribute, overriding `label`/`description` per extension (feature-flagged) | /t/configuring-model-level-localization/345 |
| Embedded tab navigation | Markdown tiles as tab buttons; POST messages to the parent frame swap the iframe URL; links carry filters via `filters.FIELD.json` | /t/creating-a-tabbed-experience-in-an-embedded-dashboard/132 |

## dbt metadata

Omni's dbt integration pulls model and column descriptions into the semantic layer (docs.omni.co/docs/integrations/dbt). On a Wire engagement the dbt layer's descriptions (including Droughty-generated ones) are the source; write descriptions there and import, rather than retyping them in Omni. The same descriptions feed AI answer quality (see `specs/utils/omni_ai_quality.md`).
