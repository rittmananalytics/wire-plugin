---
sidebar_position: 3
title: MCP Servers
---

# MCP Servers Reference

Much of what matters on an engagement happens outside the repository: decisions are taken on client calls, progress is tracked in Jira or Linear and documents are read and commented on in Confluence or Notion, and if Wire could see none of that its record would be a thinner thing. Wire integrates with five MCP (Model Context Protocol) servers to close that gap. All are optional, and Wire works without any of them, but when they are present they add meeting context to reviews, sync artifact status to issue trackers, replicate artifacts to document stores and provide library documentation lookups during development.

The servers use OAuth2 authentication managed by Claude Code's built-in auth system, which means that no credentials or tokens live in `settings.json`, only the server URL and transport type. We will look first at how servers are configured, and then take each of the five in turn.

---

## Configuring MCP servers

Where you add a server depends on how widely you want it available: add it to `.claude/settings.json` in your project root to scope it to that project, or to `~/.claude/settings.json` to make it available across all of your projects. Either way, the entry looks like this:

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "url",
      "url": "https://mcp.atlassian.com/v1/mcp"
    },
    "linear": {
      "type": "url",
      "url": "https://mcp.linear.app/sse"
    },
    "fathom": {
      "type": "url",
      "url": "https://your-fathom-mcp-server/mcp"
    },
    "context7": {
      "type": "url",
      "url": "https://mcp.context7.com/mcp"
    },
    "notion": {
      "type": "http",
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

Alternatively, you can use the Wire command interface:
```
/wire:mcp list              — see which servers are configured
/wire:mcp auth atlassian    — guided re-authentication walkthrough
```

### Adding a server via the CLI

```bash
# Streamable HTTP transport (Atlassian, Fathom, Context7); SSE for Linear
claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp

# HTTP transport (Notion)
claude mcp add --transport http-sse notion https://mcp.notion.com/mcp
```

Restart Claude Code after adding a new server, and on first use Claude Code prompts you to authorise via OAuth2 in your browser.

---

## Atlassian

**Key**: `atlassian`  
**URL**: `https://mcp.atlassian.com/v1/mcp`  
**Transport**: SSE  
**Provides**: Jira issue tracking and Confluence document search/publishing

### What Wire uses it for

If your client tracks work in Jira and reads documents in Confluence, this one server gives Wire both, so that the record in `.wire/` and the record the client sees stay in step without anyone copying between them.

**Issue tracking (Jira)**:
- `/wire:utils-jira-create`: creates one Jira Epic per engagement, one Task per artifact, one Sub-task per lifecycle step (generate/validate/review)
- Every generate/validate/review command syncs its completion status to the corresponding Sub-task
- `/wire:utils-jira-status-sync`: full reconciliation between local execution log and Jira (called by `/wire:status`)

**Document store (Confluence)**:
- `/wire:utils-docstore-setup`: creates a Confluence space or page hierarchy for the engagement
- `/wire:utils-docstore-sync`: publishes generated artifacts as Confluence pages after each generate command
- `/wire:utils-docstore-fetch`: retrieves Confluence comments and edits as review context during review commands
- `/wire:utils-atlassian-search`: searches Confluence for relevant prior work during review commands

### Setup

The Atlassian MCP server is Atlassian's own hosted server, and it requires an Atlassian Cloud account.

1. Add the server to `settings.json` with the URL above
2. On first use, Claude Code prompts for Atlassian OAuth2 authorisation
3. Grant access to Jira (read/write issues) and Confluence (read/write pages)
4. Run `/wire:new`; Wire auto-detects your Atlassian Cloud site and asks whether to create the Jira hierarchy

### Re-authentication

If you need to re-authenticate, remove the server and add it again:

```bash
claude mcp remove atlassian
claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp
```

Restart Claude Code to complete re-authentication.

---

## Linear

**Key**: `linear`  
**URL**: `https://mcp.linear.app/sse`  
**Transport**: SSE  
**Provides**: Linear issue tracking as an alternative or complement to Jira

### What Wire uses it for

Where the client's team works in Linear rather than Jira, or in both, this server gives you the same tracking in Linear's own hierarchy:

- `/wire:utils-linear-create`: creates one Linear Project per engagement, one Issue per artifact, one Sub-issue per lifecycle step
- Generate/validate/review commands sync to Linear in parallel with Jira when both are configured
- `/wire:utils-linear-status-sync`: full Linear reconciliation (called by `/wire:status`)

Wire applies a `wire-generated` label to all the issues it creates, so that you can filter your Linear board down to the Wire-managed ones.

### Setup

1. Add the server to `settings.json`
2. On first use, Claude Code prompts for Linear OAuth2 authorisation; grant `issues:write` scope
3. Run `/wire:utils-linear-create <release>` to set up the project hierarchy, or answer Yes when prompted during `/wire:new`

---

## Fathom

**Key**: `fathom`  
**URL**: Your Fathom MCP server URL (organisation-specific)  
**Transport**: SSE  
**Provides**: Meeting transcript retrieval for review commands

### What Wire uses it for

How often has a decision been taken on a call, agreed by everyone present and then never found its way into the document it affects? Every review command (`*-review`) calls `/wire:utils-meeting-context` internally, which searches Fathom for meetings in the last 30 days that mention the client name or engagement keywords, and the relevant transcript excerpts (decisions made, concerns raised, action items) are surfaced as review context alongside the artifact being reviewed.

This is the mechanism that connects Wire's "paper trail" to what was discussed and agreed in client calls.

### Setup

Fathom's MCP server URL is organisation-specific, so you will need to find yours in your Fathom account under Settings → Integrations → MCP; it follows the pattern `https://mcp.fathom.video/organisations/<org-id>/mcp`.

1. Copy the URL from your Fathom settings
2. Add it to `settings.json` replacing `https://your-fathom-mcp-server/mcp`
3. On first use, Claude Code prompts for Fathom OAuth2 authorisation

### Notes

- Transcripts take 15–30 minutes to appear after a call ends
- Only calls recorded in Fathom appear, and not all calls are auto-recorded
- If Fathom is unavailable, review commands proceed normally without meeting context

---

## Context7

**Key**: `context7`  
**URL**: `https://mcp.context7.com/mcp`  
**Transport**: HTTP  
**Provides**: Up-to-date library documentation during development

### What Wire uses it for

Anyone who has watched an assistant write code against a library version that no longer exists will recognise the problem Context7 solves: models trained on older data giving outdated API calls. It is used automatically during development commands, particularly `dbt-generate`, `pipeline-generate` and `semantic_layer-generate`, whenever Wire needs to look up current API documentation, check library version compatibility or verify a framework's conventions, and it fetches the current official documentation for the library in question before generating code that uses it.

### Setup

Context7 is a public MCP server with no authentication required, so you add the URL to `settings.json` and it works immediately.

```bash
claude mcp add --transport http-sse context7 https://mcp.context7.com/mcp
```

---

## Notion

**Key**: `notion`  
**URL**: `https://mcp.notion.com/mcp`  
**Transport**: HTTP  
**Provides**: Notion as a document store for client artifact review

### What Wire uses it for

Notion is the alternative to Confluence for the document store integration, and it suits clients who want to review documents without opening Claude Code themselves. When it is configured as the document store during `/wire:new` (or via `/wire:utils-docstore-setup`):

- Generated artifacts are published as Notion pages to a specified database after each generate command
- Reviewer comments and page edits made in Notion are surfaced as review context during review commands
- The Notion database link can be shared directly with clients for review without them needing Claude Code

### Setup

1. Create a Notion integration at `https://www.notion.so/profile/integrations`
2. Add the integration to the database you want Wire to write to (open the database → ··· → Connections → add your integration)
3. Add the server to `settings.json`
4. On first use, Claude Code prompts for Notion OAuth2 authorisation
5. Run `/wire:utils-docstore-setup <release>` and select Notion, providing the database ID when prompted

### Notes

- The database ID appears in the Notion page URL: `notion.so/<workspace>/<database-id>?v=...`
- Each artifact becomes a Notion page in the database with a `wire_artifact_id` property for tracking
- Mermaid diagrams in artifacts are rendered as images before publishing (Notion requires image format)
