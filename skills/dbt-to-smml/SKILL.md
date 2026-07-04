---
name: dbt-to-smml
description: >
  Generate an Oracle Analytics Cloud (OAC) semantic model in SMML (Semantic
  Modeler Markup Language) from a dbt project. Use when the user wants to build,
  convert, or scaffold an OAC semantic model from dbt models — generate SMML, the
  physical/logical/presentation layers, measures, hierarchies and role-playing
  dimensions — driven by dbt metadata plus `meta.oac` annotations in schema.yml.
  Triggers: "generate SMML", "dbt to OAC semantic model", "build the OAC
  semantic layer from dbt", "create logical/physical/presentation layer from
  dbt". For hand-authoring, editing, or reviewing SMML directly (no dbt
  project), use the sibling `smml-semantic-modeling` skill instead — this
  skill's `meta.oac` vocabulary and generator are built on that skill's
  modeling knowledge.
---

# dbt → OAC SMML semantic-model generator

Turn a governed dbt project into an OAC semantic model in SMML — one JSON file
per object, across the physical, logical and presentation layers — ready to
commit to a semantic-model Git repo and open in the OAC Semantic Modeler.

## How this works — deterministic core, LLM-assisted enrichment

- **The generation is a script, not the model.** `scripts/generate_smml.py`
  reads dbt's `target/manifest.json` + `target/catalog.json` (+ `meta.oac`) and
  emits the SMML deterministically. Same inputs → identical output. Never
  hand-write SMML JSON in the chat — run the script.
- **The model's job is judgement.** dbt gives the physical truth (tables,
  columns, types, descriptions). What needs a human-approved decision is the
  *semantics* — which columns are measures, their aggregation, hierarchies,
  role-playing dimensions, subject areas, friendly labels. You (the model)
  propose those as `meta.oac`, the user approves them into `schema.yml`, then
  the script consumes them. The script also infers sensible defaults where
  `meta.oac` is absent, but `meta.oac` always wins. Read
  `../smml-semantic-modeling/references/modeling-patterns.md` before proposing
  a hierarchy, role-playing alias, or derived measure — each `meta.oac` key
  encodes a specific pattern documented there; propose it wrong and the
  generator will faithfully emit the wrong SMML.

## Procedure

1. **Ensure dbt artifacts exist.** Need `target/manifest.json` and
   `target/catalog.json`. If missing, ask the user to run `dbt docs generate`
   (needs a warehouse connection).
2. **Read `../smml-semantic-modeling/references/smml-schema.md`** (the SMML
   object/property reference — confidence-tagged by whether it's
   ground-truth-validated or PDF-only) and `references/meta-oac-vocabulary.md`
   (the `meta.oac` vocabulary this script consumes) so you generate against
   real property names, not memory.
3. **Diff semantics vs metadata.** Identify which models/columns lack `meta.oac`.
   For the gaps, *propose* `meta.oac` — read column names, types, lineage and the
   model SQL to suggest measure-vs-attribute, aggregation rule, hierarchies,
   role-playing dimensions (a dimension with more than one FK pointing at it —
   see `role_alias` in the vocabulary), labels, descriptions. Present them for
   the user to approve into `schema.yml`. Do not invent business semantics
   silently — anything subjective (a metric definition, a non-additive rule,
   which declared FKs actually get joined) is surfaced for sign-off.
4. **Generate.** Run:
   ```bash
   python3 scripts/generate_smml.py \
     --manifest target/manifest.json --catalog target/catalog.json \
     --out smml --schema <ADW_SCHEMA> --business-model <NAME> \
     --database-name "<DB>" --database-type ORACLE_ADW \
     --connection "<OAC connection name>"
   ```
   By default it exposes the `warehouse` layer (`--layer all` for everything).
   It writes `smml/physical|logical|presentation/...` plus a human-readable
   `smml/MODEL.md` describing the model, including any role-playing aliases it
   built.
5. **Validate.** Run
   `python3 ../smml-semantic-modeling/scripts/validate_smml.py smml` for
   structural checks (required properties, references resolve — including
   alias-inherited physical columns). Report results + the diff.
6. **Hand off.** The SMML tree is committed to the semantic-model repo and
   imported into OAC. Reconcile measure totals against dbt (number-parity eval)
   before trusting it in production. Expect to prune: the generator proposes
   every declared FK as a join and every model as a logical/presentation table
   — a human curates the final subject-area membership before shipping, same
   as the one real project this was validated against.

## What this does NOT do

- It does not connect to OAC or run dbt — it consumes dbt's artifacts.
- It does not run the number-parity eval (needs a live OAC/Logical SQL
  connection); trigger that separately.
- It is one-way (dbt → SMML). Treat dbt as the source of truth and regenerate;
  edits made in the OAC UI will drift.
- It doesn't add presentation-layer hierarchy exposure (the `hierarchy`/
  `hierarchyLevel` presentation objects) — logical hierarchies are emitted,
  but making them drillable in a subject area needs per-level display-column
  choices this generator doesn't have enough information to make; add those
  by hand in OAC.

## Files

- `scripts/generate_smml.py` — the generator (all layers + role-playing
  aliases + `MODEL.md`).
- `scripts/sample/` — a worked fixture (manifest + catalog) exercising every
  feature: two facts sharing a dimension (`dim_users`, one plain FK each —
  must NOT get aliased), a per-fact multi-role date dimension (must get
  aliased), `presentation_label` overrides, a time hierarchy, and a derived
  ratio measure. Run the generator against it to see the output shape.
- `references/meta-oac-vocabulary.md` — the `meta.oac` schema.yml vocabulary.
- `references/eyelit-worked-example.md` — a real worked case study (the
  `eyelit-dbt` → `eyelit_smml` pairing) showing these tags applied, including
  a real tagging gap that was found and fixed.
- `README.md` — full usage, CLI reference, caveats.
- Schema reference and modeling guidance live in the sibling
  `smml-semantic-modeling` skill (`../smml-semantic-modeling/references/`) —
  not duplicated here.

## Caveats (read before production)

- Object shapes, `DataType`/`DatabaseType` mapping, and physical/logical join
  shapes are validated against a real OAC-imported export (`eyelit_smml`) —
  see `smml-schema.md`'s `[ground truth]` tags.
- **Hierarchies and derived measures are not** — the one real project that
  declared both never actually got them built into its shipped SMML. Treat
  `emit_hierarchies()`'s output and derived-measure columns as PDF-sourced
  best-effort; check a real OAC import before trusting them in production.
- The role-playing alias *naming* heuristic (base table's prefix + role label)
  is this generator's own convention, informed by but not identical to
  Oracle's example naming — rename via `presentation_name`/`role_alias` if it
  doesn't read well.
- Pin the generator to the target OAC's SMML schema version (this targets
  F38574-15, June 2026).
