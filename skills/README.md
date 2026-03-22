# Wire Framework — Development Skills

Contextual development skills that are distributed with the Wire Framework plugin. These skills activate automatically when working on dbt or LookML code, even outside of `/wire:*` commands.

## Skills

| Skill | Activates When | Description |
|-------|---------------|-------------|
| [dbt Development](dbt-development/) | Working with dbt models | Naming conventions, SQL style rules, testing patterns, multi-source framework support |
| [LookML Content Authoring](lookml-content-authoring/) | Creating/modifying LookML | View, explore, and dashboard creation with validation against source schemas |
| [LookML Content Authoring (MCP)](lookml-content-authoring%20(local%20and%20mcp-server)/) | LookML with Looker MCP | LookML authoring with Looker MCP server integration for live schema validation |

## How They Work

Each skill is a `SKILL.md` markdown file that Claude Code reads as context. When the plugin is installed, these skills are available alongside the Wire commands. They provide:

- **Naming conventions** — consistent field naming (`_pk`, `_fk`, `_ts`, `is_`/`has_`) across all dbt models
- **SQL style rules** — standardised SQL formatting and structure
- **Testing patterns** — required tests for primary keys, foreign keys, and data quality
- **Validation rules** — automated checks against source DDL/schema for LookML

## Customisation

Each skill can be customised by editing its `SKILL.md` file. The dbt skill also supports project-specific convention overrides via `dbt_project.yml` vars.

---

**Rittman Analytics** — Proprietary, internal use only.
