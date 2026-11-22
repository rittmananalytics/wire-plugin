---
wire_schema: "1.0"
command: generate
artifact: logical_model
domain: design
release_types:
  - sop_discovery
  - full_platform
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: domain
      description: "--domain <name> limits the run to one conceptual domain"
produces:
  - type: document
    path: "design/logical_model.md"
    description: "Logical data model — per-entity sources and grain, keys, cardinality, identity resolution, normalisation and attribution rules"
preconditions: dynamic
delegates_to:
  - utils/data_designer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
  - utils/reference_legibility
  - utils/mml_import
description: Logical data model between the conceptual model and the physical dbt design — per-entity sources and grain, keys, cardinality, identity resolution, normalisation and attribution rules
argument-hint: <release-folder> [--domain <name>]
---

# Logical Model — Generate

Follow `specs/utils/data_designer_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: logical_model` and `artifact_file_path: design/logical_model.md` before proceeding.

---

## Purpose

Wire has gone straight from conceptual (what entities exist, how they relate in
business terms) to physical (`data_model_specification.md`, which is a dbt
design: staging, integration and warehouse layers with `_pk` / `_fk` / `_dt`
naming). The step between them was never written down.

That step is where the decisions that are neither business nor dbt get made: what
the primary key of an entity actually is, whether a relationship is one-to-many
or many-to-many, which source wins when the same customer exists in three
systems, how far to normalise, and how a conversion is attributed. Those
decisions have been made implicitly inside `data_model-generate`, which means
they arrive already expressed as dbt models and are hard to review as decisions.

This artifact makes them reviewable on their own, before anything is built. In a
`sop_discovery` release under the `modelling_led` profile it is a client
deliverable, signed off at the playback alongside the conceptual model. In
`full_platform` it is optional, and worth running when identity resolution or
attribution is contested.

## Scope boundary

| This document | Not this document |
|---|---|
| The primary key of an entity, and why | dbt model names and layer assignment (`data_model`) |
| Cardinality and the foreign keys that carry it | Physical column types and clustering (`data_model`) |
| Which source wins per entity, and the tie-break rule | Which tool replicates which source (`pipeline_design`) |
| How far to normalise, per entity group | Business meaning of an entity (`conceptual_model`) |
| Attribution rules, stated as rules | Metric SQL (`semantic_layer`) |

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/design/conceptual_model.md` — reviewed and approved
- `.wire/releases/$ARGUMENTS/status.md` — `model_source`, `discovery_profile`, `release_type`

**Optional, and used when present**:
- `.wire/releases/$ARGUMENTS/planning/current_state_appraisal.md` — Section 2's source list. Every source this document maps an entity to must appear there, and `validate` checks it.
- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md` (`sop_discovery`) or `requirements/requirements_specification.md` (`full_platform`)
- An existing model authored outside Wire, when `model_source` names one (see Step 2)

## Workflow

### Step 1: Pre-flight

1. Resolve `$ARGUMENTS`. Read `status.md`.
2. Follow `specs/utils/precondition_gate.md`. Its Step 0 resolves the gate from
   the release type's YAML and applies the active profile, so in a `diagnostic`
   `sop_discovery` release this phase is off and the gate stops here.
3. Confirm the conceptual model is `review: approved`. The logical model refines
   entities and relationships that the client has already agreed; refining an
   unagreed set wastes both passes.

### Step 2: Decide where the model comes from

Read `model_source` from `status.md`:

- **`derived` (default)** — build the logical model from the conceptual model plus
  the appraisal's source list, asking the questions in Step 4 where the answer is
  not already recorded.
- **A named external model source** — the client already models outside Wire, and
  that model may already carry keys, cardinality and identity resolution. Do not
  restate them here. Read them, cite where each came from, and spend this
  document on what the external model does not hold: the normalisation decision,
  the attribution rules, and the prose reasoning behind each key and tie-break.
  A second copy of a model that is maintained elsewhere goes stale and then
  contradicts its source.

  Where the external model is silent on a field this document needs, ask, and
  record the answer here with a note that it is not in the external model. That
  note is what a later write-back would use.

### Step 3: Write the model

Write `design/logical_model.md`.

**Section 1 — Entity sources and grain.** One row per entity: entity name,
conceptual domain, source system(s), the table or object in each, the grain of
one record, the business owner, and the fields required. Where an entity comes
from more than one source, one row per source plus a resolution reference to
Section 4.

This section is the source definitions work: grain, keys, fields, owner. It sits
here rather than in its own artifact because grain and key are the same decision
viewed from two ends, and splitting them produces two documents that disagree.

**Section 2 — Keys.** Per entity: the natural key (the business identifier, and
whether it is genuinely unique in the source), the surrogate key strategy, and
the reason. Where the natural key is not unique, say what makes a record unique
and what that implies. This is the section a dbt `unique` test is later derived
from, so a claim here is a testable claim.

**Section 3 — Relationships and cardinality.** Per relationship: from, to,
cardinality, the foreign key that carries it, and whether it is enforced anywhere
or merely expected. Cardinality that came from an external model is cited as
such. Cardinality that nobody has stated is recorded as `undetermined` with the
question and the person to ask, never defaulted silently to one-to-many.

**Section 4 — Identity resolution.** Per multi-source entity: the sources, the
matching keys, the precedence order with the reason, the tie-break when
precedence does not settle it, and what happens to a record that matches nothing.
Precedence is a business decision, not a technical one, so each entry names who
decided it.

**Section 5 — Normalisation.** Per entity group, the chosen shape and the reason:
normalised, denormalised into a wide table, or a hybrid, with the trade-off
stated in one sentence. This is where a conceptual model with 40 entities becomes
a decision about how many tables get built.

**Section 6 — Attribution and allocation rules.** Where a fact must be assigned
to a dimension that is not directly on the record: conversion attribution,
revenue allocation across periods or entities, cost apportionment. Each rule
stated as a rule, with its window, its precedence, and what it does with the
unattributable remainder. A rule with no stated remainder handling is incomplete.

**Section 7 — Entity ownership going forward.** Per entity, who owns the
definition once it is in production, and who approves a change. The appraisal
records who owns definitions *today*; this records who will. Where the two
differ, that difference is a roadmap item.

**Section 8 — Open questions.** Every `undetermined` cardinality, unresolved
precedence, and unanswered grain question, each with the person to ask.

### Step 4: The questions this document exists to answer

Where an input does not already settle them, ask, one at a time, and record the
answer with its source. Do not proceed on an assumption without marking it as
one.

1. For each entity with a non-unique natural key: what makes one record unique?
2. For each many-to-many: is there a real associative entity, and does the
   business have a name for it?
3. For each multi-source entity: which source wins, and who says so?
4. For each attribution rule: what window, and where does the remainder go?
5. For each entity group: is anyone querying this directly, or only through a
   report? The answer changes the normalisation call.

### Step 5: Reference legibility

Follow `specs/utils/reference_legibility.md`. This document mints `LM-n` codes for
its decisions and is cited by `data_model` and the playback deck.

### Step 6: Status and log

Update `status.md`:

```yaml
logical_model:
  generate: complete
  validate: not_started
  review: not_started
  file: design/logical_model.md
  generated_date: [today]
```

If `current_phase` is still `requirements`, update to `design`.

Follow `specs/utils/execution_log.md`.

## Output

`.wire/releases/$ARGUMENTS/design/logical_model.md`


---

## `model_source: modality`

When `status.md` has `model_source: modality`, read the client's existing Modality
model as the input to the sections named below.

What this command takes from the model: Section 1 from `sources.mml`, Section 3's cardinality and foreign keys from the resolution order, Section 4 from `entity_resolutions.mml` where present. Follow
`specs/utils/mml_import.md` first: it carries the block grammar, the two
vocabularies the specification and the application disagree on, and the
cardinality resolution order.

The model does not replace the requirements. Both are read, and the difference
between them is itself a finding:

- An entity in the model and not in the requirements goes in the excluded list
  with the reason "in the Modality model, not in requirements scope". It is not
  silently carried into scope.
- An entity in the requirements and not in the model goes in the open questions.
  It is not silently added to the model's entity set.

Every value taken from the model cites the `.mml` file it came from. A reader
comparing the Wire document against the model needs to know which claims came from
where, and a later write-back needs to know which claims are new.

`validate` runs the `modality_coverage` check in both directions. Its rules,
including the ones about what absence means, are in `specs/utils/mml_import.md`.
