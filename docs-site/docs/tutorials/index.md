---
sidebar_position: 0
title: "Tutorials"
---

# Wire Framework Tutorials

The release-type reference pages tell you which artifacts a release produces and in what order, but they cannot show you what a release feels like on the day: what the command output looks like, when a specialist agent takes a task off your hands, which of the MCP integrations wakes up at a given gate and, above all, why a consultant chose one path over another when the reference offered two. Wouldn't it be useful to watch each release type run from start to finish on an engagement that resembles your own before you run it for real?

That is what these tutorials are for. Each one is a scenario-based walkthrough of a single Wire release type, built around a fictional client engagement, and each goes further than the reference page by showing realistic command output, how agent delegation plays out in practice, which MCP integrations activate at each gate and the decision-making context that shapes what gets generated. The scenarios have been constructed to surface the parts of each release type that are easy to misread from the reference alone, such as "appetite" versus scope in a Shape Up discovery, the "two-zone" safety model in a platform migration and the seed-based prototyping sequence in a Dashboard First release.

The supplementary tutorials at the bottom of the table cover the operational mechanics rather than a release type: installing and upgrading the plugin, joining an active engagement mid-stream and upgrading an existing release folder when a newer version of Wire is installed. As such, we suggest you read the tutorial for your release type before running `/wire:new`, or keep it open alongside the terminal during delivery, and turn to the supplementary tutorials when something about the environment or the engagement handover is non-standard.

## A note on typed commands

Every tutorial below shows the commands being typed, because that is the
clearest way to show what runs and in what order. **Since v4.0.0, on Claude
Code, you do not have to type them.** You say what you want done, and Wire works
out which command that is from the release-type definition, runs it, tells you what
it did and stops where a decision is yours.

It follows, therefore, that you should read the tutorials as "what Wire will run"
rather than "what you must type", since the commands, the artifacts and the record
on disk are identical either way. See
[The Release Director Model](../advanced/release-director), and the
[Dashboard First](./dashboard-first) tutorial for the same release driven by
direction rather than by keystrokes.

## Tutorial index

| Tutorial | Release Type | Scenario | Key Features Shown |
|---|---|---|---|
| [Full Platform](./full-platform) | `full_platform` | Eversholt Brewing Co: Shopify, BrewMan ERP and HubSpot into BigQuery + Looker | All six phases end-to-end; parallel dbt agent fan-out; Jira hierarchy creation; `decisions.md` accumulation across agents; the optional Agents Schema publication after the dbt models |
| [dbt Development](./dbt-development) | `dbt_development` | Vantage Financial Reporting: Stripe, Salesforce and PostgreSQL into Snowflake | Transformation-only scope; cross-system customer identity resolution; 38 schema tests; skipping pipeline and BI phases |
| [Pipeline and dbt](./pipeline-dbt) | `pipeline_only` | Meridian Logistics Group: complex multi-source ingestion with a bespoke SFTP connector | Connector configuration and activation; custom Cloud Function pipeline; staging-layer focus before warehouse design is committed |
| [Discovery (Shape Up)](./discovery-shape-up) | `discovery_shape_up` | Hallmark Property Partners: real estate investment go/no-go scoping | Appetite document; scope story map; risk catalogue; Fathom transcript integration; SOW-ready output in two days |
| [Discovery (SOP)](./discovery-sop) | `sop_discovery` | Thornfield Private Healthcare: four-clinic GDPR-sensitive assessment | Formal stakeholder interviews with MoSCoW categorisation; data inventory; capability assessment; Jira Epic auto-created at `/wire:new` |
| [Dashboard Extension](./dashboard-extension) | `dashboard_extension` | Foxwood Commerce Ltd: marketing dashboard expansion on an existing Looker instance | Starting from `semantic_layer-generate`; existing LookML pattern-matching; no pipeline or dbt work in scope |
| [Dashboard First](./dashboard-first) | `dashboard_first` | Claybrook Media Group: interactive HTML mockup before any data layer is committed | `dashboard-mock-developer` agent; Chart.js interactive prototypes; atomic derivation of viz catalog, dashboard spec and data model requirements; CSV seed files with referential integrity; mock-to-real refactor sequence |
| [Enablement](./enablement) | `enablement` | Hargreave Insurance Ltd: platform enablement and technical handover | `delivery-lead` agent reading prior build artifacts; two-audience training generation; architecture and field-catalogue documentation |
| [Platform Migration](./platform-migration) | `platform_migration` | Gatwick Data Partners: Snowflake to BigQuery migration | Audit zone versus migration zone; five equivalency check types; `equivalency-investigate` / `equivalency-fix` loop; cutover gate requiring `checks_failing: 0` and written sign-off |
| [Looker to Omni Migration](./looker-to-omni-migration) | `bi_migration` | Halcyon Outdoor Ltd, Looker to Omni on the same BigQuery warehouse, driven as release director | Director-directed run: what Wire runs at each step; LookML audit with translation classes; plan rulings and parked decisions; deterministic converter and `needs_human.json`; model and content batches as lanes; LookML drift and Omni reverse port; tile-level parity with a pinned as-of; group-by-group cutover |
| [Looker to Omni: A Real Run](./looker-to-omni-real-run) | `bi_migration` | Rittman Analytics' own Looker estate, three dashboards moved to Omni in one day, as it happened | Prompts reproduced as typed; the audit's real counts; 52 rulings and 16 parked decisions; the converter patch layer; every view as a query view; merged results as one-tile query views; two parity runs, 61 of 61 tiles passing; what a person decided and when |
| [Agentic Data Stack](./agentic-data-stack) | `agentic_data_stack` | Boutique analytics consultancy: 47-model sprawl with conflicting metric definitions | Pre-agent canonical model audit; knowledge skill authoring; eval suite with CI runner; accuracy regression prevention |
| [Droughty](./droughty) | `droughty` | Birchfield Capital Management: 240-table Snowflake warehouse, no dbt project | Discovery/audit mode; DBML entity-relationship diagram from `INFORMATION_SCHEMA`; AI field descriptions; base LookML view generation; dbt schema test stubs |
| [Custom Release](./custom) | `custom` | Summit Digital Media: content analytics advisory across BigQuery, Looker and Vertex AI | Consultant-defined artifact set; standard generate/validate/review lifecycle applied to bespoke deliverables; Wire infrastructure without a fixed release shape |
| [Installing and Upgrading](./installing-and-upgrading) | n/a | Claude Code and Gemini CLI installation from scratch | Three-step Claude Code install; Gemini CLI extension install; MCP server configuration; verification commands; keeping the plugin current |
| [Joining Mid-Release](./joining-mid-release) | n/a | Aldgate Financial Services: consultant handover at Phase 3 | `/wire:start` state recovery; `decisions.md` history; Fathom transcript surfacing; first-session planning on an engagement you did not start |
| [Upgrading Your Release](./upgrading-your-release) | n/a | Pennant Capital Management: dormant release resuming after a six-week pause | What `/wire:upgrade` changes and preserves; spec version delta; post-upgrade verification; re-entrancy with in-progress artifacts |
| [Using the Data Model Registry](./data-model-registry) | n/a | Core Dynamics, Inc.: B2B SaaS MRR/NRR model inside a `full_platform` release | Registry check as an inline step of `data_model-generate`; confident vertical match with `adapt`; cross-vertical pattern matched on technique rather than stated origin; what gets recorded in `context.md` and carried into the generated model |
| [dbt Charts Boards](./dbt-charts) | `dbt_development` (also `full_platform`, `dashboard_first`) | Norbury Coffee Roasters: three warehouse folders on BigQuery into one dashboard each, published to dbt Charts Cloud | `dbtcharts-generate --auto` with one lane per subject area; linked dimensions across folders; the design convention overridden per engagement (currency, theme, logo); the eleven validate checks; edits not regeneration after review; the `dct cloud` publish sequence and path-based access |

:::note

The original worked example at [Advanced → Worked Example](../advanced/worked-example) uses a real RA client engagement (Barton Peveril Sixth Form College), whereas the tutorials on this page use fictional scenarios designed to illustrate each release type.

:::
