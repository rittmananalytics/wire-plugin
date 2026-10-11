# Omni to Looker

The eighth pair for the `bi_migration` release type (`bi_pair: omni_to_looker`). It moves an Omni shared model (views, topics, relationships) and its dashboard documents to LookML views, explores and LookML dashboards on a branch of the client's Looker repo. The reverse of `looker_to_omni`.

> **Experimental.** The pair has run end to end once (October 2026), on Rittman Analytics' own Omni model on BigQuery: three dashboards converted, deployed to Looker and compared tile by tile with Omni, 39 of 39 tiles matching. It has not run on a client estate. Review every output before presenting it to a client.

## Why Omni converts well

Omni's model language descends from LookML: views, dimensions with SQL, measures with aggregate types, timeframes, topics that join views through declared relationships, and `${view.field}` references. Most constructs map one to one. What does not is what Omni added: Mustache templating, query views built from a topic query, AI context, workbook-only fields, field-selection controls, period-over-period comparisons and Omni's own date-window filters.

## How it fits

| Layer | Here |
|---|---|
| Snapshot | `wire/scripts/omni_export.py` (the Omni CLI with a configured profile; read only) |
| Reader and writer | `wire/scripts/omni_to_lookml.py` (Omni to the tool-neutral IR and to LookML) |
| IR | `wire/schemas/bi_ir-schema.md`, `wire/scripts/bi_ir.py` |
| Ruleset | this folder: `translation_guide.md`, `property_mapping.md`, `feature_detection.md`, `content_mapping.md` |

This is not the Omni support in `platform_migration` (`/wire:omni-audit-*`, `/wire:omni-migration-*`), which keeps Omni and moves it to a new warehouse, and it is not `looker_to_omni`'s optional `omni_audit` of a brownfield Omni target.

## Commands

`/wire:omni-source-audit-*` (this pair's audit), then the Looker target commands shared with the Tableau, Metabase and Looker Studio pairs: `/wire:looker-target-setup-*`, `/wire:lookml-model-*` (with `lint`), `/wire:looker-content-*`. The plan, parity, drift and cutover commands are shared with every pair and branch on `bi_pair`.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per Omni construct: LookML construct, class, notes |
| `property_mapping.md` | Formats, timeframes, aggregate types, join types, filter operators, date windows, calculation operators |
| `feature_detection.md` | The YAML keys, document fields and CLI calls that decide each class |
| `content_mapping.md` | Chart types, the dashboard grid, text tiles, controls, what is dropped |
| `tooling.md` | Setup, access, the two scripts, limitations |
| `examples/` | Four worked examples, round-tripped byte for byte by the test suite |

Engagement overrides go in `.wire/engagement/bi_pair_overrides/omni_to_looker/`.
