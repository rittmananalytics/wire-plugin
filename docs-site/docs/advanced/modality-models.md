---
sidebar_position: 12
title: Modality models as an input
---

# Reading a Modality model into the design artifacts

[Modality](https://github.com/rittmananalytics/modality) is the tool the team uses to capture and model client data, and it writes models as `.mml` text files into the client's own repository. If you have already captured the client's entities in Modality, the last thing you want is to type them in again when Wire reaches its design phase, and yet that is what used to happen.

Wire's design commands derive their content from approved requirements and whatever sits in `artifacts/`, so a model that already existed in Modality was invisible to them, the entities got typed in again by hand and the two copies then diverged. Linking a Modality model to the release closes that gap, and in this page we will look at how you link one, what each design command reads from it, the two MML vocabularies you will meet in the wild and how Wire reconciles them, what a missing file means, the coverage check the validate commands run and what remains out of scope.

## Linking a model

```bash
/wire:utils-modality-link <release-folder> [--path <dir>]
```

The command finds `modality_project.yaml` (an explicit `--path` first, then `client_repo_local_path` for a dedicated client repo, then the Wire repo), reports what the model actually contains, and records `model_source: modality` and `modality_path` on the release.

The report includes one line that matters more than the counts, which is **where cardinality is readable from**, and we will come back to why that matters in the section on the two vocabularies below.

A model with zero conceptual entities is a scaffold rather than a model, and the command refuses to link it, because the design commands would produce empty documents.

To unlink, set `model_source: derived`. Nothing is deleted, and documents already generated keep their content and their citations.

## What each command reads

So what does each design command take from a linked model? The table below sets it out, section by section:

| Command | Takes from the model |
|---|---|
| `conceptual_model-generate` | Entities, attributes and domains for Section 1; relationships and cardinality for Section 2's ERD; `description` and `business_logic` for Section 3 |
| `logical_model-generate` | Per-entity sources from `sources.mml`; cardinality and foreign keys for Section 3; `entity_resolution` blocks for Section 4 |
| `pipeline_design-generate` | The source list and per-entity landing tables. Replication tool and schedule are not in MML and are still asked for |

The model does not replace the requirements. Both are read, and the difference between them is a finding: an entity in the model but not in the requirements is excluded with the reason "in the Modality model, not in requirements scope", whereas an entity in the requirements but not in the model becomes an open question, and neither is resolved silently.

Every value taken from the model cites the `.mml` file it came from.

## The two vocabularies

Why does the link report say where cardinality is readable from? Because Modality's specification and its application export disagree, and both produce files in the wild, and this is the one thing to know about reading MML.

| | Specification | Application export |
|---|---|---|
| Written by | The MML authoring skill, and hand-authored files | Modality's own export |
| Cardinality | On the conceptual `relationship` block, as `type = "one-to-many"` | A separate `logical_relationship` block |
| Entity `type` | `entity`, `derived`, `aggregate` | `entity`, `metric`, `derivation` |
| Inline verbs | `belongs-to`, `has-many`, `leads-to`, `related-to` | `belongs-to`, `contains`, `leads-to`, `derived-from`, `parent-of` |
| `entity_resolution` | Not defined | Written |

A reader that handles one of these gets the other wrong, and quietly, so Wire accepts both and resolves cardinality in a stated order:

1. A `logical_relationship` block for the pair
2. A `relationship` block for the pair, where `type` is a cardinality
3. An inline verb, but only where the verb implies cardinality: `has-many`, `contains` and `parent-of` give one-to-many; `belongs-to` gives many-to-one

Only when all three yield nothing is the cardinality `undetermined`. Verbs that are relationship kinds rather than cardinality (`leads-to`, `related-to`, `derived-from`) are undetermined by nature, and are recorded as such rather than raised as a modelling failure.

## What absence means

What if a file is simply not there? Wire does not treat a silent file as a modelling failure, because the specification does not define every block the export writes, and each absence has its own reading:

| Absent | Reading |
|---|---|
| `logical_relationships.mml` | Fall through to `relationship`, then the inline verb |
| `entity_resolutions.mml` | **Never** a coverage failure. The specification does not define the block, so a spec-written model never has one. A multi-source entity with no resolution becomes an open question on the logical model |
| `sources.mml` | Sources are asked for instead |
| `physical/schema.mml` | Expected, and out of scope: MML writes one flat table per entity with `uuid` keys, and Wire's warehouse layer is a different design that `data_model` owns |

## The `modality_coverage` check

The check is run by the three validate commands when `model_source: modality`, and is reported as SKIP with the reason otherwise, never as PASS. It works in two directions:

1. Every conceptual entity in the `.mml` files appears in the Wire document, or is explicitly excluded **with a reason**.
2. Every entity in the Wire document maps to an MML entity or to a requirement.

Entities typed `metric` are outside direction 1, because they are semantic-layer measure candidates rather than conceptual entities.

## Out of scope

Finally, what does the link not do? Data products, exposures, estimates and roadmap blocks are not read, and nor is the physical model. There is no write-back either: when the model is authored in Modality, Modality is where it is maintained.
