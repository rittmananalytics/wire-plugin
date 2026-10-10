---
name: metabase
description: Connect to a Metabase instance and enumerate its collections, dashboards, cards/questions (with SQL), database connections, and permission groups. Activates for Metabase audits, reporting-layer migrations (moving Metabase to a new warehouse, or replacing Metabase with Looker on the experimental metabase_to_looker pair of bi_migration), or any work that reads or repoints Metabase content. Wraps the upstream metabase/agent-skills.
---

# Metabase

Connection details and object hierarchy for cataloguing and migrating a Metabase reporting layer. Used by `/wire:metabase-audit-*` and `/wire:metabase-migration-*`, and by any reporting-layer work that reads Metabase content.

Two kinds of migration use it. In `platform_migration`, Metabase stays and moves to a new warehouse (`/wire:metabase-audit-*`, `/wire:metabase-migration-*`). In `bi_migration` with `bi_pair: metabase_to_looker` (experimental), Metabase is replaced by Looker (`/wire:metabase-source-audit-*`); see "Replacing Metabase with Looker" below. Tell the consultant that pair is experimental at the start of that work.

## Imported upstream skills

This skill builds on the official **metabase/agent-skills** (https://github.com/metabase/agent-skills). Install them once per machine:

```
npx skills add metabase/agent-skills
```

The three relevant to Wire migration work:

- **metabase-cli** — one command surface (`mb`) over every Metabase resource: collections, dashboards, cards, database connections, permission groups. Preferred for enumeration and for serialization export/import.
- **metabase-representation-format** — the YAML serialization of collections, cards, dashboards, segments, measures, and snippets. A card's query lives in its `dataset_query` field — native SQL under `dataset_query.native.query`, otherwise MBQL. Placement is by field (`collection_id`, `parent_id`), not file location.
- **metabase-database-metadata** — database connections and their table/field metadata.

The other upstream skills (embedding/SSO upgrades) are not relevant to migration and can be ignored.

## Step 0 — Connect (three data sources, in priority order)

Mirror the `hightouch` skill's source-priority pattern.

**Option 1 — metabase-cli / serialization export (preferred).** If the `mb` CLI is installed and configured against the instance, use it to export the workspace to YAML (the representation format above) and parse collections, dashboards, cards, databases, and permission groups from the export. Set `data_source: serialization`.

**Option 2 — Metabase REST API.** If `MB_HOST` and an API key (`MB_API_KEY`) or session token are available, enumerate via the REST API (stable, public endpoints):

| Object | Endpoint |
|---|---|
| Collections | `GET /api/collection`, `GET /api/collection/:id/items` |
| Cards / questions | `GET /api/card`, `GET /api/card/:id` (SQL in `dataset_query.native.query`; MBQL otherwise) |
| Dashboards | `GET /api/dashboard`, `GET /api/dashboard/:id` (dashcards reference card IDs) |
| Database connections | `GET /api/database`, `GET /api/database/:id` (engine + connection `details`) |
| Permission groups | `GET /api/permissions/group`, `GET /api/permissions/graph` |

Set `data_source: api`. Use read-only credentials for audit.

**Option 3 — client-supplied query inventory (CSV / export).** If neither the CLI nor API is reachable, use a client-supplied inventory of cards and their SQL. Set `data_source: csv`. This is the **required** input for `/wire:metabase-migration-generate` — that command cannot proceed on inference alone (see its spec).

If none of the three is available, stop and ask the client for one.

## Object hierarchy

```
Collection (folders; nest via parent_id)
  └─ Dashboard (grid of dashcards + filter parameters)
       └─ Card / question (dataset_query: native SQL or MBQL)
Database connection (engine + details — the pivot for a warehouse migration)
Permission group (data + collection permissions, via the permission graph)
```

## Migration-relevant notes

- **Card SQL dialect** lives in `dataset_query.native.query`. Native SQL cards carry source-warehouse dialect and need translation; MBQL cards are dialect-neutral and re-map to a new database connection without SQL rewriting.
- **Repointing the warehouse** is a change to the **database connection** (`PUT /api/database/:id` with the new `engine` and `details`), not a per-card edit. Cards follow the connection they reference.
- **Permission groups** are remapped against the new database connection and collections via the permission graph.
- **Decoy / non-prod testing** is done with a throwaway collection (test copies of cards) and a separate non-production database connection, so production cards, dashboards, and their consumers are never touched during validation.

## Replacing Metabase with Looker (bi_migration, experimental)

Wire's scripts read Metabase through the API with an API key (the `x-api-key` header) and convert deterministically, with no AI call:

```bash
source ~/.wire/metabase.env          # exports MB_HOST and MB_API_KEY; mode 600, outside the repo
python3 <plugin-root>/scripts/metabase_export.py api --out <snapshot> [--dashboard <id> ...]
python3 <plugin-root>/scripts/mb_to_lookml.py audit --snapshot <snapshot> --out <audit>
python3 <plugin-root>/scripts/mb_to_lookml.py convert --snapshot <snapshot> --out <batch> --model <m> \
  --connection <c> --database <id> [--include-root <folder>]
python3 <plugin-root>/scripts/mb_to_lookml.py lint <batch>
python3 <plugin-root>/scripts/metabase_export.py card-data --card <id> [--dashboard <id> --dashcard <id>] --out rows.csv
```

What to know before running them:

- **Sync first.** Query-builder questions convert from the table metadata Metabase keeps (types, primary and foreign keys). A table whose fields are not synced cannot convert. On a large warehouse the first sync can take hours; a dataset filter on the connection shortens it.
- **Queries are MBQL 5** from Metabase 50: `stages`, clauses `[op, {options}, ...]`, fields by id, a model's or earlier stage's columns by name, aggregations referenced by `lib/uuid`. Legacy MBQL is also read.
- **Native SQL and models** become views on their SQL: exact, not reusable. Simple single-table SQL is also lifted onto the table's view as a proposal (needs `sqlglot`).
- **Relative dates differ by one unit.** "Previous 12 months" is Looker `12 months ago for 12 months`; "including the current month" adds a unit (`13 months`). Checked on a live instance.
- **Dates come back as timestamps** (`2026-10-01T00:00:00Z`) where Looker returns `2026-10`: declare the grain in each parity contract.
- **One connection per LookML model.** Convert one Metabase database at a time (`--database`).
- The full rules are in `wire/bi_pairs/metabase_to_looker/`.

