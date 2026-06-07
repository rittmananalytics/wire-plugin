---
name: hightouch
description: Skill for auditing, migrating, and working with Hightouch reverse ETL syncs. Auto-activates when cataloging Hightouch syncs, migrating warehouse targets for an existing Hightouch deployment, or assessing the impact of a source warehouse migration on downstream Hightouch activation. Covers the Hightouch REST API, all sync types (object, event, audience, journey), the Lightning sync engine, and Customer Studio.
---

# Hightouch Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | hightouch | activated | Hightouch reverse ETL work triggered this skill |
```

## Purpose

Hightouch is a reverse ETL platform: it reads data from the warehouse and syncs it outward to SaaS destinations (CRMs, ad platforms, email tools, etc.). In a warehouse migration, every Hightouch sync that points at the source warehouse needs to be re-pointed at the target — or rebuilt from scratch if the underlying model queries use source-platform SQL that cannot run unchanged.

This skill governs how we connect to Hightouch, enumerate the sync estate, assess migration impact, and plan the cutover.

## When This Skill Activates

- User mentions Hightouch, "reverse ETL", or "data activation"
- A `platform_migration` release has `migration.reverse_etl_tool: hightouch` in `status.md`
- `/wire:reverse-etl-audit-generate` is invoked
- User asks about syncs, models, or destinations in a reverse ETL context

---

## Instructions

### Step 0: API Connection

Hightouch uses a REST API. No MCP server is available — all data retrieval is via direct HTTP calls using the Bash tool.

**Auth**: Bearer token. Set `HIGHTOUCH_TOKEN` as an environment variable.
**Base URL**: `https://api.hightouch.com/api/v1`

Check connectivity before starting:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  "https://api.hightouch.com/api/v1/sources"
```

Expected: `200`. If `401`, the token is invalid. If the variable is unset, stop and output:

```
Set HIGHTOUCH_TOKEN to an API key from your Hightouch workspace
(Settings → API keys → Create API key, select Read-only scope).
Then re-run.
```

---

### Step 1: Object Hierarchy

A Hightouch workspace contains:

```
Source (warehouse connection)
  └── Model (SQL query or dbt model reference, requires a primary key)
        └── Sync (model → destination, with mode + mapping + schedule)
              └── Destination (SaaS tool: Salesforce, HubSpot, Marketo, Google Ads, …)
```

For Customer Studio deployments:

```
Source
  └── Schema (Parent model + related models + events — feeds Customer Studio)
        └── Audience (filtered segment built by marketers)
              └── Sync (audience → destination)
                    └── Journey (multi-step branching across syncs)
```

Know which product tier the engagement uses before auditing: core reverse ETL, Customer Studio, or both.

---

### Step 2: Enumerate the Workspace

Run these calls in sequence. For each, page through results using `?offset=N&limit=100` until the returned array is empty.

**List sources (warehouse connections):**
```bash
curl -s -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  "https://api.hightouch.com/api/v1/sources?limit=100" | jq '.data[]'
```

Capture per source: `id`, `name`, `type` (snowflake / bigquery / databricks / redshift), `slug`, `createdAt`.

**List models:**
```bash
curl -s -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  "https://api.hightouch.com/api/v1/models?limit=100" | jq '.data[]'
```

Capture per model: `id`, `name`, `sourceId`, `primaryKey`, `queryType` (rawSql / dbtModel / table / customSql), `sql` (or `dbtModelName`), `createdAt`, `updatedAt`.

**List destinations:**
```bash
curl -s -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  "https://api.hightouch.com/api/v1/destinations?limit=100" | jq '.data[]'
```

Capture per destination: `id`, `name`, `type` (salesforce / hubspot / marketo / google_ads / etc.), `slug`.

**List syncs:**
```bash
curl -s -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  "https://api.hightouch.com/api/v1/syncs?limit=100" | jq '.data[]'
```

Capture per sync: `id`, `slug`, `modelId`, `destinationId`, `status` (active / disabled / interrupted / pending), `schedule` (type, cron/interval value), `syncMode` (upsert / update / insert / archive / mirror), `configuration` (field mappings — names only, no secrets), `createdAt`, `updatedAt`, `lastRunAt`, `lastSuccessAt`.

**Get recent run history per sync** (sample the 5 most recent):
```bash
curl -s -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  "https://api.hightouch.com/api/v1/sync-runs?syncId={SYNC_ID}&limit=5" | jq '.data[]'
```

Capture: `status`, `plannedRows`, `successfulRows`, `failedRows`, `startedAt`, `completedAt`. Use `plannedRows` as the row volume estimate.

---

### Step 3: Classify Each Sync

For each sync, assess migration impact:

**Source dependency** — which warehouse objects does the model query?

For `queryType: rawSql` models: parse the SQL to extract referenced tables/views. These are the warehouse objects that must exist on the target platform before the sync can be re-pointed.

For `queryType: dbtModel` models: note the dbt model name. It will be included in the dbt audit; the dbt_audit feature tags drive complexity here too.

**Sync engine** — Lightning or Basic?

Lightning syncs require `hightouch_planner` and `hightouch_audit` schemas in the warehouse. On migration, these schemas must be recreated on the target before Lightning syncs can be enabled.

Check by inspecting `configuration.syncEngineType` or asking the user — the API does not always surface this field directly.

**Migration complexity:**

| Rating | Conditions |
|---|---|
| Low | rawSql model, no Snowflake-specific functions, destination type has native re-point capability, sync is active |
| Medium | dbtModel reference (depends on dbt migration), or rawSql with dialect-specific functions, or interrupted/pending status |
| High | Customer Studio audience or Journey, Lightning sync engine requiring schema recreation, rawSql with complex CTEs or Snowflake-native functions, sync volume >10M rows/run |

**Migration approach:**

- `repoint` — re-point the existing sync to the target warehouse source connection; model SQL is portable
- `rewrite_model` — the model SQL uses source-platform dialect that must be translated before re-pointing
- `rebuild` — Customer Studio audience or Journey that must be rebuilt in the target-warehouse context (schema, traits, related models all need review)
- `decommission` — sync is disabled, has no successful runs in >90 days, or the destination is no longer in use

---

### Step 4: Key Migration Considerations

**Source re-point order matters.** Hightouch has one source connection per workspace (or multiple). If the migration cuts the source over in phases, syncs that query tables not yet migrated will fail. The sync cutover order must respect the warehouse migration phases.

**Lightning schema recreation.** If any syncs use the Lightning engine, the target warehouse must have `hightouch_planner` and `hightouch_audit` schemas provisioned before syncs are enabled. Hightouch provisions them automatically on first sync run, but they must exist under the new service account's permissions.

**Primary key portability.** Hightouch stringifies primary keys for CDC. If the target warehouse changes the PK data type (e.g., NUMERIC → INT64), Hightouch CDC state is invalidated — the sync must do a full refresh on first run to rebuild the state table. Flag any syncs where the source model PK type will change.

**dbt model references.** If the model uses `queryType: dbtModel`, it references a dbt model by name. The dbt model must exist and be built in the target warehouse before the sync can run. These syncs cannot be re-pointed until the dbt migration batch containing that model is complete.

**Destination credentials are not stored in Hightouch exports.** Destination configs contain connection type and metadata only — API keys, OAuth tokens, and service account credentials are stored in Hightouch's secrets vault and are not accessible via the API. The audit captures destination type and name only. Credential rotation is an operational step managed outside this audit.

---

### Step 5: Read-Only by Default

Never modify any Hightouch object (sync enable/disable, schedule change, source re-point) without:
1. Presenting the full change to the user
2. Stating what it will do and what runs will be affected
3. Getting explicit approval
4. Executing via the appropriate API call (`PATCH /api/v1/syncs/{id}` etc.)

The audit phase is purely read-only.
