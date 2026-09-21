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

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'oac-audit-generate',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Automatic Validation (on by default)

---
description: Internal utility — injected auto-validate section so generate commands run their matching validate step automatically and fold the result into their output
---

Every `generate` command that has a matching `validate` command for the
same artifact runs that validate step automatically as part of generate —
by default, with no separate command to remember. This section only appears
on commands where that applies; artifacts with no separate validate step at
all (e.g. mockups, workshops, UAT) never carry this section.

## Step: Check `auto_validate`

Read this command's own `auto_validate` front-matter field, in the Workflow
Specification below. Two states:

- **Absent, or `true`** (the default — most artifacts): auto-validate runs.
- **`false`**: this artifact's validate step is expensive — it runs real
  code, queries a live warehouse or BI tool, or otherwise does IO beyond
  re-reading local files — so it does not run automatically. Skip to
  "If `auto_validate: false`" below.

## If `auto_validate` is absent or `true`: run validate automatically

Once this command finishes writing its artifact, before ending:

1. Run this artifact's own `/wire:<artifact-with-dashes>-validate` workflow
   in full, exactly as if the consultant had typed it themselves — same
   inputs, same `status.md` write to `artifacts.<artifact>.validate`, same
   report. This is not optional or an extra step layered on top; it is the
   default behavior for this artifact.
2. Fold the result into this command's own closing output rather than
   presenting it as a separate command run:
   - **PASS** — add a single closing line: `✅ Auto-validated — PASS`. The
     full report already went to `status.md`/`execution_log.md`, exactly as
     it would from a standalone validate run — no need to repeat it here.
   - **FAIL** — surface the validate command's own failure report in full,
     exactly as running validate standalone would show it, so the
     consultant sees what's wrong immediately without running anything
     else themselves.
3. This never blocks or undoes generate itself — the artifact is written
   either way, and its content is never rolled back because validate
   failed. Auto-validation only means validate has already run and its
   result is already on record by the time generate finishes, instead of
   waiting for the consultant to remember to run it separately.

## If `auto_validate` is `false`: state this plainly, don't run it

Do not run validate. End with a line naming why, as specifically as this
spec's own context makes possible (e.g. "runs `dbt run`/`dbt test`",
"queries the live target warehouse", "calls the Looker API directly") —
fall back to "performs live checks against an external system" only if no
more specific reason is evident from context:

```
⚠ This artifact's validate step [reason] and does not run automatically.
Run /wire:<artifact-with-dashes>-validate <release_folder> before
requesting review — review is blocked until it passes.
```

## Why this is always safe either way

`review` already requires `validate: PASS` for this same artifact as one of
its own declared preconditions (see `specs/utils/precondition_gate.md`) —
this is existing, independent enforcement, not something added by this
section. So an `auto_validate: false` opt-out never lets an artifact reach
review unvalidated; it only decides *when* the consultant pays validate's
cost — automatically on every draft (the default), or once, on their own
schedule, before requesting review (the opt-out). Auto-validation is a
convenience that closes the "forgot to run it" gap for the common case; the
gate that actually prevents unvalidated work from being reviewed was already
there.

## Workflow Specification

---
wire_schema: "1.0"
command: generate
artifact: oac_audit
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
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

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
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
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
