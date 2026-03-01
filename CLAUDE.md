# Wire Framework — Claude Code Plugin

This plugin provides the **Wire Framework**, an AI-accelerated delivery system for data platform engagements. It encodes 20+ years of analytics engineering methodology as executable workflow specifications, enabling an AI agent to produce production-grade artifacts across the full project lifecycle.

## Usage

All commands are available after installing and restarting Claude Code. Commands are namespaced under `/wire:*`:

```
/wire:start              — See all projects and available commands
/wire:new                — Create a new project
/wire:autopilot <sow>    — Autonomous end-to-end execution from SOW
/wire:status <project>   — Check project status
```

### Delivery commands

```
/wire:requirements-generate <project>   — Extract requirements from SOW
/wire:requirements-validate <project>   — Validate requirements
/wire:requirements-review <project>     — Stakeholder review

/wire:conceptual_model-generate <project>
/wire:data_model-generate <project>
/wire:dbt-generate <project>
/wire:semantic_layer-generate <project>
/wire:dashboards-generate <project>
... (and -validate/-review for each)
```

### Project data

Project data is stored in `.wire/` in the current repository. This directory is created automatically when you run `/wire:new` or `/wire:autopilot`.

## MCP Integrations

This plugin configures optional MCP servers for:
- **Atlassian** — Jira issue tracking and Confluence document search
- **Fathom** — Meeting transcript context for reviews
- **Context7** — Library documentation lookups

Authenticate via `/mcp` in Claude Code.
