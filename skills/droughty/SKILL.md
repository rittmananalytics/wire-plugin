---
name: droughty
description: Droughty schema-introspection toolkit — use when working with Droughty commands, profile/project configuration, LookML generation from warehouse schemas, dbt test generation, DBML diagrams, field documentation, or data quality reports
tags: [droughty, lookml, dbt, schema, bigquery, snowflake, dbml, qa]
---

# Droughty Skill

This skill activates when working on Droughty-related tasks within a Wire engagement. It provides guidance on the Droughty CLI, configuration, Wire integration conventions, and output structure.

## Droughty Overview

Droughty is a schema-driven toolkit that reads the live warehouse and generates semantic layer artifacts. It is the **bottom-up** counterpart to Wire's top-down, document-driven workflow.

| Command | What it does | Requires |
|---------|-------------|----------|
| `droughty dbml` | DBML entity-relationship diagram | Warehouse connection |
| `droughty docs` | AI field descriptions for all columns | Warehouse + OpenAI API key |
| `droughty qa` | LangGraph data quality agent | Warehouse + OpenAI API key |
| `droughty dbt` | Pattern-based schema.yml tests | Deployed dbt tables |
| `droughty stage` | Staging SQL + sources.yml (BigQuery only) | Source dataset in BigQuery |
| `droughty lookml` | Base LookML views, explores, measures | Deployed dbt tables |

## Pinned Version

Wire pins a specific Droughty version in `wire/droughty/pinned_version.txt`. All `/wire:droughty-setup` runs install this version. Current pin: check the file at `wire/droughty/pinned_version.txt`.

To update the pin, run the refresh script (Wire repo owner only):

```bash
bash wire/droughty/refresh_version.sh           # updates pinned_version.txt
bash wire/droughty/refresh_version.sh --commit  # also commits the change
```

Consultants re-run `/wire:droughty-setup --force` after pulling the updated repo.

## Configuration Files

### profile.yaml (`~/.droughty/profile.yaml`)

Not committed to git — contains warehouse credentials.

**BigQuery:**
```yaml
my_engagement:
  type: bigquery
  project: my-gcp-project
  dataset: analytics
  schemas:
    - analytics
    - staging
  openai_api_key: sk-...   # required for docs + qa
```

**Snowflake:**
```yaml
my_engagement:
  type: snowflake
  account: xy12345.us-east-1
  username: analyst
  password: secret
  warehouse: COMPUTE_WH
  database: ANALYTICS
  schema: PUBLIC
  role: ANALYST
  schemas:
    - PUBLIC
    - STAGING
  openai_api_key: sk-...
```

### droughty_project.yaml (git root)

Committed to git — controls output paths.

```yaml
profile_name: my_engagement

# Wire-aligned output paths
dbml_path: .wire/releases/01-discovery/artifacts/droughty/
field_description_path: .wire/releases/01-discovery/artifacts/droughty/field_descriptions/
dbt_path: ./models/
stage_path: ./models/staging/
lookml_path: ./lookml/views/generated/
```

## LookML File Organisation Convention

Droughty-generated views land in `views/generated/`. Wire-authored extensions (explores, refinements, derived fields) go in `views/extended/`. Never edit `views/generated/` by hand — Droughty regenerates it on each `/wire:droughty-lookml` run.

```
lookml/
├── views/
│   ├── generated/      ← Droughty output — auto-regenerated, do not hand-edit
│   │   ├── orders.view.lkml
│   │   └── customers.view.lkml
│   └── extended/       ← Wire extensions — business logic, explores, refinements
│       ├── orders_extended.view.lkml
│       └── explores.model.lkml
```

Use LookML refinements in `views/extended/` to extend base views:
```lookml
view: +orders {
  dimension: order_value_band {
    type: string
    sql: CASE WHEN ${order_total} < 100 THEN 'low' ...
  }
}
```

## Wire Command Reference

| Command | Purpose |
|---------|---------|
| `/wire:droughty-setup <release>` | Install Droughty, generate profile.yaml + droughty_project.yaml |
| `/wire:droughty-introspect <release>` | Schema inventory report — tables, columns, PK/FK coverage |
| `/wire:droughty-dbml <release>` | DBML entity-relationship diagram |
| `/wire:droughty-docs <release>` | AI field descriptions |
| `/wire:droughty-qa <release>` | Data quality agent report |
| `/wire:droughty-stage <release>` | Staging SQL + sources.yml (BigQuery only) |
| `/wire:droughty-dbt-tests <release>` | Pattern-based schema tests (post-dbt deploy) |
| `/wire:droughty-lookml <release>` | Base LookML views (post-dbt deploy) |
| `/wire:droughty-generate <release>` | Full Droughty phase in sequence |

## Workflow Placement

**Discovery / existing warehouse audit (Droughty release type):**
```
/wire:new (release_type: droughty)
/wire:droughty-setup
/wire:droughty-introspect
/wire:droughty-dbml
/wire:droughty-docs
/wire:droughty-qa
→ feed artifacts into /wire:problem-definition-generate
```

**Post-dbt phase (within full_platform or dbt_development):**
```
... /wire:dbt-validate ← dbt run ← /wire:dbt-generate ...
/wire:droughty-setup
/wire:droughty-dbt-tests
/wire:droughty-lookml
/wire:droughty-docs
/wire:droughty-qa
/wire:semantic_layer-generate   ← extends Droughty base views
```

## Troubleshooting

**`droughty: command not found`** — install with `pip install "droughty==[version]"`. Python 3.9–3.12.3 required.

**`profile.yaml not found`** — run `/wire:droughty-setup [release]`.

**`No tables found`** — check that `schemas:` in profile.yaml matches the actual schema names in the warehouse. BigQuery schema names are case-sensitive.

**`OpenAI API error`** — check that `openai_api_key` is set in profile.yaml and the key has billing enabled.

**`droughty qa` timeout** — the QA agent runs live warehouse queries; large schemas can take 20+ minutes. Consider limiting schemas in scope.
