---
name: rudderstack
description: Skill for managing RudderStack ingestion sources, destinations, tracking plans, and data catalog via the hosted RudderStack MCP server at mcp.rudderstack.com. Activates when the user mentions RudderStack, an event tracking plan, instrumentation, data catalog management, or RudderStack CLI / Terraform / Typer workflows.
---

# RudderStack MCP Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | rudderstack | activated | RudderStack work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

---

## When This Skill Activates

- The user mentions **RudderStack**, **rudder-cli**, **rudder-typer**, **tracking plan**, **data catalog**, or **event instrumentation** in the RudderStack sense.
- The user wants to **list, create, modify, or audit** RudderStack sources, destinations, tracking plans, or transformations.
- The user is **planning an event taxonomy** for a new mobile or web product.
- The user is **debugging schema validation errors** on RudderStack-tracked events.
- Wire's `ingestion_audit` is running against a client that uses RudderStack as their CDP / event ingestion tool.

---

## What the RudderStack MCP Server Exposes

**Server URL**: `https://mcp.rudderstack.com/mcp`
**Authoritative reference**: https://mcp.rudderstack.com/docs
**Transport**: HTTP via the `mcp-remote` proxy (npx)
**Auth**: OAuth — browser-based sign-in on first connect

The MCP server provides programmatic access to:

| Surface | Resources |
|---|---|
| Sources | List, create, configure event-collecting sources (web, mobile, server, cloud apps) |
| Destinations | List, create, configure data warehouses, marketing tools, analytics platforms |
| Tracking plans | Inspect and manage event schemas tied to specific sources |
| Data catalog | Events, properties, types, and their relationships |
| Transformations | RudderStack's in-flight event transformation projects |
| Data graphs | Entity modelling for Audiences (RudderStack Profiles) |

For full tool surface, run `/help` after connecting or refer to https://mcp.rudderstack.com/docs.

---

## Setup

### Option A — via Claude Code `/mcp` (recommended)

```
/mcp
```

Choose **Add server**, enter:
- Name: `rudderstack`
- Transport: `stdio` (via mcp-remote)
- Command: `npx -y mcp-remote https://mcp.rudderstack.com/mcp`

### Option B — via the Wire plugin's bundled `.mcp.json`

The Wire plugin's `.mcp.json` already includes the entry. After installing the plugin and running `/reload-plugins`, run `/mcp` and authenticate to RudderStack via OAuth in the browser.

### Prerequisite

`npx` must be on PATH. If `which npx` returns nothing, install Node.js from https://nodejs.org/.

---

## Authentication

On first connect, RudderStack opens the OAuth flow in your browser. Sign in to your RudderStack workspace. Subsequent calls are authenticated by the token stored in your MCP credential store — no per-call header setup is needed.

---

## Use within Wire workflows

### `ingestion_audit` for a `platform_migration` release where source = RudderStack

When `migration.ingestion_tool: rudderstack` is set in `status.md`:

1. The ingestion_audit step queries the RudderStack MCP for the full source + destination inventory.
2. Per source: capture source type (web SDK / iOS SDK / Android SDK / server SDK / cloud source), tracking plan ID, event volume tier, and the destinations it routes to.
3. Per destination: capture destination type, configuration, and whether the destination is in scope for the migration (warehouse destinations usually are; marketing destinations may not be).
4. Per tracking plan: capture event schemas, the source(s) using the plan, and any validation failures.

The audit feeds `migration_inventory` and informs `migration_strategy`. For BigQuery/Snowflake migrations, the warehouse destination is the migration target.

### `pipeline_design` for new builds where RudderStack is the chosen ingestion tool

When a new release plans to use RudderStack:

1. Use the **rudder-instrumentation-planning** approach (from the rudder-agent-skills `rudder-core` plugin): design event taxonomy from scratch before any SDK code is written.
2. Generate the tracking plan first, source SDKs second.
3. Wire's `pipeline-generate` for the source SDKs should follow RudderStack's source-specific patterns (web: rudder-sdk-js; mobile: rudder-sdk-ios / rudder-sdk-android; server: language-specific SDK).

---

## RudderStack core concepts (for non-experts)

| Term | What it means |
|---|---|
| **Source** | A point where events enter RudderStack — web SDK, mobile SDK, server SDK, or cloud source (event-based pull from a SaaS) |
| **Destination** | A target where events are routed — warehouse (BigQuery, Snowflake, Redshift), marketing tool (Braze, Iterable), analytics tool (Mixpanel, Amplitude) |
| **Tracking plan** | A schema definition for the events a source is allowed to emit — used to validate incoming events |
| **Transformation** | A piece of JS run on events in flight, before they reach destinations |
| **Data catalog** | Centralised inventory of events, properties, and types across an account |
| **Data graph** | Entity-relationship modelling for Audiences (Profile) |

---

## Recommended companion skills

This skill covers MCP-driven workflows. For programmatic CLI work, install the companion plugin from RudderStack: [`rudderlabs/rudder-agent-skills`](https://github.com/rudderlabs/rudder-agent-skills) — provides skills for the rudder CLI, Terraform provider, and rudder-typer code generation.

---

## What this skill does NOT do

- Does not configure SDK keys or write tracking code inside client apps — that's an engineering task following the tracking plan.
- Does not write transformations (JavaScript) — humans review and author those.
- Does not decide whether RudderStack is the right CDP for the engagement — that's a discovery / requirements decision.
