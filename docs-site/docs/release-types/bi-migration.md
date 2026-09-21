---
sidebar_position: 13
title: BI Tool Migration
---

# BI Tool Migration Release

:::tip[You do not have to type these commands]

Since v4.0.0, on Claude Code, you can direct this release in plain language
instead: say what you want done and Wire works out which command that is from
this release type's definition, runs it, tells you what it did and stops at
every review gate for your decision. The commands, the artifacts and the record
on disk are identical either way, and typing them still works. See
[The Release Director Model](../advanced/release-director). This release type
was built for that model: model batches, content batches and parity sweeps run
as lanes, and the rulings (parity or redesign, what to drop, PDT disposition,
cutover) are yours. The
[Looker to Omni Migration tutorial](../tutorials/looker-to-omni-migration) runs
a full release this way and names the command Wire runs at each step.

:::

Moving a reporting layer from one BI tool to another is a different job from moving a warehouse: the warehouse and the dbt layer stay where they are, and what has to be rebuilt, checked and switched over is the semantic model and the content that sits on it. The BI Tool Migration release type is for that job. The first and, in 4.0.0, only pair is **Looker to Omni**: LookML views and explores become Omni views and topics on a model branch, Looker dashboards and Looks become Omni dashboards, every migrated tile is proven equivalent before users are switched and Looker is decommissioned after a parallel run.

It is not the same as migrating an Omni estate between warehouses. That is `platform_migration` with `migration.reporting_tool: omni`, where the pivot is the Omni connection, whereas here the pivot is the semantic model itself.

**Supported pairs**: `looker_to_omni`

The flow, from the Looker estate at the start to Looker retired at the end, is as follows:

```mermaid
flowchart TD
    START([Looker estate]):::event
    BR[Business rules<br/><small>optional: agree what the numbers mean</small>]:::optional
    LA[Looker audit<br/><small>LookML constructs classified; content ranked by usage</small>]:::stage
    OA[Omni audit<br/><small>optional: brownfield target</small>]:::optional
    PLAN[Migration plan<br/><small>rulings, drop list, PDT disposition, permissions, batches, register</small>]:::stage
    TGT[Omni target setup<br/><small>connection, model branch, schema refresh, groups</small>]:::stage
    subgraph MODEL["Model migration (per batch, as lanes)"]
        direction LR
        M1[Converter<br/>LookML to Omni YAML]:::sub
        M2[Lint]:::sub
        M3[Omni validate]:::sub
    end
    subgraph CONTENT["Content migration (per batch, as lanes)"]
        direction LR
        C1[Plan<br/>fields mapped, tiles skipped with reasons]:::sub
        C2[Write<br/>omni documents v2]:::sub
    end
    EQ{Parity<br/><small>tile-level: Looker vs Omni, pinned as-of, verdict taxonomy</small>}:::gate
    CUT[Cutover<br/><small>parallel run, access switch, schedules, decommission</small>]:::stage
    EN[Training and documentation<br/><small>optional</small>]:::optional
    DONE([Omni live, Looker retired]):::event

    START --> BR --> LA
    START --> LA
    LA --> PLAN
    OA -.-> PLAN
    PLAN --> TGT --> M1 --> M2 --> M3 --> C1 --> C2 --> EQ
    EQ -->|any tile fails| MODEL
    EQ -->|every in-scope tile pass or pass_qualified| CUT --> EN --> DONE

    classDef event fill:#181B25,color:#fff,stroke:#181B25
    classDef stage fill:#E0E0FF,stroke:#C9CBF0,color:#181B25
    classDef optional fill:#F7F7FA,stroke:#C9CBF0,color:#181B25,stroke-dasharray: 4 3
    classDef sub fill:#fff,stroke:#CFE8CF,color:#181B25
    classDef gate fill:#EBFFEB,stroke:#4E7A56,color:#181B25
```

## Phases and commands

Each phase produces one artifact with its own commands, and the table below gives, for each, the artifact, the commands and what it produces:

| Phase | Artifact | Commands | What it produces |
|---|---|---|---|
| Business Rules (optional) | `business_rules` | `/wire:business-rules-*` | The register of metric definitions. LookML measures are its input. |
| Audit | `looker_audit` | `/wire:looker-audit-generate`, `-validate`, `-review` | `audit/looker_audit.md` plus two catalogues: every LookML construct with a translation class (`mechanical`, `assisted`, `redesign`) and every dashboard, Look, tile and schedule with usage. |
| Audit (optional) | `omni_audit` | `/wire:omni-audit-*` | Only when the client already has Omni content. |
| Plan | `bi_migration_plan` | `/wire:bi-migration-plan-generate`, `-validate`, `-review` | Usage-ranked inventory, the director's rulings, model and content batches, the migration register bootstrapped with one row per in-scope object. |
| Target | `omni_target_setup` | `/wire:omni-target-setup-generate`, `-validate`, `-review` | Connection check, model branch, schema refresh, groups and user attributes. |
| Model | `omni_model` | `/wire:omni-model-generate --batch N`, `-lint`, `-validate`, `-review` | Omni views, topics and relationships on the branch, written by the deterministic converter; `needs_human.json` for what it could not translate. |
| Content | `omni_content` | `/wire:omni-content-generate --batch N`, `-validate`, `-review` | A plan per dashboard (fields mapped, controls, layout, skipped tiles with reasons), then documents created through the Omni v2 document API. |
| Parity | `bi_equivalency` | `/wire:bi-equivalency-validate` | Tile-level comparison of Looker and Omni results under a pinned as-of, verdicts in the migration taxonomy. The cutover gate. |
| Cutover | `cutover` | `/wire:cutover-*` | Parallel-run window, group-by-group access switch, schedules and alerts recreated, Looker read-only then decommissioned, rollback by re-enabling Looker. |
| Enablement (optional) | `training`, `documentation` | `/wire:training-*`, `/wire:documentation-*` | |

## Optional: Agents Schema

Once a model batch passes validation, the optional `agents_schema` artifact can publish the migrated Omni model (views, dimensions, measures, topics and joins) into the warehouse's `AGENTS` schema through dbt Labs' [Agents Schema](../advanced/agents-schema), so agents that query the warehouse read the new semantic surface as it lands. `/wire:agents_schema-generate <release>` points the `omni` provider at the connection-level folder of the Omni Git sync and writes the pinned GitHub workflow; the LookML side is not published, since it is the surface being retired.

## The converter

Why is the model phase split between a script and an agent? `scripts/lookml_to_omni.py` is the deterministic core of the model phase. It reads the LookML project and writes an Omni model directory: `<SCHEMA>/<view>.view`, `<explore>.topic`, `relationships.yaml`, plus `needs_human.json` and a conversion summary. Same input, identical output, no AI call. The agent's job is what the script cannot decide: topic design, naming and each `needs_human` item.

Three classes decide what happens to each LookML construct:

| Class | Converter | Agent |
|---|---|---|
| `mechanical` | Emits it | Nothing |
| `assisted` | Emits a best effort with a note, or withholds it where a wrong emission would silently change a number | Confirms or writes it by hand before validate |
| `redesign` | Emits nothing, records the Omni alternative | Applies the plan's ruling or parks a decision |

Liquid, parameters, filter-only fields, persistent derived tables, `html` and running totals are `redesign`. The pair files at `bi_pairs/looker_to_omni/` hold the full table and six worked examples, and the test suite checks the examples against the converter on every run.

## Under the release director

This release type was built for the release director model, and four things follow from that:

- **Rulings**, each a parked decision: parity or redesign per dashboard tier, the drop list (default: no views in 90 days and last viewed over 180 days ago), PDT disposition (dbt model or Omni query view), permission mapping, topic architecture, batch order, parallel-run window, cutover date.
- **Lanes**: model slices (one batch of views and explores), content batches (one batch of dashboards), parity sweeps (one batch's tiles) and a permissions lane. Flat, tree-owned per batch folder, single writer of the record.
- **Budget**: parity runs query the same warehouse from both tools. The plan's `parity_scope` limits comparison to prioritised dashboards, and the operating model's cost rules apply.
- **Consolidation**: before a batch is reported ready, the orchestrator re-runs the Omni validator on the branch and re-reads verdicts from the register, not from the lane's report.

## Keeping the repos in sync

Both client repositories keep changing while the migration runs, and the release uses the same three mechanisms `platform_migration` uses, adapted to a BI migration, to keep up with them:

| Direction | Command | What it does |
|---|---|---|
| Upstream LookML into the delivery repo | `/wire:migration-source-register <release> lookml <github url>`, `/wire:migration-source-refresh <release> lookml` | Snapshots the client's LookML repo under `migration/source_snapshot/lookml/` and records the commit. The audit, the converter and the drift gate read the snapshot, never the live repo, and every catalogue and register row carries the commit it came from. |
| Upstream drift | `/wire:migration-drift-generate` (optional artifact, on a schedule or a client-watch trigger) | Diffs the refreshed LookML against each row's `last_migrated_commit`: `modified` (re-classified; blocking when a mechanical view gained Liquid), `removed`, `renamed`, `impacted` topics, new files with no row. Content drift: a dashboard edited in Looker after its batch is `content_drifted`. |
| Downstream Omni model back into the delivery repo | `/wire:omni-model-reverse-port` | Reads what client modellers changed in Omni (from the git-connected model repo registered as `omni_model`, or live with `yaml-get`) and classifies every emitted file: `identical`, `client_ahead` (ported), `delivery_ahead` (left), `conflict` (reported, never written). Run before each new batch and before parity. |

`/wire:new` asks for both repo URLs. Without a LookML git URL the audit still runs from a local checkout, but drift detection is not available.

## What stays manual

Text and markdown tiles, styling and colour themes, table calculations that reference runtime values and anything written in Liquid. Each is listed by the content batch for hand finishing, and each skipped tile appears in the parity report as `not_compared`.

## Prerequisites

- The LookML repo cloned locally, and Looker API credentials with System Activity access for usage.
- The Omni CLI configured, an API key that can create a model branch and documents, plus the `omni-analytics` agent skills installed (`/plugin marketplace add exploreomni/omni-agent-skills`, `/plugin install omni-analytics@omni-analytics`).
- `/wire:new` with release type "BI tool migration (Looker to Omni)". It asks for the LookML path, the Looker and Omni URLs, the Omni model id and the parallel-run length.

## See also

- [Tutorial: Looker to Omni Migration](../tutorials/looker-to-omni-migration): a complete release, directed in prose, with every command Wire runs named
- [Looker to Omni: A Real Run](../tutorials/looker-to-omni-real-run): a real migration of three dashboards on Rittman Analytics' own estate, as it was run, with the prompts, the counts and the 52 rulings
- [The Release Director Model](../advanced/release-director)
- [Platform Migration](./platform-migration): the same register and drift mechanisms applied to a warehouse move
