---
sidebar_position: 12
title: Agentic Data Stack
---

# Agentic Data Stack Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


Many clients already have the warehouse, the dbt project and the BI tool, and what they now want is an AI that answers business questions from that platform accurately, and keeps answering them accurately as the platform changes underneath it. The Agentic Data Stack release type (`release_type: agentic_data_stack`) is an **overlay for an existing data platform** for exactly this purpose, and it assumes that a warehouse, a dbt project and a BI tool are already in place. The deliverable is a governed self-service analytics capability: an AI that answers business questions accurately and stays accurate as the data platform evolves.

This is not a platform build. If a client's warehouse and dbt project do not yet exist, start with `full_platform` or `pipeline_only` first.

## When to use it

- A client already has a data platform and wants an AI that can answer business questions reliably
- The data team has tried a self-service SQL agent and accuracy is below 70%
- The engagement goal is to reduce analyst time spent answering ad-hoc data questions

## Phase overview

The release runs through five phases, each with its own artifacts:

| Phase | Duration | Artifacts |
|---|---|---|
| Audit | 1–2 weeks | dataset_audit, metric_audit, query_audit |
| Design | 1 week | governance_design, semantic_layer_design |
| Build | 2 weeks | canonical_models, lookml_views (Looker only), semantic_layer, knowledge_skill, agent_config |
| Validation | 1 week | eval_suite, adversarial_config |
| Launch | 3–5 days | launch_gate, enablement |

## Command sequence

The full command sequence, phase by phase, is as follows:

```bash
# Phase 1 — Audit (run all three in parallel)
/wire:ads-audit-all YYYYMMDD_client_agentic_data_stack

# Or run individually:
/wire:ads_dataset-audit-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_metric-audit-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_query-audit-generate YYYYMMDD_client_agentic_data_stack

# Validate and review each audit
/wire:ads_dataset-audit-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_dataset-audit-review YYYYMMDD_client_agentic_data_stack
/wire:ads_metric-audit-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_metric-audit-review YYYYMMDD_client_agentic_data_stack
/wire:ads_query-audit-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_query-audit-review YYYYMMDD_client_agentic_data_stack

# Phase 2 — Design
/wire:ads_governance-design-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_governance-design-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_governance-design-review YYYYMMDD_client_agentic_data_stack
/wire:ads_semantic-layer-design-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_semantic-layer-design-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_semantic-layer-design-review YYYYMMDD_client_agentic_data_stack

# Phase 3 — Build
/wire:ads_canonical-models-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_canonical-models-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_canonical-models-review YYYYMMDD_client_agentic_data_stack

# LookML views — Looker projects only
/wire:ads_lookml-views-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_lookml-views-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_lookml-views-review YYYYMMDD_client_agentic_data_stack

/wire:ads_semantic-layer-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_semantic-layer-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_semantic-layer-review YYYYMMDD_client_agentic_data_stack
/wire:ads_knowledge-skill-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_knowledge-skill-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_knowledge-skill-review YYYYMMDD_client_agentic_data_stack
/wire:ads_agent-config-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_agent-config-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_agent-config-review YYYYMMDD_client_agentic_data_stack

# Phase 4 — Validation
/wire:ads_eval-suite-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_eval-suite-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_eval-suite-review YYYYMMDD_client_agentic_data_stack
/wire:ads_adversarial-config-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_adversarial-config-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_adversarial-config-review YYYYMMDD_client_agentic_data_stack

# Phase 5 — Launch
/wire:ads_launch-gate-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_launch-gate-review YYYYMMDD_client_agentic_data_stack
/wire:ads_analytics-enablement-generate YYYYMMDD_client_agentic_data_stack
/wire:ads_analytics-enablement-validate YYYYMMDD_client_agentic_data_stack
/wire:ads_analytics-enablement-review YYYYMMDD_client_agentic_data_stack
```

:::info[Tutorial available]

A worked example of an Agentic Data Stack engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Agentic Data Stack](../tutorials/agentic-data-stack).

:::


## The eval suite and launch gate

Of all the artifacts in this release, the eval suite is the most important, because it is what keeps the AI accurate once the platform starts to change underneath it. It produces:
- Per-domain YAML question-answer pairs (a minimum of ten per domain)
- A CI runner script that checks accuracy against every schema change
- Per-domain accuracy thresholds (default 90%)

A domain that falls below its threshold is blocked until the specific failing questions are fixed. Anthropic documented accuracy falling from 95% to 65% within a month without active maintenance, and the eval suite together with its CI integration is the mechanism that prevents this.

## Knowledge skill colocation

Where should the knowledge about a domain live? Next to the models it describes. The `/wire:ads_knowledge-skill-generate` command writes `DOMAIN_REFERENCE.md` files into the client's dbt project alongside their mart models:

```
models/marts/
  orders/
    fct_orders.sql
    fct_orders.yml
    DOMAIN_REFERENCE.md   ← generated and maintained here
  customers/
    dim_customers.sql
    dim_customers.yml
    DOMAIN_REFERENCE.md
```

A CI check template is included that flags when a model PR does not update the collocated reference file.

## Optional: Agents Schema

The knowledge skills, the canonical models and the LookML views can also be published into the warehouse itself, through dbt Labs' [Agents Schema](../advanced/agents-schema). The optional `agents_schema` artifact runs in the implementation phase once `canonical_models` passes validation (the `knowledge_skill` and `lookml_views` gates are advisory). `/wire:agents_schema-generate <release>` turns each `DOMAIN_REFERENCE.md` into a `skill/<domain>` row in `AGENTS.ROOT` with a `uses:` declaration derived from the models in its folder, publishes the manifest and the LookML alongside, and writes the pinned GitHub workflow that keeps the schema current. An agent that queries the warehouse then finds the same context the `agent_config` routes to, without leaving SQL.

## What the release delivers

At the end of the engagement, the client has:
1. A governance-clean dbt project with canonical models
2. An extended semantic layer covering the most common analytical questions
3. Per-domain knowledge skill files in their dbt repo, with CI maintenance checks
4. An installable Wire skill (`agentic-data-stack-SKILL.md`) that their data team runs in Claude Code
5. A per-domain eval suite wired into CI with accuracy baselines
6. User training documentation and a data team maintenance guide

## Business rules and the metric audit

New in 4.0, `ads_metric-audit` keeps everything it did, the coverage-gap scoring against `query_audit`'s real questions and the semantic-layer promotion recommendations, but the half it shares with the new [business rules register](../advanced/business-rules.md) now lives in one place.

`specs/utils/definition_extract.md` holds the enumeration across the dbt Semantic Layer, LookML and `schema.yml`, together with the conflict taxonomy (filter, aggregation, grain, name collision). Both commands call it, so the algorithm cannot drift between them. It also adds an `--import` path for definitions in systems Wire cannot read, such as SAP BW, Hana or SAC, with the export date and the person who took it recorded.

Where a release also carries `artifacts/business_rules.yaml`, the metric audit reads the agreed decisions from it rather than re-deriving a settled conflict as open. A rule with a decision and a named approver is settled, and putting a second, weaker recommendation next to a signed-off one helps nobody.

`business_rules` itself is not part of this release type, since `agentic_data_stack` already splits find-conflicts from decide-conflicts between `metric_audit` and `ads_governance-design`.
