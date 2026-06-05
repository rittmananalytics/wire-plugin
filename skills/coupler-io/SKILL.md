---
name: coupler-io
description: Skill for managing Coupler.io dataflows (ingestion and reverse ETL) via the Coupler.io MCP server. Activates when the user mentions Coupler.io, a Coupler dataflow, importing from a SaaS tool to a warehouse or vice versa, or asks questions about data already pulled into Coupler.
---

# Coupler.io MCP Skill

## On Activation

Before proceeding, append a one-line entry to `.wire/execution_log.md`:

```
| YYYY-MM-DD HH:MM | skill | coupler-io | activated | Coupler.io dataflow or query work triggered this skill |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first (see `specs/utils/execution_log.md`). If no `.wire/` directory exists in the current repo, skip this step.

---

## When This Skill Activates

- The user mentions **Coupler.io** or **Coupler MCP**.
- The user wants to **list, query, or refresh** existing Coupler dataflows.
- The user wants to **build a new dataflow** to import data from a SaaS source (HubSpot, Stripe, Google Ads, Klaviyo, Shopify, etc.) into a warehouse, BI tool, or spreadsheet.
- The user wants to **send data the other direction** (reverse ETL — push warehouse rows into Google Sheets, Looker Studio, Power BI, BigQuery destinations).
- The user asks an analytics question that's answerable from data already in their Coupler workspace.
- Wire's `ingestion_audit` is running against a client that uses Coupler.io for ingestion or reverse ETL.

---

## What the Coupler.io MCP Server Exposes

**Server URL**: `https://mcp.coupler.io/mcp/`
**Reference**: https://www.coupler.io/mcp and https://blog.coupler.io/how-to-use-coupler-mcp-server/
**Auth**: Personal Access Token, generated inside the Coupler.io web app (Settings → MCP / personal access tokens). Treat the token as a secret.

The MCP exposes two distinct surfaces — keep them separate when reasoning:

### Read surface — query data already in the user's workspace
- Discover datasets the user has already pulled into Coupler
- Inspect dataset schemas (typed columns + AI-readable descriptions)
- Run SQL against the canonical `data` table per dataset

### Write surface — configure the pipelines that produce that data
- List 400+ supported integrations (Stripe, Google Ads, HubSpot, Shopify, Klaviyo, etc.)
- Manage credentials for those integrations
- Build dataflows (source → optional transform → destination) with schedules
- Trigger dataflow runs
- Use templates (pre-built dataflow + dashboard recipes)

Treat training-era knowledge of "what Stripe events look like" or "how HubSpot exposes deals" as a **hint, never ground truth**. Always confirm against the live MCP tools — connector parameters change between versions.

---

## Setup

### Option A — via Claude Code `/mcp`

```
/mcp
```

Choose **Add server**, enter the URL and the personal access token obtained from the Coupler.io app.

### Option B — via the Wire plugin's bundled `.mcp.json`

The Wire plugin's `.mcp.json` includes the entry. After installing the plugin and running `/reload-plugins`, run `/mcp auth coupler-io` and paste the personal token.

---

## Coupler.io vocabulary

| Term | What it means |
|---|---|
| **Integration** | One of 400+ services Coupler connects to (Stripe, Google Ads, HubSpot, Shopify, …) on the source side; or destinations (Claude, ChatGPT, Google Sheets, BigQuery, Looker Studio, Power BI) |
| **Credential** | The user's authorised access to a specific integration; required before any source / destination can be built |
| **Dataflow** | A configured pipeline: source → optional transform → destination, with a refresh schedule |
| **Source / destination** | The two ends of a dataflow |
| **Dataset** | The table produced by a dataflow run; always queried as the `data` table |
| **Schema** | Typed column definitions plus an AI-readable description per dataset |
| **Template** | A pre-built recipe (dataflow + dashboard) keyed by source, metric, or category |
| **Skill** | A Coupler-side expert procedure exposed by the MCP, used to handle common end-to-end requests |

---

## Use within Wire workflows

### `ingestion_audit` for a `platform_migration` release where source = Coupler.io

When `migration.ingestion_tool: coupler-io` is set in `status.md`:

1. The ingestion_audit step queries the Coupler MCP for all dataflows.
2. Per dataflow: capture source integration + credential, destination, schedule, and the dataset shape it produces.
3. Classify dataflows into ingestion (SaaS → warehouse) and reverse ETL (warehouse → SaaS / BI). Both directions need migration planning but have different cutover risk.
4. Output the inventory in the standard `ingestion_audit.md` format.

### Ad-hoc analytics during any release

If the user asks an analytics question and a relevant Coupler dataset exists, prefer querying it via `query-objects` / `ask-question-about-accounts` over rebuilding the SQL by hand. Confirm the dataset's schema first.

### New ingestion or reverse ETL during `pipeline_only` or `full_platform` releases

Coupler is a good choice when:
- The integration is one of Coupler's 400+ supported sources and a custom Fivetran connector isn't justified.
- The destination is Google Sheets / Looker Studio / Power BI (reverse ETL) where Hightouch / Census might be heavier than needed.
- The team wants a no-code interface for non-engineering stakeholders to build their own dataflows alongside engineering-managed ones.

---

## What this skill does NOT do

- Does not store or transmit personal access tokens — those live in the user's MCP credential store.
- Does not configure destination services on the destination side (e.g. Coupler can write to a BigQuery table, but the warehouse and IAM are set up separately).
- Does not write Coupler dataflow transformation JavaScript — humans author transformations; the skill only configures the dataflow shell.
