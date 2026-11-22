---
wire_schema: "1.0"
command: generate
artifact: omni_model
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
  optional:
    - name: flags
      description: "--batch <id> translates one model batch (default: the next incomplete model batch); --all translates every incomplete model batch in order"
produces:
  - type: document
    path: "migration/omni_model/omni_model.md"
    description: "Batch summary: per batch, views and topics emitted, needs_human items open, branch commit"
  - type: report
    path: "migration/omni_model/<batch_id>/needs_human.json"
    description: "Converter report for the batch: every construct the script did not emit, with its class, reason and the plan ruling applied"
  - type: document
    path: "migration/omni_model/<batch_id>/relationships.yaml"
    description: "Emitted Omni relationships for the batch (alongside <SCHEMA>/<table>.view and <topic>.topic files in the same directory)"
preconditions:
  - artifact: omni_target_setup
    action: review
    outcome: approved
auto_validate: false
delegates_to:
  - utils/semantic_layer_developer_delegate
  - utils/precondition_gate
  - utils/stale_artifact_check
description: Translate one batch of LookML views and explores into Omni views and topics on the model branch; the deterministic converter writes the mechanical YAML, and every construct it cannot emit becomes a needs_human item
argument-hint: <release-folder> [--batch <id> | --all]
---

## Auto-Delegation

Follow `specs/utils/semantic_layer_developer_delegate.md` before executing the workflow below.
Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_model` and `artifact_file_path: migration/omni_model/omni_model.md` before proceeding.

---

## Data Safety: Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

Looker: READ ONLY. This command reads the LookML repository at
  bi_migration.lookml_repo_path. It never writes to the Looker instance
  or to the LookML repository.

Omni: writes go to the MODEL BRANCH named in bi_migration.omni_branch,
  never to the published model. This command never merges the branch.
  Merging is a release director ruling, executed at cutover.

Warehouse: no queries. Validation queries belong to /wire:omni-model-validate.
```

If `bi_migration.omni_branch` is null, stop: `omni_target_setup` has not created the branch. Re-run `/wire:omni-target-setup-generate $ARGUMENTS`.

---

# Omni Model: Generate

## Purpose

Translates one batch of the Looker model into the Omni model. LookML views become Omni `.view` files, explores become `.topic` files, and joins become `relationships.yaml` entries, all written to the Omni model branch through the Omni CLI.

The translation has two halves and the split is deliberate. The mechanical half is a script: `wire/scripts/lookml_to_omni.py` reads the LookML, applies the pair's translation guide (`wire/bi_pairs/looker_to_omni/translation_guide.md`) and emits Omni YAML deterministically. Same input, identical output, no model call. The agent never hand-writes YAML the script can emit; a hand-written field is a field nothing can regenerate or test. The judgement half is what the script refuses: Liquid, parameters, persisted derived tables, joins Omni cannot express, `html`. Each of those arrives as a `needs_human` item, and the agent resolves it from the plan's rulings or parks it for the release director.

Omni differs from Looker in ways the emitted YAML must respect: there is no `${TABLE}` (a plain column dimension auto-maps by its column name and only derived fields carry `sql:`, referencing other fields as `${field}` or `${view.field}`); every view that takes part in a relationship needs a `primary_key: true` dimension, or Omni fans out aggregates silently; a measure filter is an operator object (`status: { is: complete }`), never a bare value. The lint step checks all three before validate spends a CLI call.

## Prerequisites

- `omni_target_setup review: approved`: the connection is verified, the schema is refreshed on it, and `bi_migration.omni_branch` names a branch created off the published model
- `bi_migration_plan review: approved`: `migration/bi_migration_batches.csv` exists and the rulings are recorded
- Omni CLI configured against the target profile with permission to write YAML on the branch (`omni whoami whoami` succeeds)
- `lkml` available to the converter (`python3 -c "import lkml"`)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` (`bi_migration.lookml_repo_path`, `bi_migration.omni_model_id`, `bi_migration.omni_branch`)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv` (rows with `batch_kind: model`)
- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (rulings: PDT disposition, redesign decisions, topic architecture)
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv` (the construct classes the audit assigned)
- `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- The LookML repository: `migration_sources.lookml.local_snapshot_path` when registered and refreshed, otherwise `bi_migration.lookml_repo_path`
- Pair files at `wire/bi_pairs/looker_to_omni/` and, when present, engagement overrides at `.wire/engagement/bi_pair_overrides/looker_to_omni/`

## Pairs: tableau_to_omni and metabase_to_omni

These pairs are experimental. There is no LookML to convert. The Tableau reader (`twb_to_lookml.py`) or the Metabase reader (`mb_to_lookml.py`) works out the model from the source snapshot, and `bi_to_omni.py` writes the Omni files from it directly, with Omni naming. Step 2 runs, in place of `lookml_to_omni.py`:

```bash
python3 <plugin-root>/scripts/bi_to_omni.py convert --source tableau \
  --snapshot migration/source_snapshot/tableau/ --out migration/omni_model/<batch_id>/ \
  [--workbooks <ids>] [--datasets <ids>] --prefix <plan prefix> --bind query|schema
python3 <plugin-root>/scripts/bi_to_omni.py convert --source metabase \
  --snapshot migration/source_snapshot/metabase/ --out migration/omni_model/<batch_id>/ \
  --database <id> [--dashboards <ids>] --prefix <plan prefix> --bind query|schema
```

It writes one view per table or SQL source (`<view>.query.view` by default), one `.topic` per explore the reader built, `relationships.yaml`, `documents/<slug>.json` and `documents/<slug>.plan.json` (read by `omni-content-generate`), `needs_human.json`, `parity_map.json` and `conversion_summary.json`. A dimension on a table column takes the column's name and the source caption as its label; a measure or calculation whose name would collide with a column is suffixed; a raw column that a derived field reads is declared hidden; fields that use a parameter or templated filter, and fields inside a record column, are not emitted and are listed. Step 3 works through `needs_human.json` as above. In Step 4, the model's `relationships` file is shared by every topic: read it from the branch, append the batch's entries that are not already there, and write it back; never replace it.

## Pair: looker_studio_to_omni

This pair is experimental in 4.2.2 (see `specs/migration/looker_studio_audit/generate.md`).

Looker Studio has no semantic model to convert, so there is no converter step and no `needs_human.json` from a script. For a model batch (one subject area):

- **Source of the model.** The warehouse tables named by the plan's model route: the existing modelled tables (`map`), or the linked `dbt_development` release's warehouse models (`build`, which must have passed `dbt-validate`). Never the Looker Studio data sources themselves.
- **Measures.** One Omni measure per ruled metric-catalogue group in the subject area, named by `target_name`, implementing `canonical_formula` as a ratio of totals where it is a ratio. A ruled formula is written exactly; it is not improved.
- **Joins.** Each blend in scope becomes a modelled join at a stated grain, with the join keys from `report.json` (`blends[].tree.keys`). A blend whose join type code is unconfirmed is a `needs_human` item.
- **Authoring.** The agent writes the YAML with the `omni-model-builder` skill on the release branch. Because nothing deterministic emits it, every file must pass `/wire:omni-model-lint` and `/wire:omni-model-validate` before review; the batch summary lists each measure with the catalogue group it implements.
- **needs_human.** Write the batch's open items (unconfirmed join codes, pipeline data sources not yet in the warehouse, catalogue groups still parked) to `migration/omni_model/<batch_id>/needs_human.json` in the same shape the converter uses, so review and lint read one format.


### Step 1: Resolve the batch

Before anything else: if any earlier batch is `complete`, run `/wire:omni-model-reverse-port $ARGUMENTS` (`specs/migration/omni_model/reverse_port.md`) so this batch's cross-references read what is actually on the Omni branch. If `migration_sources.lookml.last_commit` differs from `looker_audit.lookml_commit`, warn that the LookML has moved since the audit and recommend `/wire:migration-drift-generate $ARGUMENTS` before translating; do not stop.

Read `migration/bi_migration_batches.csv` and keep the rows with `batch_kind: model`. Resolve scope:

- `--batch <id>`: that batch. Accept `b01` or `1`; record the zero-padded form.
- `--all`: every model batch not yet in `artifacts.omni_model.batches_complete`, in `batch_id` order, one at a time through Steps 2 to 7.
- No flag: the lowest-numbered model batch not yet complete.

If the batch's `depends_on_batch` names a batch that is not complete, stop and name it. The batch's `object_type: view` and `object_type: explore` rows are the scope for the converter's `--views` and `--explores` arguments. A row with `ruling: drop` is excluded and its register row is set to `state: removed` with the reason in `notes`.

### Step 2: Run the converter

```bash
python3 <plugin-root>/scripts/lookml_to_omni.py \
  --lookml "<resolved LookML path: migration_sources.lookml.local_snapshot_path, else bi_migration.lookml_repo_path>" \
  --out ".wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>" \
  --views "<comma-separated view names>" \
  --explores "<comma-separated explore names>" \
  --overrides ".wire/engagement/bi_pair_overrides/looker_to_omni" \
  --report ".wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json" \
  --project "<LookML project name, as in the audit catalog's object_uri values>"
```

`<plugin-root>` is the installed Wire plugin directory (the converter ships at `scripts/lookml_to_omni.py`). The output directory follows the Omni model repo layout: `<SCHEMA>/<table>.view`, one `<explore>.topic` per explore, and one `relationships.yaml`. The `--overrides` directory is optional; when absent the canonical pair tables apply alone.

Beside the model files the converter writes its **intermediate representation**: `ir/views/<view>.json` and `ir/topics/<topic>.json`, one per LookML view and explore in the batch whether or not anything was emitted for it. Each field record carries its identity (`looker:<project>:field:<view>:<field>`, the same namespace as the audit's `object_uri`), its LookML type and SQL, the fields it references, its class (`mechanical`, `assisted`, `redesign`), whether it was emitted, the Omni body that was emitted, and every unsupported construct as a typed entry (construct, class, reason). Nothing disappears into a guess: a field the converter could not translate is still in the IR with the reason. `omni-model-review` reads the IR, not the `.view` files, to show class per field. `dependencies.jsonl` (`view` contains `field`, `field` references `field`, `topic` base_view, `topic` joins `view`, `topic` join_on `field`) is the model half of the release's dependency graph; the audit writes the content half in the same format. `conversion_summary.json` records `converter_version`, which the baseline and every evidence fingerprint carry.

The converter exits non-zero on a LookML parse failure. Do not patch the LookML to make it parse: record the file and line, exclude the view from the batch, and report it. A file that does not parse is a finding for the audit, not something to fix here.

### Step 3: Read the needs_human report

`needs_human.json` lists every construct the converter did not emit, or emitted with a flag:

```json
{
  "batch_id": "b01",
  "items": [
    {"id": "nh-001", "class": "redesign", "construct": "liquid_in_sql", "view": "orders", "field": "region_label",
     "lkml_file": "views/orders.view.lkml", "line": 41, "reason": "Liquid template in sql",
     "omni_alternative": "templated filter on the topic, or a groups dimension", "status": "open"},
    {"id": "nh-002", "class": "assisted", "construct": "derived_measure", "view": "orders", "field": "aov",
     "emitted": true, "reason": "type: number measure emitted without aggregate_type; confirm at validate", "status": "open"}
  ]
}
```

For each item, apply the plan's rulings in this order:

1. A ruling in `bi_migration_plan.md` that names the view or field (PDT disposition, redesign decision, drop) resolves the item. Record `status: resolved`, `ruling_ref` and what was done: for a PDT ruled to dbt, the view is emitted against the dbt model's table; for a PDT ruled to an Omni query view, write the query view YAML by hand in the batch directory (the one place hand-written YAML is expected, because the converter does not emit query views) and record its path on the item.
2. An `assisted` item with `emitted: true` stays `open` until validate confirms it; nothing to do here.
3. Anything else stays `open` and becomes a parked decision for the release director (`parked_decisions` in status.md, `kind: ruling`, question naming the view, field and the Omni alternative). Do not guess a redesign. A guessed redesign passes validate and returns wrong numbers in parity, which is the most expensive place to find it.

An item of class `redesign` must have no emitted counterpart in the batch directory. The lint step checks this.

### Step 4: Write the batch to the Omni branch

For every emitted file, in this order (views, then relationships, then topics, so each topic's `base_view` and joins already exist):

```bash
omni models yaml-create <bi_migration.omni_model_id> \
  --body "$(python3 -c 'import json,sys; print(json.dumps({"path": sys.argv[1], "yaml": open(sys.argv[2]).read()}))' "<SCHEMA>/<table>.view" "<local file>")" \
  --branch-id <bi_migration.omni_branch>
```

Use the exact path each time. A path that does not match an existing file creates a duplicate rather than an edit, and the duplicate is silent. After each write, read the file back:

```bash
omni models yaml-get <bi_migration.omni_model_id> --file-name "<SCHEMA>/<table>.view" --branch-id <bi_migration.omni_branch> --mode extension
```

Confirm the read-back matches the local file and that `omni models get-views` lists the view once. A second run of this command for the same batch is an edit, not a create: read first, write the same path.

Never run `omni models merge-branch` or `omni models commit` here. The branch is merged at cutover, on the release director's ruling, after parity passes.

### Step 4b: Write the batch manifest

After the write to the branch, write `migration/omni_model/<batch_id>/manifest.json`: one entry per emitted file with `path`, `emitted_sha` (SHA-256 of the file as written), `written_at`, `branch_id` and `lookml_commit` (the snapshot's `last_commit`), plus a header with `converter_version` and `ir_sha` (SHA-256 over the batch's `ir/` directory). `emitted_sha` is the `target_definition` component of every evidence fingerprint for objects in the batch. `omni-model-reverse-port` reads it to tell a client edit from a local one.

### Step 5: Update the register

For each view and explore in the batch, update its row in `migration/migration_register.csv` (object_type `view` or `topic`): `state: migrated` when its YAML is on the branch, `last_migrated_commit` set to the LookML snapshot's `last_commit` (the commit the converter read; `null` and a note when the source is not a git repository), `notes` carrying the batch id. A view whose only emission is a parked `needs_human` item is `state: deferred` with the item id in `notes`. Register writes follow the single-writer rule in `specs/migration/equivalency/verdict_schema.md`: under the release director model the orchestrating session writes the register from this lane's state file; outside it, this command writes the rows itself.

### Step 6: Write the batch summary

Append (or replace the batch's row in) `migration/omni_model/omni_model.md`:

```markdown
## Batch summary

| Batch | Views emitted | Topics emitted | Relationships | needs_human open | needs_human resolved | Branch | Written |
|---|---|---|---|---|---|---|---|
| b01 | 14 | 3 | 9 | 2 | 5 | feat/looker-to-omni | 2026-09-04 |

## needs_human (open)

| Item | Batch | View.field | Class | Reason | Parked decision |
|---|---|---|---|---|---|
| nh-001 | b01 | orders.region_label | redesign | Liquid template in sql | PD-4 |
```

Also record every construct the converter emitted with a flag (`assisted`) in a third table, so validate knows what to confirm.

### Step 7: Update status

```yaml
artifacts:
  omni_model:
    generate: complete          # complete only when every model batch is written; otherwise in_progress
    file: migration/omni_model/omni_model.md
    generated_date: "{{TODAY}}"
    batches_total: N
    batches_complete: [b01]
    views_emitted: N
    topics_emitted: N
    needs_human_open: N
    lint: not_started           # reset for the batch just written
    validate: not_started
```

`generate: complete` is set only when `batches_complete` covers every model batch in the plan. Until then it is `in_progress`, and the precondition gate on `omni_content` reads `validate`, not `generate`, so content for an early batch can start once that batch validates.

### Step 8: Output next command

```
Batch <batch_id> written to branch <bi_migration.omni_branch>.
  Views <N>, topics <N>, relationships <N>. needs_human open: <N> (parked decisions: <ids>).

Validate did not run (this artifact opts out of automatic validation because
validate calls the Omni CLI). Next:
/wire:omni-model-lint $ARGUMENTS --batch <batch_id>
/wire:omni-model-validate $ARGUMENTS --batch <batch_id>
```

## Under the release director model

This command is one **model slice** lane (`specs/utils/director_operating_model.md`). The lane brief names the batch, owns `migration/omni_model/<batch_id>/` and its state file, and carries no warehouse budget line (this command runs no queries). The lane reports once: the counts in Step 8, and the parked decisions it could not resolve. It does not write `status.md` or the register when `WIRE_INVOKED_BY=lane`; the orchestrating session does, from the lane's state file.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/<SCHEMA>/<table>.view` (one per view)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/<explore>.topic` (one per explore)
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/relationships.yaml`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/needs_human.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/ir/views/<view>.json`, `ir/topics/<topic>.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/dependencies.jsonl`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/conversion_summary.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/<batch_id>/manifest.json`
- `.wire/releases/$ARGUMENTS/migration/omni_model/omni_model.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact_id, `Omni Model` as artifact_name, and the `file` value from `artifacts.omni_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_model` as artifact, `generate` as action.
