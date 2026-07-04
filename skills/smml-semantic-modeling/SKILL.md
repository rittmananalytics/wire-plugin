---
name: smml-semantic-modeling
description: >
  Build, edit, review, or troubleshoot an Oracle Analytics Cloud (OAC)
  semantic model directly in SMML (Semantic Modeler Markup Language) —
  physical/logical/presentation layers, role-playing dimensions, hierarchies,
  calculated measures, subject-area design — independent of how the model's
  data got there (hand-authored, edited via OAC Semantic Modeler + Git, or
  machine-generated). Use when working with SMML JSON directly: adding a
  hierarchy, aliasing a role-playing dimension, writing a ratio measure,
  designing subject areas, or validating a semantic-model Git repo. Triggers:
  "edit/build an SMML semantic model", "add a hierarchy in OAC", "role-playing
  dimension in SMML", "OAC subject area design", "SMML schema", "validate
  SMML". For generating a first-pass SMML model automatically from a dbt
  project's metadata, use the sibling `dbt-to-smml` skill instead — that
  skill's `meta.oac` vocabulary is built on the modeling knowledge here.
---

# SMML semantic modeling

Knowledge and reference material for working with SMML directly — the
physical/logical/presentation layer object model, and the judgement calls
(hierarchies, role-playing dimensions, calculated measures, subject-area
design) that turn a mechanically correct model into one that actually behaves
right in OAC.

## How this differs from `dbt-to-smml`

This skill is the modeling knowledge. `dbt-to-smml` is the automation that
turns a dbt project's `meta.oac` metadata into SMML using this knowledge —
its `meta.oac` vocabulary exists to let a dbt project *express* the
constructs documented here (role-playing dimensions, hierarchies, derived
measures) without a human writing raw SMML by hand. Use this skill when:
- Hand-authoring or editing SMML JSON directly (no dbt project involved, or
  editing what a generator produced).
- Reviewing/auditing an existing semantic-model Git repo for correctness.
- Making a modeling decision (should this be a role-playing alias? one
  subject area or several? a hierarchy or a flat attribute?) that the
  `dbt-to-smml` generator or a human needs to get right before it's encoded
  as `meta.oac` or committed as SMML.

## Procedure

1. **Read `references/smml-schema.md` before writing or editing any SMML
   JSON.** Every object is wrapped in a singular type key
   (`{"physicalTable": {...}}`) — get this wrong and every downstream object
   is malformed. The file is tagged by confidence: **[ground truth]** (seen
   in a real, OAC-imported export), **[F38574-15]** (Oracle's schema doc,
   unvalidated against a real import), **[gap]** (neither source confirms
   it) — weight your confidence accordingly, especially for hierarchies and
   derived measures, which are F38574-15-only.
2. **Read `references/modeling-patterns.md` before making a modeling
   decision.** It covers the five places a mechanically-correct model still
   needs judgement: role-playing dimensions, hierarchies, calculated
   measures, subject-area design, and general star-schema defaults — each
   grounded in Oracle's own guide plus what a real shipped project actually
   did (the two don't always agree; both are cited).
3. **Design physical → logical → presentation, in that order.** Alias
   role-playing dimensions at the physical layer (never join the base table
   directly once it has any alias; never join two aliases of the same table
   together). Keep the logical layer a strict star — one table per real
   dimension/fact/role, fact-to-dimension joins many-to-one with the fact on
   the many side, snowflake FKs stay flat attributes unless there's a
   specific reason not to. Curate the presentation layer per subject area
   (default: one subject area per fact plus its directly-joined dimensions;
   set an `implicitFactColumn` on any subject area with more than one fact).
4. **Validate structurally**: `python3 scripts/validate_smml.py <smml_dir>` —
   catches missing required properties and dangling FQN references. This is
   not a substitute for OAC's own consistency check; it's the cheap check to
   run before importing.
5. **Commit to the Git-backed semantic-model repo** and open in OAC Semantic
   Modeler. Things this skill doesn't cover — number formats, session
   variables, row-level security/permissions, localization — get resolved in
   the UI; SMML round-trips them but this skill isn't a guide to authoring
   them from scratch.

## Files

- `references/smml-schema.md` — the object model: every layer, every
  property, the enums, confidence-tagged by source.
- `references/modeling-patterns.md` — the judgement calls: role-playing
  dimensions, hierarchies, calculated measures, subject-area design,
  star-schema defaults.
- `scripts/validate_smml.py` — structural validator (unwraps type-keyed
  objects, checks required properties, resolves FQN references). Shared with
  `dbt-to-smml`, which calls this same script rather than duplicating it.

## Provenance

`smml-schema.md` is built from *SMML Schema Reference for Oracle Analytics
Cloud* (F38574-15, June 2026) cross-checked against `eyelit_smml` — a real,
OAC-imported semantic model built from the `eyelit-dbt` project — wherever
the two sources overlap. `modeling-patterns.md` adds *Building Semantic
Models in Oracle Analytics Cloud* (F42737-41). Where ground truth and the
official guide disagree on practice (e.g. subject-area design), both are
cited so you can weigh them.

## Caveats

- Hierarchies and derived/calculated measures are validated against Oracle's
  written schema and modeling guide only — the one ground-truth project
  never built either, despite one dimension declaring a hierarchy in its
  source metadata. Check a real OAC import before trusting these in
  production.
- The condition-based physical join shape (`useJoinExpression` /
  `joinConditions`) is ground-truth-confirmed but not independently
  corroborated by F38574-15's own printed schema fragment for `physicalTable`,
  which is incomplete on this point.
- Degenerate dimensions have no dedicated SMML construct in either source —
  see `modeling-patterns.md` §6 for the convention to use instead.
