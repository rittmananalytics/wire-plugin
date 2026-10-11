# Metabase to Omni

The seventh pair for the `bi_migration` release type (`bi_pair: metabase_to_omni`). It moves Metabase questions, models, metrics and dashboards (Metabase Cloud or self-hosted) to an Omni model on a model branch and Omni dashboard documents.

> **Experimental.** Review every output before presenting it to a client.

## How it works

The audit is the same as for `metabase_to_looker`: `metabase_export.py` takes the snapshot and `mb_to_lookml.py` classifies every construct. For the model, the same reader works out what each table, column, calculation, join and tile becomes, and `wire/scripts/bi_to_omni.py` writes Omni files from that directly, with Omni naming: no LookML is written or parsed on the way.

| Layer | Here |
|---|---|
| Snapshot | `wire/scripts/metabase_export.py` |
| Reader | `wire/scripts/mb_to_lookml.py` (shared with `metabase_to_looker`) |
| Omni writer | `wire/scripts/bi_to_omni.py` (`convert --source metabase`, `lint`) |
| Ruleset | this folder |

## Commands

`/wire:metabase-source-audit-*` (shared with `metabase_to_looker`), then the Omni commands of Looker to Omni: `/wire:omni-target-setup-*`, `/wire:omni-model-*` (with `lint`), `/wire:omni-content-*`. The plan, parity, drift and cutover commands branch on `bi_pair`.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per Metabase construct: the Omni construct, class, notes |
| `property_mapping.md` | Filter expressions, aggregations, naming |
| `content_mapping.md` | Dashboards, tiles, chart types, controls, layout |
| `tooling.md` | Setup, the scripts, writing to the branch, parity |

Engagement overrides go in `.wire/engagement/bi_pair_overrides/metabase_to_omni/`.
