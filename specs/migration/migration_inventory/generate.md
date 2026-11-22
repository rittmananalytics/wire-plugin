---
wire_schema: "1.0"
command: generate
artifact: migration_inventory
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Synthesise all audits into a unified catalogue with dependency graph

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_inventory` and `artifact_file_path: migration/migration_inventory.md` before proceeding.

---

# Migration Inventory — Generate

## Purpose

Synthesises all approved audits into a single unified migration inventory. The five core audits (ingestion, db_object, security, dbt, orchestration) are always required. The reverse ETL audit is required when `migration.reverse_etl_tool` is set in `status.md`. The inventory is the canonical scope document — every object that will be migrated, its complexity, its migration approach, and its dependencies. It is the primary input to migration strategy and the reference point for all subsequent generate commands.


The `migration_approach` vocabulary is the closed set in `specs/utils/reverse_etl_approach.md` (normative): `repoint`, `rewrite_model`, `rebuild`, `decommission`. There is no `retire` value.

## Prerequisites

The following five audits must always have `review: approved`:
- `ingestion_audit`
- `db_object_audit`
- `security_audit`
- `dbt_audit`
- `orchestration_audit`

If `migration.reverse_etl_tool` is set in `status.md`, this audit must also be `review: approved`:
- `reverse_etl_audit`

If any required audit is not yet approved, output the list of incomplete audits and stop:
```
The following audits are not yet approved — complete them before generating the inventory:
[list of pending audits]

Run all audits in parallel: /wire:migration-audit-all $ARGUMENTS
```

## Inputs

- All required audit files under `.wire/releases/$ARGUMENTS/audit/`
- `.wire/releases/$ARGUMENTS/status.md`
- **Optional** `migration.connector_alias_patterns` in `status.md` — a list of regex or affix patterns to strip from connector/object identifiers and model `source()` references before matching them in Step 2 (see the alias-normalization note there). Examples: per-market prefixes such as `uk_`/`de_`/`es_`, or connector-suffix short-codes such as `__eu1`. These are documented examples, not a fixed list — set whatever patterns match the engagement's actual naming convention. If unset, Step 2 matches identifiers literally, as before.

## Workflow

### Step 1: Load all audit outputs

Read each approved audit file. Extract:
- Ingestion audit: connector list with complexity and migration approach
- DB object audit: object catalog with type, volume tier, migration approach, feature tags
- Security audit: role and policy inventory
- dbt audit: model catalog with complexity, batch number, feature tags (from `dbt_audit.csv`); **snapshot catalog** (from `dbt_snapshots.csv` if present) — each snapshot's strategy, `unique_key`, `updated_at`/`check_cols`, `invalidate_hard_deletes`, `target_schema`, upstream ref/source, downstream dependents, and `batch_number`. A snapshot is its own object type — a built SCD-2 history table — not a model; carry it through as such so it is inventoried, scoped, and ordered rather than falling through the model-only scan.
- Orchestration audit: job inventory
- Reverse ETL audit (if present): sync catalog with migration approach, warehouse object dependencies, Lightning engine flags

### Step 2: Cross-reference and deduplicate

Identify objects that appear in multiple audits and link them:
- Each ingestion connector/source writes to one or more schemas → link to db objects in those schemas
- dbt models reference source tables → link dbt models to db objects
- Snapshots read an upstream ref/source and are read by downstream models → link each snapshot to its upstream db object / dbt model and to each downstream dependent model, and link its `target_schema` to the built history relation in the db objects
- Orchestration jobs run dbt commands → link jobs to dbt models
- Service accounts in security audit → link to ingestion connectors/sources and orchestration jobs
- Hightouch syncs reference warehouse objects → link each sync to the db objects and dbt models it reads from (using the `warehouse_objects` field from the reverse ETL audit)
- Hightouch `dbtModel`-type syncs → link to the specific dbt models in the dbt audit

**Alias normalization before matching.** A regionalized or multi-tenant connector often carries an alias its consuming model's `source()` call doesn't literally repeat — a UK-market connector suffixed `_uk`, a German instance prefixed `de_`, a connector-suffix short-code like `__eu1`. Matched as bare strings, that alias makes a connector with a real downstream consumer look orphaned, which is exactly the kind of false orphan Fix W-7 (`migration_batching`'s `NO-DEP` bucket) exists to catch honestly rather than paper over. Before linking a connector or db-object identifier to a model's `source()` reference, strip any pattern listed in `migration.connector_alias_patterns` (see Inputs) from both sides, then match on the normalized form. If no patterns are configured, match literally as today — this normalization is additive and engagement-specific, never a fixed list of one client's naming scheme.

### Step 3: Build the dependency graph

Construct a directed dependency graph where:
- Edges point from dependency to dependent (data flows downstream)
- Node types: `connector`, `table`, `view`, `dbt_model`, `snapshot`, `job`, `role`, `reverse_etl_sync`, `reverse_etl_destination` — plus, when a `metabase_audit` is approved, `metabase_card` and `metabase_dashboard` (#184), with a **model→card** edge for every warehouse object a card reads (from the audit's dependency map) and a **card→dashboard** edge from the reverse index. These edges are what let batching schedule a card after the models it reads and `migration-status` derive dashboard state from card state.
- For every snapshot, add an **upstream→snapshot** edge (from its ref/source parent) and a **snapshot→dependent** edge to each downstream model. This is what lets migration batching order the snapshot after the model it reads and before its dependents — without these edges a downstream model looks like it has no snapshot prerequisite and can be scheduled ahead of it.

The graph now spans the full data flow: ingestion sources → warehouse objects → dbt models → reverse ETL syncs → SaaS destinations.

Output the graph in two formats:
1. Text adjacency list (always)
2. Mermaid diagram (if total nodes ≤200)

The Mermaid diagram should represent the six layers left-to-right:
```
[Ingestion] → [Raw Tables] → [dbt Models] → [Warehouse Views/Tables] → [Hightouch Syncs] → [Destinations]
```

### Step 4: Calculate migration effort estimate

For each object type, apply effort weights:

| Object type | Complexity | Est. hours |
|------------|-----------|-----------|
| Ingestion connector/source | Low | 0.5 |
| Ingestion connector/source | Medium | 2 |
| Ingestion connector/source | High | 4 |
| dbt model | Simple | 0.25 |
| dbt model | Moderate | 1 |
| dbt model | Complex | 3 |
| Snapshot | copy_and_continue | 1.5 |
| Snapshot | rebuild_from_T | 0.5 |
| View (translate) | Low feature count | 0.5 |
| View (translate) | High feature count | 2 |
| Security object | recreate | 0.1 |
| Security object | translate/evaluate | 1 |
| Orchestration job | recreate | 0.5 |
| Orchestration job | translate/evaluate | 2 |
| Hightouch sync | repoint (Low) | 0.5 |
| Hightouch sync | rewrite_model (Medium) | 2 |
| Hightouch sync | rebuild (High) | 8 |
| Lightning schema provisioning | per workspace | 0.5 |

Sum the estimates by phase and produce a total effort estimate.

### Step 5: Write the inventory

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_inventory.md`

Use the template at `TEMPLATES/migration/migration_inventory.md`. Include:
- Executive summary: total objects, total effort estimate, migration duration estimate (assuming 6 hours/day productive migration work)
- Phase breakdown: audit → strategy → ingestion → dbt batches → orchestration → reverse ETL → equivalency → cutover
- Unified object catalog (linked across audits) — snapshots appear as their own `snapshot` object type, each with its strategy, `unique_key`, `target_schema`, upstream ref/source, and downstream dependents
- Dependency graph (including upstream→snapshot and snapshot→dependent edges)
- Risk summary: count of High-complexity and evaluate objects; count of rebuild-type reverse ETL syncs
- Recommended phasing approach — note that reverse ETL syncs cannot be re-pointed until their dependent warehouse objects and dbt models are migrated in earlier phases

### Step 6: Update status

```yaml
artifacts:
  migration_inventory:
    generate: complete
    file: migration/migration_inventory.md
    generated_date: "{{TODAY}}"
    total_objects: N
    estimated_hours: N
    snapshots: N           # 0 if the project defines no snapshots
    reverse_etl_syncs: N   # 0 if not applicable
```

### Step 7: Output summary

Print: total objects, effort estimate, recommended migration duration, and next command:

```
/wire:migration-inventory-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_inventory.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_inventory` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_inventory` as artifact_id, `Migration Inventory` as artifact_name, and the `file` value from `artifacts.migration_inventory` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_inventory` as artifact, `generate` as action.
