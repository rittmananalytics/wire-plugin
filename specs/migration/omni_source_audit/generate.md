---
wire_schema: "1.0"
command: generate
artifact: omni_source_audit
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: document
    path: "audit/omni_source_audit.md"
    description: "Omni estate audit: views, fields, topics, relationships, dashboards, tiles and controls, each with a translation class; coverage"
  - type: report
    path: "audit/bi_model_catalog.csv"
    description: "One row per view, field, topic and relationship with construct, translation_class and complexity"
  - type: report
    path: "audit/bi_content_catalog.csv"
    description: "One row per document and tile with usage and translation_class"
preconditions: []
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Snapshot an Omni model and its dashboards through the Omni CLI and classify every view, field, topic, relationship, tile and control for the move to Looker"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_source_audit` and `artifact_file_path: audit/omni_source_audit.md` before proceeding.

---

# Omni Source Audit: Generate

## Purpose

> **Experimental.** The `omni_to_looker` pair is experimental. It has run end to end once, on Rittman Analytics' own Omni model on BigQuery: three dashboards converted, deployed to Looker and matched tile by tile (39 of 39). It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Catalogs the client's Omni estate so the migration plan can decide what moves to Looker and how. This is the `bi_migration` audit, for a move to another BI tool. It is not `/wire:omni-audit-generate`, which catalogs Omni for a warehouse move with Omni kept, or for a brownfield Omni target.

The audit first takes a snapshot through the Omni CLI, then classifies it. Both steps are deterministic scripts with no AI call; the agent runs them and writes the report. It never hand-writes what a script emits.

| What | Snapshot | Converts to |
|---|---|---|
| Views (schema views and query views) | The shared model's YAML (`omni models yaml-get --mode combined`) | LookML views: `sql_table_name` for a table, a derived table for SQL |
| Fields | The same YAML, plus Omni's field list per view (`omni models get-views`), which says which fields are time fields | Dimensions, dimension groups, measures |
| Topics and relationships | The topic files and the `relationships` file | Explores with joins |
| Dashboards | One `documents v2-get` file per dashboard on the model | LookML dashboards: the 24-column grid maps one to one; controls become dashboard filters |

## Prerequisites

- Release folder with `project_type: bi_migration` and `bi_pair: omni_to_looker` in `status.md`
- `bi_migration.source` block: `base_url` (the instance URL), `model_id` (the shared model), optional `documents` or `folders` in scope, `cli_profile`
- The Omni CLI installed and a profile that can read the model and the documents (`omni config init`, or `omni config use <profile>`); see `skills/omni/SKILL.md`
- The profile can run SQL on the model's connection: the snapshot reads column types from the warehouse's `INFORMATION_SCHEMA` through Omni (BigQuery and Snowflake), because Omni's YAML has none. Without them a dimension is typed only from its format and the filters that use it, and a DATE column is not marked as one (Looker then compares it with a timestamp, which BigQuery rejects)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- `wire/bi_pairs/omni_to_looker/translation_guide.md`, `feature_detection.md`, `property_mapping.md`
- `.wire/engagement/bi_pair_overrides/omni_to_looker/` (optional engagement overrides)

## Workflow

### Step 1: Locate the release

Confirm `project_type: bi_migration` and `bi_pair: omni_to_looker`. Read `bi_migration.source`. If `model_id` is not set, list the shared models (`omni models list`, `modelKind: SHARED`) and ask which one.

### Step 2: Take the snapshot

```bash
python3 <plugin-root>/scripts/omni_export.py snapshot --model-id <model_id> --profile <cli_profile> \
  --out .wire/releases/$ARGUMENTS/migration/source_snapshot/omni \
  [--documents <id,id>] [--folders <name,name>] [--columns <extra columns.json>] [--no-columns]
```

The snapshot holds the model file, the relationships, every topic, and the views those topics, the relationships, extends chains and dashboard tiles reach (`--all-views` keeps every view file); Omni's field list for those views; column types for the tables those views read (`columns.json`, one `INFORMATION_SCHEMA` query per dataset, run through Omni; tables with none returned are listed in `inventory.json` `column_gaps`); the connection's dialect and project; and one file per dashboard on the model. A workbook with no dashboard, or a document on another model or connection, is listed in `inventory.json` as skipped with its reason. Every object carries a SHA-256, and documents their `updated_at`; these are the pins drift and parity are measured against. Usage (visits, last viewed) stays in `inventory.json`. Record the CLI version and `snapshot_source: omni_cli` in `status.md`.

### Step 3: Classify

```bash
python3 <plugin-root>/scripts/omni_to_lookml.py audit \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/omni \
  --out .wire/releases/$ARGUMENTS/audit
```

Writes `bi_model_catalog.csv`, `bi_content_catalog.csv`, `dependencies.jsonl`, `needs_human.json` and the tool-neutral IR under `audit/ir/` (schema `wire/schemas/bi_ir-schema.md`). Classes follow the pair's translation guide: plain columns, time fields, aggregate measures, filtered measures, topics and their relationships, and tiles whose every field and filter maps are `mechanical`; bins, cross-view references, filter-only fields, access filters, default filters, approximate date windows, unmapped chart types and tiles without a topic are `assisted`; query views built from a topic query, Mustache in SQL, nested fields, markdown, field-selection controls, SQL tiles and composite OR filters are `redesign`; AI context and workbook tabs not on a dashboard are `drop`.

### Step 4: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/omni_source_audit.md`

Include: snapshot record (instance, model, CLI version, exported at, model files kept of total); summary (views by kind, fields, topics, relationships, dashboards and tiles, controls); classification breakdown; the redesign register (every construct not converted, with the reason); tiles on fields defined only in a workbook; usage (visits and last viewed); skipped documents with the reason; coverage gaps (views no topic reaches, `column_gaps`: tables whose column types were not read, so their dimensions are typed by default).

### Step 5: Update status

```yaml
artifacts:
  omni_source_audit:
    generate: complete
    file: audit/omni_source_audit.md
    generated_date: "{{TODAY}}"
    experimental: true
    omni_cli_version: "1.x"
    view_count: N
    topic_count: N
    relationship_count: N
    dashboard_count: N
    tile_count: N
    skipped_document_count: N
    mechanical_count: N
    assisted_count: N
    redesign_count: N
    drop_count: N
    snapshot_source: omni_cli
```

### Step 6: Output summary

Print the totals, the class breakdown and the next command:

```
/wire:omni-source-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/omni_source_audit.md`
- `.wire/releases/$ARGUMENTS/audit/bi_model_catalog.csv`, `bi_content_catalog.csv`, `dependencies.jsonl`, `needs_human.json`, `ir/`
- `.wire/releases/$ARGUMENTS/migration/source_snapshot/omni/`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_source_audit` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_source_audit` as artifact_id, `Omni Source Audit` as artifact_name, and the `file` value from `artifacts.omni_source_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_source_audit` as artifact, `generate` as action.
