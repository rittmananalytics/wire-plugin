---
description: Catalog all Fivetran connectors with MCP or CSV fallback
argument-hint: <release-folder>
---

# Catalog all Fivetran connectors with MCP or CSV fallback

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Catalog all ingestion sources for the migration — Fivetran connectors, RudderStack sources/destinations, Coupler.io dataflows, Segment sources, Airbyte connections, Kleene/Funnel marketing-data connections, or Amplitude exports — with MCP or API/CSV fallback
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: ingestion_audit` and `artifact_file_path: audit/ingestion_audit.md` before proceeding.

---

# Ingestion Audit — Generate

## Purpose

Catalogs every active ingestion source on the platform being migrated, capturing source type, destination schema, sync frequency, row volumes, and a migration readiness flag. The output is the primary input to the migration inventory and determines which sources need new destinations configured on the target platform.

Supports eight ingestion tool branches; each follows the same output shape but uses the tool's own concepts:

| `migration.ingestion_tool` value | Concept mapping | Skill |
|---|---|---|
| `fivetran` (default) | Connector → destination schema → tables | `fivetran` |
| `rudderstack` | Source → tracking plan → destinations | `rudderstack` |
| `coupler-io` | Dataflow (source integration + destination + schedule) | `coupler-io` |
| `segment` | Source → tracking plan → connected destinations | `segment` |
| `airbyte` | Workspace → source / destination / connection / sync (Airbyte API; Agent MCP optional) | `airbyte` |
| `kleene` | Connection (marketing/e-commerce source → destination + schedule) | n/a |
| `funnel` | Connector (ad-platform source → data destination + schedule) | n/a |
| `amplitude` | Export / data destination (event source → warehouse-bound export) | n/a |
| `other` | Connector → destination (CSV import only) | n/a |

**Coverage note**: every ingestion tool actually in use on the source platform must have a branch here — a source that isn't cataloged is invisible to migration planning, and any dbt models or dashboards that depend on it cannot pass equivalency testing (see `wire/specs/migration/equivalency/investigate.md` and `wire/specs/migration/equivalency/validate.md`) because their upstream data was never brought into scope. Whenever a new ingestion source is added to this audit (including a first-time run of one of the branches below), re-run `/wire:migration-inventory-generate $ARGUMENTS` afterwards so the dependency graph and effort estimate pick it up — the inventory does not auto-refresh from a re-run of this audit alone.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- Source platform confirmed in `status.md` under `migration.source_platform`
- Ingestion tool confirmed in `status.md` under `migration.ingestion_tool` (defaults to `fivetran` if absent)
- Per-tool access — one of:
  - **Fivetran**: MCP server or pre-exported `audit/fivetran_connectors_input.csv`
  - **RudderStack**: MCP server (`rudderstack` in `.claude/settings.json`, OAuth)
  - **Coupler.io**: MCP server (`coupler-io` in `.claude/settings.json`, personal access token)
  - **Segment**: Public API token (`SEGMENT_TOKEN` env var) — no MCP server available
  - **Airbyte**: Airbyte API token (`AIRBYTE_TOKEN` env var pointing at `api.airbyte.com/v1` or self-hosted endpoint). The Agent MCP at `mcp.airbyte.ai/mcp` is also available but designed for agent-driven data fetching rather than deployment inspection
  - **Kleene**: no MCP server exists in Wire's catalog today — API token (`KLEENE_API_TOKEN`) if the client has one, otherwise CSV import at `audit/kleene_connections_input.csv`
  - **Funnel**: no MCP server exists in Wire's catalog today — API token (`FUNNEL_API_TOKEN`) if the client has one, otherwise CSV import at `audit/funnel_connectors_input.csv`
  - **Amplitude**: the `amplitude` MCP server (`https://mcp.amplitude.com/mcp`) is configured in `.claude/settings.json`, but its tools are scoped to product analytics (charts, dashboards, experiments, taxonomy) and do not expose warehouse-export/destination inventory — treat it as unavailable for this audit. Use the Amplitude Export/Data Destinations API (`AMPLITUDE_API_KEY` / `AMPLITUDE_SECRET_KEY`) if configured, otherwise CSV import at `audit/amplitude_exports_input.csv`
  - **Other** (Stitch, Estuary, custom): CSV import only at `audit/ingestion_sources_input.csv`

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — source platform, ingestion tool, connectivity mode
- Tool-specific data source (MCP / API / CSV — see Step 2 branches)
- `.wire/releases/$ARGUMENTS/audit/fivetran_column_selections.csv` (Fivetran only, optional — column-level include/exclude rules)

## Workflow

### Step 1: Locate the release and ingestion tool

1. Resolve `.wire/releases/$ARGUMENTS/`. Confirm `status.md` has `release_type: platform_migration`. If not, stop — "This command only applies to platform_migration releases."
2. Read `migration.source_platform`, `migration.ingestion_tool`, and `migration.connectivity` from `status.md`. If `ingestion_tool` is absent, default to `fivetran` and note this in the audit output.
3. If the audit file already exists at `audit/ingestion_audit.md`, ask whether to re-generate (overwrite) or update (append new sources only).

### Step 2: Branch on ingestion_tool

#### Step 2a — `fivetran` (default)

Attempt to reach the Fivetran MCP server. Set a 10-second timeout.

**If Fivetran MCP responds**:
- Call `fivetran:list_connectors` to retrieve all connectors for the account
- Call `fivetran:get_connector_schema` for each connector to capture destination schema and table list
- Call `fivetran:get_connector_sync_status` for recent sync history and row volume estimates
- Proceed to Step 3 with MCP-sourced data

**If Fivetran MCP times out or is unavailable**:
- Check for `.wire/releases/$ARGUMENTS/audit/fivetran_connectors_input.csv`
- If CSV exists, read it and proceed to Step 3 with CSV-sourced data
- If CSV does not exist, output the following instructions and stop:

```
Fivetran MCP is not available and no input CSV was found.

To proceed, export your Fivetran connector list to CSV and save it at:
  .wire/releases/$ARGUMENTS/audit/fivetran_connectors_input.csv

Required CSV columns (see TEMPLATES/migration/fivetran_connectors_input.csv for the template):
  connector_id, connector_name, service_type, destination_schema, destination_table_prefix,
  sync_frequency_minutes, status, row_count_estimate, last_synced_at, include_in_migration,
  migration_notes

Then re-run: /wire:ingestion-audit-generate $ARGUMENTS
```

#### Step 2b — `rudderstack`

Attempt to reach the RudderStack MCP server at `mcp.rudderstack.com`. Activate the `rudderstack` skill for full details on the tool surface.

**If RudderStack MCP responds**:
- List all sources (web SDK / iOS / Android / server / cloud sources)
- For each source: capture type, tracking plan ID, library version, and connected destinations
- List all destinations (warehouse / marketing / analytics)
- For each destination: capture type, settings (names only, no secrets), and source filter rules
- List all tracking plans and the sources using each plan
- Proceed to Step 3 with MCP-sourced data; concept mapping: source→connector, destination_schema→tracking_plan, destination_table_prefix→connected_destinations

**If RudderStack MCP unavailable**: ask the user to authenticate via `/mcp auth rudderstack` (OAuth browser flow). If still unavailable, stop with instructions to run `npx -y mcp-remote https://mcp.rudderstack.com/mcp` manually.

#### Step 2c — `coupler-io`

Attempt to reach the Coupler.io MCP server at `app.coupler.io/mcp`. Activate the `coupler-io` skill for full details.

**If Coupler MCP responds**:
- Call `list-dataflows` to enumerate every dataflow in the workspace
- Per dataflow: capture source integration + credential, destination, schedule, and the dataset shape it produces (`get-dataflow`, `get-schema`)
- Classify each dataflow as ingestion (SaaS → warehouse) or reverse-ETL (warehouse → SaaS / BI). Both directions are in scope for the migration; reverse-ETL has different cutover risk.
- Proceed to Step 3 with MCP-sourced data; concept mapping: dataflow→connector, destination→destination_schema, dataset→destination_table_prefix

**If Coupler MCP unavailable**: ask the user to add the personal access token via `/mcp auth coupler-io`. If still unavailable, fall back to CSV import at `audit/coupler_dataflows_input.csv`.

#### Step 2d — `segment`

Segment has no MCP server; this branch uses the Segment Public API directly. Activate the `segment` skill for full details on auth and endpoints.

**Prerequisite**: `SEGMENT_TOKEN` env var set, and `SEGMENT_BASE` set to either `https://api.segmentapis.com` (US) or `https://eu1.api.segmentapis.com` (EU).

**Steps**:
- `GET /sources` — list all sources
- `GET /sources/{id}` — per source: type (analytics.js / iOS / Android / server / cloud), library version, tracking plan
- `GET /sources/{id}/connected-destinations` — per source: connected destinations
- `GET /destinations` and `GET /destinations/{id}` — destination inventory
- `GET /tracking-plans` and `GET /tracking-plans/{id}` — tracking plan schemas
- Proceed to Step 3 with API-sourced data; concept mapping: source→connector, destination_schema→tracking_plan, destination_table_prefix→connected_destinations

**Note**: most Segment migrations target RudderStack as the replacement CDP. The audit output should include a destination-by-destination "RudderStack equivalent" column where applicable.

**If `SEGMENT_TOKEN` is not set**: stop and output:
```
Set SEGMENT_TOKEN to a Public API token from your Segment workspace
(Settings → Access Management → Tokens). For EU workspaces, also set
SEGMENT_BASE=https://eu1.api.segmentapis.com. Then re-run.
```

#### Step 2e — `airbyte`

Use the Airbyte API directly (preferred for deployment inspection — the Agent MCP at `mcp.airbyte.ai/mcp` is designed for agent-driven data fetching, not workspace management). Activate the `airbyte` skill for full details.

**Prerequisite**: `AIRBYTE_TOKEN` env var set, `AIRBYTE_BASE` set to `https://api.airbyte.com/v1` (Airbyte Cloud) or the customer's self-hosted endpoint.

**Steps**:
- `GET /workspaces` — enumerate workspaces
- `GET /workspaces/{id}/sources` — per workspace: list sources (connector type + configuration without secrets)
- `GET /workspaces/{id}/destinations` — list destinations (warehouse destinations usually in scope)
- `GET /connections?workspaceId={id}` — source-to-destination mappings, sync mode, schedule, stream selection
- `GET /jobs?connectionId={id}&limit=10` — recent sync history + row volume estimates

Concept mapping: source→connector, connection→connector relationship, destination→destination_schema, connection prefix→destination_table_prefix, sync mode→migration_notes. See `wire/skills/airbyte/SKILL.md` for the full field-by-field mapping.

**If `AIRBYTE_TOKEN` is not set**: stop and output:
```
Set AIRBYTE_TOKEN to an API key from your Airbyte deployment
(Cloud: Settings → API Keys; self-hosted: per your auth integration).
Also set AIRBYTE_BASE to https://api.airbyte.com/v1 or your endpoint.
Then re-run.
```

#### Step 2f — `other` (Stitch, Estuary, custom)

CSV import only. Ask the user to export the source list to `.wire/releases/$ARGUMENTS/audit/ingestion_sources_input.csv` with columns:
`source_id, source_name, source_type, destination_schema, destination_table_prefix, sync_frequency_minutes, status, row_count_estimate, last_synced_at, include_in_migration, migration_notes`.

#### Step 2g — `kleene`

Kleene.ai (ELT for marketing/e-commerce data into a warehouse). **No MCP server for Kleene exists in Wire's catalog today** (`wire/specs/mcp.md`) — this branch is fallback-path only until one is added.

**If a `kleene` MCP server is later added to `.claude/settings.json`**: prefer it, following the same list-connections / get-connection-schema pattern used for Coupler.io in Step 2c.

**API/manual fallback (the practical path today)**: if `KLEENE_API_TOKEN` is set, use the Kleene REST API to enumerate connections (source integration, destination, schedule) and per-connection sync history. Confirm current endpoint paths against Kleene's own API documentation — none are hardcoded here.

**If no API token**: fall back to CSV import at `.wire/releases/$ARGUMENTS/audit/kleene_connections_input.csv` with columns:
`connection_id, connection_name, source_type, destination_schema, destination_table_prefix, sync_frequency_minutes, status, row_count_estimate, last_synced_at, include_in_migration, migration_notes`.

Concept mapping: connection→connector, destination→destination_schema, dataset→destination_table_prefix.

#### Step 2h — `funnel`

Funnel.io (consolidates ad-platform and marketing data into a warehouse or BI destination). **No MCP server for Funnel exists in Wire's catalog today** — this branch is fallback-path only until one is added.

**If a `funnel` MCP server is later added**: prefer it, following the same pattern as Step 2c/2g.

**API/manual fallback (the practical path today)**: if `FUNNEL_API_TOKEN` is set, use the Funnel API to list connectors and data destinations, and their schedules. Confirm current endpoint paths against Funnel's own API documentation — none are hardcoded here.

**If no API token**: fall back to CSV import at `.wire/releases/$ARGUMENTS/audit/funnel_connectors_input.csv` with columns:
`connector_id, connector_name, source_type, destination_schema, destination_table_prefix, sync_frequency_minutes, status, row_count_estimate, last_synced_at, include_in_migration, migration_notes`.

Concept mapping: connector→connector, data destination→destination_schema, dataset→destination_table_prefix.

#### Step 2i — `amplitude`

Amplitude as a data source syncing event data into the warehouse (via Amplitude's Export API / Data Destinations feature — distinct from Amplitude as a product-analytics tool). **The `amplitude` MCP server is configured in Wire's catalog (`https://mcp.amplitude.com/mcp`)**, but its documented tool surface is scoped to product analytics — charts, dashboards, experiments, session replay, instrumentation, taxonomy — not to enumerating warehouse-bound exports or destinations. Do not assume it exposes connector/sync inventory; treat it as unavailable for this audit unless/until it ships an Export or Data Destinations tool.

**API/manual fallback (the practical path today)**: if `AMPLITUDE_API_KEY` and `AMPLITUDE_SECRET_KEY` are set, use the Amplitude Export API / Data Destinations API to enumerate warehouse-bound exports (destination schema, table prefix, sync cadence). Confirm current endpoint paths against Amplitude's own API documentation — none are hardcoded here.

**If no API access**: fall back to CSV import at `.wire/releases/$ARGUMENTS/audit/amplitude_exports_input.csv` with columns:
`export_id, export_name, source_type, destination_schema, destination_table_prefix, sync_frequency_minutes, status, row_count_estimate, last_synced_at, include_in_migration, migration_notes`.

Concept mapping: export→connector, data destination→destination_schema, dataset→destination_table_prefix.

### Step 3: Build the connector catalog

For each connector, capture:

| Field | Source (MCP) | Source (CSV) |
|-------|-------------|-------------|
| `connector_id` | MCP response | CSV column |
| `connector_name` | MCP response | CSV column |
| `service_type` | MCP response | CSV column |
| `destination_schema` | MCP schema call | CSV column |
| `destination_table_prefix` | MCP schema call | CSV column |
| `sync_frequency_minutes` | MCP status | CSV column |
| `status` | MCP status | CSV column |
| `row_count_estimate` | MCP status (last sync rows) | CSV column |
| `last_synced_at` | MCP status | CSV column |
| `include_in_migration` | Derive from status (broken/paused → review) | CSV column |
| `migration_notes` | Auto-generated based on service type | CSV column |

Apply column-level selection rules from `fivetran_column_selections.csv` if present — flag any connectors that have column exclusions, as these require manual review during migration.

### Step 4: Classify migration complexity per connector

Assign each connector a complexity rating:

- **Low**: Standard SaaS source (Salesforce, HubSpot, Stripe, Google Analytics) with no column exclusions and active sync status
- **Medium**: Custom connector, paused connector, large row volumes (>100M rows), or column exclusions present
- **High**: Broken connector, unsupported service type on target platform, or schema conflicts with existing target objects

### Step 5: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`

Use the template at `TEMPLATES/migration/ingestion_audit.md`. Populate:
- Summary table of all connectors with fields from Step 3 and complexity rating from Step 4
- By-service-type breakdown (e.g., 12 Salesforce connectors, 3 custom, 1 broken)
- Migration flags: connectors marked `include_in_migration: false` listed separately with reason
- Column exclusions section if any apply
- Recommended migration order (Low complexity first, High last)

### Step 6: Update status

```yaml
artifacts:
  ingestion_audit:
    generate: complete
    file: audit/ingestion_audit.md
    generated_date: "{{TODAY}}"
    connector_count: N
    data_source: "fivetran_mcp" | "csv"
```

### Step 7: Output summary

Print: total connectors cataloged, breakdown by complexity, count flagged for exclusion, data source used (MCP or CSV), and next command:

```
/wire:ingestion-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/ingestion_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `ingestion_audit` as artifact_id, `Ingestion Audit` as artifact_name, and the `file` value from `artifacts.ingestion_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `ingestion_audit` as artifact, `generate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
