---
wire_schema: "1.0"
command: generate
artifact: metabase_source_audit
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
    path: "audit/metabase_source_audit.md"
    description: "Metabase estate audit: questions, models, metrics, dashboards, tables, fields and joins, each with a translation class; native SQL; coverage"
  - type: report
    path: "audit/bi_model_catalog.csv"
    description: "One row per table and field with construct, translation_class and complexity"
  - type: report
    path: "audit/bi_content_catalog.csv"
    description: "One row per question, model, metric and dashboard with usage and translation_class"
preconditions: []
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Snapshot a Metabase instance through its API and classify every question, model, metric, dashboard, table and join for the move to Looker"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_source_audit` and `artifact_file_path: audit/metabase_source_audit.md` before proceeding.

---

# Metabase Source Audit: Generate

## Purpose

> **Experimental.** The `metabase_to_looker` pair is experimental. It has run end to end once, on a Metabase Cloud trial instance: four BigQuery questions converted, deployed to Looker and matched row for row. It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Catalogs the client's Metabase content so the migration plan can decide what moves to Looker and how. This is the `bi_migration` audit, for a move to another BI tool. It is not `/wire:metabase-audit-generate`, which belongs to `platform_migration` and catalogs Metabase for a warehouse move with Metabase kept.

Metabase keeps its content in its application database, so the audit first takes a snapshot through the API, then classifies it. Both steps are deterministic scripts with no AI call; the agent runs them and writes the report. It never hand-writes what a script emits.

| What | Snapshot | Converts to |
|---|---|---|
| Table metadata (fields, types, primary and foreign keys) | `GET /api/table/:id/query_metadata` | Views, primary keys, foreign-key joins |
| Query-builder questions | The card's query, plus the SQL Metabase compiles for it | Explore fields, measures, filters and sorts on a dashboard element |
| Native SQL questions | The card's SQL and template tags | A view on the SQL (parameters, templated filters); simple single-table SQL is also lifted onto the table's view as a proposal |
| Models | The SQL Metabase compiles for the model | A view on that SQL, with an explore |
| Metrics | The metric's aggregation and filters | A measure on the table's view |
| Dashboards | Dashcards, tabs, filters and their field mappings | LookML dashboards: the 24-column grid maps one to one; one dashboard per tab |

## Prerequisites

- Release folder with `project_type: bi_migration` and `bi_pair: metabase_to_looker` or `metabase_to_omni` in `status.md` (the audit is the same for both targets)
- `bi_migration.source` block: `host` (the instance URL), optional `dashboards` (ids in scope)
- An API key from a group that can see the content and its databases (Admin settings, Authentication, API keys), kept in a file outside the repository that only the consultant can read (for example `~/.wire/metabase.env`, mode 600, exporting `MB_HOST` and `MB_API_KEY`), never committed or pasted into a session; `python3 -m pip install requests`
- The databases in scope fully synced in Metabase: a table whose fields are not synced has no metadata to convert
- Optional: `python3 -m pip install sqlglot` to lift simple native SQL onto table views

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- `wire/bi_pairs/metabase_to_looker/translation_guide.md`, `feature_detection.md`, `property_mapping.md`
- `.wire/engagement/bi_pair_overrides/metabase_to_looker/` (optional engagement overrides)

## Workflow

### Step 1: Locate the release

Confirm `project_type: bi_migration` and `bi_pair: metabase_to_looker` or `metabase_to_omni`. Read `bi_migration.source`. If `host` is not set, stop and ask for it.

### Step 2: Take the snapshot

```bash
source ~/.wire/metabase.env
python3 <plugin-root>/scripts/metabase_export.py api --host-env MB_HOST --key-env MB_API_KEY \
  --out .wire/releases/$ARGUMENTS/migration/source_snapshot/metabase [--dashboard <id> ...]
```

The snapshot holds every card (question, model, metric) and dashboard in scope, the metadata of every table their queries read, the SQL Metabase compiles for each query-builder card, the database connections with secret settings redacted, collections and view counts. Every object carries its `updated_at` and a SHA-256; these are the pins drift and parity are measured against. Record the Metabase version and `snapshot_source: api` in `status.md`.

### Step 3: Classify

```bash
python3 <plugin-root>/scripts/mb_to_lookml.py audit \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/metabase \
  --out .wire/releases/$ARGUMENTS/audit
```

Writes `bi_model_catalog.csv`, `bi_content_catalog.csv`, `dependencies.jsonl`, `needs_human.json` and the tool-neutral IR under `audit/ir/` (schema `wire/schemas/bi_ir-schema.md`). Classes follow the pair's translation guide: plain fields, foreign-key joins, metrics and questions whose every clause maps are `mechanical`; native SQL, models, custom columns, joins not to a primary key, binning by width and the chart types listed in the guide are `assisted`; binning by number of bins, multi-stage questions, unmapped functions and content on a database Looker cannot connect to (the Sample Database's SQLite or H2) are `redesign`; archived cards, link, iframe and action cards are `drop`.

### Step 4: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/metabase_source_audit.md`

Include: snapshot record (Metabase version, exported at, object counts); summary (questions by kind (query builder or native), models, metrics, dashboards and tabs, tables, databases with engines); classification breakdown; the redesign register (every question not converted, with the reason); native SQL questions and what the lift proposed for each; usage (view counts and last used); coverage gaps (tables not synced, databases Looker cannot reach).

### Step 5: Update status

```yaml
artifacts:
  metabase_source_audit:
    generate: complete
    file: audit/metabase_source_audit.md
    generated_date: "{{TODAY}}"
    experimental: true
    metabase_version: "v1.x"
    card_count: N
    native_card_count: N
    model_count: N
    metric_count: N
    dashboard_count: N
    table_count: N
    mechanical_count: N
    assisted_count: N
    redesign_count: N
    drop_count: N
    snapshot_source: api
```

### Step 6: Output summary

Print the totals, the class breakdown and the next command:

```
/wire:metabase-source-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/metabase_source_audit.md`
- `.wire/releases/$ARGUMENTS/audit/bi_model_catalog.csv`, `bi_content_catalog.csv`, `dependencies.jsonl`, `needs_human.json`, `ir/`
- `.wire/releases/$ARGUMENTS/migration/source_snapshot/metabase/`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_source_audit` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_source_audit` as artifact_id, `Metabase Source Audit` as artifact_name, and the `file` value from `artifacts.metabase_source_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_source_audit` as artifact, `generate` as action.
