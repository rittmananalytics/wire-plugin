---
sidebar_position: 5
title: Issue Tracking
---

# Issue Tracking Integration

Wire integrates with Jira and Linear to sync artifact status as the engagement progresses. Each integration is optional — Wire works without either, and both can be active simultaneously.

## Jira integration

### Configuration

The Atlassian MCP server must be configured in `.claude/settings.json`:

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-atlassian"],
      "env": {
        "ATLASSIAN_SITE_URL": "https://your-org.atlassian.net",
        "ATLASSIAN_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Structure

Wire creates one Jira hierarchy per engagement:

- **Epic** — one per project (e.g. "Barton Peveril Full Platform")
- **Tasks** — one per artifact (e.g. "Problem Definition", "High-Level Design")
- **Sub-tasks** — one per lifecycle step (Generate, Validate, Review)

Run `/wire:new` and answer Yes when asked whether to create the Jira hierarchy. If the hierarchy already exists, provide the existing Epic ID and Wire links to it.

### Syncing

All generate/validate/review commands sync their status to the corresponding Jira sub-task after completing:

- **Generate completes** → sub-task transitions to In Review
- **Validate fails** → sub-task transitions to Blocked, failure details added as a comment
- **Validate passes** → sub-task transitions to In Review
- **Review approved** → sub-task transitions to Done; Task transitions to Done if all sub-tasks are Done

### `/wire:status` reconciliation

Running `/wire:status` performs a full reconciliation between the local execution log and Jira — identifying any gaps, fixing stale statuses, and flagging artifacts where the local and Jira states diverge.

## Linear integration

### Configuration

The Linear MCP server must be configured in `.claude/settings.json`:

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "@linear/mcp-server"],
      "env": {
        "LINEAR_API_KEY": "your-linear-api-key"
      }
    }
  }
}
```

### Structure

Wire creates a Linear hierarchy per engagement:

- **Project** — one per engagement
- **Issues** — one per artifact
- **Sub-issues** — one per lifecycle step (Generate, Validate, Review)

Run `/wire:utils-linear-create <release-folder>` to create the hierarchy. If using both Jira and Linear, Wire maintains both in parallel.

### Labels and states

Wire maps artifact states to Linear issue states as follows:

| Wire state | Linear state |
|---|---|
| Not started | Backlog |
| Generate in progress | In Progress |
| Validation failures | Blocked |
| Awaiting review | In Review |
| Approved | Done |

Wire creates a `wire-generated` label and applies it to all issues it creates, so you can filter your Linear board by Wire-managed issues.

## Using both simultaneously

If both Atlassian and Linear are configured, Wire syncs to both after each command. The execution log records both sync results. If one sync fails (e.g. network error), Wire logs the failure but does not block the command — the next `/wire:status` will reconcile.
