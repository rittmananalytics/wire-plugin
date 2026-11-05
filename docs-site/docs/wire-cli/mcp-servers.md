---
sidebar_position: 4
title: MCP servers
---

# MCP servers

:::caution Experimental
4.6.0. Context7 has been run live through the CLI. Fathom, Jira and the warehouse servers have not yet.
:::

MCP servers give Wire's steps access to other tools: Jira and Confluence, meeting transcripts, library documentation, the warehouse. The Claude Code plugin configures a fixed set for every user. In the CLI, each engagement chooses its servers once, and each person signs in once.

## Where the list is kept

The servers an engagement uses are listed in `.wire/engagement/mcp_servers.yml`, committed with the repository. The file holds server names and URLs only. Sign-ins stay with each person, in the standalone agent's own store (`~/.wire/agent/`).

## Commands

| Command | What it does |
|---|---|
| `wire mcp list` | Wire's catalogue, what this engagement has selected, and your sign-in state for each |
| `wire mcp add atlassian` | Adds a server from the catalogue |
| `wire mcp add fathom https://...` | Adds a server with your organisation's URL |
| `wire mcp login atlassian` | Signs you in once; a browser opens |
| `wire mcp check 02-data-foundation` | Lists the servers this release's commands use, and which are missing |
| `wire mcp remove notion` | Removes a server from the engagement |

## The catalogue

`wire mcp list` shows the servers Wire knows:

```
MCP servers (catalogue: 8; this engagement: 0, in .wire/engagement/mcp_servers.yml)
  airbyte      not selected                   https://mcp.airbyte.ai/mcp
               Airbyte connectors (ingestion audits and migrations)
  amplitude    not selected                   https://mcp.amplitude.com/mcp
               Amplitude product analytics
  atlassian    not selected                   https://mcp.atlassian.com/v1/mcp
               Jira issue tracking; Confluence document store and search
  context7     not selected                   https://mcp.context7.com/mcp
               Library documentation during development
  coupler-io   not selected                   https://mcp.coupler.io/mcp/
               Coupler.io data flows
  fathom       not selected (needs your organisation's URL) https://your-fathom-mcp-server/mcp
               Meeting transcripts for review commands
  linear       not selected                   https://mcp.linear.app/mcp
               Linear issue tracking (alternative or complement to Jira)
  notion       not selected                   https://mcp.notion.com/mcp
               Notion document store for client review
Add one: wire mcp add <server> [url]   Sign in: wire mcp login <server>
```

Warehouse servers (BigQuery, Snowflake) and Fivetran are not in the catalogue. Add them with their URL.

## Setting up an engagement

```
wire mcp add atlassian
wire mcp add context7
wire mcp add fathom https://fathom-mcp.example.com/mcp
git add .wire/engagement/mcp_servers.yml && git commit -m "Wire: MCP servers for this engagement"
wire mcp login atlassian
wire mcp login fathom
```

The next person to work on the engagement pulls the file and runs only the `wire mcp login` lines.

## What a run gets

Every run (`wire run`, a typed command, `wire exec`, the session) is given the selected servers:

| Harness | How the servers are passed |
|---|---|
| `codex` | As `-c mcp_servers.<server>.url=...` on each run, so they work even in a folder Codex has not been told to trust |
| `claude` | As `--mcp-config`, with the servers' tools allowed |

A server you have not signed in to is still passed, with a note. Some servers answer without a sign-in (Context7). One that needs a sign-in fails at start-up with one error line, and the run continues without it.

Tool names match Claude Code's (`mcp__<server>__<tool>`), so a Wire spec that names a tool works on both harnesses when the server name is the same.

## Wire's own tools

Every run also gets a `wire` MCP server that the CLI starts itself, with four tools:

| Tool | What it returns |
|---|---|
| `wire_status` | A release's state in a few lines |
| `wire_gate` | Whether the precondition gate allows a command, and why |
| `wire_lint` | The conventions check on files |
| `dbt` | dbt with a short result: counts by status and each failure, not dbt's full log |

Under `warehouse_spend: none` in a release, the `dbt` tool refuses commands that query the warehouse, and in a lane the hooks refuse BigQuery `execute_sql` and Snowflake `sql_exec`. `WIRE_TOOLS=false` leaves Wire's server out.
