# Tableau to Looker: tooling

Experimental.

## Setup

| Need | How |
|---|---|
| Python 3.10 or later, PyYAML | already needed by Wire |
| `tableauserverclient` (Cloud or Server only) | `python3 -m pip install tableauserverclient` |
| A Tableau personal access token | Created by the consultant on the site (a site administrator may first need to allow token creation under Settings, General); name and secret in a file outside the repository that only the consultant can read, such as `~/.wire/tableau.env` (mode 600), loaded into two environment variables; never committed or pasted into a session |
| Looker API credentials or the Looker MCP | For target setup, validation and parity |
| The client's LookML repo | Registered with `/wire:migration-source-register <release> lookml <url>` |

## Access to request

| For | Request |
|---|---|
| Snapshot and inventory | Site Role Explorer (or higher) on every project in scope, with download permission on workbooks and data sources |
| Usage on Cloud | An Admin Insights export, or Site Administrator to produce one. Without it, the snapshot falls back to each view's all-time view count from the REST API |
| Usage on Server | Read-only access to the repository (`readonly` user) |
| Parity source side | View data permission on the views in scope |
| Looker target | Developer on the LookML project, and permission to create folders, groups and user attributes |

## Scripts

```bash
# Snapshot: Cloud or Server, or Desktop files
python3 scripts/tableau_export.py rest --server <url> --site <site> --token-name-env TABLEAU_PAT_NAME --token-env TABLEAU_PAT_SECRET --out <snapshot>
python3 scripts/tableau_export.py files --dir <files> --site <site> --out <snapshot>
# Audit: catalogs, fingerprints, IR, dependencies
python3 scripts/twb_to_lookml.py audit --snapshot <snapshot> --out <audit> --site <site>
# Convert a batch to LookML
python3 scripts/twb_to_lookml.py convert --snapshot <snapshot> --out <batch> --model <model> --connection <connection> --datasets <ids> [--workbooks <ids>] [--include-root <folder>]
# --include-root: write views and dashboards under <folder> and include only that folder; use it when the client repo already has views
# Lint emitted LookML for Tableau expressions
python3 scripts/twb_to_lookml.py lint <batch>
# Drift and parity
python3 scripts/tableau_export.py diff --old <pinned inventory.json> --new <fresh inventory.json> --parity-as-of <ts>
python3 scripts/tableau_export.py view-data --server <url> --site <site> --token-name-env ... --token-env ... --view-luid <luid> --filter region=North --out rows.csv
# IR check
python3 scripts/bi_ir.py validate <dir>/ir
```

`tableaudocumentapi` is not used: it reads fields and connections but not worksheets or dashboards, so the converter parses the XML directly with the standard library.

## Limitations

- Experimental: the snapshot, audit, conversion, lint and Query View Data have run against a Tableau Cloud trial site (October 2026): the Superstore and World Indicators samples (Excel files and an extract), and one published BigQuery data source with a one-sheet workbook, converted, deployed to a Looker instance and queried through the Looker API: its 34 rows matched Tableau's through the comparator. Not run against a client estate or a multi-tile dashboard.
- Those runs found and fixed fourteen converter and export faults the hand-written fixtures missed; `fixture/tableau/modern/` and `fixture/tableau/published/` reproduce each one. Larger client estates will hold more structures not yet seen.
- The automated tests run the REST path against a fake client with the same interface. Admin Insights column names vary between exports; the script accepts the common ones. The last extract refresh comes from the site's job history, which keeps a limited period: an older refresh is recorded as unknown.
- Query View Data returns displayed values: rounded to the sheet's number format, with currency symbols and thousands separators. Set each parity measure's precision to the displayed precision.
- The calculation translator covers the row-level subset in `property_mapping.md`. LOD expressions, table calculations, sets, blends and unmapped functions are never translated.
- Physical joins carry no cardinality in Tableau; every one is `many_to_one` until a person confirms it.
- Extracts are not opened. Views read the live warehouse tables; the plan rules each extract's disposition.
- Prep flows, Tableau user and permission migration beyond groups, and formatting fidelity are out of scope.
- Desktop files mode has no usage and no headless parity source side.
- `metric_catalogue` (from the Looker Studio pair) is not part of this profile's graph yet, although fingerprint groups are its natural input.
- The other two pairs keep their own artifact names; the tool-neutral artifact rename proposed in wire#287 is not done.
