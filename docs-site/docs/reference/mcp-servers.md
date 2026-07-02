---
sidebar_position: 3
title: MCP Servers
---

# MCP Servers Reference

Wire integrates with five MCP servers. All are optional — Wire works without any of them. When present, they add meeting context to reviews, sync artifact status to issue trackers, replicate artifacts to document stores, and provide library documentation lookups during development.

MCP servers use OAuth2 authentication managed by Claude Code's built-in auth system. No credentials or tokens live in `settings.json` — only the server URL and transport type.

---

## Configuring MCP servers

Add servers to `.claude/settings.json` in your project root (project-scoped) or `~/.claude/settings.json` (all projects):

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

Or use the Wire command interface:
```
/wire:mcp list              — see which servers are configured
/wire:mcp auth atlassian    — guided re-authentication walkthrough
```

### Adding a server via the CLI

```bash
# SSE transport (Atlassian, Linear, Fathom, Context7)
claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/mcp

# HTTP transport (Notion)
claude mcp add --transport http-sse notion https://mcp.notion.com/mcp
```

Restart Claude Code after adding a new server. On first use, Claude Code prompts you to authorise via OAuth2 in your browser.

---

## Atlassian

**Key**: `atlassian`  
**URL**: `https://mcp.atlassian.com/v1/mcp`  
**Transport**: SSE  
**Provides**: Jira issue tracking and Confluence document search/publishing

### What Wire uses it for

**Issue tracking (Jira)**:
- `/wire:utils-jira-create` — creates one Jira Epic per engagement, one Task per artifact, one Sub-task per lifecycle step (generate/validate/review)
- Every generate/validate/review command syncs its completion status to the corresponding Sub-task
- `/wire:utils-jira-status-sync` — full reconciliation between local execution log and Jira (called by `/wire:status`)

**Document store (Confluence)**:
- `/wire:utils-docstore-setup` — creates a Confluence space or page hierarchy for the engagement
- `/wire:utils-docstore-sync` — publishes generated artifacts as Confluence pages after each generate command
- `/wire:utils-docstore-fetch` — retrieves Confluence comments and edits as review context during review commands
- `/wire:utils-atlassian-search` — searches Confluence for relevant prior work during review commands

### Setup

The Atlassian MCP server is the official Anthropic-hosted server. It requires an Atlassian Cloud account.

1. Add the server to `settings.json` with the URL above
2. On first use, Claude Code prompts for Atlassian OAuth2 authorisation
3. Grant access to Jira (read/write issues) and Confluence (read/write pages)
4. Run `/wire:new` — Wire auto-detects your Atlassian Cloud site and asks whether to create the Jira hierarchy

### Re-authentication

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

- `/wire:utils-linear-create` — creates one Linear Project per engagement, one Issue per artifact, one Sub-issue per lifecycle step
- Generate/validate/review commands sync to Linear in parallel with Jira when both are configured
- `/wire:utils-linear-status-sync` — full Linear reconciliation (called by `/wire:status`)

Wire applies a `wire-generated` label to all issues it creates, so you can filter your Linear board by Wire-managed issues.

### Setup

1. Add the server to `settings.json`
2. On first use, Claude Code prompts for Linear OAuth2 authorisation — grant `issues:write` scope
3. Run `/wire:utils-linear-create <release>` to set up the project hierarchy, or answer Yes when prompted during `/wire:new`

---

## Fathom

**Key**: `fathom`  
**URL**: Your Fathom MCP server URL (organisation-specific)  
**Transport**: SSE  
**Provides**: Meeting transcript retrieval for review commands

### What Wire uses it for

Every review command (`*-review`) calls `/wire:utils-meeting-context` internally, which searches Fathom for meetings in the last 30 days that mention the client name or engagement keywords. Relevant transcript excerpts — decisions made, concerns raised, action items — are surfaced as review context alongside the artifact being reviewed.

This is the mechanism that connects Wire's paper trail to what was actually discussed and agreed in client calls.

### Setup

Fathom's MCP server URL is organisation-specific. Find it in your Fathom account under Settings → Integrations → MCP. It follows the pattern `https://mcp.fathom.video/organisations/<org-id>/mcp`.

1. Copy the URL from your Fathom settings
2. Add it to `settings.json` replacing `https://your-fathom-mcp-server/mcp`
3. On first use, Claude Code prompts for Fathom OAuth2 authorisation

### Notes

- Transcripts take 15–30 minutes to appear after a call ends
- Only calls recorded in Fathom appear — not all calls are auto-recorded
- If Fathom is unavailable, review commands proceed normally without meeting context

---

## Context7

**Key**: `context7`  
**URL**: `https://mcp.context7.com/mcp`  
**Transport**: HTTP  
**Provides**: Up-to-date library documentation during development

### What Wire uses it for

Context7 is used automatically during development commands — particularly `dbt-generate`, `pipeline-generate`, and `semantic_layer-generate` — when Wire needs to look up current API documentation, check library version compatibility, or verify a framework's conventions.

It resolves a common problem with AI-generated code: models trained on older data giving outdated API calls. Context7 fetches the current official documentation for the library in question before generating code that uses it.

### Setup

Context7 is a public MCP server with no authentication required. Add the URL to `settings.json` and it works immediately.

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

An alternative to Confluence for the document store integration. When configured as the document store during `/wire:new` (or via `/wire:utils-docstore-setup`):

- Generated artifacts are published as Notion pages to a specified database after each generate command
- Reviewer comments and page edits made in Notion are surfaced as review context during review commands
- The Notion database link can be shared directly with clients for review without them needing Claude Code

### Setup

1. Create a Notion integration at `https://www.notion.so/profile/integrations`
2. Add the integration to the database you want Wire to write to (open the database → ··· → Connections → add your integration)
3. Add the server to `settings.json`
4. On first use, Claude Code prompts for Notion OAuth2 authorisation
5. Run `/wire:utils-docstore-setup <release>` and select Notion — provide the database ID when prompted

### Notes

- The database ID appears in the Notion page URL: `notion.so/<workspace>/<database-id>?v=...`
- Each artifact becomes a Notion page in the database with a `wire_artifact_id` property for tracking
- Mermaid diagrams in artifacts are rendered as images before publishing (Notion requires image format)
