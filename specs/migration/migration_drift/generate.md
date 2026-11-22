---
wire_schema: "1.0"
command: generate
artifact: migration_drift
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Scheduled drift gate — diff the live source dbt repo against each migrated model's last-migrated commit, classify new/modified/removed, flag downstream Hightouch syncs, and trigger the masking-policy hook

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_drift` and `artifact_file_path: migration/migration_drift_report.md` before proceeding.

---

# Migration Drift — Generate

## bi_migration mode

On a `bi_migration` release the source is the client's LookML repo (`migration_sources.lookml`) and the content is the Looker instance, not a dbt project and a warehouse. The gate keeps its shape (refresh, diff against each row's baseline, classify, blast radius, report) with these rules, tested by `wire/tests/bi_migration/validate_bi_drift.py`:

**Model rows** (`object_type` `view` or `topic`), diffed with `git diff --name-status <last_migrated_commit>..<head> -- <lkml_file>` on the refreshed snapshot:

| Finding | Rule | Register |
|---|---|---|
| `not_applicable` | `last_migrated_commit` is null (never translated) | unchanged |
| `unchanged` | file not in the diff | unchanged |
| `modified` | file `M`. Re-run the four-class rule (`wire/bi_pairs/looker_to_omni/feature_detection.md`) on the changed view; `class_changed` when the class differs from the catalog, `blocking` when the new class is `redesign` (a mechanical view that gained Liquid cannot be re-translated mechanically) | `state: drifted`, `drift_head`, change summary in `notes` |
| `removed` | file `D` | `state: drifted`, `notes: removed_upstream` |
| `renamed` | file `R` | `state: drifted`, new path in `notes` |
| `impacted` | a topic whose model file is unchanged but which references a drifted view | `notes: impacted_by <views>` |
| `unregistered_new` | file `A` with no register row | reported; the plan decides whether it joins a batch |

**Content rows** (`object_type` `dashboard` or `look`), compared through the Looker API: `content_drifted` when Looker's `updated_at` is newer than the row's `source_updated_at`; `unknown` when the baseline is null (never drifted on missing data); otherwise `unchanged`. A `content_drifted` dashboard whose content batch is complete needs `omni-content-generate --batch <id>` re-run for that dashboard before its next parity run.

Blast radius on this release type is topics and dashboards that reference a drifted view, read from `audit/dependencies.jsonl` and each batch's `migration/omni_model/<batch_id>/dependencies.jsonl` (the two halves of one graph, joined on `object_uri`), not Hightouch syncs; Steps 3, 4, 5, 5b and 5c do not apply. Scheduling and CI gating are unchanged.

**Evidence invalidation.** After classification, recompute every affected object's evidence fingerprint: `python3 <plugin-root>/scripts/bi_evidence.py invalidate --old <stored components> --new <recomputed components> [--target-change-kind semantic|presentation_only] [--row-filtering-policy]`, and write the result's `invalidated` kinds to `stale_kinds` in `migration/parity/evidence.csv`. The rules, tested by `wire/tests/bi_migration/validate_bi_evidence.py`: a changed LookML definition, dependency closure, `parity_as_of`, test contract or adapter version stales `numeric_parity` and `interaction_fidelity`; a semantic Omni change (from `omni-model-reverse-port`: sql, aggregate type, filters, joins, timeframes) stales those and `presentation_fidelity`; a presentation-only Omni change (labels, formats, colours, layout) stales `presentation_fidelity` alone and triggers no warehouse query; a policy change stales `access_parity`, and `numeric_parity` too when the object is under an access filter that shapes rows. A tile with `numeric_parity` in `stale_kinds` no longer counts for the cutover gate until `bi-equivalency-validate` re-runs it. Drift never edits a verdict; it marks the evidence stale and says which tiles to re-run.

**Pair `tableau_to_looker`** (experimental). Take a fresh snapshot with `tableau_export.py` and compare it with the pinned `inventory.json`: `python3 <plugin-root>/scripts/tableau_export.py diff --old <pinned> --new <fresh> --parity-as-of <bi_migration.parity_as_of>`. `content_drifted` when `updatedAt` is newer (or the SHA-256 changed in files mode), `removed`, `new`, and `extract_refreshed_after_parity` (the tiles on that data source are `NOT_RUN` for the gate until re-run). A drifted workbook whose model batch is complete is re-run through `twb_to_lookml.py audit` to re-classify; a class that becomes `redesign` is `blocking`.

**Pair `metabase_to_looker`** (experimental). Take a fresh snapshot with `metabase_export.py api` and compare it with the pinned `inventory.json`: `python3 <plugin-root>/scripts/metabase_export.py diff --old <pinned> --new <fresh>`. `content_drifted` when `updated_at` is newer or the SHA-256 changed, `removed` (deleted or archived), `new`. A drifted card or dashboard whose batch is complete is re-run through `mb_to_lookml.py audit` to re-classify; a class that becomes `redesign` is `blocking`.

**Pair `omni_to_looker`** (experimental). Take a fresh snapshot with `omni_export.py snapshot` and compare it with the pinned `inventory.json`: `python3 <plugin-root>/scripts/omni_export.py diff --old <pinned> --new <fresh>`. `content_drifted` when a document's `updated_at` is newer or its SHA-256 changed, `model_drifted` when a model file's SHA-256 changed, `removed`, `new`. A drifted topic, view or dashboard whose batch is complete is re-run through `omni_to_lookml.py audit` to re-classify; a class that becomes `redesign` is `blocking`.

**Pairs `tableau_to_omni` and `metabase_to_omni`** (experimental). Source drift is checked as for `tableau_to_looker` and `metabase_to_looker` above; a drifted object whose batch is complete is re-run through the reader's `audit` to re-classify, and its model batch through `bi_to_omni.py convert`.

**Pairs `looker_studio_to_omni` and `looker_studio_to_looker`.** There is no source repository to diff. Drift is checked by re-capturing (`looker-studio-audit-generate`, update mode) and comparing each report's `modified_date` and `report.json` against the stored extraction: `content_drifted` when either changed, `unknown` when no stored extraction exists. Model rows are not applicable; the warehouse model's own drift is the linked `dbt_development` release's concern.

**Baseline check.** Compare `migration/baseline.yaml` against what is live: the Looker project's deployed revision, the Omni model id and branch, the converter and comparator versions installed, `parity_as_of` in status.md. Any difference is a `baseline_drift` finding, `blocking`: the plan must re-baseline (`bi-migration-plan-generate` writes a new `baseline_id`) before another parity run counts.


## Purpose

A **scheduled drift gate**. During a long migration the source platform keeps changing — models are added, edited, and removed while batches are being translated and validated. This command diffs the **live** source dbt repo against the commit each model was last migrated from (recorded in the migration register), classifies what changed, updates register state, and surfaces the blast radius: which migrated models drifted, which downstream Hightouch syncs they feed, and whether a masking-policy change needs the policy tags regenerated.

It is designed to run on a schedule (see "Scheduling" below) and as a CI gate on the BigQuery project, so drift is caught the day it happens rather than during a cutover scramble.

## Prerequisites

- `migration/migration_register.csv` exists (`migration-register generate: complete`)
- `migration_sources.dbt` registered — the live source dbt repo
- A dbt binary available **only** for `dbt ls` state comparison (no warehouse connection needed for `ls`), or the manifest-diff fallback below

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_register.csv` — last-migrated commit per model
- `migration_sources.dbt` (live repo + local snapshot) — the current source state
- `audit/lineage/model_sync_map.json` (from `lineage-generate`) — Gold→Hightouch edges (which syncs read each warehouse model)
- `audit/reverse_etl_audit.md` — the Hightouch sync inventory and config references
- Source model `meta.masking_policy` declarations (schema/properties YAML)
- Translated model SQL under `migration/dbt/` — scanned for `-- MARKET GAP:` NULL-pad markers (Step 5b)
- Active platform pair `translation_guide.md` — the **"Deployment-integration / provenance defect patterns"** section (rule 4, `STALE_NULL_PAD_BRONZE_PRESENT`)

## Workflow

### Step 1: Refresh the live source

Run (or confirm a fresh) `/wire:migration-source-refresh $ARGUMENTS dbt` so the comparison is against the current source HEAD, not a stale snapshot. Record the live HEAD commit as `drift_head`.

### Step 2: Per-model state diff

For each `state = migrated` row in the register, compare its `last_migrated_commit` against `drift_head`. Use dbt's state comparison — **`dbt ls --select state:modified`** against a manifest built at `last_migrated_commit` as the `--state` baseline:

```
dbt ls --select state:modified --state <manifest@last_migrated_commit> --output name
```

`dbt ls` needs no warehouse connection. **Fallback (no dbt binary):** diff the model's `.sql` and its companion YAML between `last_migrated_commit` and `drift_head` with `git diff --name-status`, and parse `ref()`/`source()` + `{{ config() }}` to approximate modified/added/removed.

Classify each model:
- **modified** — the model (or its compiled definition / config / upstream refs) changed since `last_migrated_commit`. Set register `state = drifted`, record `drift_head` and a one-line change summary in `notes`.
- **removed** — the model no longer exists at `drift_head`. Set `state = removed`.
- **new** — a model present at `drift_head` with no register row. Add a row with `state = pending` (it needs migrating).
- **unchanged** — leave `state` as-is.

A model that drifted but whose `last_validated_commit` equals its old `last_migrated_commit` is flagged **"validated, now drifted"** — its prior equivalency pass is stale.

### Step 3: Flag downstream Hightouch syncs (Gold→Hightouch lineage)

For every model classified **modified** or **removed**, resolve its downstream Hightouch syncs from `model_sync_map.json` (emitted by `lineage-generate`). A re-migrated or removed Gold model flags every sync that reads it: those syncs must be re-validated (modified) or re-pointed/retired (removed). List each flagged sync with the model that triggered it.

### Step 4: Hightouch config diff

For each flagged sync, produce a **Hightouch config diff**: compare the sync's current config in the GitHub-Sync repo (model SQL, field mappings, filters) against what `reverse-etl-migration` translated, and show what the upstream drift implies — e.g. a renamed/removed column the sync's model SQL still references. This tells the reverse-ETL owner exactly what to re-translate, rather than just "something upstream changed."

### Step 5: Masking-change hook

For each **modified** model, diff its source `meta.masking_policy` (in the model's schema/properties YAML) between `last_migrated_commit` and `drift_head`. If `meta.masking_policy` was **added, changed, or removed** on any column, flag a **masking change** and trigger the policy-tag generator: re-run the `target-setup` security step (`04_security.sql` policy-tag taxonomy / data policies) for the affected objects so the BigQuery policy tags match the new source masking. Record which columns changed and that the policy-tag regeneration is required (do not silently let masking drift — a dropped masking policy that isn't re-applied is a data-exposure risk; a new one that isn't applied breaks the consuming role).

### Step 5b: Stale NULL-pad restore hook (`STALE_NULL_PAD_BRONZE_PRESENT`)

Read the pair's **"Deployment-integration / provenance defect patterns"** section (rule 4) — this is the one rule of that set that belongs in drift, because the column it watches for lands *after* generation, and only a gate that runs against the moving source can see it.

At translation time, `dbt-migration-generate` Step 3.1 item b substitutes `CAST(NULL AS <type>) /* -- MARKET GAP: <col> not present in <markets> ... */` for a source column absent in one or more markets. The connector can later catch up and the column can start carrying real data. For every `state = migrated`/`drifted` model whose translated SQL carries a `-- MARKET GAP:` NULL-pad, re-check the named source column against the **live** source warehouse (the same schema introspection Step 2's diff uses) for the previously-missing market(s):

- If the column is now **present and populated** in the live source for any of the affected markets, flag a **stale NULL-pad** finding: name the model, the column, the market(s) that now carry it, and the synthesized type from the marker. This is **flag-for-restore only** — never auto-rewritten here. Restoring the real column mapping and type is a re-translation decision (`/wire:dbt-migration-generate $ARGUMENTS --select <model>`), not a mechanical edit; note that in the finding.
- If the column is still absent in every affected market, leave the NULL-pad as-is (no finding).

Record each stale NULL-pad in the drift report (Step 6) and set the model's register `state = drifted` (its translation no longer matches the source) with a `notes` entry naming the restored column. Do not silently leave a column synthesizing NULL once the source carries real data — that is a widening, invisible data gap.

### Step 5c: Cross-release triggers (tenant carve-out, #180)

Applies only when `migration.cross_release_triggers` in status.md is non-empty (a carve-out tracking a live parent release). A carve-out inherits the parent's translations, backfills, and defects, and the dependencies between the two releases go stale exactly like blocker notes do — "closes when the parent completes its Bronze backfill" is a caveat nobody re-tests unless a gate does.

For each trigger with `status: open`:

1. **Evaluate the condition** against the parent release's current state — read the parent register at `.wire/releases/<trigger.parent_release>/migration/migration_register.csv` (and, where the condition names them, the parent's verdict log or drift report). A condition is met only by evidence read this run, never by the trigger's age.
2. **When met**, set `status: fired` in status.md and surface the trigger's `action` in the drift report: the dependent carve-out models to re-verify (resolved via the register's `parent_release` / `parent_model` linkage columns), the command to run, and the event that fired.
3. **Parent defect-class propagation.** When the parent release records a defect-class sweep (`equivalency-sweep`) whose pattern hits models this carve-out relocated, mark each relocated copy **re-verify-owed**: append a `notes` entry naming the parent sweep and pattern id, and list the models in the drift report. Their standing verdicts are stale evidence — the parent's fix does not re-prove the copy.
4. A trigger stays `fired` until the surfaced re-verifications complete (the drift report lists it every run); the consultant closes it (`status: closed`) once the dependent register rows carry fresh verdicts.

### Step 6: Write the drift report

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_drift_report.md`

Use `TEMPLATES/migration/migration_drift_report.md`. Include: `drift_head` and the run timestamp; counts (modified / removed / new / unchanged); the per-model drift table (model, classification, change summary, prior equivalence state); the flagged downstream syncs with their config diffs; the masking changes with the policy-tag regeneration actions; the **stale NULL-pad restores** (Step 5b) — each flagged model, column, now-present market(s), and synthesized type, marked flag-for-restore; and the **cross-release triggers** (Step 5c) — each fired trigger with its event, the dependent re-verifications, and the re-verify-owed relocated models. Re-write the affected register rows (Step 2, Step 5b, and Step 5c item 3).

### Step 7: Update status

```yaml
artifacts:
  migration_drift:
    generate: complete
    file: migration/migration_drift_report.md
    last_run_date: "{{TODAY}}"
    drift_head: "<commit>"
    modified: N
    removed: N
    new: N
    syncs_flagged: N
    masking_changes: N
    stale_null_pads: N        # STALE_NULL_PAD_BRONZE_PRESENT — MARKET GAP columns now present in the live source, flagged for restore
    cross_release_triggers_fired: N   # carve-out only — triggers whose condition was met this run (Step 5c)
```

### Step 8: Output next command

```
/wire:migration-drift-validate $ARGUMENTS
```

If any models drifted: re-migrate them (`/wire:dbt-migration-generate $ARGUMENTS --select <drifted models>`), then re-run equivalency in baseline mode and, where masking changed, re-run `target-setup`.

## Scheduling

This gate is meant to run unattended. Deploy it two ways (templates in `TEMPLATES/migration/ci/`):

- **Scheduled** — `migration-drift-schedule.yml`: a cron GitHub Actions workflow on the delivery repo that refreshes the source and runs this drift check (e.g. nightly), opening/annotating an issue when drift is found.
- **On-change CI** — `migrated-model-ci.yml`: on any change to a migrated model (path filter derived from the register's `source_path` column), re-run compile + the tiered sweep (Tier 1 `dbt-migration-lint` + Tier 3 `equivalency-validate --baseline`).

## Output Files

- `.wire/releases/$ARGUMENTS/migration/migration_drift_report.md`
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_drift` as artifact_id, `Migration Drift` as artifact_name, and the `file` value from `artifacts.migration_drift` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_drift` as artifact, `generate` as action.
