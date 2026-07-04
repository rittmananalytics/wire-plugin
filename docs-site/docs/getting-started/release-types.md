---
sidebar_position: 2
title: Release Types
---

# Release Types

The framework encodes delivery methodology as twelve release types, each defining a different ordered set of in-scope artifacts and the commands that apply to them. When you run `/wire:new` and select a release type, the framework instantiates that process definition into the release's `status.md` file.

| Type | `release_type` | Scope | Typical Duration |
|------|----------------|-------|-----------------|
| **Discovery (Shape Up)** | `discovery` | Problem definition → pitch → release brief → sprint plan | 1–2 weeks |
| **Discovery (SOP / Canonical)** | `sop_discovery` | Wide-ranging structured discovery leading to Findings Playback | 3–6 weeks |
| **Full Platform** | `full_platform` | SOW → production dashboards + trained users | 2–3 weeks |
| **Dashboard-First** | `dashboard_first` | Interactive mocks drive data model; seed data enables immediate dbt | 1–2 weeks |
| **Pipeline + dbt** | `pipeline_only` | New data pipeline + dbt transformation layer | 1–2 weeks |
| **dbt Development** | `dbt_development` | Analytics engineering on existing infrastructure | 1 week |
| **Dashboard Extension** | `dashboard_extension` | New dashboards on an existing semantic layer | 3–5 days |
| **Enablement** | `enablement` | Training and documentation for an existing platform | 2–3 days |
| **Platform Migration** | `platform_migration` | Full lifecycle migration from one warehouse stack to another. Runs full-platform or as a **tenant carve-out** (extract one tenant into its own target), set by `migration.scope` | 4–16 weeks |
| **Agentic Data Stack** | `agentic_data_stack` | AI analytics overlay for an existing data platform | 4–6 weeks |
| **Droughty** | `droughty` | Schema introspection and base-layer generation | 1–3 days |
| **Custom** | `custom` | Bespoke scope derived from SoW or project documents | Varies |

## Choosing the right release type

- **New engagement, scope can be shaped in 1–2 weeks** → **Discovery (Shape Up)**
- **New engagement, scope genuinely unknown, requires structured discovery** → **Discovery (SOP / Canonical)**
- **Client needs a new data source connected end-to-end to a dashboard** → **Full Platform**
- **Early stakeholder feedback via interactive mocks before building the data layer** → **Dashboard-First**
- **Client has a BI tool and just needs new data flowing in** → **Pipeline + dbt**
- **Data is already in the warehouse; need to build the transformation layer** → **dbt Development**
- **Semantic layer already has the data; adding new dashboards** → **Dashboard Extension**
- **Platform exists; engaged to train and document it** → **Enablement**
- **Migrating an existing data platform between warehouses** → **Platform Migration** (full-platform, or a tenant carve-out to extract a single tenant)
- **Client wants an AI that answers business questions reliably from their warehouse** → **Agentic Data Stack**
- **Need to map an existing warehouse quickly before starting design work** → **Droughty** (discovery mode)
- **Bespoke deliverables that don't fit any standard type** → **Custom**

## Key distinctions

**Discovery (Shape Up) vs Discovery (SOP / Canonical)**: Use Shape Up when the problem domain is understood and you can shape a solution in a week or two. Use SOP / Canonical when you genuinely do not yet know what to build, stakeholder alignment is low, or this is the first analytics engagement at the client.

**Full Platform vs Dashboard-First**: Both produce the same end result. Full Platform follows the traditional flow: requirements → conceptual model → pipeline design → data model → dbt → dashboards. Dashboard-First inverts this: requirements → interactive dashboard mocks → visualization catalog → data model → seed data → dbt → dashboards → data refactor.

**When to start with Platform Migration vs a discovery release**: A discovery release is strongly recommended before starting a migration if the scope is not yet confirmed — migration is irreversible once Fivetran connectors are cut over.
