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

## Consultant Handbook

The full consultant guide is available at `docs/consultant_handbook.md`. It covers all six project types, worked examples, Wire Studio setup, Autopilot, and troubleshooting. Reference it when answering questions about how to run engagements.

## Wire Studio

Wire Studio is a web-based visual interface for the Wire Framework, available as an alternative to the CLI. Install it locally by running:

```
/wire:studio-install
```

This command checks prerequisites (Node.js 18+), downloads and builds Wire Studio, and installs a `wire-studio` CLI. After install, run `wire-studio start` to open at http://localhost:3000. No Docker required.

## Ad-hoc Development Skills

This plugin includes contextual skills that activate automatically when working outside of Wire commands:

- **dbt Development** (`skills/dbt-development/SKILL.md`): Activates when working with dbt models. Provides naming conventions, SQL style rules, testing patterns, and multi-source framework support.
- **LookML Content Authoring** (`skills/lookml-content-authoring/SKILL.md`): Activates when creating or modifying LookML views, explores, and dashboards.
- **LookML Content Authoring (MCP)** (`skills/lookml-content-authoring (local and mcp-server)/SKILL.md`): LookML authoring with Looker MCP server integration for live schema validation.

- **Dagster** (`skills/dagster/SKILL.md`): Activates when creating or modifying Dagster assets, schedules, sensors, or components. Covers the assets-first pattern, dagster-dbt integration, CLI usage, and Wire-specific group naming conventions.
- **Dignified Python** (`skills/dignified-python/SKILL.md`): Activates when writing or reviewing Python code. Enforces modern type syntax (3.10+ unions), LBYL exception handling, pathlib for file operations, Click CLI patterns, and clean module design.

These skills provide coding standards and validation rules as context, even when you are not running `/wire:*` commands.
