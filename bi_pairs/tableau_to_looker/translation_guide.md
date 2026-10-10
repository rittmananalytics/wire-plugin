# Tableau to Looker: translation guide

Experimental. Applied by `wire/scripts/twb_to_lookml.py` and tested by `wire/tests/bi_migration/validate_twb_to_lookml.py` and `validate_tableau_audit_classification.py`.

## Constructs

| Tableau construct | LookML | Class | Notes |
|---|---|---|---|
| Connection, table relation | view with `sql_table_name` | mechanical | One view per warehouse table, shared across data sources |
| Physical join | explore `join` with `sql_on`, `type`, `relationship: many_to_one` | assisted | Tableau declares no cardinality. Confirm it and set `primary_key` on the joined view |
| Logical relationship (2020.2 and later) | explore `join` with `relationship` from the declared unique keys | assisted | `unique-key` on both ends gives one_to_one, on one end many_to_one or one_to_many, on neither (Tableau's default) many_to_many. A relationship with empty key fields leaves `sql_on` to a person |
| Primary key | `primary_key: yes` on a view's single `*_pk` column | assisted | Tableau records none. Symmetric aggregates need one on every joined view; a joined view with no `*_pk` column is listed |
| Custom SQL relation | view with `derived_table: sql:` | assisted | Copied verbatim; check the dialect and any parameter references |
| Published data source | the published data source's explore, named by its site name | mechanical | The workbook's `sqlproxy` connection names it by content URL (`dbname`); its `formatted-name` can be an internal id shared by copies |
| Column (string, date, datetime, boolean) | `dimension` or `dimension_group: type: time` | mechanical | Dates get `[raw, date, week, month, quarter, year]`; datetimes add `time` |
| Column with default aggregation SUM, AVG, MIN, MAX, COUNTD | hidden `dimension` plus `measure` of the matching type | mechanical | `total_`, `average_`, `min_`, `max_`, `count_distinct_` prefixes |
| Row-level calculation in the supported function subset | `dimension` with translated `sql:` | assisted | Division becomes `a / NULLIF(b, 0)`, matching Tableau's null on divide by zero |
| Row-level numeric calculation with role measure | `dimension` plus `total_<name>` sum measure | assisted | Tableau sums it by default: a sum of row values. If it is a ratio, that is a sum of ratios |
| Aggregate calculation (`SUM([a]) / SUM([b])`) | `measure: type: number` over emitted measures | assisted | Every aggregate must be over a single field |
| Calculation with an unmapped function | not emitted | assisted | needs_human with the Tableau formula |
| LOD expression (`FIXED`, `INCLUDE`, `EXCLUDE`) | not emitted | redesign | Plan ruling: derived table, symmetric aggregate, or drop |
| Table calculation (`WINDOW_*`, `RUNNING_*`, `INDEX`, `RANK`, `LOOKUP`, `TOTAL`) | not emitted | redesign | Looker table calculation on the tile, or drop |
| Parameter | `parameter` with `allowed_value` and `default_value` | assisted | References become `{% parameter name %}` |
| Group (categorical bin) | `dimension` with `CASE WHEN ... IN (...) THEN ... ELSE <column> END` | assisted | Unmatched values keep their own value, as in Tableau |
| Bin | `dimension` with `FLOOR(x / size) * size` | assisted | |
| Set | not emitted | assisted | needs_human: a yesno dimension or a filter |
| Data blending | not emitted | redesign | Model-level join or merged results |
| Extract (`.hyper`) | views read the live tables | redesign | Plan ruling: dbt model, live connection, or drop. The audit records the refresh time |
| Prep flow | not read | redesign | Default plan disposition: dbt model |
| Worksheet on a dashboard | LookML dashboard element | mechanical | When every field maps |
| Worksheet on no dashboard | one-tile LookML dashboard | assisted | Keep it, make it a Look through the Looker API, or drop |
| Sheet sort (`sort`, `computed-sort`) | element `sorts` | mechanical | |
| Sheet filter: exclude null, member list, measure or dimension range | element `filters` (`-NULL`, `a,b`, `>=n`, `[a, b]`) | mechanical | A filter on a measure is a HAVING filter in both tools. Other filters (relative date, top N, wildcard, condition) are listed |
| Dashboard | `.dashboard.lookml` (newspaper layout) | mechanical | |
| Quick filter zone | dashboard `filters:` with `listen` on the sheets that filter that field | mechanical | |
| Filter action | not emitted | assisted | Dashboard filter `listen`, or cross-filtering |
| Text zone | `type: text` element | mechanical | |
| Image, web page, blank zones | dropped, listed | drop | |
| Device layouts | dropped, listed | drop | |
| Story | dropped, listed | drop | Recreate by hand |

Tableau parameters are mechanical into Looker but would be redesign into Omni: classification is per pair, not per source.

## Data source fingerprints

Most estates embed near-identical data sources in many workbooks. Each data source with relations gets a fingerprint: SHA-256 (first 16 hex characters) over its connection (class, project, server), its sorted relations (table, or a hash of the custom SQL), its sorted joins, and its sorted column set (remote name and relation). Names and captions are not part of it. Data sources with the same fingerprint are one group, convert to one explore (named by the group's shortest caption), and are listed in `datasource_fingerprints.csv`; the plan rules each group's consolidation. One extra column gives a different fingerprint, so near-duplicates are separate groups for the review to merge by ruling.

## Field identity

A calculated field's identity is its internal name (`[Calculation_1234]`), never its caption. The catalog carries both. Identities are `tableau:<site>:field:<datasource>:<internal_name>`, percent-encoded per `wire/schemas/bi_ir-schema.md`.
