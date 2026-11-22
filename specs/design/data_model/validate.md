---
wire_schema: "1.0"
command: validate
artifact: data_model
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: slice
      description: "--slice <slice>. In a release built from tickets, work on one slice of the release only (specs/utils/ticket_delivery.md)"
preconditions:
  - artifact: data_model
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Validate data model specification and physical ERD
argument-hint: <project-folder> [--slice <slice>]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Model Validation Command

## Purpose

Validate the generated data model specification and embedded Physical ERD against quality standards:
- All conceptual model entities are represented as warehouse models
- Every new warehouse dimension and fact maps to one agreed conceptual entity, and every new extended aggregate records why it exists
- dbt naming conventions are followed throughout
- Every model has a defined grain, surrogate key, and test coverage plan
- The Physical ERD is present, complete, and consistent with the model specs
- All FK relationships in the ERD have corresponding join definitions in the model specs
- Cross-system joins are documented

## Usage

```bash
/wire:data_model-validate YYYYMMDD_project_name
```

## Prerequisites

- `data_model`: `generate: complete`

## Sliced runs (`--slice`)

In a release built from tickets (`delivery: tickets` in `status.md`), this
command takes `--slice <slice>` and checks the slice's table section of `design/data_model.md` only
(`specs/utils/ticket_delivery.md`, "The `--slice` option"). Without
`--slice`, the workflow below runs as written.

1. The slice must be in `tickets.yaml`. If it is not, stop and list the valid
   slices.
2. Run every check below against the slice's part. A check that needs the
   whole release (a cross-model consistency check) runs against the slice and
   the parts it depends on, and says so in the report.
3. On a ticket branch, write the result (`pass` or `fail`) to the ticket
   record's front matter (`results:`) and the log row to the ticket run log
   (`iterations/<ticket>.execution_log.md`), not to `status.md` and
   `execution_log.md`.

**Design source.** A slice whose design is recorded from the Modality physical
model (a **Source: Modality** line) is checked against Wire's rules like any
other. Every gap the generate step listed must be resolved in the design
section (adopted, or kept with a recorded decision and reason) for a PASS. An
unresolved gap is a FAIL naming the table and column. The Modality file is
never written.

## Workflow

### Step 1: Verify Data Model Exists

1. Check `data_model.generate == complete` in `status.md`
2. Check that `design/data_model_specification.md` exists

If not found:
```
Error: Data model not yet generated.
Run: /wire:data_model-generate <project_id>
```

### Step 2: Read Inputs

1. Read `design/data_model_specification.md`
2. Read `design/conceptual_model.md` (for entity coverage cross-check)
3. Read `design/pipeline_architecture.md` (for source table cross-check)

### Step 3: Run Validation Checks

**Accepted naming forms.** The checks below accept both the current form and the older form. A design is never failed for singular staging or integration names, unprefixed columns, `tests:` as the test key, `_<source>__sources.yml` file names, `ephemeral` intermediate models, or existing `_agg`/`<subject>_summary` aggregates. These are different forms, not defects. Where the project's `.wire/conventions/dbt.yml` or the release's `decisions.md` records a `form_choices:` ruling, report (Info) any new model that follows neither the ruling nor the current form.

| Area | Current form | Older form, still accepted |
|------|--------------|----------------------------|
| Staging and integration names | plural: `stg_source_a__users`, `int_core__users` | singular: `stg_source_a__user` |
| Warehouse names | singular: `wh_core__user_dim` | same |
| Column prefixes | `user_name`, `user_is_active`, `order_user_natural_key` | `name`, `is_active` |
| Booleans | `<entity>_is_/has_/was_<x>` | `is_/has_/was_<x>` |
| Test key | `data_tests:` | `tests:` (never both on one resource) |
| Source file name | `_sources.yml` | `_<source>__sources.yml` |
| Warehouse aggregate | `wh_<group>__<entity>_xa` (extended aggregate) | `_agg`, `<subject>_<grain>`, `<subject>_summary` |
| Seed names | `seed__<description>.csv`, `seeds` schema | existing names and schema |

**Naming Convention Checks**:

| Check | Rule | Severity |
|-------|------|----------|
| Staging naming | All staging models follow `stg_<source>__<entity>` (double underscore), plural or singular entity name | Critical |
| Base model naming | Base models follow `base_<source>__<entity>` and sit with the staging models of their source | Major |
| Warehouse fact naming | All fact tables follow `wh_<group>__<entity>_fact` | Critical |
| Warehouse dimension naming | All dimension tables follow `wh_<group>__<entity>_dim` | Critical |
| Extended aggregate naming | New aggregate or denormalised warehouse models follow `wh_<group>__<entity>_xa`; existing aggregates keep their names | Major |
| Integration naming | Integration models follow `int_<group>__<entity>`; intermediate models follow `int_<group>__<entity>__<verb>` | Major |
| Snapshot naming | New snapshots follow `snapshot_<source>__<source_table>` | Major |
| Seed naming | New seeds in a new release follow `seed__<description>.csv`; existing seeds keep their names | Major |
| Surrogate key naming | Surrogate key columns follow `<entity>_pk` pattern | Critical |
| Foreign key naming | Foreign key columns follow `<referenced_entity>_fk` pattern | Major |
| Boolean naming | Boolean columns follow `<entity>_is_/has_/was_<x>` or `is_/has_/was_<x>` | Major |
| Column suffixes | Measures in new models use `_amount`, `_amount_<currency>`, `_<measure>_<unit>`, `_count`, `_rank`, `_pct` or `_ratio`; dates `_dt`, timestamps `_ts` | Info |
| No reserved words | No model or column names use SQL reserved words (e.g. `date`, `order`, `group`) | Major |
| snake_case columns | All column names are `lower_snake_case` | Major |

**Model Completeness Checks**:

| Check | Rule | Severity |
|-------|------|----------|
| Entity coverage | Every entity from conceptual_model.md appears as at least one warehouse model | Critical |
| Entity mapping | Every new `_dim` and `_fact` names exactly one **Conceptual entity**, and that entity is in the conceptual model's Entity Inventory (not in Section 4, out of scope). See "Entity Mapping" below | Critical |
| Extended aggregate reason | Every new `_xa` records a **Reason**: `summary: <name>` naming a row of the conceptual model's Agreed Summaries, or `performance:` followed by what it makes faster or cheaper | Major |
| Grain defined | Every model (staging and warehouse) has a grain statement | Critical |
| Key defined | Every warehouse model has a surrogate key specified. Every staging and integration model has a natural key (current form) or a surrogate key (older designs, accepted) | Critical |
| Source defined | Every staging model references a source table from the pipeline architecture | Critical |
| FK → PK traceability | Every foreign key in a warehouse model references a defined PK in another model | Critical |
| Test coverage | Every warehouse model has at minimum `unique` and `not_null` on its primary key; every staging and integration model has them on its key | Critical |
| `at_least_one` placement | Where `dbt_utils.at_least_one` is specified, it sits alongside `not_null`, never in place of it on a key column | Major |
| FK tests | Every foreign key column has a `relationships` test defined | Major |
| Audit column | Every warehouse model includes `dbt_updated_at: current_timestamp()` | Major |
| Materialisation specified | Staging, base, intermediate and integration = view (existing `ephemeral` accepted), Warehouse = table (or justified exception) | Major |
| Source definitions | `_sources.yml` content is present for each source system | Major |
| Source content | New source declarations: one source per `stg_<source>/` directory named for the directory without `stg_`; `schema` and `loader` set; each table description opens `Grain:` and ends with a `Use it for` sentence; every column of a declared table declared, inline descriptions, no doc blocks; personal data columns say "Personal data." | Major |
| Source tests | `freshness` is the only test in new `_sources.yml` content (existing source files with column tests are reported as Info, not failed) | Major |
| Freshness thresholds | Freshness `warn_after` / `error_after` set for each source table with a live feed | Major |
| Natural keys not lowercased | No natural key or source identifier is specified as lowercased | Major |

**Physical ERD Checks**:

| Check | Rule | Severity |
|-------|------|----------|
| ERD present | Section 7 exists and contains a Mermaid `erDiagram` block | Critical |
| All warehouse models in ERD | Every fact, dimension, and aggregate defined in the spec appears as an entity in the ERD | Critical |
| Columns in ERD match spec | Column names in ERD entities match column names defined in the model specs | Critical |
| PK marked | Surrogate key columns are marked `PK` in the ERD | Critical |
| FK marked | Foreign key columns are marked `FK` in the ERD | Critical |
| Relationships match joins | Every FK → PK relationship in the ERD has a corresponding join path defined in the model specs | Critical |
| Relationship labels | All relationship lines have a label (the FK column name) | Major |
| Types specified | All columns have a type (`string`, `int`, `float`, `bool`, `date`, `timestamp`) | Major |
| Mermaid syntax valid | No malformed entity definitions, unclosed braces, or syntax errors | Critical |
| No staging in ERD | Staging models are not included in the ERD (warehouse only) unless explicitly justified | Info |

**Cross-System Checks**:

| Check | Rule | Severity |
|-------|------|----------|
| Cross-system joins documented | Section 6 (Cross-System Join Keys) is present and non-empty if multiple sources are joined | Major |
| Join key types compatible | Left and right join columns have compatible types | Major |
| Reference legibility | Every reference code cited from other artifacts (e.g. FR-n, D-n, PD-n) is expanded at first mention or resolved in a Reference key table — run the `reference_legibility` check per `specs/utils/reference_legibility.md` | Major |

**Canonical Vertical Comparison** — read `.wire/engagement/context.md`'s `data_model_registry.vertical` and `data_model_registry.cross_vertical_schemas`. If both are unset/`null`/empty, skip this entirely (no section appears in the report). Otherwise run whichever of the two below apply — they're independent, since a cross-vertical pattern (e.g. `crm_identity_resolution`) can be accepted with no vertical match at all:

- If `vertical` is set (confident or adjacent match — both recorded the same way): diff the generated warehouse-model list against `<registry_root>/verticals/<vertical>/schemas/*/*.yml`'s `standard_marts` (one directory per schema, so the YAML is a level deeper than `schemas/`; `<registry_root>` resolves the same way as in `generate`'s Step 1.5: `wire/data-model-registry/`, then `~/.wire/data-model-registry/`). List any `standard_marts` entries with no corresponding generated model, any generated model whose grain notably diverges from its canonical counterpart's documented grain, and any `generation_constraints` flagged during generation as deliberately not followed. If the registry's own README or the schema notes the match was adjacent rather than confident (a different industry, structurally similar shape), say so in the report rather than comparing as if it were an exact fit.
- **If `status.md` has `model_source: modality`, say which source each divergence favours.** The entity set and grain came from the client's own model, so a generated model that diverges from the registry may be correct precisely because it follows the client. Report the divergence either way, and name whether the generated model followed the client's model, the requirements, or the registry — a divergence that follows the client's authoritative model is a recorded decision, not a finding against the model. Where `design/logical_model.md` exists, check the generated keys and cardinality against the decisions it records and report any that disagree: `logical_model` is authoritative for those, and a silent disagreement means one of the two was re-derived.
- If `cross_vertical_schemas` is non-empty: for each accepted schema, check that its entities are represented in the generated model the way `generate`'s Step 1.5 proposed. Report gaps the same way — advisory, informational.

**This entire subsection is advisory. It never affects the Critical/Major severity checks above, never changes the overall PASS/FAIL result, and never blocks `data_model-review`.** A generated model legitimately differing from the canonical pattern is an expected, normal outcome — client sources vary — not a defect.

### Step 4: Generate Validation Report

```
## Data Model Validation: [PROJECT_NAME]

**Status**: PASS | FAIL
**Validated**: [date]

### Naming Convention Checks

| Check | Status | Notes |
|-------|--------|-------|
| Naming form | ℹ️ | [current / older form / form_choices ruling followed] |
| Staging naming (stg_source__entity) | ✅/❌ | |
| Fact naming (_fact) | ✅/❌ | |
| Dimension naming (_dim) | ✅/❌ | |
| Extended aggregate naming (_xa) | ✅/⚠️ | |
| Surrogate key naming (_pk) | ✅/❌ | |
| Foreign key naming (_fk) | ✅/⚠️ | |
| Boolean naming | ✅/⚠️ | |
| snake_case columns | ✅/⚠️ | |

### Model Completeness Checks

| Check | Status | Notes |
|-------|--------|-------|
| Entity coverage | ✅/❌ | [e.g. "Enrolment from conceptual model has no warehouse model"] |
| Entity mapping | ✅/❌/➖ | [e.g. "wh_sales__order_status_history_fact names no conceptual entity"; ➖ with the reason when skipped] |
| Extended aggregate reason | ✅/⚠️ | [e.g. "wh_sales__order_summary_xa: summary 'OrderSummary' is not in Agreed Summaries"] |
| Grain defined (all models) | ✅/❌ | |
| Surrogate keys defined | ✅/❌ | |
| FK → PK traceability | ✅/❌ | |
| Test coverage (PK) | ✅/❌ | |
| FK relationship tests | ✅/⚠️ | |
| Audit columns | ✅/⚠️ | |
| Materialisations | ✅/⚠️ | |
| Source definitions | ✅/❌ | |
| Source content and tests | ✅/⚠️ | |
| Freshness thresholds | ✅/⚠️ | |

### Physical ERD Checks

| Check | Status | Notes |
|-------|--------|-------|
| ERD present | ✅/❌ | |
| All warehouse models in ERD | ✅/❌ | [e.g. "student_risk_summary missing from ERD"] |
| Columns match spec | ✅/❌ | |
| PK/FK marked correctly | ✅/❌ | |
| Relationships match joins | ✅/❌ | |
| Mermaid syntax valid | ✅/❌ | |

### Cross-System Checks

| Check | Status | Notes |
|-------|--------|-------|
| Cross-system joins documented | ✅/⚠️ | |
| Join key type compatibility | ✅/⚠️ | |

[Only include this section if data_model_registry.vertical OR .cross_vertical_schemas is set — omit entirely otherwise:]
### Canonical Vertical Comparison (Advisory — informational only, not part of PASS/FAIL)

[If vertical is set:]
**Vertical**: [vertical] ([confident / adjacent — note if adjacent]) — **Schema(s)**: [schema name(s)]

| Comparison | Finding |
|------------|---------|
| Missing standard marts | [list, or "None — full coverage"] |
| Grain divergence | [list, or "None noted"] |
| generation_constraints not followed | [list with rationale, or "None"] |

[If cross_vertical_schemas is non-empty:]
**Cross-vertical patterns**: [list]

| Pattern | Finding |
|---------|---------|
| [schema name] | [entities represented as proposed, or gaps noted] |

### Issues Found

[List each Critical and Major issue with location and specific fix instruction]

### Next Steps

[If PASS]:
  /wire:data_model-review <project_id>

[If FAIL]:
  Fix issues in design/data_model_specification.md, then re-run:
  /wire:data_model-validate <project_id>
```

### Step 5: Update Status

```yaml
data_model:
  validate: pass | fail
  validated_date: [today]
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_model`
- Action: `validate`
- Status: the validate state just written to status.md (pass/fail)

## Edge Cases

### ERD and Spec Inconsistency

If an ERD entity has columns that do not appear in the corresponding model spec (or vice versa), list each discrepancy specifically:
```
❌ ERD entity ATTENDANCE_FACT has column 'session_type' but this column is not defined
   in the wh_core__attendance_fact model spec in Section 4.
   → Add 'session_type' to the model spec, or remove it from the ERD.
```

### Missing Entity in Warehouse

If a conceptual model entity has no warehouse model, this is a Critical failure — it means that entity cannot be queried in the BI layer. Options to resolve:
1. Add a warehouse model for it
2. Explicitly document it as out of scope in the data model spec (with justification)
3. Flag it as a future phase item

### Entity Mapping

Coverage checks one direction: every conceptual entity has a warehouse model. Entity mapping checks the other: every new warehouse model traces back to an agreed entity. Without it, a design can pass with extra tables that copy the source systems rather than the business.

- Check new models only. A model marked `existing` is never reported.
- Match entity and summary names to the conceptual model ignoring case, spaces and underscores (`OrderLine`, `order_line` and `Order Line` are the same name).
- A `_dim` or `_fact` with no **Conceptual entity**, with more than one, or naming an entity the inventory does not hold, fails. The fix is in the conceptual model first (add and agree the entity), or in the design (merge the model into the entity it describes as columns).
- A `_dim` or `_fact` naming an entity listed in Section 4 (out of scope) fails.
- A junction fact recording `relationship: ...` is not failed. List it in the report for `data_model-review` to decide whether the relationship should be an entity of its own; this check does not settle that.
- An `_xa` with no **Reason**, with `summary:` naming a summary not in Agreed Summaries, or with `performance:` and nothing after it, fails at Major severity.
- If the release has no `design/conceptual_model.md` (a `dashboard_first` release can design its data model without one), report both checks as skipped with that reason. A check that cannot run has not passed.

### Existing Models in the Design

A design that extends an existing dbt project lists existing models alongside new ones. Never report a finding that would require renaming an existing model, column, seed, snapshot or schema. Apply the source content, column suffix and extended aggregate checks to new models only.

### Provisional Column Names

If staging models contain provisional column names (flagged during data_model:generate because source schema was unavailable), validate will note these as Major warnings rather than failures, since they are acknowledged placeholders.

## Output

- Validation report (displayed to user)
- Updates `.wire/<project_id>/status.md` with validate result and date
