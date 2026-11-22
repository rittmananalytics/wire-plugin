---
wire_schema: "1.0"
command: generate
artifact: droughty_stage
domain: droughty
release_types:
  - droughty
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: droughty_introspect
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Generate dbt staging models and sources.yml from a BigQuery dataset (BigQuery only)
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Droughty Stage Command

## Purpose

Run `droughty stage` to generate dbt staging model SQL files and a `sources.yml` declaration from a BigQuery dataset in one operation. Each source table gets a `stg_<table_name>.sql` file that selects all columns with basic renaming conventions applied, plus a `sources.yml` entry for the parent dataset. Output lands in the dbt project staging directory.

**BigQuery only.** Snowflake staging model generation is not supported by `droughty stage`.

## Usage

```bash
/wire:droughty-stage <release-folder>
```

## Prerequisites

- `/wire:droughty-setup` complete (BigQuery only)
- dbt project exists at the path configured in `droughty_project.yaml`
- The target dataset exists in BigQuery and is accessible

## Workflow

### Step 1: Read Setup State

1. Read `.wire/releases/[release]/status.md`
2. Confirm `droughty.setup.status == complete` and `droughty.setup.warehouse == bigquery`
3. Read `dbt_project_path` and `stage_path` from the setup block

If warehouse is Snowflake:
```
Error: droughty stage is a BigQuery-only command.

For Snowflake staging models, use /wire:dbt-generate which produces staging SQL
compatible with any warehouse.
```

### Step 2: Confirm Deployment Status

**Important**: `droughty stage` generates staging models from source tables, not from dbt-managed tables. Confirm the source dataset exists:

```
droughty stage will generate staging models for source tables in BigQuery.
This command does not require dbt to have been run.

Confirm: which BigQuery project and dataset contains the source tables?
(e.g. project: acme-raw-data, dataset: salesforce_raw)
```

Ask:
1. "GCP project ID for the source data (may differ from analytics project):"
2. "Dataset name containing the source tables:"
3. "Target a specific table, or all tables in the dataset? (table name or 'all'):"

### Step 3: Run droughty stage

```bash
droughty stage \
  --profile-dir ~/.droughty \
  --project-dir . \
  -p [gcp_project_id] \
  -d [dataset] \
  [-t [table_name]]   # only if single table targeted
```

Capture stdout and stderr. Surface any errors verbatim.

### Step 4: Verify Output

Check that files were written to `stage_path` (from `droughty_project.yaml`, defaulting to `[dbt_project_path]/models/staging/`):
- `sources.yml` — source declarations for the dataset
- `stg_[table_name].sql` — one file per table

Report file count and list generated model names.

### Step 5: Merge Check for Existing sources.yml

If a `sources.yml` already exists in the staging directory, check for conflicts:
- If the same source/table is already declared, warn the consultant and offer to skip those entries or overwrite
- Never silently overwrite an existing `sources.yml`

```
⚠️  A sources.yml already exists in [stage_path].
Droughty has generated new entries for [n] tables.

Options:
  a) Merge — append new entries, skip duplicates
  b) Overwrite — replace existing sources.yml with Droughty output
  c) Review diff first
```

### Step 5.5: Source Declarations Are Written by Hand

The `sources.yml` droughty writes is a column list for the dataset. It is not the project's source declaration. droughty does not generate `_sources.yml` files. The `_sources.yml` in each `models/staging/stg_<source>/` directory is written by hand, following the content rules in `/wire:data_model-generate` Step 2 (grain line, `Use it for` sentence, inline column descriptions, personal data marked, `freshness` as the only test). Use droughty's output as a starting list of tables and columns, then write the declaration. An existing project keeps its existing source file names.

droughty names staging files `stg_<table_name>.sql`. Before adding them to the project, rename new files to `stg_<source>__<entities>.sql` (plural entity name) in `models/staging/stg_<source>/`, or to the form a recorded `form_choices:` ruling sets. Never rename staging models that already exist in the project.

### Step 6: Update status.md

```yaml
droughty:
  stage:
    status: complete
    models_generated: [n]
    source_dataset: "[project].[dataset]"
    output_path: "[stage_path]"
    completed_date: [today]
```

### Step 7: Confirm Output

```
## Staging Models Generated ✅

[n] staging models written to [stage_path]
sources.yml updated with [n] source table declarations

Generated models:
  [list of stg_*.sql filenames]

Next steps:
  1. Review generated staging SQL — Droughty uses a straight SELECT with column aliasing.
     Add incremental logic, source freshness tests, or business logic transformations as needed.
  2. Run dbt to test the generated models:
     /wire:utils-run-dbt [release]
  3. Augment with schema tests:
     /wire:droughty-dbt-tests [release]
```

## Output

This command creates:
- `[stage_path]/stg_[table_name].sql` — one file per source table
- `[stage_path]/sources.yml` — source declarations
- Updated `droughty.stage` block in `status.md`
