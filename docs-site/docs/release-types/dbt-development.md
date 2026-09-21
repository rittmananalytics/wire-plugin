---
sidebar_position: 6
title: dbt Development
---

# dbt Development Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


Often the data is already in the warehouse, loaded by Fivetran, Stitch or manual loads, and what the client needs is the dbt transformation layer built or extended on top of it. Use this release type for that case, where the loading is done and the work is in the models.

**In-scope artifacts**: `requirements`, `conceptual_model`, `data_model`, `dbt`, `data_quality`

## Workflow

At a high level, the release runs as follows, with the business rules step optional and the rest in order:

```
/wire:new                                         # release_type: dbt_development

/wire:business-rules-generate <release-folder>    # Optional, new in 4.0 — agree what the numbers mean first
/wire:business-rules-validate <release-folder>
/wire:business-rules-review <release-folder>

/wire:requirements-generate <release-folder>      # Focus on transformation requirements
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

/wire:conceptual_model-generate <release-folder>
/wire:conceptual_model-validate <release-folder>
/wire:conceptual_model-review <release-folder>

/wire:data_model-generate <release-folder>        # Read existing source schema + requirements
/wire:data_model-validate <release-folder>
/wire:data_model-review <release-folder>

/wire:dbt-generate <release-folder>
/wire:dbt-validate <release-folder>
/wire:utils-run-dbt <release-folder>
/wire:dbt-review <release-folder>

/wire:data_quality-generate <release-folder>
/wire:data_quality-validate <release-folder>
/wire:data_quality-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a dbt Development engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: dbt Development](../tutorials/dbt-development).

:::


**Tips for dbt-only releases**:
- Add any existing dbt project files (existing `schema.yml`, source definitions, SQL examples) to `requirements/` before running `data_model-generate`, so that the AI can use them to understand the existing model structure and extend it correctly
- Store SQL examples from the source database (schema introspection results, sample queries) so that the AI understands the actual column names and types

> **Tip**: Run `/wire:playbook-generate <release-folder>` after requirements are approved.

## Optional: dbt Charts boards

A dbt development release often has no BI tool in scope, and yet the client wants to see the numbers. The optional `dbtcharts` artifact answers that: once `dbt` passes validation, `/wire:dbtcharts-generate <release>` writes one [dbt Charts](../advanced/dbt-charts) board per warehouse subject area, as YAML in the dbt project reading the models through `ref()`, validated and rendered by the `dct` CLI. The scaffold is deterministic and the curation is recorded, so the reviewer sees what was proposed and what changed. `/wire:dbtcharts-validate` runs the `dct` checks and Wire's own, and `/wire:dbtcharts-review` presents the renders for sign-off.

## Optional: Agents Schema

Where AI agents will query the warehouse, the optional `agents_schema` artifact publishes the dbt project's metadata into the warehouse's own `AGENTS` schema through dbt Labs' [Agents Schema](../advanced/agents-schema): one row per model, column and dependency, plus skills assembled from the release's knowledge and a warehouse guide the consultant completes. `/wire:agents_schema-generate <release>` writes the pinned GitHub workflow, `agents.yml` and the skills; `/wire:agents_schema-validate` compares the warehouse against the plan; `/wire:agents_schema-review` presents what an agent will be told for sign-off. It runs after `dbt` passes validation; the `semantic_layer` gate is advisory because a dbt-only publication is a legitimate choice.

## Business rules discovery (optional first phase)

Before the design work begins, there is a question that is easy to skip and expensive to leave open: what do the numbers actually mean? New in 4.0, `/wire:business-rules-generate` runs before design and establishes this, one business domain at a time.

It reads the definitions that already exist, in dbt, in LookML and, through `--import`, from systems Wire cannot read such as SAP BW, Hana or SAC, and then asks the people who own the numbers to settle the ones that disagree. The output is a register with one entry per rule, holding every competing definition with the file it came from, what they disagree on, the decision, the named approver and a reconciliation query that runs at generate time rather than in QA.

A rule nobody has decided is recorded with status `unknown`, which passes validate. That is the point of it: a register has to be able to say "nobody has agreed whether in-store orders are in this figure", because that sentence is what stops the number being wrong nine months later.

**The gate is advisory.** ``data_model-generate`` warns when the register has not been reviewed, asks for a one-line reason, records it as an `advisory_skip` and proceeds. Skipping is a real choice; what matters is that the choice is visible.

A transformation-only release is the case where this matters most, because the models being built or rebuilt are where a definition becomes permanent.

Full reference: [Business rules discovery](../advanced/business-rules.md).
