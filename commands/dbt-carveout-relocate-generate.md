---
description: Relocate already-translated dbt models into a post-migration tenant carve-out instead of re-translating them
argument-hint: <release-folder> [--wave id \
---

# Relocate already-translated dbt models into a post-migration tenant carve-out instead of re-translating them

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Relocate already-translated, already-correct dbt models into a new carve-out dbt project instead of re-translating them, injecting a tenant row filter where a model is shared
argument-hint: <release-folder> [--wave id | --batch N | --select selector] --source-dbt-project-path <path> --target-dbt-project-path <path> --target-project <name> [--target-dataset <name>] [--config <path>]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_carveout_relocate` and `artifact_file_path: migration/dbt_carveout_relocate_manifest.md` before proceeding.

---

## Data Safety — Read Before Proceeding

This command never re-translates and never touches the original source platform. Before relocating any model, output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source dbt project ([--source-dbt-project-path]): READ ONLY.
  This command reads already-translated, already-correct target-dialect SQL
  from here. It is never written to, and no source-platform MCP is touched.

Target writes go to: [--target-dbt-project-path], compiled against
  [--target-project]/[--target-dataset or default schema].
```

If any generated step would write to `--source-dbt-project-path`, stop immediately and report the conflict before proceeding.

---

# dbt Carveout Relocate — Generate

## Purpose

Relocates already-translated, already-correct target-dialect dbt SQL for a tenant carve-out that is scoped **after** its parent platform migration has already landed — the carve-out does not touch the original source platform at all, so re-running `dbt-migration-generate`'s translate-and-equivalency loop against it would be pointless work re-deriving SQL that is already correct. This command is `dbt_migration`'s relocation-only counterpart, in the same relationship `bulk_copy_migration` (copy data instead of re-ingesting) has to `ingestion_migration` (re-ingest from source).

For each in-scope model:
- **`bucket: confident-region`** (tenant-exclusive) — the `.sql` file and its companion schema/properties YAML are copied unchanged.
- **`bucket: shared-row-level`** (serves every tenant) — the file is copied, then a `WHERE {migration.tenant_predicate}` clause is injected into the model's outermost `SELECT`. Where the model's structure doesn't allow a clean single-point injection, the file is copied unmodified and flagged `predicate_injection: manual_review_required` rather than guessed.

This command runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`), and only after the carve-out's `region_tagging` output has been through human adjudication — it consumes that adjudication, it never re-derives it.

## Prerequisites

- `migration.scope == tenant_carveout` and `migration.tenant_predicate` is set
- `region_tagging review: approved`
- `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` exists (written by `region-tagging-review`)
- `--target-dbt-project-path` is an already-initialized dbt project (`dbt_project.yml` and a working profile exist) pointed at the carve-out's target warehouse — this command relocates models into it, it does not scaffold the project itself

## Flags

- `--wave <id>` / `--batch N` / `--select <selector>` — scope resolution. Identical grammar, normalisation, and mutual-exclusivity rules to `dbt-migration-generate`'s Steps 1/1a/1w (same abort messages, substituting this command's name) — see that spec for the full algorithm. Resolved against the **source** dbt project (`--source-dbt-project-path`), since that is where the audit/batching/manifest data this grammar reads was produced. No flag — abort: `[wire] One of --wave, --batch, or --select is required to determine relocation scope.` (unlike `dbt-migration-generate`, there is no "next incomplete batch" default here, since relocation scope is always driven by an explicit wave/batch/selector tied to the adjudicated carve-out plan.)
- `--source-dbt-project-path <path>` — **required.** The dbt project holding the already-translated, already-correct target-dialect SQL (typically the parent platform-migration release's dbt repo). Never written to.
- `--target-dbt-project-path <path>` — **required.** The dbt project this command writes into.
- `--target-project <name>` — **required.** The target warehouse project/account this run's models should compile against (the caller runs this command once per environment — playground, then production — this flag doesn't distinguish between them).
- `--target-dataset <name>` — optional target dataset/schema override, when the target project's default isn't the intended destination.
- `--config <path>` — load a per-run config overlay file; see **Config overlay** below.

### Config overlay (`--config`)

`--config <path>` points at a small YAML or JSON file that can set `dbt_carveout_relocate.source_dbt_project_path`, `dbt_carveout_relocate.target_dbt_project_path`, `dbt_carveout_relocate.target_project`, `dbt_carveout_relocate.target_dataset`, and `migration.tenant_predicate`, read once at Step 0 and held in memory for this invocation only — never written back to status.md. Where a discrete CLI flag (`--source-dbt-project-path`, `--target-dbt-project-path`, `--target-project`, `--target-dataset`) is also supplied, the discrete flag wins for that key. This exists for the repeated-invocation case the worked example below shows — running the same source/target pair across several waves — so the operator sets the shared fields once instead of retyping them on every call.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` — the adjudicated region-tagging output (see `region-tagging-review`); columns `item_id,item_type,source_audit,bucket,signal,confidence_score,adjudicated_ruling,adjudication_note`
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — model catalog (used by `--batch` resolution)
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — authoritative execution schedule (used by `--wave` resolution)
- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`
- Source dbt project at `--source-dbt-project-path` (or the `--config` overlay equivalent) — model `.sql` and companion schema/properties YAML
- **`--config <path>` overlay (optional)** — see **Config overlay** above

## Workflow

### Step 0: Confirm prerequisites and load config overlay

1. Confirm `migration.scope == tenant_carveout`. If it is `full_migration` or absent, stop: `[wire] dbt-carveout-relocate runs in tenant carve-out scope only.`
2. Confirm `migration.tenant_predicate` is set (unless overridden by `--config`, see below). If null everywhere, stop: `[wire] migration.tenant_predicate is required to inject the shared-row-level filter.`
3. Confirm `region_tagging review: approved` in status.md. If not, stop: `[wire] region-tagging-review has not been approved yet. This command consumes adjudicated region tags — it does not run ahead of that gate.`
4. Confirm `.wire/releases/$ARGUMENTS/migration/region_tags_adjudicated.csv` exists. If not, stop: `[wire] No region_tags_adjudicated.csv found. Run /wire:region-tagging-review $ARGUMENTS first.`
5. If `--config <path>` was supplied: read and parse the file (YAML or JSON by extension/content-sniff). If it does not exist or fails to parse, abort: `[wire] --config file <path> not found or invalid. Aborting.` Hold the parsed overlay in memory; every field below checks the overlay first, then the discrete CLI flag (which wins over the overlay per-key), then status.md for `migration.tenant_predicate`.
6. Confirm `--target-dbt-project-path/dbt_project.yml` exists. If not, stop: `[wire] No dbt_project.yml found at <path>. Initialize the target dbt project (dbt init, or clone the project skeleton) before relocating models into it.`

### Step 1: Determine scope

Resolve the source dbt project via `specs/utils/dbt_manifest_parse.md` Steps 1–2, pointed at `--source-dbt-project-path`. Then resolve the model set exactly as `dbt-migration-generate` Steps 1/1a/1w describe for `--select`/`--batch`/`--wave` respectively, reading `dbt_audit.csv` and `migration/migration_batching.csv` from `$ARGUMENTS`. Print the same mandatory resolved-list preview those steps require before proceeding.

If neither `--wave`, `--batch`, nor `--select` was supplied, abort per the **Flags** section above.

### Step 1.5: Filter to the adjudicated carve-in set

Load `migration/region_tags_adjudicated.csv`. Filter to rows where `item_type == "dbt_model"` **and** `adjudicated_ruling == "carve_in"`. Intersect this set with Step 1's resolved model list, matching `item_id` against the model name.

- A Step 1 model with no matching adjudicated row at all is **not in scope for this command** — print it as skipped (`[wire] <model>: no carve_in adjudication — not relocated by this run.`) rather than treating it as an error; the wave/batch may legitimately mix carve-in and non-carve-in models.
- If the intersection is empty, stop cleanly: `[wire] No carve_in dbt_model rows in this scope. Nothing to relocate.`
- Print the resolved relocation set (model name, bucket) before proceeding, mirroring the mandatory preview pattern used elsewhere.

### Step 2: Relocate each in-scope model

For each model in the Step 1.5 set, read its bucket from `region_tags_adjudicated.csv`:

- **`bucket: confident-region`** — read the model's relative path within `--source-dbt-project-path` (from the manifest node), copy the `.sql` file and its companion schema/properties YAML entry into the mirrored path under `--target-dbt-project-path`, unchanged. Record `predicate_injection: not_applicable`.
- **`bucket: shared-row-level`** — copy the file to the mirrored path, then inject `WHERE {migration.tenant_predicate}` into the model's outermost `SELECT`:
  - **Single top-level `SELECT`, no top-level `UNION`/`UNION ALL`/`INTERSECT`/`EXCEPT`** — this is the clean case. Append the predicate to the outermost `SELECT`'s `WHERE` clause (combining with `AND` if a `WHERE` already exists there), not to any subquery/CTE. Record `predicate_injection: injected` and the exact predicate text applied.
  - **Anything else** — no top-level `SELECT` at all (e.g. a pure CTE chain with an ambiguous final projection), a top-level `UNION`/`UNION ALL`/`INTERSECT`/`EXCEPT` (injecting on one branch and not the others is wrong; injecting after the set operation may not be equivalent), or any other structure where a single clean injection point can't be identified — **do not guess.** Copy the file unmodified and record `predicate_injection: manual_review_required` with the specific reason (e.g. `"top-level UNION ALL across 2 branches — ambiguous injection point"`).
- **Any other `bucket` value** (`global-deferred`, missing, or anything not `confident-region`/`shared-row-level`) that reached this scope despite Step 1.5's filter — this is a resolution bug upstream, not a case to paper over here. **Abort**: `[wire] <model> has bucket "<bucket>" but adjudicated_ruling carve_in — this combination should not exist. Check region-tagging-review's output before re-running.`

Preserve the exact subdirectory structure from the source project for both the `.sql` file and its companion YAML.

### Step 3: Configure the target profile

Confirm `--target-dbt-project-path`'s active profile target resolves to `--target-project` (and `--target-dataset`, if supplied). This is the destination the caller passed — playground or production — the command does not distinguish between them; it runs once per environment.

### Step 4: Compile the target project

Parse/compile only — no materialisation. Run `dbt parse` (or `dbt compile`) against `--target-dbt-project-path` for the relocated models, via `specs/utils/dbt_manifest_parse.md` Step 2's scratch-directory pattern (never writing to the target project's own `target/`/`dbt_packages/`). Catch injection errors (a broken `WHERE` clause, a YAML the copy left inconsistent) before they reach a build.

If compile fails, list the failing models and the compile error; do not silently continue past a broken relocation.

### Step 5: Write the relocation manifest

**Output location**: `.wire/releases/$ARGUMENTS/migration/dbt_carveout_relocate_manifest.md`

Include:
- Scope resolved (wave/batch/selector), source and target project paths, target project/dataset
- Every relocated model: bucket, `predicate_injection` state, and the exact predicate text where injected
- The manual-review-required list, each with its specific reason
- Models skipped because they had no `carve_in` adjudication in this scope
- Compile result (pass/fail, per model on failure)

### Step 6: Update status

```yaml
artifacts:
  dbt_carveout_relocate:
    generate: complete
    generated_date: "{{TODAY}}"
    file: migration/dbt_carveout_relocate_manifest.md
    source_dbt_project_path: "{{SOURCE_DBT_PROJECT_PATH}}"
    target_dbt_project_path: "{{TARGET_DBT_PROJECT_PATH}}"
    target_project: "{{TARGET_PROJECT}}"
    target_dataset: "{{TARGET_DATASET}}"
    models_relocated: N
    confident_region_count: N
    shared_row_level_count: N
    manual_review_required_count: N
    compile: pass | fail
    wave: "B01"          # set only when run with --wave
    waves_complete: ["B01"]   # set only when run with --wave; accumulates across runs
```

### Step 7: Output summary

Print a per-model results table (model, bucket, predicate_injection state, compile result), then:

```
/wire:dbt-carveout-relocate-validate $ARGUMENTS --target-dbt-project-path <path>
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/dbt_carveout_relocate_manifest.md`
- Relocated `.sql` and companion schema/properties YAML files under `--target-dbt-project-path`, mirroring the source project's subdirectory structure
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact_id, `dbt Carveout Relocate` as artifact_name, and the `file` value from `artifacts.dbt_carveout_relocate` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_carveout_relocate` as artifact, `generate` as action.

Execute the complete workflow as specified above.
