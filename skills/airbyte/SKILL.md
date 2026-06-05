---
name: airbyte
description: Skill for managing Airbyte connections and data ingestion via the Airbyte Agent MCP server at mcp.airbyte.ai. Activates when the user mentions Airbyte, an Airbyte connection, Airbyte source / destination, or wants to audit / build / migrate an Airbyte deployment. Distinguishes between the hosted Agent MCP (for AI agents using connectors) and managing an existing Airbyte Cloud / OSS workspace.
---

# Airbyte Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | airbyte | activated | Airbyte work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

---

## When This Skill Activates

- The user mentions **Airbyte**, an Airbyte **source / destination / connection**, or wants to **list, create, audit, or migrate** an Airbyte deployment.
- The user is **planning a new ingestion pipeline** using Airbyte's open-source connector catalogue.
- The user is **building an AI agent** that needs to access SaaS data through Airbyte connectors (the upstream `airbyte-agent-sdk` use case).
- Wire's `ingestion_audit` is running against a client that uses Airbyte (Cloud or self-hosted OSS) for data ingestion.

---

## Two surfaces — keep them separate

Airbyte exposes two distinct programmatic surfaces. Confuse them and you'll generate the wrong code.

### 1. Agent MCP server — `mcp.airbyte.ai/mcp`

**For AI agents that USE Airbyte connectors** as a data-fetch layer (e.g. a CRM agent that fetches HubSpot contacts via Airbyte's HubSpot connector). The agent doesn't care about how Airbyte is deployed; it just wants typed, paginated, authenticated access to SaaS data.

- **URL**: `https://mcp.airbyte.ai/mcp`
- **Transport**: Streamable HTTP
- **Auth**: OAuth 2.0 — two layers: first to Airbyte itself, then per-connector to each third-party service (HubSpot, Salesforce, Stripe, etc.)
- **Surface**: connector-scoped entity actions (`list`, `get`, `search`, `create`, `update`) on connector-specific entities (contacts, deals, invoices, etc.). Tool names are connector-specific and discovered at runtime.
- **Documentation**: https://docs.airbyte.com/ai-agents/interfaces/mcp

### 2. Airbyte API — `api.airbyte.com`

**For managing an Airbyte deployment** — the workspace, its connections, sources, destinations, syncs, and sync history. Used by Wire's `ingestion_audit` when a customer's existing Airbyte deployment is in scope for a platform_migration release.

- **Base URL**: `https://api.airbyte.com/v1` (Airbyte Cloud) or the customer's self-hosted endpoint
- **Auth**: Bearer token (API key) generated in the Airbyte Cloud UI under Settings → API Keys, or via OAuth 2.0 client credentials
- **Surface**: full management surface — `GET /sources`, `GET /destinations`, `GET /connections`, `GET /jobs`, `POST /connections/sync`, etc.
- **Documentation**: https://reference.airbyte.com/reference/start

When in doubt, ask: *"Is the goal to inspect or change Airbyte's own configuration?"* If yes → use the Airbyte API. *"Is the goal to fetch some SaaS data through Airbyte for downstream agent use?"* If yes → use the Agent MCP.

---

## Setup — Agent MCP (default; pre-registered in Wire plugin)

The Wire plugin's `.mcp.json` already includes the entry. After installing the plugin and running `/reload-plugins`, run `/mcp` and authenticate via the OAuth flow that opens in the browser.

**Manual install (outside the Wire plugin)**:

```bash
claude mcp add --transport http airbyte-agent https://mcp.airbyte.ai/mcp
```

On first invocation, OAuth opens in the browser. Sign in to your Airbyte account, then approve consent for each third-party connector you add.

---

## Setup — Airbyte API (for ingestion_audit work)

Used directly via `WebFetch` or curl. No MCP wrapper.

```bash
export AIRBYTE_TOKEN='your-api-key'
export AIRBYTE_BASE='https://api.airbyte.com/v1'   # or self-hosted endpoint

curl -s -H "Authorization: Bearer $AIRBYTE_TOKEN" "$AIRBYTE_BASE/workspaces" | head -20
```

Get the API key from the Airbyte Cloud UI → Settings → API Keys. For self-hosted OSS, generate an API token via the application's auth integration.

---

## Use within Wire workflows

### `ingestion_audit` for a `platform_migration` release where source = Airbyte

When `migration.ingestion_tool: airbyte` is set in `status.md`:

1. **Prefer the Airbyte API over the Agent MCP** for this work. The MCP is designed for agent-driven data fetching, not deployment inspection — its connector list is hosted by Airbyte and may differ from a customer's actual configured connections.
2. Iterate `GET /workspaces` → `GET /workspaces/{id}/sources` to enumerate sources.
3. Per source: capture connector type (e.g. `hubspot`, `stripe`, `salesforce`), configuration (without secrets), and sync schedule.
4. `GET /workspaces/{id}/destinations` for destinations; usually warehouse destinations are in scope.
5. `GET /connections?workspaceId=...` for source-to-destination mappings + their sync mode (full refresh / incremental append / incremental dedup history).
6. `GET /jobs?connectionId=...&limit=10` for recent sync history and row volume estimates.

Output follows the standard `ingestion_audit.md` format. Concept mapping for Airbyte:

| Wire audit field | Airbyte concept |
|---|---|
| `connector_id` | Source ID |
| `connector_name` | Source name (user-set) |
| `service_type` | Source `sourceDefinitionId` → connector name (e.g. `airbyte/source-hubspot`) |
| `destination_schema` | Connection's `namespaceDefinition` + `namespaceFormat` |
| `destination_table_prefix` | Connection's `prefix` field |
| `sync_frequency_minutes` | Connection's `schedule.basicSchedule` |
| `status` | Connection's `status` (active / inactive) |
| `row_count_estimate` | Sum of recent job row counts |
| `last_synced_at` | Most recent job `endedAt` |
| `include_in_migration` | Derive from status + sync activity |

### New ingestion build using Airbyte

When a `pipeline_only` or `full_platform` release picks Airbyte as the ingestion tool:

1. Use Airbyte Cloud where possible — operational overhead of self-hosting OSS is substantial.
2. Standard connectors first; only build a custom connector if no Airbyte-maintained option exists.
3. For each source-to-destination connection, document: sync mode (full refresh vs incremental), schedule, stream selection (which tables/streams are in scope), and primary keys.
4. Wire's `pipeline-generate` for Airbyte writes Terraform (using the `airbyte/airbyte` provider) where IaC is the standard, or Airbyte API calls in Python for one-shot setups.

### Agent-building (the upstream `airbyte-agent-sdk` use case)

If the user is building an agent that uses Airbyte connectors to fetch SaaS data, point them at the upstream Airbyte skills:

```bash
/plugin install airbyte-agent-sdk@airbyte-agent-sdk
```

Or via the cross-agent installer:

```bash
npx skills add airbytehq/airbyte-agent-sdk
```

The upstream plugin ships four skills:

- `bootstrapping-agent` — wiring a single Airbyte connector into a PydanticAI or Claude SDK agent
- `building-multi-connector-agent` — scaffolding agents with multiple connectors
- `discovering-connectors` — enumerating available connectors and entities
- `airbyte-sdk-reference` — SDK API reference (`configure()`, `connect()`, `Workspace`)

Wire's `airbyte` skill covers the **inspection / management / migration-audit** surface; the upstream plugin covers the **agent-building** surface. Both can be installed side by side.

---

## Airbyte core concepts

| Term | What it means |
|---|---|
| **Workspace** | Top-level Airbyte tenant; sources / destinations / connections are workspace-scoped |
| **Source** | A configured instance of a connector pulling data from a system (e.g. "Production HubSpot") |
| **Destination** | A configured instance of a connector writing data to a system (e.g. "Snowflake Analytics") |
| **Connection** | A source → destination mapping with a sync schedule, namespace strategy, and stream selection |
| **Stream** | A logical table inside a source (e.g. `contacts`, `deals`) |
| **Sync mode** | How data is moved per stream: full refresh / incremental append / incremental dedup history / CDC |
| **Connector** | The reusable code that knows how to talk to a specific source or destination system; maintained by Airbyte or the community |
| **Job** | A single execution of a connection's sync; jobs have status, duration, row counts |

---

## Tokens, secrets, and audit hygiene

- **Never** commit Airbyte API keys to git, Wire artifacts, or status.md.
- For automation, store the token in a CI secret (GitHub Actions, GCP Secret Manager, etc.) referenced by name.
- The Wire `ingestion_audit.md` output captures source / destination **names** and connector **types**, not credentials.

---

## What this skill does NOT do

- Does not configure third-party-side OAuth consent screens for connectors — those are handled in the source system's developer console.
- Does not write custom Airbyte connectors — that's a substantial engineering effort following Airbyte's CDK; out of Wire's scope.
- Does not decide whether Airbyte is the right ingestion tool — that's a discovery / requirements decision.
- Does not store the API key. The token lives in the user's shell or secret store.
