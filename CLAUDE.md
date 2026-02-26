# Wire Framework — Claude Code Plugin

This plugin provides the **Wire Framework**, an AI-accelerated delivery system for data platform engagements. It encodes 20+ years of analytics engineering methodology as executable workflow specifications, enabling an AI agent to produce production-grade artifacts across the full project lifecycle.

## Usage

All commands are available after installing and restarting Claude Code. Commands are namespaced under `/wire:dp-*`:

```
/wire:dp-start              — See all projects and available commands
/wire:dp-new                — Create a new project
/wire:dp-status <project>   — Check project status
```

### Delivery commands

```
/wire:dp-requirements-generate <project>   — Extract requirements from SOW
/wire:dp-requirements-validate <project>   — Validate requirements
/wire:dp-requirements-review <project>     — Stakeholder review

/wire:dp-conceptual_model-generate <project>
/wire:dp-data_model-generate <project>
/wire:dp-dbt-generate <project>
/wire:dp-semantic_layer-generate <project>
/wire:dp-dashboards-generate <project>
... (and -validate/-review for each)
```

### Project data

Project data is stored in `.wire/` in the current repository. This directory is created automatically when you run `/wire:dp-new`.

## MCP Integrations

This plugin configures optional MCP servers for:
- **Atlassian** — Jira issue tracking and Confluence document search
- **Fathom** — Meeting transcript context for reviews
- **Context7** — Library documentation lookups

Authenticate via `/mcp` in Claude Code.
