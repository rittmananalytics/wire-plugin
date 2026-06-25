---
name: metabase
description: Connect to a Metabase instance and enumerate its collections, dashboards, cards/questions (with SQL), database connections, and permission groups. Activates for Metabase audits, reporting-layer migrations, or any work that reads or repoints Metabase content. Wraps the upstream metabase/agent-skills.
---

# Metabase

Connection details and object hierarchy for cataloguing and migrating a Metabase reporting layer. Used by `/wire:metabase-audit-*` and `/wire:metabase-migration-*`, and by any reporting-layer work that reads Metabase content.

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
