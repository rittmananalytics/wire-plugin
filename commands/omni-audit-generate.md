---
description: Catalog Omni connections, model (topics/views/dimensions/measures), and folders/workbooks/tiles
argument-hint: <release-folder>
---

# Catalog Omni connections, model (topics/views/dimensions/measures), and folders/workbooks/tiles

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
description: Catalog Omni connections, model (topics, views, dimensions, measures, relationships), folders/workbooks/tiles, with migration approach and warehouse dependency mapping
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: omni_audit` and `artifact_file_path: audit/omni_audit.md` before proceeding.

---

# Omni Audit — Generate

## Purpose

Catalogs the client's Omni reporting layer: every connection, the model (topics, views, dimensions, measures, relationships), and the folder → workbook → tile content hierarchy, plus the warehouse objects each model view reads from. The output maps view-to-warehouse dependencies so the migration inventory can sequence cutover correctly — views cannot be repointed to the target until their source warehouse objects exist there — and records which model views, and which individual tiles, carry source-platform SQL dialect that needs translating.

This is a **reporting-layer** audit, the Omni counterpart to the Metabase and reverse ETL audits. It is **not gated by `migration.scope`** — it runs for any migration where the client uses Omni, full migration or tenant carve-out alike.

Omni's object model splits dialect-specific SQL differently to Metabase's. Metabase scatters native SQL across individually-authored cards; Omni concentrates it in the model's view definitions (base table SQL, derived table SQL), which a handful of modelers maintain centrally. Most tiles query through a topic and carry no SQL of their own — dialect-neutral, and they inherit whatever the model resolves to. A tile with a raw-SQL override is the exception, not the default, and gets the same source-dialect scan as a Metabase native-SQL card. This audit therefore classifies migration approach at the **view** level, not the tile level, and separately flags the smaller set of raw-SQL-override tiles for their own classification.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- `migration.reporting_tool: omni` set in `status.md`
- Omni CLI configured against the instance — a named profile (`omni config use <profile>`), or `OMNI_BASE_URL` + `OMNI_API_TOKEN` passed explicitly (see `skills/omni/SKILL.md` Step 0)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The Omni instance, via the Omni CLI
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` (if present — cross-reference dbt model dependencies)

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration` in `status.md`. Read `migration.reporting_tool` — if it is not `omni`, stop and output:

```
reporting_tool is not set to omni.
Set migration.reporting_tool: omni in status.md and re-run.
```

Activate the `omni` skill (`skills/omni/SKILL.md`) for connection details and the object hierarchy.

If the audit file already exists at `audit/omni_audit.md`, ask whether to re-generate (overwrite) or update (append new items only).

### Step 2: Connect to Omni

Per `skills/omni/SKILL.md` Step 0:

```
omni config show
omni config use <profile-name>
```

If no profile exists, try `--base-url "$OMNI_BASE_URL" --token "$OMNI_API_TOKEN"` explicitly. There is **no CSV/inventory fallback for Omni** — the CLI is the only supported access path. If neither a configured profile nor the environment variables are available, stop and output:

```
No Omni CLI access configured. Provide one of:

  1. A configured profile — run `omni config init`, or `omni config use <profile-name>`
     if one already exists
  2. OMNI_BASE_URL + OMNI_API_TOKEN environment variables

Then re-run: /wire:omni-audit-generate $ARGUMENTS
```

### Step 3: Catalog connections

Using `omni-admin`, enumerate every connection: id, name, engine (e.g. `snowflake`), and which model views run against each. The connection is the pivot for repointing at migration time.

### Step 4: Catalog the model

Using `omni-model-explorer`, walk the model: topics, and for every view exposed through a topic:

| Field | Source |
|---|---|
| `view_id` / `view_name` | view identifier / name |
| `topic_ids` | topics that expose this view |
| `connection_id` | the connection this view's table/query runs against |
| `sql_type` | `base_table` (points at a table, no SQL) / `base_table_sql` / `derived_table` |
| `sql_summary` | first 200 chars of the view's base or derived table SQL, where present |
| `warehouse_objects` | resolved source tables/views (see resolution below) |
| `source_resolved` | true if ≥1 object resolved, else false |
| `dimension_count` / `measure_count` | count of fields defined on the view |
| `relationships` | other views this one joins to |
| `complexity` | assigned in Step 6 |
| `migration_approach` | assigned in Step 6 |

**Warehouse object extraction**: for views with `sql_type: base_table`, resolve directly to the underlying warehouse table/view (dialect-neutral — no SQL to translate). For `base_table_sql` and `derived_table`, parse the view's SQL to extract referenced schema-qualified table/view names. Cross-reference resolved objects against the dbt audit where present, to confirm each is in migration scope. For any view where no source object resolves, set `warehouse_objects` empty **and** `source_resolved: false` so it is counted and listed, never silently dropped.

**Source-resolution coverage metric**: over active views, compute `active_view_count`, `resolved_view_count`, `unresolved_view_count`, and `source_resolution_coverage_pct = resolved / active`, broken down by `sql_type`.

### Step 5: Catalog folders, workbooks, and tiles

Using `omni-content-explorer`, walk the content hierarchy: folder → workbook/document → tile. For each tile:

| Field | Source |
|---|---|
| `tile_id` / `tile_name` | tile identifier / name |
| `workbook_id` / `workbook_name` | the tile's workbook/document |
| `folder_id` / `folder_name` | the workbook's folder |
| `query_surface` | `topic` (queries through the model) or `raw_sql` (SQL override) |
| `topic_id` | the topic queried, if `query_surface: topic` |
| `sql_summary` | first 200 chars of the raw SQL, if `query_surface: raw_sql` |
| `warehouse_objects` | resolved source objects, for `raw_sql` tiles only |
| `source_resolved` | for `raw_sql` tiles only |
| `migration_approach` | `inherits_via_model` for `topic` tiles; assigned in Step 6 for `raw_sql` tiles |
| `include_in_migration` | true (default) unless archived / unused >90 days |
| `migration_notes` | auto-generated |

A `topic`-backed tile needs no migration work of its own: once the model's connection swap and view translations are promoted, the tile resolves against the target automatically. Only `raw_sql` tiles carry their own dialect risk — scan each one's SQL for source-platform constructs the same way as a view.

### Step 6: Classify views and raw-SQL tiles

**Views** — assign complexity (Low / Medium / High) and migration approach:

- `repoint` — the view has no SQL (`base_table`) or portable SQL; only the connection changes after warehouse migration
- `rewrite_sql` — the view's base/derived table SQL uses source-platform dialect; translate to the target dialect before repointing
- `rebuild` — the view depends on a source-only construct with no direct translation; rebuild against the target connection

Default: `base_table` views → `repoint` (Low). Scan `base_table_sql` and `derived_table` SQL for source-dialect constructs (`::` casts, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, variant `:` paths) and reclassify `repoint` → `rewrite_sql` where found; reclassify to `rebuild` where no direct translation exists.

**Raw-SQL tiles** — assign the same three buckets (`repoint` / `rewrite_sql` / `rebuild`), scanned against the same construct list. Topic-backed tiles do not get their own bucket; they carry `migration_approach: inherits_via_model`.

### Step 7: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/omni_audit.md`

Include:
- Summary table (connections, topics, views by approach, views by complexity, tiles by query surface, raw-SQL tiles by approach)
- **Source-resolution coverage**: `resolved_view_count` / `active_view_count` (`source_resolution_coverage_pct`), broken down by `sql_type`
- Full model catalog: topic → view table (SQL summaries, dimension/measure counts, relationships)
- Content hierarchy: folder → workbook → tile
- Connection inventory (engine, views per connection)
- Warehouse object dependency map (which warehouse objects each view depends on)
- Raw-SQL tile catalog (tile, workbook, SQL summary, resolved objects, migration approach)
- **Unresolved views** — every active view with `source_resolved: false`, listed explicitly
- **Unresolved raw-SQL tiles** — every raw-SQL tile with `source_resolved: false`, listed explicitly
- dbt model dependencies (views that cannot be repointed until a dbt migration batch is complete)
- Excluded / decommission candidates (archived or unused workbooks/tiles)

### Step 8: Update status

```yaml
artifacts:
  omni_audit:
    generate: complete
    file: audit/omni_audit.md
    generated_date: "{{TODAY}}"
    tool: omni
    connection_count: N
    topic_count: N
    view_count: N
    folder_count: N
    workbook_count: N
    tile_count: N
    raw_sql_tile_count: N
    decommission_count: N
    active_view_count: N
    resolved_view_count: N
    unresolved_view_count: N
    source_resolution_coverage_pct: 0.00
```

### Step 9: Output summary

Print: totals, breakdown by approach/complexity, source-resolution coverage (with unresolved count called out), and next command:

```
/wire:omni-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/omni_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_audit` as artifact_id, `Omni Audit` as artifact_name, and the `file` value from `artifacts.omni_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_audit` as artifact, `generate` as action.

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
