---
sidebar_position: 5
title: Pipeline + dbt
---

# Pipeline + dbt Release

Use this when a new data source needs connecting through to the dbt layer, but a BI tool / semantic layer is already in place or out of scope.

**In-scope artifacts**: `requirements`, `pipeline_design`, `data_model`, `pipeline`, `dbt`, `data_quality`, `deployment`

**Out of scope**: `mockups`, `semantic_layer`, `dashboards`, `uat`, `training`, `documentation`

## Choosing a pipeline replication tool

`/wire:pipeline_design-generate` includes a **pipeline tool selection step**. The framework supports three managed tools plus a custom option:

| Tool | Best for | Cost model | Infrastructure |
|------|----------|-----------|----------------|
| **Fivetran** | SaaS sources, managed CDC, minimal engineering | MAR-based | Fully managed |
| **dlt** | Python-native teams, cost-sensitive, custom APIs | Open-source | Scripts + dlt Cloud |
| **Airbyte** | Mixed sources, open-source preference | Open-source / Cloud | Self-hosted or Airbyte Cloud |
| **Custom** | Highly specialised sources, full control | Engineering time | Self-managed |

The chosen tool is recorded as `pipeline_tool` in `status.md`. All downstream `/wire:pipeline-*` commands read this value and route automatically.

## Workflow

```
/wire:new                                   # release_type: pipeline_dbt

/wire:requirements-generate <release-folder>
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

/wire:pipeline_design-generate <release-folder>
/wire:pipeline_design-validate <release-folder>
/wire:pipeline_design-review <release-folder>

/wire:data_model-generate <release-folder>
/wire:data_model-validate <release-folder>
/wire:data_model-review <release-folder>

/wire:pipeline-generate <release-folder>
/wire:pipeline-validate <release-folder>
/wire:pipeline-review <release-folder>

/wire:dbt-generate <release-folder>
/wire:dbt-validate <release-folder>
/wire:utils-run-dbt <release-folder>
/wire:dbt-review <release-folder>

/wire:data_quality-generate <release-folder>
/wire:data_quality-validate <release-folder>
/wire:data_quality-review <release-folder>

/wire:deployment-generate <release-folder>
/wire:deployment-validate <release-folder>
/wire:deployment-review <release-folder>
/wire:utils-deploy-to-prod <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a Pipeline and dbt engagement — using a fictional client scenario with realistic command output, agent delegation, and reviewer decisions — is available in the [Tutorial: Pipeline and dbt](../tutorials/pipeline-dbt).

:::


> **Tip**: Run `/wire:playbook-generate <release-folder>` after the pipeline design is approved to generate a visual delivery plan.
