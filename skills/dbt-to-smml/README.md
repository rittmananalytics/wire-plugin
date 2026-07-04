# dbt-to-smml

A Claude skill + utility that generates an Oracle Analytics Cloud (OAC) semantic
model in **SMML** from a dbt project. dbt builds and refreshes the warehouse; this
stands the governed semantic layer on top of it — physical, logical and
presentation layers, one JSON file per object, ready for the OAC Semantic Modeler
and Git.

It's both:
- a **utility** — `scripts/generate_smml.py`, runnable standalone (CI, scheduled),
- a **skill** — `SKILL.md` wraps it with the metadata-enrichment + validation flow.

See `SKILL.md` for the interactive procedure. This README is the utility
reference. For the SMML object model and the modeling judgement behind it
(role-playing dimensions, hierarchies, subject-area design), see the sibling
`smml-semantic-modeling` skill — this one builds on that knowledge rather than
repeating it.

## Design in one line

Deterministic generation (a script) + human-approved semantics (`meta.oac`). dbt
gives the physical truth automatically; the judgement — measures, aggregation,
hierarchies, subject areas, labels — is captured as `meta.oac` in `schema.yml`,
proposed by the model and approved by a human. The script never guesses business
meaning silently.

## Install / run

Pure Python 3, no dependencies.

```bash
# 1. produce dbt artifacts (needs a warehouse connection)
dbt docs generate                      # writes target/manifest.json + target/catalog.json

# 2. generate the SMML model
python3 scripts/generate_smml.py \
  --manifest target/manifest.json \
  --catalog  target/catalog.json \
  --out      smml \
  --schema          MESTEC_DW \
  --database-name   "MESTEC ADW" \
  --database-type   ORACLE_ADW \
  --business-model  MESTEC \
  --connection      "MESTEC ADW Connection"

# 3. validate (shared validator lives in the sibling skill)
python3 ../smml-semantic-modeling/scripts/validate_smml.py smml
```

### CLI options

| Option | Default | Meaning |
|--------|---------|---------|
| `--manifest` | `target/manifest.json` | dbt manifest |
| `--catalog` | `target/catalog.json` | dbt catalog (column data types) |
| `--out` | `smml` | output directory |
| `--database-name` | `MESTEC ADW` | SMML physical database object name |
| `--database-type` | `ORACLE_ADW` | `databaseType` — `ORACLE_ADW` or `ORACLE_DATABASE` (on-prem); see the sibling skill's `DatabaseType` enum |
| `--connection` | `REPLACE_WITH_OAC_CONNECTION` | connection-pool connection name |
| `--business-model` | `MESTEC` | logical business-model name |
| `--schema` | (from catalog) | override the physical schema name |
| `--layer` | `warehouse` | dbt layer to expose (`all` for everything) |

## Output

```
smml/
  physical/<DB>.json, <DB>/<SCHEMA>.json, <DB>/<SCHEMA>/<table>.json  (+ role-play aliases)
  logical/<BM>.json, <BM>/<logical table>.json                        (+ alias logical tables)
  presentation/<SA>.json, <SA>/<presentation table>.json
  MODEL.md                      human-readable description of the generated model
```

What each layer carries:
- **physical** — tables, columns (type/length/nullable), physical aliases for
  role-playing dimensions (built automatically for every FK once one fact has
  more than one FK into the same dimension — Oracle's own best practice, not
  just an opt-in), and fact→dim/alias joins as `useJoinExpression: false` +
  `joinConditions`.
- **logical** — fact/dimension/alias tables; measures with `aggregation.rule`;
  derived measures over already-aggregated sibling logical columns; logical
  table sources mapping each logical column to its physical column; logical
  joins (fact→dimension only, never dimension→dimension); level-based
  hierarchies with `chronologicalKey` on every non-Grand-Total level of a time
  hierarchy.
- **presentation** — one subject area per `meta.oac.subject_area` value (a
  model can belong to more than one — give it a list — for a shared dimension
  used across subject areas), presentation tables and columns with friendly
  labels, nothing hidden by default including FK/degenerate id columns, plus
  named presentation tables for role-playing dimensions (`role_alias`/
  `presentation_label`).

## Try it on the bundled fixture

`scripts/sample/` is a worked manifest + catalog exercising every feature:
two facts (`fact_attendance_log`, `fact_activity_log`) sharing a dimension
(`dim_users`, one plain FK each — proving shared dimensions across facts
don't get spuriously aliased), a per-fact multi-role date dimension (proving
every role gets aliased once a fact has more than one FK into it),
`presentation_label` overrides distinct from the alias name, a time dimension
with a Calendar hierarchy, and a staging model that gets correctly excluded:

```bash
python3 scripts/generate_smml.py \
  --manifest scripts/sample/manifest.json \
  --catalog  scripts/sample/catalog.json \
  --out /tmp/smml_demo --schema MESTEC_DW --business-model MESTEC
python3 ../smml-semantic-modeling/scripts/validate_smml.py /tmp/smml_demo
cat /tmp/smml_demo/MODEL.md
```

## `meta.oac`

The semantic metadata lives in the dbt `schema.yml` under `meta.oac` — see
`references/meta-oac-vocabulary.md`. Where it's absent the generator infers
defaults; `meta.oac` always overrides. `references/eyelit-worked-example.md`
walks through applying it to a real project, including a real tagging gap
that was found and fixed.

## Caveats — validate against a real OAC export before production

- **Object shapes, `DataType`/`DatabaseType` enums, and join shapes are
  validated** against a real OAC-imported export (`eyelit_smml`) — see the
  sibling skill's `smml-schema.md` `[ground truth]` tags.
- **Hierarchies and derived measures are not.** The one real project that
  declared both (a Calendar hierarchy on `dim_date`, four OLE ratio measures)
  never actually shipped either into its SMML export — these constructs are
  sourced from Oracle's written schema/modeling-guide PDFs only. Check a real
  OAC import before trusting `levelBasedHierarchy` or a `LOGICAL_COLUMNS`-
  derived measure in production.
- **The generator over-produces relative to what typically ships** — every
  declared FK becomes a join, every model becomes a logical + presentation
  table. That's deliberate (complete, mechanical translation for review); a
  human prunes the final subject-area membership before shipping, same as
  the real project this was validated against.
- **One-way only.** dbt is the source of truth; regenerate rather than editing in
  the OAC UI (which would drift).
- **Number parity** — reconcile a few measures through OAC Logical SQL against the
  same metric in dbt before trusting the model. That eval needs a live OAC
  connection and is out of this script's scope.
- Pin to the target OAC's SMML schema version (this targets **F38574-15**, June 2026).

## Provenance

Designed in `.wire/releases/01-poc-productionisation/artifacts/dbt-to-smml-generator-plan.md`.
Schema and modeling guidance sourced from `.wire/research/sessions/smml-schema-reference-oracle-analytics-cloud.pdf`
(F38574-15) and `.wire/research/sessions/building-semantic-models-oracle-analytics-cloud.pdf`
(F42737-41), cross-checked against `eyelit_smml` — a real, OAC-imported
semantic model built from the `eyelit-dbt` project — wherever the two
overlap. Candidate to promote into the Wire plugin (`wire:dbt-to-smml` +
`wire:smml-semantic-modeling`) as reusable RA assets.
