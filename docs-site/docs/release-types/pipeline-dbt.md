---
sidebar_position: 5
title: Pipeline + dbt
---

# Pipeline + dbt Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


A new data source often has to be connected through to the dbt layer while the BI tool and semantic layer above it are already in place, or are out of scope for this piece of work. The pipeline and dbt release is for that situation: it takes the source from requirements through pipeline design, data model, pipeline and dbt to data quality and deployment, and leaves the reporting layer alone.

**In-scope artifacts**: `requirements`, `pipeline_design`, `data_model`, `pipeline`, `dbt`, `data_quality`, `deployment`

**Out of scope**: `mockups`, `semantic_layer`, `dashboards`, `uat`, `training`, `documentation`

## Choosing a pipeline replication tool

Which tool should move the data? `/wire:pipeline_design-generate` includes a **pipeline tool selection step** for this, and the framework supports three managed tools plus a custom option:

| Tool | Best for | Cost model | Infrastructure |
|------|----------|-----------|----------------|
| **Fivetran** | SaaS sources, managed CDC, minimal engineering | MAR-based | Fully managed |
| **dlt** | Python-native teams, cost-sensitive, custom APIs | Open-source | Scripts + dlt Cloud |
| **Airbyte** | Mixed sources, open-source preference | Open-source / Cloud | Self-hosted or Airbyte Cloud |
| **Custom** | Highly specialised sources, full control | Engineering time | Self-managed |

The chosen tool is recorded as `pipeline_tool` in `status.md`, and all downstream `/wire:pipeline-*` commands read this value and route automatically, so you make the choice once.

## Workflow

At a high level, the release runs as follows, with the business rules step optional and the rest in order:

```
/wire:new                                   # release_type: pipeline_only

/wire:business-rules-generate <release-folder>   # Optional, new in 4.0
/wire:business-rules-validate <release-folder>
/wire:business-rules-review <release-folder>

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

A worked example of a Pipeline and dbt engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Pipeline and dbt](../tutorials/pipeline-dbt).

:::


> **Tip**: Run `/wire:playbook-generate <release-folder>` after the pipeline design is approved to generate a visual delivery plan.

## Business rules discovery (optional first phase)

Before the design work begins, there is a question that is easy to skip and expensive to leave open: what do the numbers actually mean? New in 4.0, `/wire:business-rules-generate` runs before design and establishes this, one business domain at a time.

It reads the definitions that already exist, in dbt, in LookML and, through `--import`, from systems Wire cannot read such as SAP BW, Hana or SAC, and then asks the people who own the numbers to settle the ones that disagree. The output is a register with one entry per rule, holding every competing definition with the file it came from, what they disagree on, the decision, the named approver and a reconciliation query that runs at generate time rather than in QA.

A rule nobody has decided is recorded with status `unknown`, which passes validate. That is the point of it: a register has to be able to say "nobody has agreed whether in-store orders are in this figure", because that sentence is what stops the number being wrong nine months later.

**The gate is advisory.** ``pipeline_design-generate`` warns when the register has not been reviewed, asks for a one-line reason, records it as an `advisory_skip` and proceeds. Skipping is a real choice; what matters is that the choice is visible.

Full reference: [Business rules discovery](../advanced/business-rules.md).

## Reading an existing Modality model

Where the client already models their data in Modality, new in 4.0, `/wire:utils-modality-link <release-folder>` points the release at it and sets `model_source: modality`, and `pipeline_design-generate` then reads entities, sources and cardinality from the `.mml` files rather than deriving them.

The requirements are still read. An entity in the model but not in the requirements is excluded with a reason, and one in the requirements but not in the model becomes an open question. Every value taken from the model cites the file it came from, and the matching validate commands gain a two-direction `modality_coverage` check.

Full reference: [Modality models as an input](../advanced/modality-models.md).

The source list and the per-entity landing tables come from `sources.mml`, while the replication tool and the schedule are not in MML and are still asked for.
