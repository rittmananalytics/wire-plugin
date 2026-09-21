---
sidebar_position: 2
title: Release Types
---

# Release Types

Every engagement has a shape, and the shape decides which documents get written, in what order and who signs off each one before the next begins. A discovery that ends in a pitch is a different piece of work from a warehouse migration, and a framework that treated them alike would either bury the first in ceremony or leave the second short of the checks it needs. Wire therefore encodes its delivery methodology as twelve release types, each defining a different ordered set of in-scope artifacts and the commands that apply to them, and when you run `/wire:new` and select a release type the framework instantiates that process definition into the release's `status.md` file. In this page we will look at the twelve types side by side, at how the choice between them is made since 4.0.0 and at the distinctions that most often decide it.

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
| **Platform Migration** | `platform_migration` | Full lifecycle migration from one warehouse stack to another, through to production-verified code in the client's repo. Runs full-platform or as a **[tenant carve-out](../release-types/tenant-carveout)** (extract one tenant into its own target), set by `migration.scope`. At scale, runs as a director-plus-agent-fleet (v3.11.0): the consultant issues rulings, the agent invokes the commands | 4–16 weeks |
| **Agentic Data Stack** | `agentic_data_stack` | AI analytics overlay for an existing data platform | 4–6 weeks |
| **Droughty** | `droughty` | Schema introspection and base-layer generation | 1–3 days |
| **Custom** | `custom` | Bespoke scope derived from SoW or project documents | Varies |

## You do not have to know the command sequence

How much of each sequence do you need to hold in your head? Every release type below is a defined sequence of artifacts with explicit dependencies between them, and **since v4.0.0, on Claude Code, Wire reads that sequence for you.** Say what you want done and it works out what is runnable, runs it, tells you what it did in plain words and stops at every review gate for your decision.

It follows that the choice below is one you make in conversation: point Wire at the SOW and it proposes a release type **with its reason** for you to confirm, rather than asking you to pick from a list cold. Where a release type offers profiles, as `dashboard_first` does (`seeded` or `live_data`) and `sop_discovery` does (`diagnostic` or `modelling_led`), `/wire:new` now asks which, instead of applying the default silently.

See [The Release Director Model](../advanced/release-director) for the rules behind this.

## Choosing the right release type

If you would rather make the choice yourself, or want to check the one Wire proposes, the following rules of thumb map the situation you find at the client to a release type.

- **New engagement, scope can be shaped in 1–2 weeks** → **Discovery (Shape Up)**
- **New engagement, scope genuinely unknown, requires structured discovery** → **Discovery (SOP / Canonical)**
- **Client needs a new data source connected end-to-end to a dashboard** → **Full Platform**
- **Early stakeholder feedback via interactive mocks before building the data layer** → **Dashboard-First**
- **Client has a BI tool and just needs new data flowing in** → **Pipeline + dbt**
- **Data is already in the warehouse; need to build the transformation layer** → **dbt Development**
- **Semantic layer already has the data; adding new dashboards** → **Dashboard Extension**
- **Platform exists; engaged to train and document it** → **Enablement**
- **Migrating an existing data platform between warehouses** → **Platform Migration** (full-platform, or a [tenant carve-out](../release-types/tenant-carveout) to extract a single tenant)
- **Client wants an AI that answers business questions reliably from their warehouse** → **Agentic Data Stack**
- **Need to map an existing warehouse quickly before starting design work** → **Droughty** (discovery mode)
- **Bespoke deliverables that do not fit any standard type** → **Custom**

## Key distinctions

Three of those choices come up often enough to deserve a closer look.

**Discovery (Shape Up) vs Discovery (SOP / Canonical)**: Use Shape Up when the problem domain is understood and you can shape a solution in a week or two. Use SOP / Canonical when you genuinely do not yet know what to build, stakeholder alignment is low or this is the first analytics engagement at the client.

**Full Platform vs Dashboard-First**: Both produce the same end result, and the difference is the order in which you get there. Full Platform follows the traditional flow: requirements → conceptual model → pipeline design → data model → dbt → dashboards. Dashboard-First inverts this: requirements → interactive dashboard mocks → visualisation catalogue → data model → seed data → dbt → dashboards → data refactor.

**When to start with Platform Migration vs a discovery release**: A discovery release is strongly recommended before starting a migration if the scope is not yet confirmed, because migration is irreversible once Fivetran connectors are cut over.
