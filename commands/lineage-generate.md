---
description: Generate interactive dbt lineage HTML, with optional reverse-ETL layer showing Hightouch syncs and destinations
argument-hint: <release-folder>
---

# Generate interactive dbt lineage HTML, with optional reverse-ETL layer showing Hightouch syncs and destinations

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Generate interactive dbt lineage HTML for a platform migration release, including an optional Reverse ETL layer showing Hightouch syncs and their downstream destinations
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: lineage` and `artifact_file_path: audit/lineage/lineage.html` before proceeding.

---

# Lineage View — Generate

## Purpose

Produces a self-contained interactive HTML visualisation of the full data lineage — source tables, seeds, staging, integration, warehouse, physical output objects, and (when a reverse ETL audit is present) the Hightouch syncs that read from those objects and the SaaS destinations they write to. The view is used in client deliverables and migration planning to communicate the full end-to-end data flow, identify high-fan-out models, and show which activation syncs depend on which warehouse objects.

The output is a single HTML file with no external dependencies beyond CDN-loaded vis.js and Font Awesome. It can be opened in a browser, shared with stakeholders, or committed to the project repo.


The `migration_approach` vocabulary is the closed set in `specs/utils/reverse_etl_approach.md` (normative): `repoint`, `rewrite_model`, `rebuild`, `decommission`. There is no `retire` value.

## Prerequisites

- `migration_inventory: review: approved` — the migration inventory must be approved first; lineage enriches nodes with the complexity and batch data it produces
- `dbt_audit: generate: complete` — also required for complexity, batch, and feature tag enrichment
- dbt project files accessible at `migration.dbt_project_path`
- `wire/scripts/generate_lineage.py` and `wire/scripts/lineage_template.html` present (bundled with the Wire plugin)
- `reverse_etl_audit: generate: complete` (optional) — when present, adds the Reverse ETL and Destinations layers to the right of DB Objects

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — reads `migration.dbt_project_path` and `migration.reverse_etl_tool`
- dbt project `.sql` model files
- `.wire/releases/$ARGUMENTS/audit/dbt/dbt_audit.csv` (or `audit/dbt_audit.csv`) — optional enrichment
- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md` — optional; drives the Reverse ETL and Destinations layers

## Workflow

### Step 1: Locate the release

Read `.wire/releases/$ARGUMENTS/status.md`. Confirm `release_type: platform_migration`. Read `migration.dbt_project_path` and `migration.reverse_etl_tool`.

Check whether `audit/reverse_etl_audit.md` exists. If it does, the script will include the Reverse ETL and Destinations layers.

### Step 2: Run the generation script

```bash
python3 wire/scripts/generate_lineage.py \
  --dbt-path <migration.dbt_project_path> \
  --release-path .wire/releases/$ARGUMENTS \
  --title "<project_name> — <source_platform> to <target_platform>" \
  [--reverse-etl-audit .wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md]
```

Pass `--reverse-etl-audit` only when the file exists.

The script:
- Walks all `.sql` files under `models/` and classifies them as staging, integration, or warehouse by directory name
- Parses `ref()` and `source()` calls to build the dependency graph
- Reads `config(alias='...')` from each warehouse model to get the physical table name
- Enriches nodes with complexity, batch number, and feature tags from `dbt_audit.csv` if present
- Packs nodes into group boxes by folder (connector group for sources, dbt folder for dbt layers)
- Computes a topological depth for warehouse folders to spread them horizontally where inter-folder dependencies exist
- Adds a DB Objects output layer at the far right showing the physical table/view name each warehouse model creates
- **When `--reverse-etl-audit` is passed**: parses the `warehouse_objects` column from the audit to draw edges from DB Object nodes to Reverse ETL sync nodes; adds a Reverse ETL layer (one node per sync, labelled `<sync_name> → <destination_type>`) and a Destinations layer (one node per unique destination); groups syncs by destination type in group boxes
- Writes `audit/lineage/lineage.html`, `audit/lineage/lineage_nodes.csv`, `audit/lineage/lineage_edges.csv`
- **When `--reverse-etl-audit` is passed, also writes `audit/lineage/model_sync_map.json`** — a machine-readable Gold→Hightouch edge map: for each warehouse/Gold model, the syncs that read it (`{ "<model>": [{ "sync_id", "sync_name", "destination" }, …] }`). The HTML is for humans; this JSON is the lookup the **migration drift gate** (`migration-drift-generate`) consumes to flag downstream syncs when a model is re-migrated or removed.

### Step 3: Verify output

Confirm the script exits without error. The summary output should show node and edge counts. Open `audit/lineage/lineage.html` in a browser to visually verify that:
- All five dbt layers are visible (Ingestion, Seeds, Staging, Integration, Warehouse)
- The DB Objects output layer is visible to the right of Warehouse
- When reverse ETL data is present: the Reverse ETL layer is visible to the right of DB Objects, and the Destinations layer is rightmost
- Clicking a DB Object node that is consumed by a Hightouch sync highlights the full chain: upstream dbt lineage AND downstream syncs and destinations
- Group labels appear above their bounding boxes

### Step 4: Update status

```yaml
artifacts:
  lineage_view:
    generate: complete
    file: audit/lineage/lineage.html
    generated_date: "{{TODAY}}"
    node_count: <N>
    edge_count: <N>
    generated_files:
      - audit/lineage/lineage.html
      - audit/lineage/lineage_nodes.csv
      - audit/lineage/lineage_edges.csv
```

### Step 5: Output next command

```
Lineage view generated: .wire/releases/$ARGUMENTS/audit/lineage/lineage.html

Open in a browser to explore the full dbt dependency graph.

Next: /wire:migration-strategy-generate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/lineage/lineage.html` — interactive browser explorer
- `.wire/releases/$ARGUMENTS/audit/lineage/lineage_nodes.csv` — flat node catalogue for analysis
- `.wire/releases/$ARGUMENTS/audit/lineage/lineage_edges.csv` — flat edge catalogue for analysis
- `.wire/releases/$ARGUMENTS/audit/lineage/model_sync_map.json` — Gold→Hightouch model→syncs map (reverse-ETL audit present only); consumed by `migration-drift-generate`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Lineage View Features

**Layers visible in the view** (left to right):

| Layer | Colour | Represents |
|-------|--------|-----------|
| Ingestion | Steel blue | Raw source tables from connectors (Fivetran, Coupler, etc.) |
| Seeds | Amber | dbt seed CSV files |
| Staging | Mid blue | Staging models (`stg_*`) |
| Integration | Forest green | Integration/intermediate models |
| Warehouse | Sienna | Warehouse/mart models |
| DB Objects | Teal | Physical tables/views in target warehouse |
| Reverse ETL | Purple | Hightouch syncs reading from warehouse objects |
| Destinations | Coral | SaaS destinations receiving activated data (Salesforce, HubSpot, etc.) |

The Reverse ETL and Destinations layers are only rendered when `reverse_etl_audit.md` is present. Nodes in the Reverse ETL layer are coloured by migration approach: green = repoint, amber = rewrite_model, red = rebuild. Clicking any warehouse object or DB Object node that feeds a sync highlights the full lineage from source through to destination.

**Interactions**:
- Click any node to reveal its full lineage (upstream and downstream) and collapse unrelated nodes
- Click the canvas background to restore the full view
- Filter by layer, complexity tier, or migration batch using the sidebar controls
- Drag a node to reposition its entire folder group
- Search by name to jump to a node and highlight its lineage

## Notes

- `lineage_view` is a generate-only artifact — there is no validate or review step
- Run `/wire:lineage-generate` again after `/wire:dbt-audit-generate` to refresh complexity and batch enrichment
- If the dbt project uses platform variant subdirectories (e.g. `models/warehouse/w_crm/bigquery/`) the script selects the BigQuery version over agnostic, and agnostic over Snowflake, matching the source platform. Adjust `PLAT_RANK` in `generate_lineage.py` for Snowflake-source projects


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `lineage` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `lineage` as artifact_id, `Migration Lineage` as artifact_name, and the `file` value from `artifacts.lineage` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `lineage` as artifact, `generate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
