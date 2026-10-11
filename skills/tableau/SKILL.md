---
name: tableau
description: Read a Tableau estate (Tableau Cloud, Tableau Server, or Desktop workbook files) for a migration to Looker or Omni. Activates for Tableau audits, the experimental tableau_to_looker and tableau_to_omni pairs of the bi_migration release type, or any work that reads .twb, .twbx, .tds or .tdsx files. Covers sign-in with a personal access token, what each surface gives, the workbook XML, the calculation language, and Wire's export and converter scripts.
---

# Tableau

Experimental (wire#287). Used by `/wire:tableau-audit-*`, `/wire:lookml-model-*` and `/wire:looker-content-*` on a `bi_migration` release with `bi_pair: tableau_to_looker`, by `/wire:omni-model-*` and `/wire:omni-content-*` with `bi_pair: tableau_to_omni` (the Omni writer `bi_to_omni.py --source tableau`, rules in `wire/bi_pairs/tableau_to_omni/`), and by any work that reads Tableau workbooks. Tell the consultant the pair is experimental at the start of that work.

## Sign-in

Tableau Cloud and Server use a **personal access token** (PAT): a name and a secret, created by the consultant under My Account Settings on the site. If the site says PAT creation is disabled, a site administrator allows it under Settings, General. Keep both in a file outside the repository that only the consultant can read, such as `~/.wire/tableau.env` (mode 600) exporting `TABLEAU_PAT_NAME` and `TABLEAU_PAT_SECRET`; source it in the same command that runs the script and pass the variable names. Never commit the secret, print it, or paste it into a session. Password sign-in does not work for scripts on Tableau Cloud, which requires multi-factor authentication. The site is the content URL segment (`https://<pod>.online.tableau.com/#/site/<site>/...`); it is also the identity scope (`tableau:<site>:...`).

## What each surface gives

| Surface | Cloud | Server | Desktop files |
|---|---|---|---|
| Inventory and download (REST API, `tableauserverclient`) | Yes | Yes | Files on disk |
| Lineage (Metadata API, GraphQL) | Yes | 2019.3 and later | No |
| Usage | Admin Insights export; else all-time view counts from REST | Repository, read-only user | None |
| Parity source rows | Query View Data (CSV per view, filters as `vf_` parameters); VizQL Data Service | Query View Data; VizQL Data Service from 2025.1 | Manual export |

Wire uses the REST API for the snapshot and Query View Data for parity. The Metadata API is not used in this version.

## The workbook XML in one page

A `.twb` is XML; a `.twbx` is a zip holding the `.twb` (and extracts, images). Published data sources are `.tds` / `.tdsx`.

- `datasources/datasource`: one per data source. `name` is internal (`federated.0abc`), `caption` is what users see. A `Parameters` data source holds the parameters.
- `connection/named-connections/.../connection`: the warehouse (`class`, `project`, `schema`, `server`). `connection[@class='sqlproxy']` means "use the published data source `dbname`".
- `relation`: `type='table'` (a table), `type='text'` (custom SQL), `type='join'` (physical join with a `clause`). `object-graph` holds 2020.2+ logical relationships with `unique-key` on each end.
- `metadata-records/metadata-record[@class='column']`: physical columns with `remote-name`, `local-name`, `parent-name` (the relation), `local-type`, default `aggregation`.
- `column` with `calculation/@formula`: a calculated field. Its identity is `name` (`[Calculation_1234]`), never `caption`.
- `worksheets/worksheet`: `view/datasources` (two or more means a blend), `datasource-dependencies/column-instance` (`[sum:sales:qk]` is derivation, field, type), `rows`, `cols`, `encodings`, `filter`, `sort`, `panes/pane/mark/@class`.
- `dashboards/dashboard`: `size`, `zones` (positions in units of 100,000), `devicelayouts`; `type='storyboard'` is a story.
- `actions/action`: `command/@command` (`tsc:tsl-filter` is a filter action).

## The calculation language in one page

- Fields `[x]`, qualified `[datasource].[x]`, parameters `[Parameters].[Parameter 1]`. Strings in single or double quotes. Comments `//`.
- Logic: `IF c THEN a ELSEIF c2 THEN b ELSE d END`, `CASE x WHEN v THEN r END`, `IIF(c, a, b)`, `AND`, `OR`, `NOT`.
- Row-level vs aggregate: a formula with `SUM`, `AVG`, `MIN`, `MAX`, `COUNTD`, `COUNT`, `MEDIAN`, `ATTR` is aggregate; otherwise row-level. A row-level numeric field with role measure is summed by default, so a row-level ratio becomes a sum of ratios.
- LOD: `{ FIXED [dim] : SUM([m]) }`, `INCLUDE`, `EXCLUDE`. Computed at a different grain from the view: no direct LookML equivalent.
- Table calculations: `WINDOW_SUM`, `RUNNING_SUM`, `INDEX`, `RANK`, `LOOKUP`, `TOTAL`: computed over the result table, after aggregation.
- Division by zero returns null; Wire translates `a / b` to `a / NULLIF(b, 0)`.

The full function map per dialect is in `wire/bi_pairs/tableau_to_looker/property_mapping.md`.

## Wire's scripts

```bash
python3 <plugin-root>/scripts/tableau_export.py rest --server <url> --site <site> \
  --token-name-env TABLEAU_PAT_NAME --token-env TABLEAU_PAT_SECRET --out <snapshot>
python3 <plugin-root>/scripts/tableau_export.py files --dir <files> --site <site> --out <snapshot>
python3 <plugin-root>/scripts/twb_to_lookml.py audit --snapshot <snapshot> --out <audit>
python3 <plugin-root>/scripts/twb_to_lookml.py convert --snapshot <snapshot> --out <batch> --model <m> --connection <c> [--include-root <folder>]
python3 <plugin-root>/scripts/twb_to_lookml.py lint <batch>
python3 <plugin-root>/scripts/tableau_export.py diff --old <inventory> --new <inventory> --parity-as-of <ts>
```

All are deterministic and make no AI call. The agent decides each `needs_human` item, explore design and consolidation; it never hand-writes LookML the converter emits.

## Pitfalls

- Embedded data sources are often copies of one another under different names. Check `datasource_fingerprints.csv` before designing explores.
- A physical join has no cardinality. Confirm each one and set `primary_key` on joined views, or symmetric aggregates cannot protect the numbers.
- An extract may be stale or fed by a Prep flow, not the warehouse. The plan rules each one; parity on an extract-backed sheet records the extract refresh time.
- Captions change; internal names do not. Never key anything on a caption.
- `.twbx` packages can hold image and extract files; only the `.twb` is read.
- Data sources often read Excel or CSV files, or an extract-only `.hyper` file, not the warehouse. The audit classes them redesign; the plan rules load to the warehouse or drop.
- Modern workbooks (2020.2 and later) list tables in a `collection` relation and join them through `object-graph` relationships. A logical object's caption is a label; the relation name is the table.
- Query View Data returns displayed values (rounded, with currency symbols). Set parity precision to the displayed precision. The view LUID is in `bi_content_catalog.csv` (`view_luid`); a sheet not published as a view has none.
