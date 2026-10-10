# Metabase to Looker: tooling

Experimental.

## Setup

| Need | How |
|---|---|
| Python 3.10 or later, PyYAML | already needed by Wire |
| `requests` | `python3 -m pip install requests` (it carries its own certificate bundle; some Python installs have none for the standard library) |
| `sqlglot` (optional) | `python3 -m pip install sqlglot`, to lift simple native SQL onto table views and to read native questions' sort order |
| A Metabase API key | Admin settings, Authentication, API keys; in a group that can see the content and its databases. Keep it in a file outside the repository that only the consultant can read, such as `~/.wire/metabase.env` (mode 600) exporting `MB_HOST` and `MB_API_KEY`; never committed or pasted into a session |
| Looker API credentials or the Looker MCP | For target setup, validation and parity |
| The client's LookML repo | Registered with `/wire:migration-source-register <release> lookml <url>` |

## Access to request

| For | Request |
|---|---|
| Snapshot | An API key in a group with view access to the collections in scope and the databases behind them |
| Table metadata | The databases fully synced in Metabase. A large warehouse can take hours on the first sync: narrowing the connection to the datasets in scope (Admin, Databases, dataset filter) shortens it |
| Parity source side | The same key: card data runs each question as it runs on its dashboard |
| Looker target | Developer on the LookML project, and an admin to configure the new model |

## Scripts

```bash
source ~/.wire/metabase.env
# Snapshot (all content, or the dashboards in scope)
python3 scripts/metabase_export.py api --out <snapshot> [--dashboard <id> ...]
# Audit: catalogs, IR, dependencies, needs_human
python3 scripts/mb_to_lookml.py audit --snapshot <snapshot> --out <audit>
# Convert one database (one connection per LookML model)
python3 scripts/mb_to_lookml.py convert --snapshot <snapshot> --out <batch> --model <model> \
  --connection <connection> --database <id> [--dashboards <ids>] [--include-root <folder>]
# Lint
python3 scripts/mb_to_lookml.py lint <batch>
# Drift and parity
python3 scripts/metabase_export.py diff --old <pinned inventory.json> --new <fresh inventory.json>
python3 scripts/metabase_export.py card-data --card <id> [--dashboard <id> --dashcard <id> --param <id>=<value>] --out rows.csv
```

Use `--include-root <folder>` when the client's LookML repo already has views: the output goes under the folder and the model includes only it.

## Limitations

- Experimental: run end to end once on a Metabase Cloud trial (Metabase 1.64): four questions on BigQuery, two native SQL and two query-builder, deployed to Looker and matched row for row. Not run on a client estate, on Snowflake or other warehouses, on dashboards with many tiles and filters, or on Metabase versions before 50.
- Native SQL questions and models become views on their SQL: exact, but not reusable. Lifting covers simple single-table SQL only, and never the `WHERE` clause.
- Binning by number of bins, multi-stage questions (other than a filter on an aggregation or grouping column), share, offset, snippets, segments and custom columns over more than one table are not converted.
- Metabase infers primary keys only where a warehouse declares them or a column is named `id`; BigQuery declares none, so joined views on BigQuery often need keys set by hand.
- Dashboard filters that change date grouping, click behaviour, link, iframe and action cards are not migrated. Text cards cannot show filter values.
- A field filter in native SQL is written table-qualified, as Metabase writes it; SQL that aliases that table needs a hand fix (it does not work in Metabase either).
- Permissions, sandboxing, subscriptions, alerts and embedding are out of scope.
