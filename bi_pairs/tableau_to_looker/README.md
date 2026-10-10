# Tableau to Looker

The third pair for the `bi_migration` release type (`bi_pair: tableau_to_looker`, wire#287). It moves Tableau Cloud or Tableau Server workbooks and published data sources to LookML views, explores and LookML dashboards on a branch of the client's Looker repo. Tableau Desktop-only estates run in a files mode.

> **Experimental.** The pair has run end to end once (October 2026): a Tableau Cloud trial site's BigQuery sheet was converted, deployed to Looker and matched row for row. It has not run on a client estate. Review every output before presenting it to a client.

## Editions

| Surface | Tableau Cloud | Tableau Server | Desktop files only |
|---|---|---|---|
| Inventory, download, subscriptions (REST API, `tableauserverclient`) | Yes | Yes | No: files on disk |
| Usage (`views_90d`, `last_viewed`) | Admin Insights export | Repository (read-only user) | None: `unknown` |
| Parity source side | REST Query View Data; VizQL Data Service for published data sources | Query View Data; VizQL Data Service from 2025.1 | Manual export per sheet |
| Workbook and data source XML | Same | Same | Same |

The XML parse, the classification, the converter and the IR are the same in all three.

## How it fits

| Layer | Here |
|---|---|
| Reader | `wire/scripts/twb_to_lookml.py` (Tableau XML to the tool-neutral IR) |
| IR | `wire/schemas/bi_ir-schema.md`, `wire/scripts/bi_ir.py` |
| Ruleset | this folder: `translation_guide.md`, `property_mapping.md`, `feature_detection.md`, `content_mapping.md` |
| Writer | the LookML writer in `twb_to_lookml.py` |
| Snapshot | `wire/scripts/tableau_export.py` (Tableau has no git repo to register) |

The Looker to Omni pair keeps its own IR for now; moving it onto `bi_ir.py` is a later, deliberate change.

## Commands

`/wire:tableau-audit-*`, `/wire:looker-target-setup-*`, `/wire:lookml-model-*` (with `lint`), `/wire:looker-content-*`. The plan, parity, drift and cutover commands are shared with the other pairs and branch on `bi_pair`.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per Tableau construct: LookML construct, class, notes |
| `property_mapping.md` | Data types, default aggregations, formats, derivations, the calculation-language function map per dialect |
| `feature_detection.md` | The XML paths and patterns that decide each class |
| `content_mapping.md` | Mark types to Looker chart types, zones to the newspaper grid, filters and actions, what is dropped |
| `tooling.md` | Setup, access, the three scripts, limitations |
| `examples/` | Six worked examples, round-tripped byte for byte by the test suite |

Engagement overrides go in `.wire/engagement/bi_pair_overrides/tableau_to_looker/`.
