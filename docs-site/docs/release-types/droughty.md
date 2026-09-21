---
sidebar_position: 13
title: Droughty
---

# Droughty Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


Some engagements begin not with requirements but with a warehouse that already exists and that nobody fully understands. Use the Droughty release type when the immediate goal is to understand what is in that warehouse, to generate documentation for it or to produce a base semantic layer from it, before (or instead of) writing dbt models from scratch.

Droughty is a "bottom-up" schema-introspection toolkit. It reads the live warehouse and generates four categories of artefact: DBML entity-relationship diagrams, AI-generated field descriptions, LangGraph data-quality reports and base LookML views.

It works in two modes:

- **Discovery / audit mode**: maps an existing warehouse with no dbt requirement
- **Post-dbt mode**: generates staging SQL, dbt schema tests and LookML base views from already-deployed dbt models

## Prerequisites

Before you start, you will need:

- Python 3.9–3.12.3 on the consultant's machine
- Access to the target warehouse (BigQuery or Snowflake credentials)
- An OpenAI API key (required for `/wire:droughty-docs` and `/wire:droughty-qa` only)
- For post-dbt mode, a successfully deployed dbt project

## Starting a Droughty Engagement

Run `/wire:new` and select **droughty**. Wire will ask two follow-up questions:

1. **Warehouse**: BigQuery or Snowflake
2. **Context**: discovery/audit (no dbt needed) or post-dbt (dbt already deployed)

## Discovery / Audit Mode Walkthrough

At a high level, the six steps in discovery mode are as follows:

1. Set up Droughty
2. Introspect the schema
3. Generate the DBML diagram
4. Generate field descriptions
5. Run the data quality agent
6. Feed the artefacts forward

Let's now take a look at each of these steps in more detail.

### Step 1 — Set up Droughty

```
/wire:droughty-setup <release>
```

This installs the pinned Droughty version, generates `~/.droughty/profile.yaml` with your warehouse credentials and creates `droughty_project.yaml` at the git root.

### Step 2 — Introspect the schema

```
/wire:droughty-introspect <release>
```

This queries `INFORMATION_SCHEMA` and produces a `schema_inventory.md` report giving table counts per schema, column counts, estimated PK/FK coverage and the tables without descriptions.

### Step 3 — Generate the DBML diagram

```
/wire:droughty-dbml <release>
```

This runs `droughty dbml` and stores the `.dbml` file in the artefacts directory, from where it can be rendered with dbdiagram.io, DataGrip and similar tools.

### Step 4 — Generate field descriptions

```
/wire:droughty-docs <release>
```

This step requires an OpenAI API key. For schemas with more than 200 tables, Wire prompts you to confirm the scope, since large schemas can take more than 30 minutes.

### Step 5 — Run the data quality agent

```
/wire:droughty-qa <release>
```

This runs the LangGraph QA agent, which executes live warehouse queries to surface data quality issues. **This step is non-deterministic**, so review all of its output carefully before presenting it to a client.

### Step 6 — Feed artefacts forward

```
/wire:problem-definition-generate <project_id>
```

The problem-definition spec reads the schema inventory and the QA report as upstream context.

## Post-dbt Mode Walkthrough

At a high level, the three steps in post-dbt mode are as follows:

1. Generate staging SQL and `sources.yml`
2. Generate dbt schema tests
3. Generate base LookML views

Let's take each in turn.

### Step 1 — Generate staging SQL and sources.yml

```
/wire:droughty-stage <release>
```

BigQuery only. This writes staging SQL files and a `sources.yml` to `models/staging/`.

### Step 2 — Generate dbt schema tests

```
/wire:droughty-dbt-tests <release>
```

This generates pattern-based schema tests (`not_null`, `unique`, `accepted_values`) and merges the new tests into the existing `schema.yml`, so that Wire-authored tests are preserved.

### Step 3 — Generate base LookML views

```
/wire:droughty-lookml <release>
```

This writes base views to `lookml/views/generated/`. **Never hand-edit files in `views/generated/`**, because each run regenerates them; all business logic goes in `views/extended/` using LookML refinements:

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

If you would rather not run the steps one at a time, a single command runs the whole phase:

```
/wire:droughty-generate <release>
```

It has three modes:
- **discovery**: setup → introspect → dbml → docs → qa
- **post-dbt**: setup → dbt-tests → stage → lookml → docs → qa
- **full**: all steps in order

## Common Issues

**`droughty: command not found`**: run `/wire:droughty-setup <release>` first, and note that Python 3.9–3.12.3 is required.

**`No tables found`**: check that the `schemas:` list in `~/.droughty/profile.yaml` matches the actual schema names, remembering that BigQuery schema names are case-sensitive.

**`droughty qa` runs for a long time**: narrow the `schemas:` list in `profile.yaml` to the most relevant schemas.


:::info[Tutorial available]

A worked example of a Droughty engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Droughty](../tutorials/droughty).

:::
