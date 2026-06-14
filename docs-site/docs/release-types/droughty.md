---
sidebar_position: 13
title: Droughty
---

# Droughty Release

Use the Droughty release type when the engagement begins with an existing data warehouse and the immediate goal is to understand what's in it, generate documentation, or produce a base semantic layer — before (or instead of) writing dbt models from scratch.

Droughty is a bottom-up schema-introspection toolkit. It reads the live warehouse and generates four categories of artefact: DBML entity-relationship diagrams, AI-generated field descriptions, LangGraph data-quality reports, and base LookML views.

**Two modes:**

- **Discovery / audit mode** — maps an existing warehouse with no dbt requirement
- **Post-dbt mode** — generates staging SQL, dbt schema tests, and LookML base views from already-deployed dbt models

## Prerequisites

- Python 3.9–3.12.3 on the consultant's machine
- Access to the target warehouse (BigQuery or Snowflake credentials)
- OpenAI API key (required for `/wire:droughty-docs` and `/wire:droughty-qa` only)
- For post-dbt mode: a successfully deployed dbt project

## Starting a Droughty Engagement

Run `/wire:new` and select **droughty**. Wire will ask two follow-up questions:

1. **Warehouse**: BigQuery or Snowflake
2. **Context**: discovery/audit (no dbt needed) or post-dbt (dbt already deployed)

## Discovery / Audit Mode Walkthrough

### Step 1 — Set up Droughty

```
/wire:droughty-setup <release>
```

This installs the pinned Droughty version, generates `~/.droughty/profile.yaml` with your warehouse credentials, and creates `droughty_project.yaml` at the git root.

### Step 2 — Introspect the schema

```
/wire:droughty-introspect <release>
```

Queries `INFORMATION_SCHEMA` and produces a `schema_inventory.md` report — table counts per schema, column counts, estimated PK/FK coverage, and tables without descriptions.

### Step 3 — Generate the DBML diagram

```
/wire:droughty-dbml <release>
```

Runs `droughty dbml` and stores the `.dbml` file in the artefacts directory. Renderable with dbdiagram.io, DataGrip, etc.

### Step 4 — Generate field descriptions

```
/wire:droughty-docs <release>
```

Requires an OpenAI API key. For schemas with more than 200 tables, Wire prompts to confirm scope — large schemas can take 30+ minutes.

### Step 5 — Run the data quality agent

```
/wire:droughty-qa <release>
```

Runs the LangGraph QA agent, which executes live warehouse queries to surface data quality issues. **This step is non-deterministic** — review all output carefully before presenting to a client.

### Step 6 — Feed artefacts forward

```
/wire:problem-definition-generate <project_id>
```

The problem-definition spec will read the schema inventory and QA report as upstream context.

## Post-dbt Mode Walkthrough

### Step 1 — Generate staging SQL and sources.yml

```
/wire:droughty-stage <release>
```

BigQuery only. Writes staging SQL files and a `sources.yml` to `models/staging/`.

### Step 2 — Generate dbt schema tests

```
/wire:droughty-dbt-tests <release>
```

Generates pattern-based schema tests (`not_null`, `unique`, `accepted_values`). Merges new tests into existing `schema.yml` — Wire-authored tests are preserved.

### Step 3 — Generate base LookML views

```
/wire:droughty-lookml <release>
```

Writes base views to `lookml/views/generated/`. **Never hand-edit files in `views/generated/`** — each run regenerates them. All business logic goes in `views/extended/` using LookML refinements:

```lookml
view: +orders {
  dimension: order_value_band {
    type: string
    sql: CASE WHEN ${order_total} < 100 THEN 'low'
              WHEN ${order_total} < 500 THEN 'medium'
              ELSE 'high' END ;;
  }
}
```

## Running the Full Phase in One Command

```
/wire:droughty-generate <release>
```

Modes:
- **discovery**: setup → introspect → dbml → docs → qa
- **post-dbt**: setup → dbt-tests → stage → lookml → docs → qa
- **full**: all steps in order

## Common Issues

**`droughty: command not found`** — run `/wire:droughty-setup <release>` first. Python 3.9–3.12.3 is required.

**`No tables found`** — check that the `schemas:` list in `~/.droughty/profile.yaml` matches the actual schema names. BigQuery schema names are case-sensitive.

**`droughty qa` runs for a very long time** — narrow the `schemas:` list in `profile.yaml` to the most relevant schemas.


:::info[Tutorial available]

A worked example of a Droughty engagement — using a fictional client scenario with realistic command output, agent delegation, and reviewer decisions — is available in the [Tutorial: Droughty](../tutorials/droughty).

:::