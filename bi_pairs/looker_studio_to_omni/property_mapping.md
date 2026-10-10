# Looker Studio to Omni: property mapping

Looker Studio's internal responses use numeric codes. A code is named here only when it was checked against an independent source. Every other code is kept as its raw number in `report.json` and never guessed.

## Confirmed codes

| Field | Code | Meaning | Checked against |
|---|---|---|---|
| `aggregation`, `defaultAggregationType` | 6 | SUM | The SQL Looker Studio sent to BigQuery |
| Blend `join.type` | 2 | Full outer join | The blend editor |

## Seen, not confirmed

Kept raw. Each needs one check (SQL or editor) before it is named.

| Field | Code | Where seen | Likely meaning (not used) |
|---|---|---|---|
| `aggregation` | 0 | Dimensions | None |
| `aggregation` | 7 | Fields whose formula aggregates itself (`SUM(a)/SUM(b)`), and the record count | Auto |
| Blend `join.type` | 3 | Blends with no join keys | Cross join |
| `createdBy` | 1, 2, 3 | Data source fields | Source column, user calculated field, derived field |
| `dataType` | 0, 2, 3, 6, 8 | Fields | Text, number, integer, date, date |
| `processingLocation` | 1 | BigQuery connections | |
| `datasetType` | 1, 2 | Component datasets | Data source, blend |

## Connector types

| `connectorConfig` key | `datasourceType` | Connector in `report.json` |
|---|---|---|
| `bigQueryConnectorConfig` with `tableId` | 2 | `bigquery_table` |
| `bigQueryConnectorConfig` with a string value starting `SELECT` or `WITH` and no `tableId` | 2 | `bigquery_custom_sql` (the key holding the SQL is recorded as `sql_key`; not yet seen in a real capture) |
| `appsScriptAddonConnectorConfig` | 28 | `community_connector`, with `deployment_id` and `params` (secret values redacted) |
| `sheetsConfig` | 8 | `google_sheets` |
| anything else | | `other`, with the config key names |

## Field kinds

| Looker Studio | Omni |
|---|---|
| Source column (bare `t0.<column>` formula) | Dimension or measure over the warehouse column |
| Data source calculated field | A metric catalogue entry; one Omni measure per ruled group |
| Chart-level calculated field | A metric catalogue entry (scope `chart`) |
| Default aggregation SUM on a numeric column | `aggregate_type: sum` |
| Record Count | `aggregate_type: count` |

## Secrets

Connector settings whose key matches `password`, `secret`, `token`, `api_key`, `apikey`, `private` or `credential` (any case) are written as `<redacted>` in `report.json`. The raw capture still holds them, which is why the capture folder is git-ignored and refused if tracked.
