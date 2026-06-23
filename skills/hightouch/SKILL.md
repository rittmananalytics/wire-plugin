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

### Step 0b: Git Source (Alternative)

If the client uses Hightouch's Git sync feature, the full workspace configuration — sources, models, syncs, and destinations — is stored as YAML files in a GitHub repository. This is a valid alternative to the API for the structural parts of the audit.

**When to use this path**: API token is unavailable or the client prefers not to issue one; the client's Hightouch workspace has Git sync configured.

**How to obtain the files**: Ask the client to share access to their Hightouch config repo, or confirm it is already accessible under the delivery project's GitHub access. Then copy the Hightouch config directory into the delivery repo:

```bash
# From within the delivery repo
git clone --depth 1 <hightouch-config-repo-url> /tmp/ht_config
cp -r /tmp/ht_config/<config-dir> .wire/releases/$PROJECT_ID/audit/hightouch_git/
```

**Expected directory structure** (typical — confirm against the client's actual repo):

```
audit/hightouch_git/
  sources/
    <source-name>.yaml        # warehouse connection config
  models/
    <model-name>.yaml         # SQL or dbt model reference + primary key
  syncs/
    <sync-name>.yaml          # destination, mode, schedule, field mappings
  destinations/
    <destination-name>.yaml   # SaaS destination type and metadata
```

**Typical YAML shapes**:

```yaml
# models/<name>.yaml
id: "model-456"
name: "Contacts Model"
source_id: "source-001"
primary_key: "id"
query_type: raw_sql          # or: dbt_model, table
sql: |
  SELECT id, email, ...
  FROM prod.contacts
```

```yaml
# syncs/<name>.yaml
id: "sync-123"
name: "Contact Sync to Salesforce"
model_id: "model-456"
destination_id: "dest-789"
sync_mode: upsert
schedule:
  type: interval             # or: cron, triggered
  interval: 3600
configuration:
  # field mappings — structure varies by destination type
```

**Fields available from Git vs API**:

| Field | Git | API |
|---|---|---|
| sync id, name, model, destination | Yes | Yes |
| model SQL (full) | Yes | Yes (200-char truncated via API) |
| model query type | Yes | Yes |
| primary key | Yes | Yes |
| sync mode, schedule, field mappings | Yes | Yes |
| source type (warehouse platform) | Yes | Yes |
| destination type | Yes | Yes |
| `status` (active / disabled / interrupted) | **No** | Yes |
| `last_run_at`, `last_run_rows` | **No** | Yes |
| run history | **No** | Yes |
| Lightning engine flag | Partial (may appear in sync config) | Inferred |

Runtime state — sync status, row volumes, last run timestamps — is not stored in Git. When auditing from Git files, mark those fields as `n/a (git source)` in the audit report and note that decommission decisions and volume estimates require manual input from the client.

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

**Prefer additive PR-gated syncs in the existing GitHub-Sync repo.** GitHub Sync is configured per workspace and carries models and syncs but **not destinations** — so spinning up a separate workspace would force re-creating and re-authenticating every destination connection. The default migration topology is therefore additive: branch the existing Hightouch config repo, add a new batch of target-warehouse syncs alongside the existing source-warehouse syncs, reuse the existing destination definitions in place, and stage every change as a pull request for the client to review and merge. The PR gate is the safety control — RA does not enable/disable syncs or mutate the workspace directly. Cutover is two client-merged PRs: one disables every source-origin sync, one enables every target-origin sync. A **parallel workspace** is an alternative only when destinations can be re-authenticated without operational cost; an **in-place API re-point** (PATCH the existing syncs' `sourceId`) is the last-resort alternative when neither GitHub Sync nor a second workspace is available.

**Validate by preview, against decoy destinations.** There is no need to point a sync at a production destination to validate a migration — and it is unsafe to, since a sync writes to whatever destination it carries. Reusing destinations in place means "disabled" is not enough protection; instead, every new test sync carries a **decoy destination ID** of the same destination type (a decoy Google Sheet for a Google Sheets destination, etc.), written through a scoped credential that can reach the decoy targets only and has no grant on production destinations. Production destination IDs stay absent from the test syncs until the cutover PR swaps them back in. Validate with Hightouch's sync previews and record-level inspection. Compare model outputs (row counts, primary-key uniqueness, aggregates, samples) and audience sizes against a **frozen source baseline** (not moving production, which keeps ingesting and rebuilding). Only enable target syncs against production destinations at cutover, after business sign-off, via the client-merged PR.

**Review sync-level logic, not just model output.** A matching model output does not prove a matching sync. Transformation logic also lives on the sync — field mappings, computed fields, sync filters, match rules and identity resolution, and audience inclusion/exclusion. Review and test these per sync; they are a common source of silent divergence.

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
