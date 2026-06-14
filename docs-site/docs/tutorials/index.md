---
sidebar_position: 0
title: "Tutorials"
---

# Wire Framework Tutorials

These tutorials are scenario-based walkthroughs of each Wire release type, built around fictional client engagements. They go further than the release-type reference pages: each one shows realistic command output, how agent delegation plays out in practice, which MCP integrations activate at each gate, and the decision-making context that shapes what gets generated. The scenarios are constructed to surface the parts of each release type that are easy to misread from the reference alone — appetite versus scope in a Shape Up discovery, the two-zone safety model in a platform migration, the seed-based prototyping sequence in a Dashboard First release.

The supplementary tutorials at the bottom of the table cover the operational mechanics: installing and upgrading the plugin, joining an active engagement mid-stream, and upgrading an existing release folder when a newer version of Wire is installed. Read the tutorial for your release type before running `/wire:new`, or keep it open alongside the terminal during delivery. The supplementary tutorials are most useful when something about the environment or the engagement handover is non-standard.

## Tutorial index

| Tutorial | Release Type | Scenario | Key Features Shown |
|---|---|---|---|
| [Full Platform](./full-platform) | `full_platform` | Eversholt Brewing Co — Shopify, BrewMan ERP, and HubSpot into BigQuery + Looker | All six phases end-to-end; parallel dbt agent fan-out; Jira hierarchy creation; `decisions.md` accumulation across agents |
| [dbt Development](./dbt-development) | `dbt_development` | Vantage Financial Reporting — Stripe, Salesforce, and PostgreSQL into Snowflake | Transformation-only scope; cross-system customer identity resolution; 38 schema tests; skipping pipeline and BI phases |
| [Pipeline and dbt](./pipeline-dbt) | `pipeline_only` | Meridian Logistics Group — complex multi-source ingestion with a bespoke SFTP connector | Connector configuration and activation; custom Cloud Function pipeline; staging-layer focus before warehouse design is committed |
| [Discovery (Shape Up)](./discovery-shape-up) | `discovery_shape_up` | Hallmark Property Partners — real estate investment go/no-go scoping | Appetite document; scope story map; risk catalogue; Fathom transcript integration; SOW-ready output in two days |
| [Discovery (SOP)](./discovery-sop) | `sop_discovery` | Thornfield Private Healthcare — four-clinic GDPR-sensitive assessment | Formal stakeholder interviews with MoSCoW categorisation; data inventory; capability assessment; Jira Epic auto-created at `/wire:new` |
| [Dashboard Extension](./dashboard-extension) | `dashboard_extension` | Foxwood Commerce Ltd — marketing dashboard expansion on an existing Looker instance | Starting from `semantic_layer-generate`; existing LookML pattern-matching; no pipeline or dbt work in scope |
| [Dashboard First](./dashboard-first) | `dashboard_first` | Claybrook Media Group — interactive HTML mockup before any data layer is committed | `dashboard-mock-developer` agent; Chart.js interactive prototypes; atomic derivation of viz catalog, dashboard spec, and data model requirements; CSV seed files with referential integrity; mock-to-real refactor sequence |
| [Enablement](./enablement) | `enablement` | Hargreave Insurance Ltd — platform enablement and technical handover | `delivery-lead` agent reading prior build artifacts; two-audience training generation; architecture and field-catalogue documentation |
| [Platform Migration](./platform-migration) | `platform_migration` | Gatwick Data Partners — Snowflake to BigQuery migration | Audit zone versus migration zone; five equivalency check types; `equivalency-investigate` / `equivalency-fix` loop; cutover gate requiring `checks_failing: 0` and written sign-off |
| [Agentic Data Stack](./agentic-data-stack) | `agentic_data_stack` | Boutique analytics consultancy — 47-model sprawl with conflicting metric definitions | Pre-agent canonical model audit; knowledge skill authoring; eval suite with CI runner; accuracy regression prevention |
| [Droughty](./droughty) | `droughty` | Birchfield Capital Management — 240-table Snowflake warehouse, no dbt project | Discovery/audit mode; DBML entity-relationship diagram from `INFORMATION_SCHEMA`; AI field descriptions; base LookML view generation; dbt schema test stubs |
| [Custom Release](./custom) | `custom` | Summit Digital Media — content analytics advisory across BigQuery, Looker, and Vertex AI | Consultant-defined artifact set; standard generate/validate/review lifecycle applied to bespoke deliverables; Wire infrastructure without a fixed release shape |
| [Installing and Upgrading](./installing-and-upgrading) | — | Claude Code and Gemini CLI installation from scratch | Three-step Claude Code install; Gemini CLI extension install; MCP server configuration; verification commands; keeping the plugin current |
| [Joining Mid-Release](./joining-mid-release) | — | Aldgate Financial Services — consultant handover at Phase 3 | `/wire:start` state recovery; `decisions.md` history; Fathom transcript surfacing; first-session planning on an engagement you did not start |
| [Upgrading Your Release](./upgrading-your-release) | — | Pennant Capital Management — dormant release resuming after a six-week pause | What `/wire:upgrade` changes and preserves; spec version delta; post-upgrade verification; re-entrancy with in-progress artifacts |

:::note

The original worked example at [Advanced → Worked Example](../advanced/worked-example) uses a real RA client engagement (Barton Peveril Sixth Form College). These tutorials use fictional scenarios specifically designed to illustrate each release type.

:::
