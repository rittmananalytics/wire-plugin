---
name: omni
description: Connect to an Omni Analytics instance and work with its semantic model, dashboards, content, and admin surfaces via the Omni CLI. Activates for Omni audits, reporting-layer migrations, semantic-layer work where the client's BI tool is Omni, or any work that reads or repoints Omni content. Wraps the official exploreomni/omni-agent-skills.
---

# Omni

Connection details and object hierarchy for cataloguing, modeling, and migrating an Omni Analytics reporting layer. Used by `/wire:omni-audit-*` and `/wire:omni-migration-*`, by `dashboards-generate`/`semantic_layer-generate` when `migration.reporting_tool: omni` (or the equivalent non-migration `reporting_tool` setting), and by any reporting-layer work that reads or edits Omni content.

## Imported upstream skills

This skill builds on the official **exploreomni/omni-agent-skills** (https://github.com/exploreomni/omni-agent-skills), published by Omni Analytics for exactly this purpose. Install once per machine or engagement:

```
/plugin marketplace add exploreomni/omni-agent-skills
/plugin install omni-analytics@omni-analytics
```

Or, for non-Claude-Code agents, via the shared skills.sh flow:

```
npx skills add exploreomni/omni-agent-skills
```

Nine upstream skills ship in the package. The ones relevant to Wire migration and dashboard work:

- **omni-model-explorer** — discover and inspect an existing Omni model: topics, views, fields, dimensions, measures, relationships. Use first, to understand what's already modeled before auditing or migrating.
- **omni-model-builder** — create and edit the Omni semantic model (views, topics, dimensions, measures, relationships, query views) via YAML through the Omni CLI. The Omni counterpart to LookML — this is what `semantic_layer-generate` drives when the target BI tool is Omni.
- **omni-content-explorer** — find, browse, and organise dashboards, workbooks, folders, and labels. The enumeration surface for `omni-audit-generate`.
- **omni-content-builder** — create, update, and manage documents/dashboards: tiles, visualisations, filters, controls, layouts, drafts and publishing. The build surface for `dashboards-generate`, and for applying `omni-migration-generate`'s pending raw-SQL tile edits at cutover (topic-backed tiles need no edits — they inherit the model's connection change automatically once its branch is promoted).
- **omni-query** — run queries against the semantic layer, interpret results, chain multi-step analysis. Used for equivalency comparison during migration validation.
- **omni-admin** — manage connections, users, groups, user attributes, permissions, and schedules. The surface for `omni-migration-generate`'s connection repoint and permission remap.

Two further skills exist upstream but aren't relevant to migration work: **omni-ai-optimizer** and **omni-ai-eval** (tuning and evaluating Omni's Blobby AI assistant — a post-migration enablement concern, not a migration one). **omni-embed** matters only if the client embeds Omni dashboards in an external application.

The `omni-integrations` sub-plugin (`omni-to-databricks-metric-views`, `omni-to-snowflake-semantic-view`) is relevant only when the target platform is Databricks or Snowflake and the client wants Omni's model expressed as native metric views/semantic views on that platform — check before installing it.

## Step 0 — Connect

The Omni CLI authenticates against a named profile:

```
omni config show
omni config use <profile-name>
```

If no profile exists, run `omni config init` (interactive) or pass `--base-url "$OMNI_BASE_URL" --token "$OMNI_API_TOKEN"` explicitly per command. Prefer the CLI profile flow — it's what the upstream skills assume and what their examples use.

If neither a configured profile nor the environment variables are available, stop and ask for one before proceeding — there is no CSV/inventory fallback for Omni the way there is for Metabase, since the CLI is the only supported access path upstream.

## Object hierarchy

```
Connection (warehouse/database connection — the pivot for a warehouse migration)
  └─ Model (topics, views, dimensions, measures, relationships — YAML, via omni-model-builder)
       └─ Topic (query surface exposed to content)
Folder (organises content)
  └─ Workbook / Document (dashboard)
       └─ Tile (chart/visualisation, backed by a topic query or raw SQL)
```

Unlike Metabase's card-level SQL, most Omni tiles query through the semantic model (a topic), not raw SQL directly — dialect-specific SQL mostly lives in the **model's** view definitions (base table SQL, derived table SQL) rather than scattered across every tile. A tile with a raw-SQL override is the exception, not the default, and needs the same source-dialect scan as a Metabase native-SQL card.

## Migration-relevant notes

- **The connection is the repoint pivot**, same as Metabase — add the target connection alongside the source, point the model at it, don't touch the source connection until cutover.
- **Model SQL, not tile SQL, is where dialect translation concentrates.** Audit the model's views (`omni-model-builder`) for source-platform SQL constructs first; only then scan tiles for raw-SQL overrides.
- **Content and model are versioned separately.** Omni supports branch-based model development (promote model changes independently of dashboard/content changes) — a migration can translate and validate the model on a branch before any dashboard is touched, which Metabase's card-level model doesn't offer.
- **Schema refresh** (`omni-admin`) must run against the new connection before the model can validate — a Snowflake→BigQuery migration needs a fresh schema refresh on the target connection, not a copy of the source connection's cached schema.
