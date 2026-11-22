---
wire_schema: "1.0"
command: validate
artifact: reverse_etl_equivalency
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: reverse_etl_audit
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Sync-level equivalence — verify a repointed reverse-ETL sync would write the same rows to its destination, at the sync grain, before its promotion PR merges
argument-hint: <release-folder> [--syncs name1,name2] [--tier 1|2]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Tier 1 reads both warehouses, SELECT only. Tier 2 runs syncs against **decoy destinations only** — the decoy ID-mapping table and scoped credential from `reverse-etl-migration`'s validation posture; production destination IDs are never present — or, for a dedicated-mode sync, against its confirmed dedicated destination, which no existing sync writes to. If any step would run a sync against a live shared destination, stop and report.

---

# Reverse ETL Equivalency — Validate

## Purpose

Model equivalency proves the warehouse tables match; nothing proved a **repointed sync writes the same rows to its destination**. The register's sync rows carried no real equivalence result, and the gap was flagged to a client as an assurance hole at cutover (#179 item 5). This command closes it with a two-tier comparison, verdicts in the same taxonomy as models, and a gate the promotion flow consumes.

Like `equivalency-validate`, this is a repeatable loop command, not a generate/validate/review artifact.

## Prerequisites

- `reverse_etl_audit` complete (the sync inventory, each sync's model resolved)
- The target-side twin exists for each in-scope sync (`reverse-etl-migration` authored it)

## Workflow

### Step 1 — Resolve scope

Every migrated sync pair (old sync on the source warehouse, twin on the target warehouse) from the reverse-ETL audit and migration outputs; `--syncs name1,name2` narrows. Under `migration.scope == tenant_carveout`, each sync's model resolves its filter from the tenant predicate registry exactly as models do — an `unresolved` sync is verdict `fail`, reason `unresolved_predicate`, never compared unfiltered, and a sync whose registry expression fails the well-formedness check in `specs/utils/tenant_predicate_registry.md` is verdict `fail`, reason `malformed_expression`, never compared on a truncated filter (#200).

### Step 2 — Tier 1: model-output comparison at the sync grain (no destination access needed)

Per sync pair, run the OLD sync's model query against the source warehouse and the NEW twin's against the target warehouse, under the same pinned-vintage discipline as model equivalence (a pinned as-of, or the baseline `T`), and compare **at the sync grain**:

- **Row set by primary key** — the sync's configured PK. Every key present on exactly both sides; missing/extra keys are named.
- **Changed-field hashes** — per row, hash the synced field set (the sync's field mapping, canonically ordered and normalised per the equivalency edge-case rules). A key present on both sides with differing hashes is a differing row, named by key and field.

This is a real verdict on "would the destination receive the same rows": the destination write is a function of the model output and the field mapping, both of which this compares. Verdicts use the model taxonomy (`pass`, `pass_qualified` via the pair allow-list or a known-difference entry, `diff_*` with a named mechanism, `fail`). Tests mirror the comparison: `wire/tests/platform_migration/validate_reverse_etl_equivalency.py`.

### Step 3 — Tier 2: decoy-destination diff (where the destination or its API allows)

Run the twin against the **decoy** destination, export or read back what landed, and compare it to the tier-1 expectation. Tier 2 catches what tier 1 cannot — destination-side transformation, API-level field coercion — and is run where the destination offers a read-back path; where it does not, the verdict rests on tier 1 and the report says so. Tier 2 never runs against a live shared destination. A dedicated-mode sync (`destination_mode: dedicated` under the `additive_dedicated_destination` topology) has no decoy, so no tier-2 decoy diff exists for it: where its confirmed dedicated destination offers a read-back path, that read-back is the tier-2 comparison — safe because no existing sync writes to the destination; where it does not, the verdict rests on tier 1 and the report says so.

### Step 4 — Verdicts, register, and log

Each sync's verdict appends to `migration/migration_verdict_log.csv` (`object_type: reverse_etl_sync`, same single-writer merge as model lanes, per `specs/migration/equivalency/verdict_schema.md`) and updates the sync's register row. `migration-register-generate` seeds one `reverse_etl_sync` row per audit sync, keyed on the normalised sync id (wire#191), so the verdict always has a row to land on. A missing row means the register predates the sync seeding: re-run `/wire:migration-register-generate $ARGUMENTS`, then write the verdict; never skip the register update. Sync rows carry a **real** `last_equivalence_result` from here on; the status table's `n/a` disappears wherever tier 1 has run.

### Step 5 — Gate integration

Sync promotion (the reverse-ETL cutover PRs, or `dbt-migration-batch-raise` deriving sync twins) requires **tier-1 `pass`** for every sync in the batch — a sync's output leaves the warehouse by definition, so the external-exactness rule applies (`pass_qualified` is not sufficient). Go-live remains the client's call; this gate governs what RA raises, not what the client merges.

### Step 6 — Report and status

`.wire/releases/$ARGUMENTS/migration/reverse_etl_equivalency_report_{run_number}.md`: per sync — tier(s) run, PK counts both sides, missing/extra/differing keys (named), verdict. Update status:

```yaml
artifacts:
  reverse_etl_equivalency:
    last_run_date: "{{TODAY}}"
    syncs_checked: N
    tier1_pass: N
    tier2_run: N
    failing: N
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_equivalency` as artifact, `validate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_equivalency` as artifact, `validate` as action.
