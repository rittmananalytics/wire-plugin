---
wire_schema: "1.0"
command: generate
artifact: canonical_models
domain: agentic_data_stack
release_types:
  - agentic_data_stack
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: governance_design
    action: review
    outcome: approved
auto_validate: false          # validate runs dbt test --select tag:canonical, dbt compile, and dbt ls against the real warehouse
delegates_to:
  - utils/precondition_gate
description: Refactor dbt project to implement canonical models and deprecate near-duplicates
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Agentic Data Stack — Canonical Models Generate

Follow `specs/utils/agentic_data_stack_delegate.md` before executing the workflow below.

## Purpose

Implement the canonical dataset model from governance_design in the client's dbt project — renaming, consolidating, or creating mart models so every domain has one unambiguous canonical table. Apply dbt documentation and deprecation notices to tables being sunset.

## Usage

```bash
/wire:ads_canonical-models-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `governance_design.review: approved`
- `semantic_layer_design.review: approved`
- dbt project access (path in status.md)

## Workflow

### Step 1: Read Governance Design

1. Read `artifacts/governance_design.md` — canonical tables, deprecation list, domain ownership
2. Read dbt project at `dbt_project_path`
3. Check each canonical table candidate: is it already a dbt model, or does it need to be created?

### Step 2: Consolidate Near-Duplicates

For each duplicate group where the canonical candidate is already a dbt model:

1. Verify the canonical model has a schema.yml entry with:
   - Description
   - Column-level descriptions for all key fields
   - At least `not_null` and `unique` tests on the primary key
   - A `relationships` test on every foreign key

2. Add a deprecation notice to every model being sunset. In schema.yml:
   ```yaml
   models:
     - name: orders_raw
       description: |
         ⚠️ DEPRECATED — Sunset date: YYYY-MM-DD
         Use `fct_orders` instead. This model will be removed after the sunset date.
         Migration guide: replace all references to `orders_raw` with `ref('fct_orders')`.
       config:
         tags: ['deprecated']
   ```

   Then **physically relocate the model's `.sql` file to `models/deprecated/`**, mirroring
   its prior subfolder structure if it had one (e.g. `models/marts/finance/orders_raw.sql`
   → `models/deprecated/finance/orders_raw.sql`). Use `git mv` so history is preserved.
   This is required, not optional: `ref()` resolves by model name, not file path, so
   downstream references are unaffected by the move — but Step 4's folder-based
   `dbt_project.yml` config only tags a model `deprecated` if it's actually located under
   `models/deprecated/`. A model left in `models/marts/` would still match the `marts:`
   folder rule and get tagged `canonical` as well as `deprecated`, which is a contradiction:
   a table can't simultaneously be the live canonical source for its domain and be marked
   for sunset. Physically segregating deprecated models by folder is also what makes the
   eventual removal trivial once the sunset date passes — delete the file (and its
   schema.yml entry), nothing else to hunt down.

3. If the canonical model does not yet exist (consolidation required):
   - Create a new mart model combining the relevant sources
   - Follow Wire dbt naming conventions: `wh_<group>__<entity>_fact` for facts, `wh_<group>__<entity>_dim` for dimensions, `wh_<group>__<entity>_xa` for an extended aggregate (singular entity name); entity-prefixed columns such as `order_amount` and `order_is_paid`
   - Apply full schema.yml documentation and tests
   - Reference the new model from the deprecation notice on the legacy tables

### Step 3: Apply Wire dbt Conventions

For every canonical model touched in this phase, verify the rules below. Accept both naming forms on existing models and never rename an existing model or column to meet them; report a gap as a finding instead.

- Surrogate key generated via `dbt_utils.generate_surrogate_key()`
- Primary key column named `<entity>_pk`
- Foreign keys named `<entity>_fk`
- Boolean columns named `<entity>_is_/has_/was_<x>` (`user_is_active`) or, on existing models, `is_/has_/was_<x>` (`is_active`)
- Timestamp columns suffixed `_ts`
- All references use `{{ ref() }}` — no hardcoded table names
- Tests: `not_null` + `unique` on PK; `not_null` on all NOT NULL columns; `relationships` on all FKs. Use `data_tests:` in new schema files (`tests:` for dbt before 1.8, or where the file already uses `tests:`)

### Step 4: Update dbt_project.yml Tags

Add canonical and deprecated tags to the project config:

```yaml
models:
  +tags: []
  marts:
    +tags: ['canonical']
  deprecated:
    +tags: ['deprecated']
    +meta:
      sunset_date: "YYYY-MM-DD"
```

This is safe to apply in bulk precisely because Step 2 already relocated every sunset model to `models/deprecated/` — the two folders are mutually exclusive by construction, so no model can pick up both the `canonical` and `deprecated` tags.

### Step 5: Run dbt and Verify

```bash
cd <dbt_project_path>
dbt compile
dbt test --select tag:canonical
```

All canonical model tests must pass before proceeding.

### Step 6: Generate Lineage Summary

Produce a brief lineage summary for each canonical model showing:
- Sources (raw tables or staging models)
- Transformations applied
- Downstream consumers (other dbt models or BI tool explores)

Write to `.wire/<release-folder>/artifacts/canonical_models_lineage.md`.

### Step 7: Update Status

```yaml
canonical_models:
  generate: complete
  generated_date: YYYY-MM-DD
  models_canonicalized: N
  models_deprecated: N
  test_pass_rate: 100%
```

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `canonical_models`
- `artifact_name`: `Canonical Models`
- `file_path`: `.wire/[release_folder]/artifacts/canonical_models_lineage.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

## Edge Cases

### Canonical Model Already Exists and Is Well-Documented

If a canonical model already has full documentation and tests, the work is adding the deprecation notices to duplicate tables only. Note this as a low-effort domain.

### Consolidation Requires Data Reconciliation

If multiple tables need merging and have conflicting field names or data types, flag for the consultant rather than guessing. Document the conflict in the artifact and pause until resolved.

## Output

- Modified dbt models and schema.yml files in `<dbt_project_path>`
- `.wire/<release-folder>/artifacts/canonical_models_lineage.md`
- Updated `status.md`
