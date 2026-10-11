# Omni to Looker: tooling

Experimental.

## Setup

| Need | How |
|---|---|
| Python 3.10 or later, PyYAML | already needed by Wire |
| The Omni CLI | `brew install exploreomni/tap/omni` (or the release binary), then `omni config init` for a profile on the instance. See `skills/omni/SKILL.md` |
| Column types | Read by the snapshot from the warehouse's `INFORMATION_SCHEMA` through Omni (BigQuery and Snowflake), so the profile must be able to run SQL on the model's connection. `--columns <file>` adds or overrides types; `--no-columns` skips the read |
| Looker API credentials or the Looker MCP | For target setup, validation and parity |
| The client's LookML repo | Registered with `/wire:migration-source-register <release> lookml <url>` |

## Access to request

| For | Request |
|---|---|
| Snapshot | An Omni user (or API key) that can read the shared model and the documents in scope; the snapshot only reads |
| Parity source side | The same profile: tile data runs each tile's saved query |
| Looker target | Developer on the LookML project, and an admin to configure the new model |

## Scripts

```bash
# Snapshot: the shared model, the views it reaches, and the dashboards on it
python3 scripts/omni_export.py snapshot --model-id <uuid> --out <snapshot> [--profile <p>] \
  [--documents <id,id>] [--folders <name,name>] [--columns extra.json] [--no-columns] [--all-views]
# Audit: catalogs, IR, dependencies, needs_human
python3 scripts/omni_to_lookml.py audit --snapshot <snapshot> --out <audit>
# Convert a batch of topics and dashboards
python3 scripts/omni_to_lookml.py convert --snapshot <snapshot> --out <batch> --model <model> \
  --connection <connection> [--topics <names>] [--documents <ids>] [--include-root <folder>]
# Lint
python3 scripts/omni_to_lookml.py lint <batch>
# Drift and parity
python3 scripts/omni_export.py diff --old <pinned inventory.json> --new <fresh inventory.json>
python3 scripts/omni_export.py tile-data --document <id> --query-key <key> --out rows.csv [--keep-pivots] [--limit 5000]
```

Use `--include-root <folder>` when the client's LookML repo already has views: the output goes under the folder and the model includes only it.

## Limitations

- Experimental: run end to end once, on one real Omni model on BigQuery: 57 views and 28 of 32 topics converted, lint clean; three dashboards deployed to Looker, 39 of 39 tiles matching Omni. Not run on Snowflake or other warehouses or on a client estate.
- Types are not in Omni's YAML. They are read from `INFORMATION_SCHEMA` for schema views and `SELECT *` query views; a view on other SQL is typed only from its formats and the filters that use it.
- Bare column qualification uses a keyword list. A function or keyword it does not know is qualified as a column; Looker's validator catches it in `lookml-model-validate`.
- Workbook-only fields (defined in a document's workbook model) are not in the shared model: their tiles are listed, not converted.
- Mustache templating, query views built from a topic query, nested fields, field-selection controls, period-over-period comparisons, SQL tiles and AI context are not converted.
- Omni's tile query is read as saved: dashboard control values are not applied on either side of parity.
- Permissions, schedules, alerts and embedding are out of scope.
