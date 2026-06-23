---
description: Translate dbt models batch by batch to target dialect
argument-hint: <release-folder> [--batch N] [--model name]
---

# Translate dbt models batch by batch to target dialect

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
description: Translate dbt models batch by batch to target dialect with inline equivalency validation
argument-hint: <release-folder> [--batch N] [--model name] [--select selector] [--exclude selector]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_migration` and `artifact_file_path: migration/dbt/batch_1_summary.md` before proceeding.
Follow `specs/utils/migration_preflight.md` with `caller: dbt_migration` and `batch_ref` set to the batch/scope about to be translated (Checks 1–3); if any fail, output the blockers and stop before generating. This supersedes the soft Step 0b freshness warning below — the gate's Check 1 is the blocking version.

---

## Data Safety — Read Before Proceeding

Before running any translation, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT run INSERT, UPDATE, DELETE, CREATE TABLE, DROP, or TRUNCATE
  against the source platform. Query it only.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not write to these):
  [list each production project ID]
```

If the current working context or tool calls would write to a source platform or a production project listed in `data_safety.production_projects`, stop immediately and report the conflict before proceeding.

---

# dbt Migration — Generate

## Purpose

Translates dbt models from the source platform dialect to the target platform dialect — both the model `.sql` **and the companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`). Each model goes through an inline translation-and-equivalency loop: translate → compile → run on target → three-check equivalency test → auto-fix on failure → iterate up to 5 times before flagging for manual review. Both the source platform MCP and the target platform MCP are mandatory — this command cannot run without live connections to both.

Works in batches as defined in the dbt audit. Normally the auto-delegation layer handles splitting a batch into parallel groups and spawning one agent per group — this spec executes on whatever scope it is handed. Supports `--batch N` to process a specific batch, `--model <name>` to process a single model, and `--models <name1,name2,...>` to process a specific subset (used by parallel agents within a batch).

## Prerequisites

- `ingestion_migration review: approved`
- `audit/dbt_audit.csv` exists with batch assignments
- Source platform MCP connected and readable
- Target platform MCP connected and writable to the test project

## Flags

- `--batch N` — process batch number N only (all models in that batch, unless `--models` also provided)
- `--models <name1,name2,...>` — process only these named models (comma-separated); used by the parallel-dispatch layer to hand a subset of a batch to each agent
- `--model <name>` — process a single model by name (shorthand for `--models` with one entry)
- `--select <selector>` — resolve the models to translate using dbt node-selection grammar (graph operators `+`, `n+`, `@`; space-separated unions; comma-separated intersections; `tag:`, `config.materialized:`, `path:` set selectors). Resolved by Wire over the source project's dependency graph — **no dbt binary required**. See Step 1a.
- `--exclude <selector>` — companion to `--select`; removes matching models from the resolved set. Same grammar. Optional.
- No flag — process the next incomplete batch (read from status.md `dbt_migration.current_batch`)

`--select`/`--exclude` and `--batch` are different scoping models — abort if both are supplied. Likewise abort if both `--select` and `--model`/`--models` are supplied. A bare name (`--select vehicles`) resolves to that single model, identical to `--model vehicles`. `--exclude` may be supplied without `--select` (it filters whatever scope is otherwise in effect). `--select ""` aborts with: `[wire] --select value is empty. Pass a selector, or omit the flag to use --batch / --model.`

Full grammar and resolution algorithm: `wire/docs/specs/dbt-node-selection.md`.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv`
- `.wire/releases/$ARGUMENTS/status.md` — dbt_migration.current_batch
- Source dbt model SQL files **and their companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`) at `migration.dbt_project_path` (or `migration_sources.dbt.local_snapshot_path` if registered)
- Canonical platform pair files:
  - `wire/platform_pairs/{pair}/translation_guide.md` — pattern table
  - `wire/platform_pairs/{pair}/translation_reference.md` — exhaustive deep reference, if present (snowflake → bigquery has one). Consult it when a model trips a silent-behaviour-change case (timezone defaults, `DATEDIFF` boundary semantics, day-of-week numbering, regex engine, hash-key mismatch, NaN/NULL sort) or uses a construct the pattern table doesn't list. Where it disagrees with the quick guide, it wins.
  - `wire/platform_pairs/{pair}/type_mapping.md` — data-type table
  - `wire/platform_pairs/{pair}/feature_detection.md` — feature patterns the audit uses
  - `wire/platform_pairs/{pair}/examples/` — before/after worked examples used as few-shot context when translating models with matching patterns
  - `wire/platform_pairs/dbt_neutral_translation.md` — shared, direction-agnostic macro-first strategy: where each dialect difference should live (dbt built-in → `dbt_utils` → dispatched macro → `target.type` as a last resort). Apply when deciding how to handle a construct, especially one with no built-in equivalent (array-membership joins, NULL-safe `ARRAY_AGG`). Prefer lifting in-model `target.type` branches up to dispatched macros over reproducing them.
- **Engagement-level overrides (optional)**: `.wire/engagement/platform_pair_overrides/{pair}/`
  - `translation_guide.md` — extra rows or rules that override the canonical guide for this engagement
  - `examples/` — engagement-specific worked examples (e.g. patterns unique to this client's data shapes)
  - Used in addition to (and prioritised over) the canonical files.

## Workflow

### Step 0: Verify MCP connectivity

Both platform connections are mandatory. Check before doing any translation work:

1. **Source platform MCP** — query a known system table or run a trivial SELECT against the source. For Snowflake: `SELECT CURRENT_TIMESTAMP()`. For BigQuery (as source): `SELECT CURRENT_DATE()`. If this fails, abort:
   ```
   [wire] ERROR: Source platform MCP is not connected or not responding.
   Connect the [source_platform] MCP server and retry.
   /mcp — to check connection status
   ```

2. **Target platform MCP** — run a trivial write-safe query against the test project. For BigQuery: `SELECT 1 AS test`. If this fails, abort:
   ```
   [wire] ERROR: Target platform MCP is not connected or not responding.
   Connect the [target_platform] MCP server (test project: [target_project]) and retry.
   ```

Both must be confirmed live before proceeding to Step 0b.

### Step 0b: Check source snapshot freshness

Read `migration_sources.dbt` from status.md (if the block exists):

- If `last_refreshed` is null or the block is absent: warn but continue — the source files will be read from `migration.dbt_project_path` directly.
- If `last_refreshed` is set and is more than 24 hours ago:
  ```
  ⚠️  Source snapshot is [N] hours old (last refreshed: [timestamp]).
  The local snapshot at [local_snapshot_path] may not reflect recent upstream changes.
  Run /wire:migration-source-refresh $ARGUMENTS dbt to update it, then retry.
  Proceeding anyway — use your judgement.
  ```
  Do not block. Continue after the warning.

### Step 1: Determine scope

1. Read `migration.dbt_project_path` (or `migration_sources.dbt.local_snapshot_path` if set) and `migration.source_platform` from status.md.
2. Determine which models to translate:
   - If `--select <selector>` (optionally with `--exclude`) provided: resolve the model set per **Step 1a**.
   - If `--model <name>` provided: process that single model
   - If `--batch N` provided: load all models with `batch_number = N` from `dbt_audit.csv`
   - Otherwise: read `dbt_migration.current_batch` from status.md (default: 1 if not set)
3. Confirm the batch/model has not already been translated (check for existing translated files). If already done, ask whether to re-translate.

### Step 1a: Resolve `--select` (only when `--select`/`--exclude` is used)

Resolve the selector yourself over the source project's dependency graph. **Do not shell
out to dbt** and do not reimplement graph traversal over `dbt_audit.csv` (it stores
`ref_count`/`source_count`, not edges).

1. **Build the graph (no dbt binary):**
   - **Preferred:** read `<migration.dbt_project_path>/target/manifest.json`. For each
     `model` node it gives `name`, `depends_on.nodes` (parent edges), `tags`,
     `config.materialized`, and `path`/`fqn`. It is a plain JSON artifact — reading it
     needs no dbt install and no warehouse connection. A manifest almost always exists
     (the dbt audit was built from this project); if absent, it can be regenerated once
     offline with `dbt parse`.
   - **Fallback (no manifest):** build edges by scanning each model `.sql` for `ref(...)`
     / `source(...)`, and read tags/config from `_models.yml`/`schema.yml`, in-file
     `{{ config(...) }}`, and the folder-level `models:` config in `dbt_project.yml`.
     Graph operators and `tag:` are reliable this way; `config.materialized:` set at the
     `dbt_project.yml` folder level is the one fragile case — when a `config.*` selector
     is used under fallback, mark the result **medium confidence** and have the user
     confirm the printed list.

2. **Resolve the selector** as set algebra over the graph:
   - Split on spaces → union components; split each on commas → intersection atoms.
   - Per atom: strip leading `@`, leading `N+`/`+`, trailing `+N`/`+`; resolve the core
     (bare name, or `tag:` / `config.materialized:` / `path:` / `fqn:` method) to a base
     set; then leading `+`/`N+` adds ancestors (BFS up `depends_on`, optional hop limit),
     trailing `+`/`+N` adds descendants (BFS down inverted edges), `@` adds descendants
     then their ancestors.
   - Intersect atoms within a comma group; union the groups. Subtract the `--exclude`
     set, resolved the same way.

3. **Preview (mandatory).** Print the resolved list and proceed only after it looks right:

   ```
   [wire] Models selected (n):
     - stg_vehicles
     - vehicles
     ...
   [wire] Proceeding to translate n models...
   ```

   If the resolved set is empty, abort: `[wire] No models matched selector "<selector>". Aborting.`

The resolved model list then flows into Step 3 unchanged.

### Step 2: Load translation context

Read the translation guide for the active platform pair. For the models in this batch, identify which feature tags are present and load the corresponding translation patterns.

### Step 3: Translate and validate each model (iterative loop)

For each model in the batch, run an iterative translation-and-equivalency loop. The loop has a maximum of **5 iterations**. No manual review prompts are issued mid-loop — the loop runs to completion automatically for every model before any human interaction.

**Before the loop**, initialise per-model tracking:
```
model_name: <name>
status: not_started
iteration: 0
loop_history: []
```

**Each iteration** (iterations 1 through 5):

#### 3.1 Translate or auto-fix

**Iteration 1 — initial translation:**

1. Read the source SQL from the dbt project (or local snapshot).
2. Record the model's **relative path within the source dbt project** (e.g. `models/staging/stripe/stg_stripe_charges.sql`). This path is mirrored in the output.
3. Apply translations in this order:
   a. Data type references (inline casts, SAFE_CAST equivalents)
   b. SQL function translations (per the translation guide)
   c. Configuration block updates (adapter profile, materialisation config)
   d. Jinja macro calls that need dispatch overrides
4. Assign a confidence rating: `high` = only simple, table-driven replacements. `medium` = engagement-specific nuance. `low` = no clean equivalent or a construct the guide marks "manual".

**Iterations 2–5 — auto-fix:**

Read the failure recorded from the previous iteration. Diagnose the root cause:
- Compilation failure: identify the offending construct and apply a targeted syntax fix.
- Run failure: identify the runtime error (type mismatch, unsupported function, missing reference) and fix the translated SQL.
- Equivalency failure: identify which check failed and what it indicates (row loss, schema drift, value drift), then apply a targeted correction to the model logic or type handling.

Apply the fix to the translated SQL. Record what was changed and why in `loop_history`.

**Translation safeguards** — apply on every iteration:
- **Guard against silent record loss**: never quietly drop or duplicate rows. Watch JOIN semantics, `QUALIFY`/window changes, implicit `DISTINCT`, and NULL-handling in filters.
- **Guard against silent value drift**: do not introduce timezone assumptions, currency conversions, or precision changes not present in the source. If a construct is ambiguous, flag `low` and leave `-- MANUAL REVIEW`.
- **Wide schemas**: translate in sections if needed to avoid truncation. Confirm same column count and CTE structure.

#### 3.2 Write translated SQL

Write the translated SQL to `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path_from_models_root}` — preserving the exact subdirectory structure from the source project. Also write a side-by-side diff to `{same_path_without_extension}.diff.md`.

#### 3.3 Compile check (target BigQuery/Snowflake MCP)

Validate the translated SQL will compile against the target platform without materialising data. Use the target platform MCP to run the compiled SQL with `LIMIT 0` appended (or equivalent). For Jinja-templated models, compile against the target profile's `LIMIT 0` pattern.

If compile fails:
- Record: `{ iteration: N, stage: "compile", error: "<message>", action: "auto-fix" }`
- Update DAG state for this model to `migrated` (orange — in progress)
- Go to next iteration (3.1 auto-fix)

If compile succeeds: proceed to 3.4.

#### 3.4 Run on target

Execute the full model SQL as a materialisation against the test project using the target platform MCP's write tool. For BigQuery: `execute_sql` (not readonly). The target dataset/schema is read from `data_safety.target_project` and `migration.target_schema` in status.md.

Run only against the test project — never against production. If the write tool would target a project listed in `data_safety.production_projects`, stop immediately and report the conflict.

If run fails:
- Record: `{ iteration: N, stage: "run", error: "<message>", action: "auto-fix" }`
- Go to next iteration (3.1 auto-fix)

If run succeeds: proceed to 3.5.

#### 3.5 Three-check equivalency

Run these three checks using both the source platform MCP (read-only) and the target platform MCP (read-only). Do not run any write queries here.

**Check A — Row count** (tolerance ±0.5%):
```sql
-- Source
SELECT COUNT(*) AS row_count FROM {source_db}.{source_schema}.{table_name};
-- Target
SELECT COUNT(*) AS row_count FROM {target_project}.{target_schema}.{table_name};
```
PASS: `|source_count - target_count| / source_count ≤ 0.005`
FAIL: count outside tolerance — record source count, target count, and deviation.

**Check B — Schema**:
Compare column names, data types (per `type_mapping.md`), and nullability between source and target by querying `INFORMATION_SCHEMA.COLUMNS` on both platforms.
PASS: all columns present with expected types (modulo documented type translations).
FAIL: missing columns, extra columns, unexpected type changes, or nullability mismatches — record the specific column differences.

**Check C — Column value sampling** (1000 rows):
For a deterministic 1000-row sample (e.g. `ORDER BY 1 LIMIT 1000` or `TABLESAMPLE`), compare:
- Numeric columns: mean, min, max, null percentage. PASS: all within ±1%.
- String columns: distinct count, null percentage. PASS: distinct count within ±2%, null% within ±1%.

For the sample to be comparable, use the same filter or row-limiting method on both platforms. Document the sampling approach used.
PASS: all column statistics within thresholds.
FAIL: record which columns deviated and by how much.

#### 3.6 Assess iteration result

If checks A, B, and C all PASS:
- `status = PASSED`
- Update DAG state for this model to `complete` (green)
- Exit the loop for this model

If any check fails AND `iteration < 5`:
- Record the failure details in `loop_history`
- Increment `iteration`
- Go to 3.1 (auto-fix)

If any check fails AND `iteration == 5`:
- `status = FAILED`
- Update DAG state for this model to `failed` (red)
- Add `-- MANUAL REVIEW` comment to the translated SQL
- Record the final failure in `loop_history`
- Exit the loop for this model

**No manual review prompts are issued between iterations.** The loop runs automatically for all models in the batch. Flagging for manual review happens only after all 5 iterations are exhausted.

After the loop, record for this model:
```
model_name: <name>
final_status: PASSED | FAILED
iterations_taken: N
loop_history: [{ iteration, stage, result, error, action }]
confidence: high | medium | low
```

### Step 3b: Translate the companion schema / properties YAML

For each model in the batch, also translate its schema/properties YAML. Integrate this into the loop at iteration 1 (initial translation) and carry it through subsequent iterations — YAML schema fixes are part of the same auto-fix process as SQL fixes when schema check B fails.

Three parts to handle:

1. **Column definitions and descriptions** — dialect-neutral; copy across unchanged. Confirm the column list still matches the translated model (a dropped column in either place is a defect).

2. **`sources.yml`** — the source `database`/`schema` must resolve to the target platform's namespace. Prefer parameterising through `vars`. This is real migration work.

3. **Tests** — generic tests (`not_null`, `unique`, `accepted_values`, `relationships`) are portable. Custom tests, `where:` filters, and `dbt_utils`/`dbt_expectations` arguments containing source-dialect SQL get the same translation as model bodies.

4. **PII / column policy tags and `meta`** — if column-level protection is applied through dbt (e.g. BigQuery `policy_tags`), author the `policy_tags` references into the column YAML here. Confirm ownership with the security-migration scope first — do not apply tags in both dbt YAML and warehouse DDL.

Write the translated YAML alongside the model, preserving the same relative path: `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path_from_models_root_without_extension}.yml`. Note any `sources.yml` repoint, custom-test translation, or `policy_tags` in the model's diff file.

### Step 4: Generate batch summary

Write `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`:
- Models translated in this batch
- Translation patterns applied (counts by type)
- Confidence breakdown (count of high / medium / low)
- Per-model loop results: iterations taken, which checks failed, final status
- Models requiring manual review (every `FAILED` model and every `low` confidence model)
- **Companion YAML changes**: `sources.yml` repoints, custom/singular tests translated, `policy_tags` authored or deferred
- Recommended next steps

### Step 4b: Update per-batch DAG

Update the Mermaid batch DAG file at `.wire/releases/$ARGUMENTS/artifacts/migration_strategy/dag_batch_{N}.md` with the final state of each model in this batch. If the file does not exist (e.g. `migration_strategy/generate.md` was not run), create it now with a minimal DAG covering only the models just processed.

DAG state mapping:
```
PASSED     → classDef complete fill:#2a2,color:#fff
FAILED     → classDef failed  fill:#c00,color:#fff
not_started → classDef notStarted fill:#999,color:#fff
in_progress → classDef migrated fill:#f90,color:#000
```

The DAG is a Mermaid flowchart. Each model is a node. Models with upstream `ref()` dependencies are shown downstream of their parents (from the batch scope — cross-batch edges are shown as dashed lines to external nodes). Apply the appropriate `:::class` to each node based on its final status.

Rewrite the full DAG with current states rather than patching individual lines.

### Step 4c: Generate migration acceptance pack (when all batch models are terminal)

If every model in the batch has reached a terminal state (PASSED or FAILED — not still in progress), generate the acceptance pack at `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md`.

Use this template:

```markdown
# Migration Batch {N} — Acceptance Pack

**Generated**: {TODAY}
**Release**: {ARGUMENTS}
**Batch**: {N}
**Models in batch**: {count}
**Status**: {count_passed} passed · {count_failed} failed

## Results Table

| Model | Iterations | Compile | Run | Row Count | Schema | Value Sample | Status |
|-------|-----------|---------|-----|-----------|--------|--------------|--------|
| model_a | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | **PASSED** |
| model_b | 5 | ✅ | ✅ | ❌ | ✅ | ✅ | **FAILED** |

## Confirmation Statements

- All {count} models in batch {N} have been processed through the translation and equivalency loop
- Models marked PASSED have satisfied: row count ±0.5%, schema match, column value sampling ±1%/±2%
- Models marked FAILED exhausted 5 iterations without passing all three equivalency checks
- No writes were made to the source platform ({source_platform}) during this batch
- All translated models are committed to `.wire/releases/{ARGUMENTS}/migration/dbt/`
- [If any FAILED models]: The following models require manual remediation before this batch can be considered complete: {list}

## Batch {N} DAG

[Embed the Mermaid DAG from dag_batch_{N}.md here]

## Sign-off

*Pending review by `/wire:migration-acceptance-pack-review $ARGUMENTS --batch {N}`*

---
*Generated automatically by Wire Framework v3.10.0 · `/wire:dbt-migration-generate {ARGUMENTS}`*
```

Update status.md to record that the acceptance pack was generated:
```yaml
artifacts:
  migration_acceptance_pack:
    batch_{N}_generated: true
    batch_{N}_generated_date: "{{TODAY}}"
    batch_{N}_review: pending
```

### Step 4d: Persist per-model transformation log to BigQuery

Carwow asked for a structured, queryable audit trail of what each model's translation changed — not just console output and `.diff.md` files. This step is **additive**: the diff files (Step 3.2) and batch summary (Step 4) are still written. It persists one structured record per migrated object to a BigQuery audit table.

**Configurable target table.** Read the audit table location from status.md:

```yaml
migration:
  transformation_log_table: null   # e.g. "carwow-migration.wire_audit.dbt_transformation_log"
```

- If `transformation_log_table` is null or absent, **skip this step** with a one-line note (`[wire] No transformation_log_table configured — skipping BigQuery transformation log (diff.md still written).`). Do not block.
- The table must live in the target project, never a source or a `data_safety.production_projects` entry — apply the same write guard as Step 3.4. If it resolves to a blocked project, stop and report.

**Schema** (create with `CREATE TABLE IF NOT EXISTS` on first run, via the target platform MCP write tool):

| Column | Type | Meaning |
|--------|------|---------|
| `logged_at` | TIMESTAMP | When the record was written |
| `release` | STRING | `$ARGUMENTS` |
| `batch` | INT64 | Batch number (null for `--model`/`--select` scope) |
| `object_name` | STRING | Model name |
| `relative_path` | STRING | Path within the source dbt project |
| `source_dialect` | STRING | `migration.source_platform` |
| `target_dialect` | STRING | `migration.target_platform` |
| `dialect_changes` | JSON | Array of `{construct, from, to, category}` — the source→target dialect changes applied (function swaps, type casts, config/macro changes) |
| `manual_review` | BOOL | True if the model is FAILED or `low` confidence |
| `manual_review_reasons` | JSON | Array of strings — which checks failed / why review is flagged |
| `confidence` | STRING | `high` \| `medium` \| `low` |
| `final_status` | STRING | `PASSED` \| `FAILED` |
| `iterations_taken` | INT64 | Loop iterations used |

**Write one row per migrated object** in this batch/scope, derived from the per-model record produced by Step 3.6 and the translations applied in Step 3.1 / Step 3b. Use parameterised `INSERT` (or a staged `MERGE` keyed on `release` + `object_name` + `batch` if re-running, so a re-translation updates rather than duplicates).

Record in the batch summary that the transformation log was written (or skipped, with the reason).

### Step 5: Update status

```yaml
artifacts:
  dbt_migration:
    generate: complete
    generated_date: "{{TODAY}}"
    current_batch: N
    batches_complete: [1, 2, ..., N]
    models_translated: total_count
    models_passed: passed_count
    models_failed: failed_count
    transformation_log_written: true | false   # false when transformation_log_table is unconfigured
    transformation_log_rows: N                  # rows written this run (0 if skipped)
```

If `--model` or `--select` was used, update only the translated models' status. Do not advance `current_batch`.

### Step 6: Output summary

Print a model-by-model results table:
```
[wire] Batch N — Translation + Equivalency Results
┌──────────────────────────────────┬────────┬───────────┬─────────┐
│ Model                            │ Iter.  │ Status    │ Checks  │
├──────────────────────────────────┼────────┼───────────┼─────────┤
│ stg_admin_site__leads            │ 1      │ ✅ PASSED  │ A B C   │
│ stg_admin_site__dealers          │ 3      │ ✅ PASSED  │ A B C   │
│ stg_admin_site__products         │ 5      │ ❌ FAILED  │ A ✗ C   │
└──────────────────────────────────┴────────┴───────────┴─────────┘
N passed · M failed · acceptance pack generated (batch {N})
```

Then:
```
Review and sign off the acceptance pack:
/wire:migration-acceptance-pack-review $ARGUMENTS --batch N
```

If all batches are complete:
```
All N batches translated.
/wire:orchestration-migration-generate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.sql` — subdirectory structure mirrors the source dbt project
- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.yml` — companion schema/properties YAML
- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.diff.md` — covers `.sql` and `.yml` changes
- `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`
- `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md` — generated when all batch models reach terminal state
- BigQuery table `migration.transformation_log_table` (when configured) — one structured row per migrated object; not a file
- `.wire/releases/$ARGUMENTS/artifacts/migration_strategy/dag_batch_{N}.md` — updated Mermaid DAG with current model states
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact_id, `dbt Migration` as artifact_name, and the `file` value from `artifacts.dbt_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `generate` as action.

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
