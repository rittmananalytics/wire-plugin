---
sidebar_position: 12
title: Agentic Data Stack
---

# Agentic Data Stack Release

The Agentic Data Stack release type (`release_type: agentic_data_stack`) is an **overlay for an existing data platform** — it assumes a warehouse, a dbt project, and a BI tool are already in place. The deliverable is a governed self-service analytics capability: an AI that answers business questions accurately and stays accurate as the data platform evolves.

This is not a platform build. If a client's warehouse and dbt project don't yet exist, start with `full_platform` or `pipeline_only` first.

## When to use it

- A client already has a data platform and wants an AI that can answer business questions reliably
- The data team has tried a self-service SQL agent and accuracy is below 70%
- The engagement goal is to reduce analyst time spent answering ad-hoc data questions

## Phase overview

| Phase | Duration | Artifacts |
|---|---|---|
| Audit | 1–2 weeks | dataset_audit, metric_audit, query_audit |
| Design | 1 week | governance_design, semantic_layer_design |
| Build | 2 weeks | canonical_models, lookml_views (Looker only), semantic_layer, knowledge_skill, agent_config |
| Validation | 1 week | eval_suite, adversarial_config |
| Launch | 3–5 days | launch_gate, enablement |

## Command sequence

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

A worked example of a Agentic Data Stack engagement — using a fictional client scenario with realistic command output, agent delegation, and reviewer decisions — is available in the [Tutorial: Agentic Data Stack](../tutorials/agentic-data-stack).

:::


## The eval suite and launch gate

The eval suite is the most important artifact in the release. It produces:
- Per-domain YAML question-answer pairs (minimum 10 per domain)
- A CI runner script that checks accuracy against every schema change
- Per-domain accuracy thresholds (default 90%)

A domain that falls below its threshold is blocked until the specific failing questions are fixed. Anthropic documented accuracy falling from 95% to 65% within a month without active maintenance. The eval suite and its CI integration are the mechanism that prevents this.

## Knowledge skill colocation

The `/wire:ads_knowledge-skill-generate` command writes `DOMAIN_REFERENCE.md` files into the client's dbt project alongside their mart models:

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

A CI check template is included that flags when a model PR doesn't update the collocated reference file.

## What the release delivers

At engagement end, the client has:
1. A governance-clean dbt project with canonical models
2. An extended semantic layer covering the most common analytical questions
3. Per-domain knowledge skill files in their dbt repo, with CI maintenance checks
4. An installable Wire skill (`agentic-data-stack-SKILL.md`) their data team runs in Claude Code
5. A per-domain eval suite wired into CI with accuracy baselines
6. User training documentation and a data team maintenance guide
