---
sidebar_position: 6
title: Issue Tracking
---

# Issue Tracking Integration

If your client's delivery team lives in Jira or Linear, they will want to see the state of each Wire artifact where they already look for it, rather than having to ask you. Wire therefore integrates with Jira and Linear to sync artifact status as the engagement progresses. Each integration is optional, Wire works without either, and both can be active simultaneously. In this page we will look at the Jira integration first, then Linear, and finish with what happens when both are configured.

## Jira integration

### Configuration

To use Jira, the Atlassian MCP server must be configured in `.claude/settings.json`:

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

Wire creates one Jira hierarchy per engagement, with three levels:

- **Epic**: one per project (e.g. "Barton Peveril Full Platform")
- **Tasks**: one per artifact (e.g. "Problem Definition", "High-Level Design")
- **Sub-tasks**: one per lifecycle step (Generate, Validate, Review)

To create it, run `/wire:new` and answer Yes when asked whether to create the Jira hierarchy, and if the hierarchy already exists, provide the existing Epic ID and Wire links to it instead.

### Syncing

Once the hierarchy exists, how does it stay current? All generate/validate/review commands sync their status to the corresponding Jira sub-task after completing:

- **Generate completes** → sub-task transitions to In Review
- **Validate fails** → sub-task transitions to Blocked, failure details added as a comment
- **Validate passes** → sub-task transitions to In Review
- **Review approved** → sub-task transitions to Done; Task transitions to Done if all sub-tasks are Done

### `/wire:status` reconciliation

Running `/wire:status` performs a full reconciliation between the local execution log and Jira, identifying any gaps, fixing stale statuses and flagging artifacts where the local and Jira states diverge.

## Linear integration

### Configuration

For Linear, the Linear MCP server must be configured in `.claude/settings.json`:

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

Wire creates a Linear hierarchy per engagement, again with three levels:

- **Project**: one per engagement
- **Issues**: one per artifact
- **Sub-issues**: one per lifecycle step (Generate, Validate, Review)

Run `/wire:utils-linear-create <release-folder>` to create the hierarchy, and if you are using both Jira and Linear, Wire maintains both in parallel.

### Labels and states

Wire maps artifact states to Linear issue states as follows:

| Wire state | Linear state |
|---|---|
| Not started | Backlog |
| Generate in progress | In Progress |
| Validation failures | Blocked |
| Awaiting review | In Review |
| Approved | Done |

Wire also creates a `wire-generated` label and applies it to all issues it creates, so that you can filter your Linear board down to Wire-managed issues.

## Using both simultaneously

If both Atlassian and Linear are configured, Wire syncs to both after each command, and the execution log records both sync results. If one sync fails (e.g. a network error), Wire logs the failure but does not block the command, and the next `/wire:status` will reconcile.
