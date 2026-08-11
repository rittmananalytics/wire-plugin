---
description: Catalog Metabase collections, dashboards, cards/SQL, and permission groups
argument-hint: <release-folder>
---

# Catalog Metabase collections, dashboards, cards/SQL, and permission groups

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
description: Catalog all Metabase collections, dashboards, cards/questions, their SQL, and permission groups with migration approach and warehouse dependency mapping
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: metabase_audit` and `artifact_file_path: audit/metabase_audit.md` before proceeding.

---

# Metabase Audit — Generate

## Purpose

Catalogs the client's Metabase reporting layer: every collection, dashboard, and card/question (with its SQL), the warehouse objects each card reads from, and the permission groups that govern access. The output maps card-to-warehouse dependencies so the migration inventory can sequence cutover correctly — cards cannot be repointed to the target until their source warehouse objects exist there — and records which cards carry source-platform SQL dialect that needs translating.

This is a **reporting-layer** audit, the Metabase counterpart to the reverse ETL audit. It is **not gated by `migration.scope`** — it runs for any migration where the client uses Metabase, full migration or tenant carve-out alike.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- `migration.reporting_tool: metabase` set in `status.md`
- One of the following data sources (in priority order, see `skills/metabase/SKILL.md` Step 0):
  1. metabase-cli / serialization export configured against the instance
  2. `MB_HOST` + `MB_API_KEY` (read-only) for the Metabase REST API
  3. Client-supplied query inventory CSV at `audit/metabase_cards_input.csv`

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The Metabase instance (CLI export / REST API) or CSV fallback
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` (if present — cross-reference dbt model dependencies)

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration` in `status.md`. Read `migration.reporting_tool` — if it is not `metabase`, stop and output:

```
reporting_tool is not set to metabase.
Set migration.reporting_tool: metabase in status.md and re-run.
```

Activate the `metabase` skill (`skills/metabase/SKILL.md`) for connection details and the object hierarchy.

If the audit file already exists at `audit/metabase_audit.md`, ask whether to re-generate (overwrite) or update (append new items only).

### Step 2: Connect to Metabase

Check data sources in priority order per `skills/metabase/SKILL.md` Step 0:

- **Option 1 — serialization export**: export via the `mb` CLI and parse the YAML. Set `data_source: serialization`.
- **Option 2 — REST API**: enumerate collections, dashboards, cards, databases, and permission groups via the endpoints in the skill. Set `data_source: api`.
- **Option 3 — CSV fallback**: use `audit/metabase_cards_input.csv`. Set `data_source: csv`.

If none is available, stop and output the required CSV columns:

```
No Metabase data source found. Provide one of:

  1. metabase-cli configured against the instance (npx skills add metabase/agent-skills)
  2. MB_HOST + MB_API_KEY (read-only) for the REST API
  3. audit/metabase_cards_input.csv — exported card inventory

Required CSV columns:
  card_id, card_name, collection_id, collection_name, dashboard_ids,
  query_type, sql_summary, source_database_id, warehouse_objects,
  permission_groups, last_viewed_at, archived, include_in_migration, migration_notes

Then re-run: /wire:metabase-audit-generate $ARGUMENTS
```

### Step 3: Build the content catalog

Capture the collection → dashboard → card hierarchy, plus database connections and permission groups. For each card/question:

| Field | Source |
|---|---|
| `card_id` / `card_name` | card id / name |
| `collection_id` / `collection_name` | the card's collection |
| `dashboard_ids` | dashboards whose dashcards reference this card |
| `query_type` | `native` (SQL) or `mbql` |
| `sql_summary` | first 200 chars of `dataset_query.native.query` (full SQL from serialization/CSV) |
| `source_database_id` | the Metabase database connection the card runs against |
| `warehouse_objects` | resolved source tables/views (see resolution below) |
| `source_resolved` | true if ≥1 object resolved, else false |
| `permission_groups` | groups with access to the card's collection / database |
| `complexity` | assigned in Step 4 |
| `migration_approach` | assigned in Step 4 |
| `include_in_migration` | true (default) unless archived / unused >90 days |
| `migration_notes` | auto-generated |

Also catalog:
- **Database connections** — id, name, engine (e.g. `snowflake`), and which cards run against each. The connection is the pivot for repointing.
- **Permission groups** — each group and the databases/collections it can access (from the permission graph).

**Warehouse object extraction**: resolve `warehouse_objects` for every card.
- **`native` (SQL)** — parse the SQL to extract referenced schema-qualified table/view names.
- **`mbql`** — resolve to the table the MBQL question targets (dialect-neutral; no SQL to translate).
- Cross-reference resolved objects against the dbt audit where present, to confirm each is in migration scope.

For any card where no source object resolves, set `warehouse_objects` empty **and** `source_resolved: false` so it is counted and listed, never silently dropped.

**Source-resolution coverage metric**: over active (non-archived) cards, compute `active_card_count`, `resolved_card_count`, `unresolved_card_count`, and `source_resolution_coverage_pct = resolved / active`.

### Step 4: Classify each card

Assign complexity (Low / Medium / High) and migration approach:

- `repoint` — SQL is portable (or the card is MBQL); only the database connection changes after warehouse migration
- `rewrite_sql` — native SQL uses source-platform dialect; translate to the target dialect before repointing
- `rebuild` — the card depends on a source-only construct that has no direct translation; rebuild against the target connection
- `decommission` — archived or unused; exclude from migration

Default: active MBQL cards and simple portable-SQL cards → `repoint` (Low). Re-scan native SQL for source-dialect constructs (`::` casts, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, variant `:` paths) and reclassify `repoint` → `rewrite_sql` where found.

### Step 5: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`

Include:
- Summary table (total cards, dashboards, collections; by approach; by complexity)
- **Source-resolution coverage**: `resolved_card_count` / `active_card_count` (`source_resolution_coverage_pct`), broken down by query type
- Full card catalog table
- Collection → dashboard → card hierarchy
- Database connection inventory (engine, cards per connection)
- **Permission group inventory** — each group and its database/collection access
- Warehouse object dependency map (which warehouse objects each card depends on)
- **Unresolved cards** — every active card with `source_resolved: false`, listed explicitly
- dbt model dependencies (cards that cannot be repointed until a dbt migration batch is complete)
- Excluded / decommission candidates

### Step 6: Update status

```yaml
artifacts:
  metabase_audit:
    generate: complete
    file: audit/metabase_audit.md
    generated_date: "{{TODAY}}"
    tool: metabase
    card_count: N
    dashboard_count: N
    collection_count: N
    permission_group_count: N
    data_source: "serialization" | "api" | "csv"
    decommission_count: N
    active_card_count: N
    resolved_card_count: N
    unresolved_card_count: N
    source_resolution_coverage_pct: 0.00
```

### Step 7: Output summary

Print: totals, breakdown by approach/complexity, source-resolution coverage (with unresolved count called out), and next command:

```
/wire:metabase-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/metabase_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_audit` as artifact_id, `Metabase Audit` as artifact_name, and the `file` value from `artifacts.metabase_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_audit` as artifact, `generate` as action.

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
