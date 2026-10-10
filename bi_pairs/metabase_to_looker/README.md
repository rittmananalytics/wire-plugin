# Metabase to Looker

The fourth pair for the `bi_migration` release type (`bi_pair: metabase_to_looker`). It moves Metabase questions, models, metrics and dashboards (Metabase Cloud or self-hosted) to LookML views, explores, measures and LookML dashboards on a branch of the client's Looker repo.

> **Experimental.** The pair has run end to end once (October 2026): two native SQL questions and two query-builder questions on a Metabase Cloud trial instance's BigQuery database were converted, deployed to Looker and matched row for row. It has not run on a client estate. Review every output before presenting it to a client.

## Why Metabase converts well

Metabase keeps typed metadata for every table: each field's type, and its primary and foreign keys. Query-builder questions refer to fields by id, so the converter knows exactly which column a question reads, which view it belongs to and how tables join. Native SQL questions carry no such structure: they become views on their SQL.

## How it fits

| Layer | Here |
|---|---|
| Snapshot | `wire/scripts/metabase_export.py` (Metabase API with an API key; no git repo to register) |
| Reader and writer | `wire/scripts/mb_to_lookml.py` (Metabase to the tool-neutral IR and to LookML) |
| IR | `wire/schemas/bi_ir-schema.md`, `wire/scripts/bi_ir.py` |
| Ruleset | this folder: `translation_guide.md`, `property_mapping.md`, `feature_detection.md`, `content_mapping.md` |

This is not the Metabase support in `platform_migration` (`/wire:metabase-audit-*`, `/wire:metabase-migration-*`), which keeps Metabase and moves it to a new warehouse.

## Commands

`/wire:metabase-source-audit-*` (this pair's audit), then the Looker target commands shared with the Tableau pair: `/wire:looker-target-setup-*`, `/wire:lookml-model-*` (with `lint`), `/wire:looker-content-*`. The plan, parity, drift and cutover commands are shared with every pair and branch on `bi_pair`.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per Metabase construct: LookML construct, class, notes |
| `property_mapping.md` | Types, aggregations, date units, relative date filters, filter operators, the custom-column function map |
| `feature_detection.md` | The API fields and query clauses that decide each class |
| `content_mapping.md` | Chart types, the dashboard grid, tabs, text cards, dashboard filters, what is dropped |
| `tooling.md` | Setup, access, the two scripts, limitations |
| `examples/` | Four worked examples, round-tripped byte for byte by the test suite |

Engagement overrides go in `.wire/engagement/bi_pair_overrides/metabase_to_looker/`.
