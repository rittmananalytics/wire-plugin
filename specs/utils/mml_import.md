---
description: Shared convention — reading Modality `.mml` model files as an input to the Wire design artifacts, covering both the specification's vocabulary and the application's export vocabulary
---

# MML Import — Shared Reading Convention

Cited by `specs/design/conceptual_model/generate.md`,
`specs/design/logical_model/generate.md` and
`specs/design/pipeline_design/generate.md` when `status.md` has
`model_source: modality`. Read this before reading any `.mml` file.

## What Modality is, and why this exists

Modality (`rittmananalytics/modality`) is the tool the team uses to capture and
model client data. It writes models as `.mml` text files into the client's own
repository. Wire's design commands derive their content from approved
requirements and whatever sits in `artifacts/`, so a model that already exists in
Modality was invisible to them: the entities got typed in again, by hand, and
then diverged.

There is no export path to read instead. The parser is TypeScript inside the
application, the CLI has only a `view` command, and the package exposes no
library entry point. So Wire reads the `.mml` text itself, and this document is
the grammar it reads.

## The two vocabularies

**This is the thing to get right.** Modality's specification
(`MML_SPECIFICATION.md`) and its generator (`src/services/mmlGenerator.ts`) do not
agree, and both produce files in the wild:

| | Specification vocabulary | Application export vocabulary |
|---|---|---|
| Written by | The MML authoring skill, and anyone writing `.mml` by hand | The application's own export |
| Entity `type` | `entity`, `derived`, `aggregate` | `entity`, `metric`, `derivation` |
| Inline relationship verbs | `belongs-to`, `has-many`, `leads-to`, `related-to` | `belongs-to`, `contains`, `leads-to`, `derived-from`, `parent-of` |
| Cardinality | On the conceptual `relationship` block, as `type = "one-to-many"` | In a separate `logical_relationship` block |
| `entity_resolution` | Not defined | Written |
| Physical table references | By name | By internal id (`entity_group = "group_sales"`) |

A reader that handles only one of these produces a wrong answer on the other,
and quietly: a spec-written model read by an export-only reader loses every
cardinality and gains an open question per relationship. **Accept both.** The
disagreement is tracked upstream as `modality#26`; until it is settled, both are
valid input.

## File layout

Read `modality_project.yaml` at the model root for the authoritative globs. The
standing layout:

| Path | Blocks |
|---|---|
| `modality/models/conceptual/<domain>.mml` | `domain` (legacy `entity_group`), `entity`, `attribute`, inline relationship verbs |
| `modality/models/conceptual/relationships.mml` | `relationship` |
| `modality/models/logical/sources.mml` | `source`, with per-entity `table` |
| `modality/models/logical/entity_resolutions.mml` | `entity_resolution` |
| `modality/models/logical/logical_relationships.mml` | `logical_relationship` |
| `modality/models/logical/exposures.mml`, `reverse_etls.mml` | `exposure`, `reverse_etl` |
| `modality/models/physical/schema.mml` | `physical_model` |
| `modality/products/*.mml` | `data_product` |
| `modality/estimates/*.mml`, `modality/roadmap/roadmap.mml` | `entity_estimate`, `source_estimate`, `report_estimate`, `task` |

A file named in `modality_project.yaml` that does not exist is recorded as absent
and is not an error. Most models do not populate every layer.

## Block grammar

```
<keyword> "<name>" {
  key = "value"
  key "value"
  <verb> "Domain.Entity"
  <nested-keyword> "<name>" { ... }
}
```

Rules:

1. **Both attribute syntaxes are valid.** `key = "value"` and directive form
   `key "value"` mean the same thing.
2. **A repeated key accumulates into an array.** Two `table "x"` lines under one
   `source` give `table: [x, y]`, not the second overwriting the first.
3. **Names are snake_case by convention but not by enforcement.** The generator
   converts `"Sales Operations"` to `sales_operations` and `"CustomerAccount"` to
   `customer_account`. A hand-written file may carry either. Normalise to
   snake_case for matching, and keep the original for display.
4. **References use `domain.entity` dot notation.**
5. **`#` starts a comment** to end of line, outside a quoted string.
6. **Hex colours appear as values** (`color = "#4A90D9"`). A `#` inside quotes is
   not a comment.
7. **`domain` and the legacy `entity_group` are the same block.** Accept either.
8. **Unknown keys are carried through, not dropped.** A key this document does not
   name is recorded against the block so a later reader or a write-back can use
   it.

## Cardinality resolution

Look in three places, in this order, and stop at the first that yields a value:

1. **`logical_relationship` block** matching the from/to pair. Use its `type`, and
   its `foreign_key` if present.
2. **`relationship` block** matching the from/to pair, where `type` is one of
   `one-to-one`, `one-to-many`, `many-to-many`. This is the specification form,
   and skipping it is the defect this ordering exists to prevent.
3. **Inline verb** on the conceptual entity, but only where the verb implies
   cardinality:

   | Verb | Cardinality | Source vocabulary |
   |---|---|---|
   | `has-many` | one-to-many | specification |
   | `belongs-to` | many-to-one | both |
   | `contains` | one-to-many | export |
   | `parent-of` | one-to-many | export |
   | `leads-to` | none — sequential, not structural | both |
   | `related-to` | none — generic | specification |
   | `derived-from` | none — lineage, not cardinality | export |

Only when all three yield nothing is the cardinality `undetermined`, and only
then does it become an open question. A relationship whose verb is `leads-to`,
`related-to` or `derived-from` and which has no `relationship` or
`logical_relationship` entry is `undetermined` by nature, not by omission, and is
recorded as such rather than raised as a modelling failure.

## Entity type mapping

| MML `type` | Vocabulary | Wire reading |
|---|---|---|
| `entity` | both | A conceptual entity. Becomes a dimension or a fact depending on grain |
| `derived` | specification | A calculated entity. Signals a `_xa` or `_fact` warehouse model |
| `aggregate` | specification | A rolled-up entity. Signals a `_xa` model |
| `metric` | export | Not a conceptual entity. A semantic-layer measure candidate |
| `derivation` | export | A calculated entity, same reading as `derived` |

`derived` and `aggregate` are specification-only: the generator never writes
them. They are accepted on read, and the behavioural test carries them as
explicitly skipped cases rather than guessing what the application would do with
them.

## Physical id resolution

`physical_model` blocks reference internal ids (`entity_group = "group_sales"`)
where every other block uses names. Build the id-to-name map from the conceptual
files first, then resolve. An id with no mapping is recorded unresolved and named;
it is not guessed from the id string.

## Mapping to Wire artifacts

| MML | Wire artifact and section |
|---|---|
| `domain`, `entity`, `attribute` | `conceptual_model.md` Section 1, Entity Inventory |
| Cardinality, resolved as above | `conceptual_model.md` Section 2 ERD; `logical_model.md` Section 3 |
| `description`, `business_logic` | `conceptual_model.md` Section 3 narrative |
| `source` with per-entity `table` | `pipeline_design.md` Section 1; `logical_model.md` Section 1 |
| `entity_resolution` | `logical_model.md` Section 4 |
| `logical_relationship.foreign_key` | `logical_model.md` Section 3 |
| `type = metric`, `derived-from` | Semantic-layer measure candidates. Out of scope for the design artifacts |
| `physical_model` | Out of scope. MML writes one flat table per entity with `uuid` keys; Wire's warehouse layer is a different design, and `data_model` owns it |
| `exposure`, `data_product`, `entity_estimate`, `task` | Out of scope |

**MML adds fields Wire's templates have no column for**: `pii`, `sensitivity`,
`owner`. Carry them into the entity inventory as extra columns rather than
dropping them; they are the kind of thing that is expensive to re-gather.

## What absence means

Wire must not treat a silent MML file as a modelling failure, because the
specification does not define every block the export writes:

| Absent | Reading |
|---|---|
| `logical_relationships.mml` | Not an error. Fall through to `relationship` then the inline verb |
| `entity_resolutions.mml` | Not an error, and **not** a coverage failure. The specification does not define the block, so a spec-written model never has one. A multi-source entity with no resolution becomes an open question on `logical_model`, answered by asking |
| `sources.mml` | Not an error. `pipeline_design` and `logical_model` ask for sources instead |
| `physical/schema.mml` | Expected. Out of scope |
| A `type` on an entity | Default to `entity`, and record the default as an assumption |

## The `modality_coverage` check

Run by `conceptual_model-validate`, `logical_model-validate` and
`pipeline_design-validate` when `model_source: modality`. Two directions:

1. **Every MML entity is accounted for.** Each entity in the conceptual `.mml`
   files appears in the Wire document, or is listed as explicitly excluded with a
   reason. Unaccounted entities are FAIL, named.
2. **Every Wire entity traces back.** Each entity in the Wire document maps to an
   MML entity or to a requirement. An entity in neither is FAIL, named.

Entities with `type = metric` are excluded from direction 1: they are measure
candidates, not conceptual entities, and requiring them in the entity inventory
would force a wrong answer.

A missing `entity_resolution` never fails this check.
