---
description: Catalog OAC's SMML semantic model — physical/logical/presentation layers
argument-hint: <release-folder>
---

# Catalog OAC's SMML semantic model — physical/logical/presentation layers

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
description: Catalog the OAC semantic model's physical connections/tables/joins, logical tables/joins/hierarchies/measures, and presentation subject areas, with migration approach and warehouse dependency mapping
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: oac_audit` and `artifact_file_path: audit/oac_audit.md` before proceeding.

---

# OAC Audit — Generate

## Purpose

Catalogs the client's Oracle Analytics Cloud (OAC) semantic model, read directly from its SMML (Semantic Modeler Markup Language) representation in the Git-backed semantic-model repo: every physical database, connection pool, physical table, and physical join (where dialect-specific SQL lives), the logical layer built on top (logical tables, joins, hierarchies, measures), and the presentation subject areas exposed to business users. The output maps physical-table-to-warehouse dependencies so the migration inventory can sequence cutover correctly — physical tables cannot be repointed to the target until their source warehouse objects exist there — and records which physical tables, joins, and table-level SQL overrides carry source-platform dialect that needs translating.

This is a **reporting-layer** audit, the OAC counterpart to the Metabase and Omni audits. It is **not gated by `migration.scope`** — it runs for any migration where the client uses OAC, full migration or tenant carve-out alike.

SMML splits dialect-specific SQL differently again to either Metabase or Omni. Metabase scatters native SQL across individually-authored cards; Omni concentrates it in model view definitions. OAC concentrates it one layer further down, in the **physical layer**: physical tables' connection pools, any physical table defined by a raw `SELECT` or stored procedure rather than a plain table reference, and physical joins built as raw expressions (`useJoinExpression: true`) rather than plain column-equality conditions. The logical layer sitting on top (logical tables, columns, joins, hierarchies) and the presentation layer above that (subject areas) reference physical columns by fully-qualified name, not by writing SQL of their own — they are dialect-neutral by construction, per `wire/skills/smml-semantic-modeling/references/smml-schema.md`. This audit therefore classifies migration approach at the **physical table** level, not the logical column or subject area level, and separately scans and classifies the finer-grained raw SQL constructs (expression-based joins, `SELECT`/procedure-sourced tables, connection-pool scripts, and any non-identity physical mapping expression riding on a logical column) that drive a physical table's classification.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- `migration.reporting_tool: oac` set in `status.md`
- A local clone (or configured path) of the OAC semantic-model Git repo, containing the SMML JSON tree (`physical/`, `logical/`, `presentation/` directories) — path recorded in `status.md` as `migration.oac_smml_repo_path`
- Python 3 available to run `wire/skills/smml-semantic-modeling/scripts/validate_smml.py`

## Inputs

- `.wire/releases/$ARGUMENTS/status.md`
- The SMML tree at `migration.oac_smml_repo_path` (`physical/`, `logical/`, `presentation/`)
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` (if present — cross-reference dbt model dependencies)

## Workflow

### Step 1: Locate the release

Confirm `release_type: platform_migration` in `status.md`. Read `migration.reporting_tool` — if it is not `oac`, stop and output:

```
reporting_tool is not set to oac.
Set migration.reporting_tool: oac in status.md and re-run.
```

Activate the `smml-semantic-modeling` skill (`skills/smml-semantic-modeling/SKILL.md`) and read `references/smml-schema.md` before parsing any SMML JSON — every object is wrapped in a singular type key (`{"physicalTable": {...}}`), and getting that wrong makes every downstream field read as missing. Note the schema doc's confidence tags: treat **[ground truth]** and **[F38574-15]** content as reliable, but don't assert something as settled fact where the schema doc itself tags it **[gap]** — carry the same caveat into this audit's output where relevant (e.g. hierarchies).

If the audit file already exists at `audit/oac_audit.md`, ask whether to re-generate (overwrite) or update (append new items only).

### Step 2: Locate the semantic-model repo

Check `migration.oac_smml_repo_path` in `status.md`. If unset, ask for the path to a local clone of the semantic-model Git repo (or its Git remote URL, to clone one), and record the answer back to `status.md`. There is **no CLI/API fallback for OAC** — SMML is a plain JSON file tree committed to Git, so the repo itself is the only supported access path; there is nothing to authenticate against the way there is a Metabase REST API or an Omni CLI.

If no path or repo is available, stop and output:

```
No OAC semantic-model repo found. Provide migration.oac_smml_repo_path pointing at
a local clone of the SMML Git repo (containing physical/, logical/, presentation/
directories), then re-run:

/wire:oac-audit-generate $ARGUMENTS
```

### Step 3: Catalog the physical layer — databases, connection pools, physical tables

Walk `physical/<Database>.json` for each `database` object: `name`, `databaseType`, and its `connectionPools[]` (name, `connection`, `requiresFullyQualifiedTableNames`, any `runOnConnectScripts` / `runBeforeQueryScripts` / `runAfterQueryScripts` / `runOnDisconnectScripts`). The connection pool is the pivot for repointing at migration time.

Walk `physical/<Database>/<Schema>/*.json` for each `physicalTable`. Distinguish base tables from aliases (role-playing dimensions — a `physicalTable` with a `sourceTable` pointing at another physical table's FQN and no `physicalColumns` of its own):

| Field | Source |
|---|---|
| `table_id` / `table_name` | physical table FQN / name |
| `database_name` / `schema_name` | parent database / schema |
| `table_type` | `base` or `alias` |
| `source_alias_of` | FQN of the base table, if `table_type: alias` |
| `source_type` | `TABLE` / `STORED_PROCEDURE` / `SELECT` (from `sourceType`) |
| `sql_summary` | first 200 chars of the `SELECT`/procedure text, where `source_type` is not `TABLE` |
| `join_count` | number of entries in `physicalTable.joins` |
| `condition_based_join_count` / `expression_based_join_count` | joins split by `useJoinExpression` |
| `warehouse_objects` | resolved source table/view (see resolution below) |
| `source_resolved` | true if ≥1 object resolved, else false |
| `column_count` | count of `physicalColumns` (aliases inherit the base table's count) |
| `complexity` | assigned in Step 6 |
| `migration_approach` | assigned in Step 6 |

**Warehouse object extraction**: for `source_type: TABLE`, resolve directly to the underlying warehouse table/view (dialect-neutral — no SQL to translate). For `STORED_PROCEDURE` and `SELECT`, parse the table's SQL/procedure call to extract referenced schema-qualified table/view names. Cross-reference resolved objects against the dbt audit where present, to confirm each is in migration scope. For any physical table where no source object resolves, set `warehouse_objects` empty **and** `source_resolved: false` so it is counted and listed, never silently dropped.

**Source-resolution coverage metric**: over active (non-decommissioned) base tables, compute `active_table_count`, `resolved_table_count`, `unresolved_table_count`, and `source_resolution_coverage_pct = resolved / active`, broken down by `source_type`.

Also catalog the **database/connection inventory**: database name, `databaseType`, each connection pool's name and connection string, and the physical tables per connection pool.

### Step 4: Catalog physical joins and raw SQL constructs

For each `physicalTable.joins` entry, capture:

| Field | Source |
|---|---|
| `join_id` | left table FQN + right table FQN (synthetic) |
| `left_table` / `right_table` | FQNs of the two physical tables |
| `use_join_expression` | boolean, from `useJoinExpression` |
| `join_type` / `cardinality` | as declared |
| `condition_summary` | for condition-based joins: `leftColumn = rightColumn` pairs |
| `expression_summary` | for expression-based joins: first 200 chars of `physicalExpression.expressionTemplate` |
| `construct_action` | assigned in Step 5, expression-based joins only — condition-based joins are plain column equality, dialect-neutral, and need no action |

Also catalog three further raw-SQL-construct categories, each of which is genuine physical-layer SQL riding somewhere other than a plain physical join:

- **`SELECT`/`STORED_PROCEDURE`-sourced physical tables** — the table's SQL/procedure text (already captured as `sql_summary` in Step 3).
- **Connection-pool scripts** — any `runOnConnectScripts`, `runBeforeQueryScripts`, `runAfterQueryScripts`, or `runOnDisconnectScripts` on a connection pool. These run literal SQL/session-configuration statements against the physical connection on every query cycle and are inherently platform-specific.
- **Non-identity physical mapping expressions** — a `logicalColumn.logicalColumnSource.physicalMappings[].physicalExpression` whose `expressionTemplate` is not the trivial passthrough `"%1"`. Although declared on a logical column, this expression executes as native SQL against the physical column(s) it references, so it is physical-layer SQL riding on a logical-layer object — scan for these specifically; don't assume every logical column mapping is dialect-neutral just because it lives in `logical/`.

Each raw SQL construct gets its own row: `construct_id`, `construct_type` (`expression_join` / `select_table` / `stored_procedure_table` / `connection_script` / `non_identity_mapping`), `owning_object` (the physical table, connection pool, or logical column it belongs to), `sql_summary`, `construct_action` (Step 5).

### Step 5: Classify raw SQL constructs

Reuses the three-way macro-classification vocabulary from `wire/specs/migration/dbt_audit/generate.md`, since these are embedded SQL fragments riding on configuration objects — the same shape of problem as a dbt macro body, not a whole queryable report object the way a Metabase card or an Omni view is:

- `translate` (default) — the construct's SQL uses a source-platform function or syntax with a direct target-platform equivalent (e.g. a date-arithmetic function translatable via the platform-pair guide).
- `redesign` — no direct equivalent (e.g. a Snowflake JavaScript/Snowpark UDF called from inside a physical `SELECT`, or a proprietary function with no target-platform analogue). Needs an architectural decision — surface at the human review gate, do not silently translate.
- `manual-review-out-of-scope` — connection-lifecycle or session-configuration scripts (`runOnConnectScripts` and siblings setting session parameters, warehouse-specific `ALTER SESSION`-equivalent statements) and catalog/dev-tooling operations. Not query-shape SQL; no target equivalent as written, and out of this audit's mechanical-translation scope.

Scan each expression-based join's `physicalExpression.expressionTemplate`, each `SELECT`/procedure table's SQL text, each connection-pool script, and each non-identity physical mapping expression for source-dialect constructs (`::` casts, `FLATTEN`, `QUALIFY`, `IFF`, `NVL`, `CONVERT_TIMEZONE`, variant `:` paths, or platform-specific function names) and assign `construct_action` accordingly.

### Step 6: Classify physical tables

Assign complexity (Low / Medium / High) and migration approach at the **physical table** level:

- `repoint` — the table is `TABLE`-sourced with condition-based joins only and no `translate`/`redesign`/`manual-review-out-of-scope` constructs attached; only the connection pool changes after warehouse migration.
- `rewrite_sql` — the table has one or more attached raw SQL constructs classified `translate` (a `SELECT`/procedure definition, an expression-based join, or a non-identity mapping); translate those constructs to the target dialect before repointing.
- `rebuild` — the table has an attached construct classified `redesign`, or depends on a source-only construct with no direct translation; rebuild against the target connection.

Default: `TABLE`-sourced physical tables with condition-based joins only → `repoint` (Low). Reclassify to `rewrite_sql` where an attached construct is `translate`, and to `rebuild` where an attached construct is `redesign`. A table with a `manual-review-out-of-scope` construct keeps its otherwise-assigned approach but is flagged separately — that construct isn't part of the mechanical translation regardless of what happens to the rest of the table.

### Step 7: Catalog the logical layer

Walk `logical/<Business Model>.json` (the `businessModel`) and `logical/<Business Model>/*.json` (each `logicalTable`):

| Field | Source |
|---|---|
| `logical_table_id` / `logical_table_name` | logical table FQN / name |
| `business_model` | the owning business model |
| `type` | `FACT` or `DIMENSION` |
| `primary_key` | as declared (dimensions only, per convention) |
| `physical_sources` | FQNs of the physical tables/aliases in `logicalTableSources` |
| `dimension_count` / `measure_count` | count of logical columns without / with `aggregation.rule` set |
| `hierarchy_count` | count of declared `logicalHierarchies` |
| `relationships` | other logical tables this one joins to (`logicalTable.joins`) |
| `migration_impact` | `none`, unless the table has a logical column flagged as a non-identity physical mapping in Step 4, in which case `see construct <construct_id>` |

The logical layer is dialect-neutral by construction: `logicalColumnSource.physicalMappings` reference physical columns by FQN, and derived/calculated measures (`derivedFrom: LOGICAL_COLUMNS`) always divide already-aggregated logical columns, never raw SQL, per `smml-schema.md`. No further translation work happens here once the physical layer underneath resolves against the target — the one exception (non-identity physical mapping expressions) is already captured and classified in Steps 4–5.

### Step 8: Catalog the presentation layer

Walk `presentation/<Subject Area>.json` and its nested `presentationTable`/`presentationColumn` objects:

| Field | Source |
|---|---|
| `subject_area` | subject area name |
| `business_model` | `sourceBusinessModel` |
| `table_count` | tables in `tableOrder` (recursively, including nested `children`) |
| `implicit_fact_column_set` | true if `implicitFactColumn` is set (relevant once the subject area spans more than one fact) |
| `hidden_object_count` | presentation tables/columns with a `hideIfTrue` expression set |
| `migration_impact` | `none` |

Presentation objects reference logical columns by FQN only and carry no SQL of their own — dialect-neutral, same as the logical layer.

### Step 9: Run structural validation

Run `python3 wire/skills/smml-semantic-modeling/scripts/validate_smml.py <migration.oac_smml_repo_path>`. This checks required properties and resolves FQN references — a structural/schema-integrity check, not an equivalency check against the warehouse. Record the pass/fail result and every reported error or warning verbatim; this is the cheap check the skill recommends running before any import into OAC, and a failing result here should be resolved (or explicitly accepted with a reason) before this audit is reviewed.

### Step 10: Write the audit report

**Output location**: `.wire/releases/$ARGUMENTS/audit/oac_audit.md`

Include:
- Summary table (databases, connection pools, physical tables by approach, physical tables by complexity, physical joins by condition/expression, raw SQL constructs by `construct_action`, logical tables/hierarchies/measures, subject areas)
- **Source-resolution coverage**: `resolved_table_count` / `active_table_count` (`source_resolution_coverage_pct`), broken down by `source_type`
- Full physical table catalog (physical layer table from Step 3)
- Physical join and raw SQL construct catalog (Step 4, with `construct_action` from Step 5)
- Database / connection pool inventory
- Logical layer catalog (Step 7) — dialect-neutral, `migration_impact` called out per table
- Presentation layer catalog (Step 8) — dialect-neutral
- Warehouse object dependency map (which warehouse objects each physical table depends on)
- **Structural validation** — the `validate_smml.py` result, verbatim
- **Unresolved physical tables** — every active table with `source_resolved: false`, listed explicitly
- dbt model dependencies (physical tables that cannot be repointed until a dbt migration batch is complete)
- Excluded / decommission candidates (unused subject areas or physical tables)

### Step 11: Update status

```yaml
artifacts:
  oac_audit:
    generate: complete
    file: audit/oac_audit.md
    generated_date: "{{TODAY}}"
    tool: oac
    database_count: N
    connection_pool_count: N
    physical_table_count: N
    physical_join_count: N
    expression_based_join_count: N
    raw_sql_construct_count: N
    translate_count: N
    redesign_count: N
    manual_review_count: N
    logical_table_count: N
    hierarchy_count: N
    measure_count: N
    subject_area_count: N
    presentation_table_count: N
    decommission_count: N
    active_table_count: N
    resolved_table_count: N
    unresolved_table_count: N
    source_resolution_coverage_pct: 0.00
    smml_validation: pass | fail
```

### Step 12: Output summary

Print: totals, breakdown by approach/complexity, raw SQL construct breakdown by action, source-resolution coverage (with unresolved count called out), structural validation result, and next command:

```
/wire:oac-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/oac_audit.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_audit` as artifact_id, `OAC Audit` as artifact_name, and the `file` value from `artifacts.oac_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `oac_audit` as artifact, `generate` as action.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
