---
wire_schema: "1.0"
command: generate
artifact: tableau_audit
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
    path: "audit/tableau_audit.md"
    description: "Tableau estate audit: workbooks, sheets, dashboards, data sources, fields and joins, each with a translation class; data source fingerprint groups; extracts; coverage"
  - type: report
    path: "audit/bi_model_catalog.csv"
    description: "One row per data source, join and field with construct, translation_class and complexity"
  - type: report
    path: "audit/bi_content_catalog.csv"
    description: "One row per workbook, sheet, dashboard and story with usage and translation_class"
  - type: report
    path: "audit/datasource_fingerprints.csv"
    description: "One row per group of identical data sources, with member workbooks and the proposed shared explore"
preconditions: []
delegates_to:
  - utils/precondition_gate
  - utils/migration_agent_delegate
  - utils/stale_artifact_check
description: "Experimental: Snapshot the Tableau estate (Cloud, Server, or Desktop files) and classify every workbook, data source, field and join for the move to Looker, with data source fingerprints for consolidation"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.
Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: tableau_audit` and `artifact_file_path: audit/tableau_audit.md` before proceeding.

---

# Tableau Audit: Generate

## Purpose

> **Experimental.** The `tableau_to_looker` pair is experimental. It has run end to end once, on a Tableau Cloud trial site: one BigQuery sheet converted, deployed to Looker and matched row for row. It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Catalogs the client's Tableau estate so the migration plan can decide what moves to Looker and how. Tableau keeps the model and the content in one XML document per workbook (plus published data sources), and there is no git repository to register, so the audit first takes a snapshot, then classifies it. Both steps are deterministic scripts with no AI call; the agent runs them and writes the report. It never hand-writes what a script emits.

| Edition | Snapshot | Usage | Parity source side |
|---|---|---|---|
| Tableau Cloud | `tableau_export.py rest` | Admin Insights export, else REST all-time view counts | REST Query View Data |
| Tableau Server | `tableau_export.py rest` | Repository (read-only user) or `unavailable` | REST Query View Data |
| Desktop files only | `tableau_export.py files` (no network call) | `unavailable` | Manual export per sheet |

## Prerequisites

- Release folder with `project_type: bi_migration` and `bi_pair: tableau_to_looker` or `tableau_to_omni` in `status.md` (the audit is the same for both targets)
- `bi_migration.source` block: `edition`, and either `server_url` and `site` (Cloud or Server) or `files_path` (Desktop)
- For Cloud or Server: a personal access token in two environment variables (name and secret), loaded from a file outside the repository that only the consultant can read (for example `~/.wire/tableau.env`, mode 600), never committed or pasted into a session; `python3 -m pip install tableauserverclient`. Token creation can be switched off for the site: a site administrator turns it on under Settings, General
- For usage on Cloud: an Admin Insights export (CSV) path in `bi_migration.source.usage_csv`. Without one, the snapshot records each view's all-time view count from the REST API (`usage_source: rest_total_views`): it has no time window and no last-viewed date, so the report says so and ranks by it with care

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- `wire/bi_pairs/tableau_to_looker/translation_guide.md`, `feature_detection.md`, `property_mapping.md`
- `.wire/engagement/bi_pair_overrides/tableau_to_looker/` (optional engagement overrides)

## Workflow

### Step 1: Locate the release

Confirm `project_type: bi_migration` and `bi_pair: tableau_to_looker` or `tableau_to_omni`. Read `bi_migration.source`. If neither `server_url` nor `files_path` is set, stop and ask for one.

### Step 2: Take the snapshot

```bash
# Cloud or Server
python3 <plugin-root>/scripts/tableau_export.py rest --server <server_url> --site <site> \
  --token-name-env TABLEAU_PAT_NAME --token-env TABLEAU_PAT_SECRET \
  --out .wire/releases/$ARGUMENTS/migration/source_snapshot/tableau [--usage-csv <admin_insights.csv>]
# Desktop files
python3 <plugin-root>/scripts/tableau_export.py files --dir <files_path> --site <site> \
  --out .wire/releases/$ARGUMENTS/migration/source_snapshot/tableau
```

Workbooks are downloaded without extracts. The snapshot records every object's LUID, project, owner, `updatedAt`, SHA-256, extract refresh time and subscriptions. These are the pins drift and parity are measured against. Record `snapshot_source` (`rest` or `files`), `edition`, the API version and `usage_source` in `status.md`.

### Step 3: Classify

```bash
python3 <plugin-root>/scripts/twb_to_lookml.py audit \
  --snapshot .wire/releases/$ARGUMENTS/migration/source_snapshot/tableau \
  --out .wire/releases/$ARGUMENTS/audit --site <site>
```

Writes `bi_model_catalog.csv`, `bi_content_catalog.csv`, `datasource_fingerprints.csv`, `dependencies.jsonl` and the tool-neutral IR under `audit/ir/` (schema `wire/schemas/bi_ir-schema.md`). Classes follow the pair's translation guide: plain columns are `mechanical`; row-level and aggregate calculations, parameters, groups, bins, sets, custom SQL, physical joins and relationships are `assisted`; LOD expressions, table calculations, blends and extract-backed data sources are `redesign`; stories, images and device layouts are `drop`. If the script stops with `ERROR`, the workbook XML has a structure it does not know: record the file and stop.

### Step 4: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/tableau_audit.md`

Include: snapshot record (edition, source, API version, exported at, object counts); summary (workbooks, sheets, dashboards, stories, data sources embedded and published, fields by kind); classification breakdown; fingerprint groups (how many embedded data sources collapse into how many shared explores); the redesign register (every LOD, table calculation, blend, extract and file source (Excel, CSV, extract-only `.hyper`) with its workbook); usage (the 80% cut when usage is available, else `unknown`); subscriptions; coverage gaps.

### Step 5: Update status

```yaml
artifacts:
  tableau_audit:
    generate: complete
    file: audit/tableau_audit.md
    generated_date: "{{TODAY}}"
    experimental: true
    workbook_count: N
    datasource_count: N
    fingerprint_group_count: N
    mechanical_count: N
    assisted_count: N
    redesign_count: N
    drop_count: N
    usage_source: admin_insights | repository | unavailable
    snapshot_source: rest | files
```

### Step 6: Output summary

Print the totals, the class breakdown, the fingerprint groups and the next command:

```
/wire:tableau-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/tableau_audit.md`
- `.wire/releases/$ARGUMENTS/audit/bi_model_catalog.csv`, `bi_content_catalog.csv`, `datasource_fingerprints.csv`, `dependencies.jsonl`, `ir/`
- `.wire/releases/$ARGUMENTS/migration/source_snapshot/tableau/`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `tableau_audit` as artifact, `generate` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `tableau_audit` as artifact_id, `Tableau Audit` as artifact_name, and the `file` value from `artifacts.tableau_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `tableau_audit` as artifact, `generate` as action.
