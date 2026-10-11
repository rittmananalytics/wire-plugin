# Tableau to Omni: tooling

Experimental.

## Setup

- The Tableau access of `tableau_to_looker` (see `wire/bi_pairs/tableau_to_looker/tooling.md`), kept in a file under `~/.wire/` outside the repository.
- The Omni CLI with a profile that can create a model branch, write model YAML and create documents (`omni config login`).
- Python with `pyyaml` and `lkml` (the writer reuses the Looker to Omni mapping tables).

## Convert and lint

```bash
python3 wire/scripts/bi_to_omni.py convert --source tableau --snapshot <snapshot> --out <batch> --prefix <prefix> [--bind query|schema]
python3 wire/scripts/bi_to_omni.py lint <batch>
```

## Write to the branch

1. `omni models create-branch <model-id> --name <branch>` (done by `omni-target-setup`).
2. Each `.view` and `.topic` file: `omni models yaml-create <model-id>` with `branchId`, `fileName` and `yaml`.
3. The model's `relationships` file is shared by every topic: read it from the branch (`omni models yaml-get --branch-id`), append the batch's entries, write it back.
4. `omni models validate <model-id> --branch-id <branch>`.
5. Each document: `omni documents v2-create <model-id> "<title>"`, then `omni documents v2-patch-draft <identifier>` with the body from `documents/<slug>.json` and `branchId`. The draft runs against the branch; the published document stays empty until the branch merges.

## Parity

The source side is each sheet's rows through REST Query View Data (`tableau_export.py view-data`). The target side is each tile's query, read from the draft (`omni documents v2-get-draft`) and run with `omni query run` (`branchId`, `resultType: json`, `formatResults: false`). JSON rows are keyed by field label: write them to CSV with the tile's `fields` as the header. `parity_map.json` gives each source field's Omni field for the contract's `field_map`.
