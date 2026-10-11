# Tableau to Omni

The sixth pair for the `bi_migration` release type (`bi_pair: tableau_to_omni`). It moves Tableau Cloud or Server workbooks and published data sources (or Desktop files) to an Omni model on a model branch and Omni dashboard documents.

> **Experimental.** Review every output before presenting it to a client.

## How it works

The audit is the same as for `tableau_to_looker`: `tableau_export.py` takes the snapshot and `twb_to_lookml.py` classifies every construct. For the model, the same reader works out what each table, column, calculation, join and tile becomes, and `wire/scripts/bi_to_omni.py` writes Omni files from that directly, with Omni naming: no LookML is written or parsed on the way.

| Layer | Here |
|---|---|
| Snapshot | `wire/scripts/tableau_export.py` |
| Reader | `wire/scripts/twb_to_lookml.py` (shared with `tableau_to_looker`) |
| Omni writer | `wire/scripts/bi_to_omni.py` (`convert --source tableau`, `lint`) |
| Ruleset | this folder |

## Commands

`/wire:tableau-audit-*` (shared with `tableau_to_looker`), then the Omni commands of Looker to Omni: `/wire:omni-target-setup-*`, `/wire:omni-model-*` (with `lint`), `/wire:omni-content-*`. The plan, parity, drift and cutover commands branch on `bi_pair`.

## Files

| File | Content |
|---|---|
| `translation_guide.md` | One row per Tableau construct: the Omni construct, class, notes |
| `property_mapping.md` | Filter expressions, aggregations, naming |
| `content_mapping.md` | Dashboards, tiles, chart types, controls, layout |
| `tooling.md` | Setup, the scripts, writing to the branch, parity |

Engagement overrides go in `.wire/engagement/bi_pair_overrides/tableau_to_omni/`.
