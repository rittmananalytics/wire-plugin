---
sidebar_position: 4
title: Full Platform
---

# Full Platform Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director).

:::


Some engagements start with a signed SOW and nothing else, and the work runs from the first requirements through to production dashboards and trained users. The full platform release is the release type for that engagement, and all 15 artifact types are in scope, moving through six phases in order:

```mermaid
graph LR
    REQ["Phase 1<br/>Requirements"] --> DESIGN["Phase 2<br/>Design"]
    DESIGN --> DEV["Phase 3<br/>Development"]
    DEV --> TEST["Phase 4<br/>Testing"]
    TEST --> DEPLOY["Phase 5<br/>Deployment"]
    DEPLOY --> ENABLE["Phase 6<br/>Enablement"]
```

## Workflow

At a high level, the six phases and the commands that run them are as follows. Each phase is described in more detail below, together with the point at which it is ready to hand over to the next.

```
/wire:new                                          # release_type: full_platform

# Phase 1: Requirements
/wire:requirements-generate <release-folder>
/wire:requirements-validate <release-folder>
/wire:requirements-review <release-folder>

# Phase 2: Design
/wire:conceptual_model-generate <release-folder>
/wire:conceptual_model-validate <release-folder>
/wire:conceptual_model-review <release-folder>

/wire:pipeline_design-generate <release-folder>
/wire:pipeline_design-validate <release-folder>
/wire:pipeline_design-review <release-folder>

/wire:data_model-generate <release-folder>
/wire:data_model-validate <release-folder>
/wire:data_model-review <release-folder>

/wire:mockups-generate <release-folder>
/wire:mockups-review <release-folder>

# Phase 3: Development
/wire:pipeline-generate <release-folder>
/wire:pipeline-validate <release-folder>
/wire:pipeline-review <release-folder>

/wire:dbt-generate <release-folder>
/wire:dbt-validate <release-folder>
/wire:utils-run-dbt <release-folder>
/wire:dbt-review <release-folder>

/wire:orchestration-generate <release-folder>    # choose Dagster or dbt Cloud
/wire:orchestration-validate <release-folder>
/wire:orchestration-review <release-folder>

/wire:semantic_layer-generate <release-folder>
/wire:semantic_layer-validate <release-folder>
/wire:semantic_layer-review <release-folder>

/wire:dashboards-generate <release-folder>
/wire:dashboards-validate <release-folder>
/wire:dashboards-review <release-folder>

# Phase 4: Testing
/wire:data_quality-generate <release-folder>
/wire:data_quality-validate <release-folder>
/wire:data_quality-review <release-folder>

/wire:uat-generate <release-folder>
/wire:uat-review <release-folder>

# Phase 5: Deployment
/wire:deployment-generate <release-folder>
/wire:deployment-validate <release-folder>
/wire:deployment-review <release-folder>
/wire:utils-deploy-to-dev <release-folder>
/wire:utils-deploy-to-prod <release-folder>

# Phase 6: Enablement
/wire:training-generate <release-folder>
/wire:training-validate <release-folder>
/wire:training-review <release-folder>

/wire:documentation-generate <release-folder>
/wire:documentation-validate <release-folder>
/wire:documentation-review <release-folder>

/wire:archive <release-folder>
```

:::info[Tutorial available]

A worked example of a Full Platform engagement, using a fictional client scenario with realistic command output, agent delegation and reviewer decisions, is available in the [Tutorial: Full Platform](../tutorials/full-platform).

:::


## Phase 1: Requirements (Day 1)

After `/wire:new` completes, copy the SOW PDF and any source materials into the release's `requirements/` directory, and ensure that `engagement/sow.md` and `engagement/context.md` are populated, since these are what the first command reads.

`/wire:requirements-generate` reads the SOW and engagement context, extracts structured requirements (functional, non-functional, data, technical, user), maps each SOW deliverable to the framework artifacts that will produce it and writes `requirements/requirements_specification.md`.

**Ready criteria**: the requirements artifact is `review: approved`.

## Phase 2: Design (Days 2–4)

The design phase follows a defined sequence, and the conceptual model gates everything else, so we take the steps in order.

### Step 1: Conceptual entity model

`/wire:conceptual_model-generate` produces a business-level entity model: an inventory of domain entities, a Mermaid `erDiagram` (entity names and relationships, no columns) and a relationship narrative.

> **Review audience: business stakeholders, not just the technical team.** Approving entities here constrains everything that follows.

### Step 2: Pipeline design + data flow diagram

`/wire:pipeline_design-generate` produces the full pipeline architecture document, covering source system analysis, replication scenarios with cost analysis, scheduling, error handling and the design decisions requiring client input, **plus an embedded Data Flow Diagram (DFD)**.

### Step 3: Logical model (optional)

Between the conceptual model and the physical one sit a set of decisions that are neither business nor dbt: what the primary key of an entity actually is, whether a relationship is one-to-many or many-to-many, which source wins when the same customer exists in three systems, how far to normalise and how a conversion is attributed. `/wire:logical_model-generate` sits between the two models and holds those decisions.

They were previously made implicitly inside `data_model-generate`, which meant they arrived already expressed as dbt models and were hard to review as decisions. The logical model is optional here, and worth running when identity resolution or attribution is contested.

Where the client already models in Modality, this command reads the existing `.mml` rather than restating it. See [Modality models as an input](../advanced/modality-models.md).

### Step 4: Data model specification + physical ERD

`/wire:data_model-generate` produces the complete dbt-layer data model specification, covering source definitions, staging models, integration models, warehouse models with surrogate keys and FK paths and seed files, **plus an embedded Physical ERD**.

> **This is the most important review gate in the full-platform workflow.** Approving a model with incorrect grain, wrong join keys or missing entities is expensive to fix after dbt code is generated.

### Step 5: Dashboard mockups

`/wire:mockups-generate` produces dashboard wireframes, which you review with end users rather than with the technical stakeholder.

**Ready criteria**: every required design artifact is `review: approved`. `logical_model` is optional and is reported as not applicable when it has not been run.


## Business rules discovery (optional first phase)

Before any of the design work above, there is a question that is easy to skip and expensive to leave open: what do the numbers actually mean? New in 4.0, `/wire:business-rules-generate` runs before design and establishes this, one business domain at a time.

It reads the definitions that already exist, in dbt, in LookML and, through `--import`, from systems Wire cannot read such as SAP BW, Hana or SAC, and then asks the people who own the numbers to settle the ones that disagree. The output is a register with one entry per rule, holding every competing definition with the file it came from, what they disagree on, the decision, the named approver and a reconciliation query that runs at generate time rather than in QA.

A rule nobody has decided is recorded with status `unknown`, which passes validate. That is the point of it: a register has to be able to say "nobody has agreed whether in-store orders are in this figure", because that sentence is what stops the number being wrong nine months later.

**The gate is advisory.** ``conceptual_model-generate`` warns when the register has not been reviewed, asks for a one-line reason, records it as an `advisory_skip` and proceeds. Skipping is a real choice; what matters is that the choice is visible.

Full reference: [Business rules discovery](../advanced/business-rules.md).

## Phase 3: Development (Days 5–8)

With the design approved, development is where the models get built. `/wire:dbt-generate` generates all dbt models from the approved data model specification, and the generation embeds comprehensive analytics engineering conventions: field naming rules (`_pk`, `_fk`, `_ts`, `is_`/`has_` prefixes), field ordering, SQL style rules and multi-source framework support. It includes YAML documentation files and automated tests (not_null and unique on every PK, relationships on every FK, which comes to 40–50 tests for a typical mid-sized engagement).

`/wire:orchestration-generate` prompts you to choose between **Dagster** (Python-native, assets-first) and **dbt Cloud** (managed scheduling).

`/wire:semantic_layer-generate` generates LookML views, explores, measures and dimension definitions from the approved dbt models.

**Ready criteria**: all five development artifacts are `review: approved` and the dbt tests are passing.

### Optional: dbt Charts boards

If the client wants dashboards that live with the dbt models rather than in a BI tool, ask for them and Wire adds the optional `dbtcharts` artifact after the dbt models pass validation: `/wire:dbtcharts-generate <release>` scaffolds one [dbt Charts](../advanced/dbt-charts) board per warehouse subject area from the dbt manifest and catalog, curates the charts against the requirements and the business rules register, and validates them with `dct`, including a warehouse dry-run. It can run alongside `dashboards`, or instead of it where no BI tool is in scope.

### Optional: Agents Schema

If AI agents will query the warehouse, ask for the optional `agents_schema` artifact once the dbt models pass validation (the semantic layer gate is advisory). `/wire:agents_schema-generate <release>` publishes the release's metadata into the warehouse's own `AGENTS` schema through dbt Labs' [Agents Schema](../advanced/agents-schema): the dbt manifest, the LookML, and skills assembled from the release's knowledge, including a warehouse guide the consultant completes from the business rules register. It writes the pinned GitHub workflow that keeps the schema current on every merge, and `/wire:agents_schema-validate` checks the warehouse holds exactly what the plan said.

## Phase 4: Testing (Days 9–10)

`/wire:data_quality-generate` generates additional data quality tests beyond the embedded dbt tests: freshness checks, row count reconciliation, cross-system validation and custom business rules.

`/wire:uat-generate` generates a UAT plan mapped to the functional requirements, and you should not proceed to deployment without UAT sign-off.

## Phase 5: Deployment (Day 11)

`/wire:deployment-generate` generates the deployment runbook, CI/CD pipeline configuration, monitoring and alerting setup and rollback procedures.

## Phase 6: Enablement (Days 12–13)

`/wire:training-generate` generates two training packages:
- **Data team enablement**: a technical session plan (two hours)
- **End user training**: a dashboard usage session (90 minutes)

## Utility commands available at any phase

Six utility commands are available at any phase:

- **`/wire:utils-run-dbt`**: runs the generated dbt models in dbt Cloud or locally
- **`/wire:utils-deploy-to-dev`**: deploys to the development environment
- **`/wire:utils-deploy-to-prod`**: deploys to the production environment
- **`/wire:utils-meeting-context`**: retrieves Fathom meeting transcripts for context
- **`/wire:utils-jira-sync`**: syncs artifact status to Jira issues
- **`/wire:utils-atlassian-search`**: searches Confluence for documentation

> **Tip**: Run `/wire:playbook-generate <release-folder>` after requirements are approved to get a visual end-to-end plan for this release.
