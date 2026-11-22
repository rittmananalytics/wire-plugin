---
wire_schema: "1.0"
command: utility
artifact: omni_model
domain: migration
release_types:
  - bi_migration
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> limits the sweep to one model batch; --dry-run classifies and reports without writing; --adopt-new also ports files that exist in Omni but not in the delivery tree"
preconditions:
  - artifact: omni_model
    action: generate
    outcome: complete
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
description: "Carry changes made to the Omni model downstream (in Omni's IDE or its git repo) back into the delivery tree: four-way classification per emitted file, never clobbering unwritten local work, recorded in the register"
argument-hint: <release-folder> [--batch N] [--dry-run] [--adopt-new]

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.

---

## Data Safety: Read Before Proceeding

```
DATA SAFETY REMINDER

This command WRITES into the delivery tree (migration/omni_model/<batch>/).
It never writes to Omni, never merges a branch, and never writes to the
client's Omni model repo. It reads the downstream and copies selected files in.
```

---

# Omni Model: Reverse Port

## Purpose

After a model batch is written to the Omni branch, the version in Omni can move on without the delivery tree knowing: a client modeller edits a view in Omni's model IDE, a reviewer changes a topic during the branch review, or a fix lands after `omni models validate` flagged something. Omni writes those edits back to the model's git repo when the model is git-connected (`omni models commit`), and holds them on the branch when it is not. Nothing carried them back to `migration/omni_model/<batch>/`, which the lint, the next batch's cross-references, `omni-content-generate`'s field mapping and `bi-equivalency-validate` all treat as the authored truth.

This command makes the sweep a step with a state, the Omni counterpart of `dbt-migration-reverse-port` (`specs/migration/dbt_migration/reverse_port.md`). It is a different axis from `migration-drift-generate`: drift asks "has the LookML we translated changed underneath us"; this asks "has the Omni model we wrote changed after we wrote it". Both can be true at once.

## Prerequisites

- `omni_model generate: complete` for at least one batch (each batch folder carries a `manifest.json` written by `omni-model-generate` with the SHA-256 of every emitted file at the time it was written to Omni)
- One of:
  - `migration.client_repos[]` has an entry with `role: bi_target_model` and `migration_sources.omni_model` is registered (git-connected model): the downstream is read from the refreshed snapshot
  - Neither is set: the downstream is read live with `omni models yaml-get <modelId> --file-name <path> --branch-id <branchId> --mode extension` per emitted file

## Flags

| Flag | Effect |
|---|---|
| `--batch <id>` | Only that batch's folder |
| `--dry-run` | Classify and report; write nothing |
| `--adopt-new` | Also port files that exist downstream but not in the delivery tree (default: report them as `client_new`, do not port) |

## The four-way classification (deterministic)

For every file in `migration/omni_model/<batch>/` (views, topics, `relationships.yaml`), three hashes: `emitted_sha` (from the batch manifest, the version last written to Omni), `delivery_sha` (the delivery tree file now), `omni_sha` (the downstream file now).

| Class | Condition | Action |
|---|---|---|
| `identical` | `omni_sha == emitted_sha` and `delivery_sha == emitted_sha` | None |
| `client_ahead` | `omni_sha != emitted_sha` and `delivery_sha == emitted_sha` | Port: copy the downstream file into the delivery tree, set `emitted_sha` to it |
| `delivery_ahead` | `omni_sha == emitted_sha` and `delivery_sha != emitted_sha` | Leave: the next `omni-model-generate` for the batch writes it |
| `conflict` | both differ | Report, never write. A conflict is a parked decision for the release director |
| `client_new` | file downstream, not in the delivery tree | Report; port only with `--adopt-new` |
| `client_removed` | file in the delivery tree, not downstream | Report; the register row for that view or topic is noted `removed_downstream` |

## Workflow

### Step 1: Resolve scope and read both sides

Read `status.md`. Resolve the batches (all with `generate: complete`, or `--batch`). For each batch read `manifest.json`. Resolve the downstream:

1. If `migration_sources.omni_model` is registered, run `/wire:migration-source-refresh $ARGUMENTS omni_model` first and read files from `local_snapshot_path`. Record `migration_sources.omni_model.last_commit` as `downstream_ref`.
2. Otherwise read each file with `omni models yaml-get <bi_migration.omni_model_id> --file-name <path> --branch-id <bi_migration.omni_branch> --mode extension`. Record the branch id as `downstream_ref`.

Compute the three hashes per file.

### Step 2: Classify

Apply the table above. Nothing is written yet.

### Step 3: Port the `client_ahead` files

Unless `--dry-run`: copy each `client_ahead` file into the delivery tree, update its `emitted_sha` in `manifest.json`, and append a line to `decisions.md` naming the file and `downstream_ref`. With `--adopt-new`, do the same for `client_new` files and add them to the manifest.

Never touch a `conflict` or `delivery_ahead` file.

### Step 4: Update the register

For every register row whose emitted file was ported: `notes` gains `reverse_ported@<downstream_ref>`. For `client_removed`: `notes` gains `removed_downstream@<downstream_ref>`. For `conflict`: `notes` gains `reverse_port_conflict@<downstream_ref>` and the row is listed as a parked decision.

Under the release director model the orchestrating session is the single writer of the register; a lane running this command writes the classification to its state file and the orchestrator applies it.

### Step 5: Report

Write `migration/omni_model/reverse_port_<YYYYMMDD>.md`: per file, class, hashes, action taken. Summary counts per class. Conflicts listed first with a diff summary.

### Step 6: Update status

```yaml
artifacts:
  omni_model:
    last_reverse_port: "{{TODAY}}"
    reverse_port_conflicts: N
```

### Step 7: Output next step

```
Reverse port complete: <ported> ported, <conflicts> conflicts, <new> new downstream, <removed> removed downstream.
Conflicts need a ruling before the next batch runs:
  /wire:omni-model-review $ARGUMENTS --batch <id>
```

If any batch has open conflicts, `omni-model-lint` and `bi-equivalency-validate` for that batch should not run until they are resolved; state that.

## When to run it

- Before each new model batch (`omni-model-generate --batch N+1`), so cross-references read the shipped truth
- Before every `bi-equivalency-validate` run
- On a `utils-client-watch` trigger when a commit lands in the `bi_target_model` repo (`specs/utils/client_watch.md`)

## Output Files

- `migration/omni_model/reverse_port_<YYYYMMDD>.md`
- `migration/omni_model/<batch>/manifest.json` (updated `emitted_sha` values)
- `migration/omni_model/<batch>/*.view`, `*.topic`, `relationships.yaml` (ported files only)
- `decisions.md` (appended)

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact, `reverse_port` as action.

3. **Auto-commit**: Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_model` as artifact, `reverse_port` as action.
