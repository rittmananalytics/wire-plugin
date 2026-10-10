# Looker Studio to Looker

The fifth pair for the `bi_migration` release type (`bi_pair: looker_studio_to_looker`). It moves Looker Studio (formerly Data Studio) reports to LookML views, explores and LookML dashboards on a branch of the client's Looker repo.

> **Experimental.** The pair has run end to end once (October 2026): two reports, one on BigQuery tables and custom SQL and one on Looker Studio's Looker connector, were converted, deployed to Looker and matched chart by chart. It has not run on a client estate. Review every output before presenting it to a client.

## How it fits

The source side is the Looker Studio to Omni pair's, unchanged: the capture of the report editor, `report.json`, the audit catalogs and the metric catalogue (`wire/bi_pairs/looker_studio_to_omni/`). The target side is the Looker phases shared with the Tableau and Metabase pairs.

| Layer | Here |
|---|---|
| Capture and extraction | `looker_studio_capture.py`, `looker_studio_extract.py` (shared with the Omni pair) |
| Audit and metric catalogue | `looker_studio_catalog.py`, `looker_studio_metrics.py` (shared) |
| Converter | `wire/scripts/ls_to_lookml.py` (`report.json` and the ruled catalogue to LookML) |
| Parity source side | `looker_studio_parity.py`: each chart's recorded rows (shared) |

## Three kinds of data source

| Data source | Becomes |
|---|---|
| BigQuery table or view | A view on the table, with measures for the charts' aggregations and the translated calculated fields |
| BigQuery custom SQL | A view on the SQL |
| Looker Studio's Looker connector | Nothing new: the charts point at the existing explore, and each field's formula (`t0.<view>.<field>`) names the Looker field |
| Search Console, GA4, Sheets, community connectors (Funnel.io) | Listed: a pipeline task or a drop in the plan |

## Commands

`/wire:looker-studio-audit-*` and `/wire:metric-catalogue-*` (shared with the Omni pair), then `/wire:looker-target-setup-*`, `/wire:lookml-model-*` (with `lint`) and `/wire:looker-content-*`. The plan, parity, drift and cutover commands are shared with every pair.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per Looker Studio construct: LookML construct, class, notes |
| `property_mapping.md` | Data type, aggregation, sort and date range codes; the formula function map |
| `feature_detection.md` | The `report.json` fields that decide each class |
| `content_mapping.md` | Chart types, the grid, controls, the dashboard folder for an existing model |
| `tooling.md` | Setup, the converter, limitations |
| `examples/` | Three worked examples, round-tripped byte for byte by the test suite |
