# Omni to Looker: feature detection

Experimental. What the converter reads to decide each class. The snapshot is written by `omni_export.py snapshot`; the CLI calls behind each part are listed.

| Construct | Where it is | Class |
|---|---|---|
| Model files | `omni models yaml-get <model> --mode combined`: `files`, keyed by path (`model`, `relationships`, `<dir>/<name>.topic`, `<dir>/<name>.view`, `<name>.query.view`) | |
| View name | the file path without `.view` / `.query.view`, `/` replaced by `__` | |
| Topic name | the file name without `.topic` (the folder is a grouping) | |
| Schema view | `schema` and `table_name` | mechanical |
| Query view | `sql` | mechanical |
| Topic-built query view | `query` | redesign |
| Template, extends | `template: true`, `extends` | mechanical |
| Time field | `timeframes`; or `omni models get-views` lists `field[date]`; or `columns.json` says DATE, DATETIME or TIMESTAMP | mechanical |
| Column types | `columns.json` (`{"schema.table": {"column": "TYPE"}}`): one `INFORMATION_SCHEMA.COLUMNS` query per dataset, run through Omni as SQL on the model's connection (`omni query run` with `userEditedSQL`), for schema views and `SELECT *` query views; tables with none returned are in `inventory.json` `column_gaps` | |
| Boolean and numeric dimensions without a type file | a document filter of `type: boolean` or `type: number` on the field; a numeric `format` | |
| Mustache | `{{` ... `}}` in any `sql` | redesign |
| Nested field | `parent_field`, `nested_on_field` | redesign |
| Relationship | `relationships` file and a topic's own `relationships`: `join_from_view`, `join_to_view`, `join_to_view_as`, `on_sql`, `relationship_type`, `join_type` | mechanical |
| AI context | `ai_context`, `ai_fields`, `sample_queries`, `synonyms`, `sample_values` | drop |
| Dashboards | `omni documents list` (`hasDashboard`, `connectionId`, `folder`, `updatedAt`, `visits`), then `omni documents v2-get <id>` (`modelId`) | |
| Workbook with no dashboard | `hasDashboard: false` | drop (listed in `skipped_documents`) |
| Tile | `queryPresentations.data.<key>`: `topicName`, `isSql`, `query` (`table`, `fields`, `pivots`, `sorts`, `filters`, `limit`, `calculations`, `userEditedSQL`, `period_over_period_computations`), `visConfig.chartType` | |
| Tile position | `containers`: a node with `metadata.attachedQueryKey` and `gridPosition` (`x`, `y`, `w`, `h`) | |
| Tile not on the dashboard | a query key no container attaches | drop |
| Text tile | a container node of `type: inline-text` (or `markdown`, `text`) with `content` | mechanical |
| Pages | a container of `type: inline-page-switcher` | assisted |
| Control | `controls.data.<id>.config` (`fieldName`, `kind`, `type`, `values`, `left_side`, `right_side`, `required`) and `map` (tile key to field, or `false`) | mechanical |
| Field-selection control | `config.type: FIELD_SELECTION`, `kind: FIELD` | redesign |
| Workbook-only field | a tile field whose view or field is not in the shared model's files | assisted |
| SQL tile | `isSql: true` or a non-empty `userEditedSQL` | redesign |
| Period over period | `omni_period_pivot` in `fields` or `pivots`, or `period_over_period_computations` | assisted |
