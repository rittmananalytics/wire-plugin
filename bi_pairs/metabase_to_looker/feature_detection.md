# Metabase to Looker: feature detection

Experimental. What the converter reads to decide each class. Queries are read in MBQL 5 (`stages`, clauses `[op, {options}, ...]`) and in legacy MBQL (`query`, `native`); Metabase 50 and later store MBQL 5.

| Construct | Where it is | Class |
|---|---|---|
| Card kind | `card.type`: `question`, `model`, `metric`; native when a stage has `native` | |
| Archived | `card.archived` | drop |
| Table and fields | `GET /api/table/:id/query_metadata`: `fields[]` with `effective_type`, `semantic_type`, `fk_target_field_id`, `visibility_type`, `coercion_strategy`, `nfc_path` | mechanical |
| Unsynced table | `fields` empty for a table a query reads | gap: validate fails |
| Field reference | `["field", {...}, <field id>]`; by name (`"region"`) when reading a model's or earlier stage's column | |
| Implicit join | `source-field` in the field's options (the foreign key it goes through) | mechanical |
| Question join | `stages[].joins[]` with `alias`, `strategy`, `conditions` | mechanical or assisted |
| Join alias reference | `join-alias` in the field's options | |
| Date unit | `temporal-unit` in the field's options | mechanical |
| Binning | `binning: {strategy: bin-width, bin-width}` or `{strategy: num-bins}` / `default` | assisted or redesign |
| Aggregation reference in a sort | `["aggregation", {}, <index or lib/uuid>]` | mechanical |
| Metric reference | `["metric", {}, <card id>]` | mechanical |
| Custom column | `stages[].expressions[]` named by `lib/expression-name` (MBQL 5) or a name map (legacy) | assisted |
| Second stage | `stages[1]` with only `filters`, `order-by`, `limit` | assisted; anything else redesign |
| Template tags | `template-tags`: `text`, `number`, `date` (variables), `dimension` (field filter), `card`, `snippet` | assisted; snippet redesign |
| Optional clause | `[[ ... ]]` in native SQL | assisted |
| Database engine | `inventory.json` `databases[].engine` | `sqlite`, `h2`: redesign |
| Dashboard tabs | `dashboard.tabs[]`, `dashcards[].dashboard_tab_id` | assisted |
| Text, heading, link, iframe, action cards | `dashcards[].visualization_settings.virtual_card.display` | mechanical (text, heading); drop (others) |
| Dashboard filter | `dashboard.parameters[]` and `dashcards[].parameter_mappings[]` | mechanical; `temporal-unit` drop |
| Combined series | `dashcards[].series[]` | assisted |
| Click behaviour | `visualization_settings.click_behavior` | drop |
