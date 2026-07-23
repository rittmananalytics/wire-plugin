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
argument-hint: <release-folder> [--batch N] [--wave id] [--model name] [--select selector] [--exclude selector] [--macros] [--snapshots [names]] [--no-chain] [--config path] [--tag-map path] [--target-dataset name] [--dbt-project-path path]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_migration` and `artifact_file_path: migration/dbt/batch_1_summary.md` before proceeding.
Follow `specs/utils/migration_preflight.md` with `caller: dbt_migration` and `batch_ref` set to the batch/scope about to be translated (Checks 1–3); if any fail, output the blockers and stop before generating. This supersedes the soft Step 0b freshness warning below — the gate's Check 1 is the blocking version.
When the target platform is BigQuery, route every BigQuery MCP call in Steps 0, 3.3, and 3.4 through `specs/utils/bigquery_mcp_fallback.md` — see that utility for the compile-check/run/equivalency-query mapping to the `bq` CLI on an MCP connection failure.

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

Works in batches as defined in the dbt audit, or in waves as defined by the authoritative execution schedule (`migration_batching.csv`). Normally the auto-delegation layer handles splitting a batch or wave into parallel groups and spawning one agent per group — this spec executes on whatever scope it is handed. Supports `--batch N` to process a specific (topological) dbt-audit batch, `--wave <id>` to process a specific (execution-schedule) wave, `--model <name>` to process a single model, and `--models <name1,name2,...>` to process a specific subset (used by parallel agents within a batch or wave).

## Prerequisites

- `ingestion_migration review: approved`
- `audit/dbt_audit.csv` exists with batch assignments
- `migration/migration_batching.csv` exists — required only when running with `--wave`
- Source platform MCP connected and readable
- Target platform MCP connected and writable to the test project

## Flags

- `--batch N` — process batch number N only (all models in that batch, unless `--models` also provided). Reads `dbt_audit.csv`'s `batch_number` — the topological, ~20-model translation grouping. Finer-grained than a wave; use it for a topological-only run or to re-run a slice inside a wave.
- `--wave <id>` — **the intended execution unit for a normal run.** Resolves the model scope from `migration/migration_batching.csv`'s `batch_id` — the authoritative, client-facing execution schedule (`migration_batching-generate`'s output; e.g. "Wave 1" spans however many `dbt_audit.batch_number` micro-batches it happens to cross). Accepts either the zero-padded form (`--wave B01`) or a bare number (`--wave 1`); both normalise to the same wave. See Step 1w. `--wave` and `--batch` read two different numbering schemes and must not be combined — see below.
- `--models <name1,name2,...>` — process only these named models (comma-separated); used by the parallel-dispatch layer to hand a subset of a batch to each agent
- `--model <name>` — process a single model by name (shorthand for `--models` with one entry)
- `--select <selector>` — resolve the models to translate using dbt node-selection grammar (graph operators `+`, `n+`, `@`; space-separated unions; comma-separated intersections; `tag:`, `config.materialized:`, `path:` set selectors). Resolved by Wire over the source project's dependency graph — **no dbt binary required**. See Step 1a.
- `--exclude <selector>` — companion to `--select`; removes matching models from the resolved set. Same grammar. Optional.
- `--macros` — **batch-zero macro pass.** Translate the shared Jinja / dispatched *macro definition* files listed in `audit/batch_zero_plan.json`, in tier order, instead of the model graph. This is the pass that must land before model batch 1: a widely-used macro is expanded by models scattered across every batch, so it is rewritten once, up front, and every downstream model then compiles against the already-translated macro. See **Macro Mode Workflow** below. UDF-layer entries (`layer: udf`) are **not** in scope here — they are `CREATE FUNCTION` DDL deployed by `/wire:target-setup-generate`.
- `--snapshots` — **targeted snapshot scope.** `--snapshots` (bare) processes every snapshot object-type node in the release (`object_type = snapshot` in the migration register / `audit/dbt_snapshots.csv`); `--snapshots name1,name2` processes only the named snapshots. Selection resolves against the snapshot object-type rows, never the model selector. When this is the scope, run **only Step 3s** (translate the inner SELECT + adopt-and-continue) over the selected snapshots and skip the model translation loop (Steps 2–3.x model path). This is the retrofit lever — migrate (or re-migrate) snapshots without re-running already-migrated models. Normal `--wave`/`--batch` runs still process any in-scope snapshot inline via Step 3s (as the object-type work already wires); `--snapshots` is an additional targeted scope, not the only path. See **Snapshot Mode Workflow** below.
- `--config <path>` — load a per-run config overlay file; see **Config overlay** below. Orthogonal to scope — combine freely with `--batch`, `--wave`, `--model`/`--models`, `--select`/`--exclude`, or `--macros`.
- `--tag-map <path>` — shorthand for a `--config` overlay that sets only `migration.pii_tag_map_path`. Equivalent to `--config` with a one-key overlay file; use this when the *only* thing an isolated run needs to override is the PII tag map, without writing a throwaway YAML file first.
- `--target-dataset <name>` — shorthand for a `--config` overlay that sets only `migration.target_schema`. Use for a one-off run against a scratch/test dataset without touching the release's real target schema.
- `--dbt-project-path <path>` — shorthand for a `--config` overlay that sets only `migration.dbt_project_path`. Use to point a single run at a different project root (e.g. a scratch checkout) without a full overlay file.
- `--no-chain` — **opt out of the downstream-gate chain.** By default a model-path run chains `dbt-migration-validate` → `dbt-migration-lint` → `dbt-migration-fix` → `dbt-migration-pre-pr-review` after the batch loop (Step 7), so a run leaves the gates already applied rather than stopping at "recommended next steps". `--no-chain` stops after Step 6 with the next-command hint only — for when the consultant wants to inspect the batch before gating, or is driving the gates manually. The chain is model-path only: `--macros` and `--snapshots` never chain regardless of this flag (see Step 7).
- No flag — process the next incomplete batch (read from status.md `dbt_migration.current_batch`)

**Discrete overlay flags vs. `--config`**: `--tag-map`/`--target-dataset`/`--dbt-project-path` are convenience aliases — each is exactly equivalent to `--config` pointed at a one-key overlay file setting that single field, read at Step 0c the same way, in memory for this invocation only, never written back to status.md. They compose freely with each other and with `--config` itself (later flags on the command line win on a per-key basis if the same key is set more than once — e.g. `--config base.yml --target-dataset scratch_v2` uses every key from `base.yml` except `target_schema`, which `--target-dataset` overrides). Use the discrete flags for a single-field override where writing a whole overlay file would be overkill; use `--config` when overriding several fields at once (e.g. `dbt_project_path` and `target_schema` and `pii_tag_map_path` together for a full scratch-project run).

`--select`/`--exclude` is a different scoping model from `--batch`, `--wave`, and `--model`/`--models` — abort if `--select` is supplied alongside any of `--batch`, `--wave`, `--model`, or `--models`. `--batch` and `--wave` are themselves mutually exclusive with each other (two different numbering schemes over the same models — see below), but each independently composes with `--model`/`--models` exactly as `--batch` always has: `--model`/`--models` narrows the batch or wave down to a named subset (this is what the parallel-dispatch layer uses to hand each agent its slice of a batch **or** a wave), it does not replace it. `--model`/`--models` supplied with neither `--batch` nor `--wave` still works as its own scope (a single model or named subset, independent of any batch/wave), unchanged from today.

A bare name (`--select vehicles`) resolves to that single model, identical to `--model vehicles`. `--exclude` may be supplied without `--select` (it filters whatever scope is otherwise in effect). `--select ""` aborts with: `[wire] --select value is empty. Pass a selector, or omit the flag to use --batch / --wave / --model.` Passing both `--wave` and `--batch` aborts with: `[wire] --wave and --batch read different numbering schemes (migration_batching.csv vs dbt_audit.batch_number) and cannot be combined. Pick one.`

`--macros` is its own scope mode — abort if it is combined with `--batch`, `--wave`, `--model`, `--models`, `--select`, `--exclude`, or `--snapshots`: `[wire] --macros is a standalone scope. Run it on its own; do not combine with --batch/--wave/--model/--models/--select/--exclude/--snapshots.` Do **not** overload `--batch 0` for this — audit batches run 1–N, and `--macros` reads unambiguously.

`--snapshots` is likewise a standalone scope — abort if it is combined with `--batch`, `--wave`, `--model`, `--models`, `--select`, `--exclude`, or `--macros`: `[wire] --snapshots is a standalone scope. Run it on its own; do not combine with --batch/--wave/--model/--models/--select/--exclude/--macros.` It composes only with the orthogonal overlay flags (`--config`/`--tag-map`/`--target-dataset`/`--dbt-project-path`), exactly as `--macros` does.

Full grammar and resolution algorithm: `wire/docs/specs/dbt-node-selection.md`.

### Config overlay (`--config`, `--tag-map`, `--target-dataset`, `--dbt-project-path`)

By default every per-run field this spec reads from status.md (`migration.dbt_project_path`, `migration.pii_tag_map_path`, `migration.target_schema`, `migration.source_platform`, `migration.target_platform`, `migration.materialization_overrides_path`, `migration.transformation_log_table`, `data_safety.target_project`, and any other status.md-sourced field referenced below) comes from the release's `status.md`. That forces an isolated or one-off run (e.g. validating against a different schema, or a scratch project without a status.md yet fully wired up) to hand-edit status.md first.

`--config <path>` points at a small YAML or JSON file that overrides these fields **for this invocation only** — it is read at Step 0c, held in memory, and never written back to status.md. Where the overlay sets a key, it wins over status.md for the duration of this run; where it doesn't set a key, status.md's value applies as normal. The overlay's shape mirrors the status.md field names it overrides, e.g.:

```yaml
migration:
  dbt_project_path: ".wire/scratch/acme-source-layer"
  target_schema: "wire_migration_test"
  pii_tag_map_path: ".wire/releases/acme-migration/migration/tag_map_v2.json"
data_safety:
  target_project: "acme-migration-test-2"
```

`--tag-map <path>`, `--target-dataset <name>`, and `--dbt-project-path <path>` are discrete, single-field shorthands for the three overlay keys used most often in practice — `migration.pii_tag_map_path`, `migration.target_schema`, and `migration.dbt_project_path` respectively. Each is read and applied at Step 0c exactly like a one-key `--config` overlay: in memory for this invocation only, never written back to status.md. If both a discrete flag and a `--config` overlay set the same key, the discrete flag wins (it's the more specific, later-considered override) — every other key from the `--config` overlay still applies normally.

**`data_safety.production_projects` is never overridable** — that blocklist always comes from status.md, so no overlay (whether `--config` or a discrete flag) can ever be used to route a write around the production-write guard in Step 0 / Step 3.4. If the `--config` overlay declares a `data_safety.production_projects` key, ignore it and print a one-line warning; the guard still reads status.md's list. (There is no discrete-flag equivalent for this key — it is deliberately only reachable, if at all, through `--config`, and even there it's ignored.)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv`
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — consumed only by `--wave` mode (see Step 1w); the authoritative execution-schedule scoping
- `.wire/releases/$ARGUMENTS/audit/batch_zero_plan.json` — consumed only by `--macros` mode (the `layer: macro`, `action: translate` entries, tiered)
- `.wire/releases/$ARGUMENTS/status.md` — dbt_migration.current_batch
- **`--config <path>` overlay (optional)**: a YAML/JSON file overriding status.md-sourced per-run fields for this invocation only — see **Config overlay** above
- **`--tag-map <path>` / `--target-dataset <name>` / `--dbt-project-path <path>` (optional)**: discrete single-field overlay shorthands for `migration.pii_tag_map_path` / `migration.target_schema` / `migration.dbt_project_path` respectively — see **Config overlay** above
- Source dbt model SQL files **and their companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`) at `migration.dbt_project_path` (or `migration_sources.dbt.local_snapshot_path` if registered)
- PII tag map (optional): the file at `migration.pii_tag_map_path` in status.md, defaulting to `.wire/releases/$ARGUMENTS/migration/tag_map.json` — a flat `{source_masking_policy_name: target_policy_tag_resource_path}` JSON map, loaded in Step 2 and consumed in Step 3b item 4
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

1. **Source platform MCP** — query a known system table or run a trivial SELECT against the source. For Snowflake: `SELECT CURRENT_TIMESTAMP()`. For BigQuery (as source): `SELECT CURRENT_DATE()`. If the source platform is BigQuery and this probe fails, follow `specs/utils/bigquery_mcp_fallback.md` (`operation: read`) before treating it as a hard failure — only abort if the `bq` CLI fallback also fails:
   ```
   [wire] ERROR: Source platform MCP is not connected or not responding, and the bq CLI fallback also failed.
   Connect the [source_platform] MCP server and retry.
   /mcp — to check connection status
   ```
   For a Snowflake source (no CLI fallback defined here), this remains a hard abort on probe failure, unchanged.

2. **Target platform MCP** — run a trivial write-safe query against the test project. For BigQuery: `SELECT 1 AS test`. If the target platform is BigQuery and this probe fails, follow `specs/utils/bigquery_mcp_fallback.md` (`operation: write`) before treating it as a hard failure — only abort if the `bq` CLI fallback also fails:
   ```
   [wire] ERROR: Target platform MCP is not connected or not responding, and the bq CLI fallback also failed.
   Connect the [target_platform] MCP server (test project: [target_project]) and retry.
   ```
   For a Snowflake target, this remains a hard abort on probe failure, unchanged.

Both must be confirmed live (via MCP or the `bq` CLI fallback) before proceeding to Step 0b.

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

### Step 0c: Load per-run config overlay (`--config`, `--tag-map`, `--target-dataset`, `--dbt-project-path`)

If `--config <path>` was supplied: read and parse the file (YAML or JSON by extension/content-sniff). If it does not exist or fails to parse, abort: `[wire] --config file <path> not found or invalid. Aborting.` Hold the parsed overlay in memory as the override layer for this invocation — every subsequent step that reads a status.md field checks the overlay first, then falls back to status.md. Never write the overlay's values back to status.md. Drop (with a warning) any `data_safety.production_projects` key the overlay declares, per **Config overlay** above.

If `--tag-map <path>` was supplied: set `migration.pii_tag_map_path` in the in-memory overlay to `<path>`, overwriting whatever `--config` set for that key (if any).

If `--target-dataset <name>` was supplied: set `migration.target_schema` in the in-memory overlay to `<name>`, overwriting whatever `--config` set for that key (if any).

If `--dbt-project-path <path>` was supplied: set `migration.dbt_project_path` in the in-memory overlay to `<path>`, overwriting whatever `--config` set for that key (if any).

If none of `--config`/`--tag-map`/`--target-dataset`/`--dbt-project-path` were supplied, skip this step; every field resolves from status.md exactly as today.

### Step 0d: Deployment warehouse type pre-flight

Before the per-model loop, establish the **deployment** warehouse's column types so the loop's Check B (Step 3.5) validates against them, not against a scratch/sample/playground validation warehouse whose types differ. Run `specs/utils/deployment_type_preflight.md` for the in-scope models: it reads the deployment warehouse's actual column types (from `migration.deployment_project` in status.md if set, else the prod-like target in `profiles.yml` — never the validation warehouse), loads the pair's **"Deployment type-divergence patterns"** section, and returns per-model divergence findings plus an explicit warning when the validation warehouse and the deployment warehouse differ.

Hold the returned deployment types and findings in memory for the loop. When the validation and deployment warehouses are the same warehouse, this is a no-op beyond recording "no type-drift risk". Skip only if no target/deployment warehouse is reachable at all — in which case Step 3.5 Check B runs against whatever it can and the batch summary records that the deployment type pre-flight could not run (a coverage gap, not a silent pass).

### Step 1: Determine scope

1. Resolve the dbt project(s): read `migration.dbt_project_path` (or `migration_sources.dbt.local_snapshot_path` if set) and `migration.source_platform` from status.md, honouring the `--config` overlay from Step 0c. Then resolve the actual project(s) and their manifest(s) via `specs/utils/dbt_manifest_parse.md` Steps 1–2 — its nested/multi-project resolution (a single project at the path, or one-level-down subdirectories each with their own `dbt_project.yml`) and hard-fail-on-unresolvable-path behaviour, rather than assuming a single project sits directly at `dbt_project_path`. This matters for a monorepo with more than one dbt project (e.g. a `source_layer` project and an `acme` project, neither at the parent path) — resolving the wrong single project silently mis-scopes everything downstream. Wherever this spec below reads a manifest node for a given model or macro, locate it by its **project-qualified node ID** (`model.<package_name>.<model_name>`) in whichever resolved project's manifest contains it, per the utility's Step 3 — never assume all models live in one manifest.
2. Determine which models to translate:
   - If `--macros` provided: this is not a model scope. Skip Steps 2–6 entirely and run the **Macro Mode Workflow** below instead.
   - If `--snapshots` provided: this is not a model scope. Skip the model translation loop (Steps 2–3.x model path) entirely and run the **Snapshot Mode Workflow** below instead.
   - If `--select <selector>` (optionally with `--exclude`) provided: resolve the model set per **Step 1a**.
   - If `--model <name>` provided: process that single model
   - If `--wave <id>` provided: resolve the model set per **Step 1w** (every dbt-model row in that wave, unless `--models` also provided to narrow further)
   - If `--batch N` provided: load all models with `batch_number = N` from `dbt_audit.csv` (unless `--models` also provided to narrow further)
   - Otherwise: read `dbt_migration.current_batch` from status.md (default: 1 if not set)
3. Confirm the batch/model has not already been translated (check for existing translated files). If already done, ask whether to re-translate.
4. **Snapshots in scope.** Any snapshot whose `batch_number` (from `audit/dbt_snapshots.csv`) falls in this batch — or any snapshot row in this wave's `migration_batching.csv` slice — is part of the scope and is handled by **Step 3s**, not the model loop. Because the audit placed each snapshot after its upstream ref and before its dependents (dbt-audit Step 7), a snapshot is translated and continued before the downstream models that read it.

### Step 1a: Resolve `--select` (only when `--select`/`--exclude` is used)

Resolve the selector yourself over the source project's dependency graph. **Do not shell
out to dbt** and do not reimplement graph traversal over `dbt_audit.csv` (it stores
`ref_count`/`source_count`, not edges).

1. **Build the graph (no dbt binary):**
   - **Preferred:** use the manifest(s) already resolved in Step 1 via `specs/utils/dbt_manifest_parse.md` (nested/multi-project aware — do not assume a single manifest sits directly at `<migration.dbt_project_path>/target/manifest.json`). For each `model` node, across every resolved project's manifest, take `name`, `depends_on.nodes` (parent edges), `tags`, `config.materialized`, and `path`/`fqn`, keyed by the project-qualified node ID (`model.<package_name>.<model_name>`) so same-named models in different nested projects are never merged. It is plain JSON — reading it needs no dbt install and no warehouse connection beyond what Step 1's resolution already did.
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

### Step 1w: Resolve `--wave` (only when `--wave`/`--wave <id>` is used)

`--wave` reads the authoritative execution schedule (`migration_batching.csv`) rather than the topological micro-batch numbering in `dbt_audit.csv`. It never touches, reinterprets, or repurposes `dbt_audit.batch_number` — that field stays a pure topological-ordering value, unchanged by this flag, because `dbt-audit-validate`'s Check 4 ("batch ordering respects dependency graph") and `migration_batching`'s batch-zero macro-dependency-per-batch logic both depend on it staying exactly that.

1. **Normalise the wave id.** Accept either form:
   - Zero-padded (`B01`, `b01`, `B1`) — uppercase the `B`, extract the digits, left-pad to two digits.
   - Bare number (`1`, `01`) — left-pad to two digits and prefix `B`.

   Both normalise to the same `batch_id` value (e.g. `--wave B01` and `--wave 1` both resolve to `B01`). If the argument matches neither shape, abort: `[wire] --wave value "<value>" is not a recognised wave id. Use a form like --wave B01 or --wave 1.`

2. **Load `migration/migration_batching.csv`.** If it does not exist, abort: `[wire] No migration_batching.csv found — run /wire:migration-batching-generate $ARGUMENTS first.`

3. **Filter to this wave's dbt-model rows.** Select rows where `batch_id` equals the normalised wave id **and** `object_type` indicates a dbt model (`dbt_model`, per `migration_inventory-generate`'s node-type vocabulary). Rows for other object types (ingestion connectors, warehouse objects, reverse-ETL syncs, etc.) in the same wave are out of scope for this command — they belong to their own migration commands. If no rows match the wave id at all (any object type), abort: `[wire] No rows found for wave <id> in migration_batching.csv. Check the wave id against the batch_id column.` If rows match the wave but none are `dbt_model` rows, print `[wire] Wave <id> has no dbt model objects — nothing to translate for this command.` and stop cleanly (not an error).

4. **Cross-reference `dbt_audit.csv`.** Each matched row's `object_id` is a model name — look it up by `model_name` in `dbt_audit.csv` to pull the actual per-model detail this command needs (`file_path`, `layer`, `complexity`, `batch_number`, `enabled`, `platform_macros`, etc.). A wave's ~172 models can scatter across dozens of `dbt_audit.batch_number` micro-batches; that's expected — the wave is the execution unit, the audit batch number is just carried along as per-model metadata. If a wave's `object_id` has no matching row in `dbt_audit.csv`, list it as unresolved rather than silently skipping it: `[wire] Wave <id>: object_id "<name>" has no matching row in dbt_audit.csv — check the two artifacts are in sync (re-run /wire:dbt-audit-generate or /wire:migration-batching-generate).`

5. **Preview (mandatory)**, same posture as Step 1a:

   ```
   [wire] Wave B01 — 172 models resolved (audit batches: B01 spans dbt_audit batch_number 1–32):
     - stg_admin_site__leads
     - stg_admin_site__dealers
     ...
   [wire] Proceeding to translate 172 models...
   ```

   If the resolved set is empty after cross-referencing (all unresolved), abort per item 4.

The resolved model list then flows into Step 3 unchanged, exactly like a `--select` or `--batch` resolution. Where Steps 4–6 below label output artifacts and status fields with the batch number `N` (e.g. `batch_{N}_summary.md`, `dag_batch_{N}.md`), substitute the wave id (e.g. `batch_B01_summary.md`, `dag_batch_B01.md`) when the scope is `--wave`. Step 5's status update records the wave under `wave` / `waves_complete` (see Step 5) in addition to the model-level counts, and — like `--model`/`--select` — a `--wave` run never advances `dbt_migration.current_batch`, since that field belongs to the `dbt_audit.batch_number` scheme, not the wave schedule.

## Macro Mode Workflow (`--macros`)

Runs **instead of** Steps 2–6 when `--macros` is supplied. Steps 0 (MCP connectivity), 0b (snapshot freshness), and the data-safety reminder still apply — the source MCP is needed to read macro bodies and the target MCP to compile-check. There is **no row-equivalency loop** here: macros are definitions, not tables. A macro is "correct" when the models that expand it compile on the target — that verification happens in the model batches, not here.

### Step M1: Load the batch-zero plan

Read `.wire/releases/$ARGUMENTS/audit/batch_zero_plan.json`. If it is missing, abort: `[wire] No batch_zero_plan.json found — run /wire:dbt-audit-generate $ARGUMENTS first.`

Select the entries to translate: every macro with `action: "translate"` **and** `layer: "macro"`. Exclude:
- `layer: "udf"` entries — these are `CREATE FUNCTION` DDL owned by `/wire:target-setup-generate`; print a one-line note stating how many UDF-layer entries were skipped and that they deploy via target-setup.
- `action: "redesign"` and `action: "manual-review-out-of-scope"` entries — list them so the consultant knows they are handled outside this pass (redesign at the target-setup review gate; manual-review out of scope).

Order the selected macros by `tier` ascending (tier 0 first, then tier 1, …). Within a tier, order is free. If the selected set is empty, print `[wire] No macro-layer entries need translation — nothing to do.` and stop cleanly.

### Step M2: Load translation context

Same as Step 2: read the platform-pair `translation_guide.md`, `translation_reference.md` (authoritative on conflict), and `dbt_neutral_translation.md`. Apply the **macro-first strategy** from `dbt_neutral_translation.md` — where each dialect difference should live (dbt built-in → `dbt_utils` → dispatched macro → `target.type` as a last resort). Prefer lifting in-macro `target.type` branches up to clean dispatched macros over reproducing per-dialect switches. Load any engagement-level overrides at `.wire/engagement/platform_pair_overrides/{pair}/`. The PII tag map does not apply to macros.

### Step M3: Translate each macro (tier order, compile-only)

For each macro, in tier order:

1. Read the macro definition file from the `macros/` tree of whichever resolved project (per Step 1's `dbt_manifest_parse.md`-based resolution) owns it — do not assume a single `macros/` tree directly under `migration.dbt_project_path`; a monorepo with nested projects has one `macros/` tree per project. Record its **relative path within its source project** (e.g. `macros/cross_dialect/globalize_id.sql`) — mirrored in the output.
2. Translate the macro body applying the same treatments as a model (function swaps, type handling, dispatch/adapter updates, Jinja macro calls). A tier-N macro may call already-translated tier-`<N` macros — reference the translated version, never re-translate a dependency inline.
3. Assign a confidence rating (`high` / `medium` / `low`) on the same basis as models.
4. **Compile check** against the target MCP: compile a trivial probe that expands the macro (e.g. a `SELECT` wrapping the macro call with representative literal args, run with `LIMIT 0` / dry-run) so the translated definition is exercised without materialising data. Never run a write query. If compile fails, auto-fix (same diagnosis-and-fix loop as models, **max 5 iterations**), then re-check. Some macros cannot be exercised standalone (they assume a `ref`/relation context) — if a macro is not independently compile-checkable, record `compile: deferred` with the reason and rely on the model-batch compile to validate it; do not count this as a failure.
5. Apply the **translation safeguards** (guard against silent record loss and value drift) exactly as for models.

Write the translated macro to `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}` preserving the subdirectory structure, and a side-by-side diff to `{same_path_without_extension}.diff.md`.

Macros are not models: do **not** write a `migration_register.csv` row and do **not** run the three-check equivalency (Step 3.5). The register tracks per-model source-commit provenance; macros are validated transitively.

### Step M4: Write the macro-pass summary

Write `.wire/releases/$ARGUMENTS/migration/dbt/batch_zero_macros_summary.md`:
- Macros translated, grouped by tier, with per-macro confidence and compile result (passed / deferred / failed)
- Translation patterns applied (counts by type)
- Any macro that exhausted 5 iterations without compiling — flagged `-- MANUAL REVIEW`
- UDF-layer entries skipped (count) with the pointer to `/wire:target-setup-generate`
- `redesign` / `manual-review-out-of-scope` entries listed as out of scope for this pass

### Step M5: Update status and output

```yaml
artifacts:
  dbt_migration:
    macros_translated: true
    macros_translated_date: "{{TODAY}}"
    macros_translated_count: N        # layer:macro, action:translate entries written
    macros_deferred_count: N          # compile deferred to model-batch validation
    macros_failed_count: N            # exhausted 5 iterations
```

Do **not** touch `current_batch` or the model counts — the macro pass is orthogonal to model batches. Print a tier-ordered summary table and the next command:

```
Batch-zero macro pass complete. Deploy the UDF layer, then translate model batch 1:
/wire:target-setup-generate $ARGUMENTS      # deploys the layer:udf CREATE FUNCTION objects
/wire:dbt-migration-generate $ARGUMENTS --batch 1
```

## Snapshot Mode Workflow (`--snapshots`)

Runs **instead of** the model translation loop (Steps 2–3.x model path, Steps 4–6's model-labelled output) when `--snapshots` is supplied. Steps 0 (MCP connectivity), 0b (snapshot freshness), 0c (config overlay), 0d (deployment type pre-flight), and the data-safety reminder still apply — the source MCP reads snapshot bodies, the target MCP compile-checks and adopt-and-continues. This is the retrofit lever: migrate the release's snapshots on their own, without re-running already-migrated models. A snapshot's pass criterion is still the three-layer gate in `dbt-migration-validate` / `equivalency-validate` (Check 9), not a SELECT row-equivalence.

### Step S1: Resolve the snapshot scope

Resolve the selected snapshots against the **snapshot object-type nodes** only — the `object_type = snapshot` rows in `migration/migration_register.csv`, cross-referenced to `audit/dbt_snapshots.csv` for each snapshot's strategy, `target_schema`, and meta-column set. **Never** resolve against `dbt_audit.csv`'s model rows or the model selector — a name that matches a model but not a snapshot node is not in scope.

- `--snapshots` (bare): select every `object_type = snapshot` node in the release.
- `--snapshots name1,name2`: select only the named snapshots. A name that does not resolve to a snapshot node (unknown, or the name of a model rather than a snapshot) is listed as unresolved rather than silently skipped: `[wire] --snapshots: "<name>" is not a snapshot object-type node — check audit/dbt_snapshots.csv.`

If the register / `dbt_snapshots.csv` does not exist, abort: `[wire] No dbt_snapshots.csv found — run /wire:dbt-audit-generate $ARGUMENTS first.` If the resolved set is empty (no snapshot nodes, or none of the named entries resolve), abort: `[wire] No snapshots matched --snapshots. Aborting.`

**Preview (mandatory)**, same posture as Step 1a:

```
[wire] Snapshots selected (n):
  - snap_customers
  - snap_orders
[wire] Proceeding to translate n snapshots...
```

### Step S2: Load translation context

Read the pair's `translation_guide.md`, `translation_reference.md` (authoritative on conflict), and its **"Snapshot SCD mechanisms"** section, plus any engagement-level overrides at `.wire/engagement/platform_pair_overrides/{pair}/`. Load the PII tag map per Step 2 (its companion-YAML handling in Step 3s still applies).

### Step S3: Translate and continue each selected snapshot

For each snapshot in the resolved set, run **Step 3s** (translate the inner SELECT, keep the hash-input config byte-identical, confirm the `dbt_scd_id` inputs stringify identically, adopt-and-continue after the history copy, test gate) exactly as it runs inside a normal batch, and upsert its register row per Step 3.7 with `object_type = snapshot`. The per-snapshot inner-SELECT correctness still runs the three-check equivalency (Step 3.5) as in Step 3s; the snapshot itself passes only at the Check 9 gate.

### Step S4: Snapshot summary and status

Write `.wire/releases/$ARGUMENTS/migration/dbt/snapshots_summary.md` — a snapshot-labelled batch summary carrying the **Snapshots** section from Step 4 (each snapshot translated, its `snapshot_strategy`, confirmation the hash-input config is unchanged, whether the `dbt_scd_id` inputs stringify identically, and whether the target adopt-and-continue `dbt snapshot` run was ordered after the history copy) plus any `-- MANUAL REVIEW` flags. Do **not** touch `current_batch` or the model counts — the snapshot pass is orthogonal to model batches, exactly like the macro pass. Update status:

```yaml
artifacts:
  dbt_migration:
    snapshots_translated: true
    snapshots_translated_date: "{{TODAY}}"
    snapshots_translated_count: N     # object_type=snapshot nodes translated this run
    snapshots_failed_count: N         # flagged -- MANUAL REVIEW
```

Then print the next command:

```
Snapshot pass complete. Validate the snapshot three-layer gate:
/wire:dbt-migration-validate $ARGUMENTS --snapshots
```

### Step 2: Load translation context

Read the translation guide for the active platform pair. For the models in this batch, identify which feature tags are present and load the corresponding translation patterns.

**PII tag map.** Read `migration.pii_tag_map_path` from status.md (or the `--config` overlay's `migration.pii_tag_map_path`, if loaded in Step 0c and it sets that key). If unset, look for the default `.wire/releases/$ARGUMENTS/migration/tag_map.json`. The file is a flat JSON map of source masking-policy name → target policy-tag resource path, e.g. `{"pii_email": "projects/<project>/locations/<loc>/taxonomies/<id>/policyTags/<id>"}` — it comes from the same PII policy-tag taxonomy the target-setup security step stands up (`04_security.sql`), so do not invent tag paths here. On load, build a lookup keyed on the **normalised** policy name: lowercase and trim both the map keys and, later, every source `meta.masking_policy` value before comparing — masking-policy names are inconsistently cased in the wild, and an exact-match lookup silently misses `PII_EMAIL` against a `pii_email` key. If no file exists at either location, print `[wire] No PII tag map found — policy_tags will be authored manually per column (Step 3b item 4).` and continue. The map is an enhancement, not a prerequisite — never block on its absence.

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
   a. **Source-to-ref resolution.** For each `source('<source_name>', '<table>')` call in the model body, check whether `<source_name>.<table>` is the output relation of a model that has **already been translated earlier in this migration** — cross-reference `migration/migration_register.csv` (the per-model state store maintained by this command per Step 3.7; see `migration-register-generate`), matching `<source_name>.<table>` against each row's `bq_target` where `state = migrated`. On a match, rewrite the call to `ref('<model>')` using that row's `model` column, instead of emitting a fresh `source(...)` call — leaving it as `source(...)` regresses to reading a Bronze/source table that a hand-done or later translation has already replaced with a warehouse model. Record the substitution (`source(...)` → `ref(...)`, and which register row matched) in `loop_history` and the model's `.diff.md`. If `migration_register.csv` doesn't exist yet (no models translated yet this migration), there is nothing to match against — proceed with `source(...)` calls untouched; this is not a failure. This check runs before Step 3b's `sources.yml` repointing, which handles whatever `source(...)` calls remain genuine external sources after this substitution.
   b. **Bronze-schema existence check.** Before finalising the translated SQL, for every column still referenced via a `source(...)` call after item a (a `ref()` reads a sibling model's own reconciled output, so this check applies to genuine source references only): confirm the column exists in the source/Bronze relation for **every** market/region in scope. Read the in-scope markets from `migration.target_markets` in status.md (or the `--config` overlay's equivalent key) — a list of market/region identifiers, each mapping to its own Bronze schema/dataset instance. Use the target platform MCP's read-only schema introspection (`INFORMATION_SCHEMA.COLUMNS`, the same mechanism Step 3.5 Check B uses for schema comparison), queried once per market against the Bronze relation. For a column absent in one or more markets: do not leave the raw column reference — it will error the build the moment it runs against a market lacking the column. Instead emit `CAST(NULL AS <type>)` in its place, inferring `<type>` from the source's own schema in whichever market(s) do have the column, and add an inline SQL comment flagging the substitution and the affected market(s), e.g. `CAST(NULL AS STRING) /* -- MARKET GAP: authentication_token not present in DE, FR — synthesized NULL, see batch summary */`. Record every substitution in `loop_history` and the model's `.diff.md`, and carry it into the batch summary (Step 4) so it is never a silent drop. If `migration.target_markets` is unset (single-market engagement), skip this check with a one-line note — there is nothing to reconcile across a single schema.
   c. Data type references (inline casts, SAFE_CAST equivalents)
   d. SQL function translations (per the translation guide)
   e. Configuration block — adapter/dispatch updates, plus materialisation per **Materialisation config** below
   f. Jinja macro calls that need dispatch overrides
4. Assign a confidence rating: `high` = only simple, table-driven replacements. `medium` = engagement-specific nuance. `low` = no clean equivalent or a construct the guide marks "manual".

##### Materialisation config

**Read the resolved materialisation from the manifest node, not the fallback path.** Take `config.materialized` (and the keys below) from the model's node in whichever resolved project's manifest contains it, per Step 1's `dbt_manifest_parse.md`-based resolution (`nodes[...].config`, keyed by the project-qualified node ID). The manifest already merges `dbt_project.yml` folder config with in-file `{{ config() }}` blocks, so the node's config is the authoritative resolved value. Do not re-derive materialisation from `dbt_project.yml` + in-file blocks separately — that is the fragile fallback called out in Step 1a and it gets folder-level defaults wrong. Do not assume the manifest sits at a single `<migration.dbt_project_path>/target/manifest.json` — a monorepo with more than one dbt project resolves to more than one manifest, and the wrong one gets the config subtly wrong for every model in the other project.

**Default — faithful preservation (every client).** Carry the source's resolved materialisation across unchanged. A lift-and-shift must not silently change how a model is materialised:
- Preserve the `materialized` value as-is: `table` → `table`, `view` → `view`, `incremental` → `incremental`, `ephemeral` → `ephemeral`.
- For `incremental`, carry across `incremental_strategy`, `unique_key`, `partition_by`, `cluster_by`, and `on_schema_change` — translating only their *values* to target-dialect equivalents where the platform pair requires it, never their intent. An incremental model stays incremental with its strategy intact.
- Preserve `persist_docs` and any other config key with a target equivalent.

A blanket `materialized: table` rewrite is **wrong** — it discards incremental strategies and partitioning and silently re-shapes the build. Preservation is the correct default.

**Override hook (declarative; the spec ships no path, no layer names, and no default rules).** The default above (faithful preservation) is the whole behaviour unless the engagement points the hook at an overrides file. Read a **configurable engagement path** from `status.md`:

```yaml
migration:
  materialization_overrides_path: ".wire/engagement/<file>.yml"   # engagement-relative; unset = preserve only
```

The file it resolves to declares the policy. The schema is `default: preserve` plus an `overrides` list of `select` / `exclude` / `force_materialized` rules:

```yaml
default: preserve              # the default for every unmatched model — always "preserve"
overrides:
  - select: "<selector>"            # models this rule forces — a path glob, or a `path:`/`tag:` selector
    exclude: "<selector>"            # optional — models to leave preserved (e.g. a staging exception)
    force_materialized: "<table|view|incremental|...>"
    # plus any config the forced materialisation needs: incremental_strategy, partition_by, cluster_by, …
```

Resolution: for each in-scope model, if it matches a rule's `select` and is not caught by that rule's `exclude`, force `force_materialized` (and the rule's accompanying config) in place of the preserved value; record the override and the rule that fired in `loop_history` and the `.diff.md`. `default: preserve` governs every model no rule forces. The staging exception is just an `exclude` the engagement supplies — the spec hardcodes no path, no selector, and no rules. When `materialization_overrides_path` is unset, missing, or the file declares no `overrides`, every model keeps its preserved materialisation.

**Selector grammar.** `select` and `exclude` are each a **single** selector — a bare glob matched against the model's path (which includes its filename), a `path:<glob>` prefix/glob, or a `tag:<tag>`. Space-separated unions are **not** supported (a space is treated literally), and a bare glob matches the path, not a standalone model name. Because the filename is part of the path, a path glob still reaches name prefixes: `*stg_*` excludes `stg_`-named models and `*/stg/*` excludes a `stg/` directory. To exclude two disjoint sets in one rule, tag them and use `exclude: "tag:<tag>"`.

**Optional `name` / `description`.** Each override rule may carry optional `name` and `description` keys. The parser tolerates them: they are **ignored by the matcher** and **must not** be copied into the forced model config (only keys other than `select`/`exclude`/`force_materialized`/`name`/`description` are treated as accompanying materialisation config). The fired rule's `name` is surfaced in run metadata (`loop_history` / the `.diff.md`).

Forcing a materialisation the source did not use **diverges from the source** — it is an opt-in engagement optimisation, not faithful lift-and-shift. It happens only when a rule explicitly says so; it is never a default.

**Relationship to `dbt-migration-lint`.** The lint command's `MATERIALIZATION_DRIFT` rule is the after-the-fact backstop for anything this hook cannot reach — a model hand-edited after generation, or a written materialisation that is wrong despite preservation. Both mechanisms are intentionally kept: the hook prevents the wrong choice being written; the lint rule detects one that got written anyway.

##### Proactive deterministic-defect pass (shift-left)

Modelled on the materialisation-preservation hook above — the hook prevents the wrong choice being *written*; this pass prevents the known silent-and-deploy-time defects being written. Today a defect that doesn't break the sampled data (a bare `PARSE_JSON`, a `DIV0` emitted as bare `SAFE_DIVIDE`, an unpinned `SELECT *`, a `column_order_drift`, a dropped policy tag) sails through the three-check equivalency and is left for a later gate. This pass catches them **during translation** instead.

**Run this on every iteration, right after applying the translations in this step and before writing the SQL (3.2), alongside the translation safeguards.** Load the active pair's full deterministic rule set — the union of:
- the `dbt-migration-lint` catalogue (`BARE_UNION`, `LEFTOVER_CAST_OP`, `DATEDIFF_ARGORDER`, `ARRAY_AGG_NULLS`, `QUALIFY_NO_WHERE`, `REGEXP_ANCHOR`, `CLUSTER_BY_ORDER_BY_CONFLICT`, `MATERIALIZATION_DRIFT`, `UNPINNED_SELECT_STAR`, …);
- the `dbt-migration-pre-pr-review` edge-case / governance / column-order patterns — the pair's **"Edge-case runtime-failure patterns"** (`UNGUARDED_JSON_PARSE`, `CAST_BLANK_STRING_NUMERIC`, `UNANCHORED_REGEX`, `DIV0_NULL_COERCION`), **"Column governance / masking mechanisms"** (`governance_regression` — the dropped policy tag), and **"Schema-parity / column-order"** (`column_order_drift`);
- the pair's **"Deployment-integration / provenance defect patterns"** rules 1–3 (`MODEL_NOT_REGISTERED_FOR_DEPLOYMENT`, `HARDCODED_TARGET_DATABASE_XPROJECT`, `CDC_SOURCE_NO_SOFT_DELETE_FILTER`) — rule 4 (`STALE_NULL_PAD_BRONZE_PRESENT`) is **not** run here (the column lands after generation — it lives in `migration-drift`).

Classify every pattern that fires using the **`dbt-migration-fix` auto/propose/decision classifier** (fix.md's fix-policy table — pair/engagement overrides applied):

- **`auto` (deterministic and semantically safe regardless of intent) — rewrite inline, now.** `UNGUARDED_JSON_PARSE`→`SAFE.`; `CAST_BLANK_STRING_NUMERIC`→`SAFE_CAST`; `UNANCHORED_REGEX`→`^(?:...)$`; `DIV0_NULL_COERCION`→the faithful `IF(...)` form; `ARRAY_AGG_NULLS`→`IGNORE NULLS`; `TS_WRAP_ALREADY_TS`→drop the wrap; `IMPLICIT_JOIN_COERCION`/`JSON_FN_ON_*`→align the type; `governance_regression`→author the `policy_tags` from the tag map (this is what Step 3b item 4 already does — the pass just guarantees it is not skipped); `column_order_drift`→author the output projection in source ordinal order plus the pair's allow-listed tail; `HARDCODED_TARGET_DATABASE_XPROJECT`→rewrite to `source()` with the correct pair database; `CDC_SOURCE_NO_SOFT_DELETE_FILTER`→inject the pair's soft-delete filter macro; `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT`→add the model's dataset/folder to the deployment manifest resolved via the pair's `deployment_manifest` pointer.
- **`UNPINNED_SELECT_STAR` — authored explicitly at generate time.** Unlike the post-hoc fix loop (where it is `propose` because a hand-authored star's intent is unknown), here Wire is *authoring* the projection and has the resolved upstream schema in hand — the same introspection Check B (3.5) and Step 3.1 item b already use. Author the explicit source column list in source ordinal order from the start rather than emitting a star, so the output never trips the rule. If the upstream schema is genuinely not resolvable, leave the star and flag `-- MANUAL REVIEW` (falling back to the post-hoc `propose` posture) rather than guessing a column list.
- **`propose` / `decision` (intent-dependent or needs information the loop lacks) — never auto-rewritten.** `STRING_FN_ON_NONSTRING` (cast vs. remove is a judgment), an undeclared `MATERIALIZATION_DRIFT` beyond the preservation hook, `parity_vs_correctness`, `HARDCODED_TARGET_DATABASE_XPROJECT` whose relation maps to no declared source, `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` when the manifest resolves read-only, `governance_regression` with no tag-map entry. Leave a `-- MANUAL REVIEW` comment naming the pattern and carry it into the batch summary (Step 4) and the transformation log's `manual_review_reasons` (Step 4d). Do not auto-rewrite — a wrong auto-fix that still passes the deterministic gate is worse than an escalation.

**Manifest no-op (rule 1).** Read the `migration.deployment_manifest` pointer from status.md (or the `--config` overlay). If it is unset or its `path` does not resolve, `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` is a **no-op** — record `deployment manifest not configured — MODEL_NOT_REGISTERED_FOR_DEPLOYMENT not checked` in the batch summary as a coverage gap, never a silent pass.

**Data-safety guard (unchanged).** Everything this pass reads is compile-, dry-run-, or metadata-only — the same schema introspection Step 3.5 Check B uses, and a read/append edit to the deployment manifest file. It writes **no** data to any warehouse and never touches a source platform or a `data_safety.production_projects` project. The manifest edit is a repo-file edit, not a warehouse write.

**`dbt-migration-lint` remains the independent backstop.** This pass fixes what *`generate` itself* translates; it cannot see a model hand-edited after generation or a non-Wire/hand-ported model. `dbt-migration-lint` (and the pre-PR review) still run the same rule catalogue over the whole diff afterwards — both mechanisms are intentionally kept, exactly as the materialisation hook and `MATERIALIZATION_DRIFT` are (proactive vs. after-the-fact backstop). Record every fired pattern (auto-rewritten or flagged) in `loop_history` and the model's `.diff.md`.

**Acceptance.** A model translated by this command that would otherwise trip `DIV0_NULL_COERCION`, `UNGUARDED_JSON_PARSE`, `CAST_BLANK_STRING_NUMERIC`, `UNANCHORED_REGEX`, `UNPINNED_SELECT_STAR`, `column_order_drift`, a dropped policy tag, or any of the three deploy-integration rules comes out already fixed — a subsequent `dbt-migration-lint` / `dbt-migration-pre-pr-review` over the same diff reports zero of those.

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

Validate the translated SQL will compile against the target platform without materialising data. Use the target platform MCP to run the compiled SQL with `LIMIT 0` appended (or equivalent). For Jinja-templated models, compile against the target profile's `LIMIT 0` pattern. For a BigQuery target, route this call through `specs/utils/bigquery_mcp_fallback.md` (`operation: compile_check`) — a connection failure is not a SQL problem, and must not be recorded as a compile error or burn an auto-fix iteration; only a genuine compile error (from either the MCP or the `bq --dry_run` fallback) counts below.

If compile fails:
- Record: `{ iteration: N, stage: "compile", error: "<message>", action: "auto-fix" }`
- Update DAG state for this model to `migrated` (orange — in progress)
- Go to next iteration (3.1 auto-fix)

If compile succeeds: proceed to 3.4.

#### 3.4 Run on target

Execute the full model SQL as a materialisation against the test project using the target platform MCP's write tool. For BigQuery: `execute_sql` (not readonly), routed through `specs/utils/bigquery_mcp_fallback.md` (`operation: write`) on a connection failure — again, do not record a fallback-triggering connection error as a run failure. The target dataset/schema is read from `data_safety.target_project` and `migration.target_schema` in status.md (or the `--config` overlay's equivalents, if loaded).

Run only against the test project — never against production. If the write tool (or its `bq` CLI fallback) would target a project listed in `data_safety.production_projects`, stop immediately and report the conflict.

**Long-running model guard.** The MCP's `execute_sql` enforces a hard job timeout of roughly 3 minutes. If a model is expected to run long — a large CTAS, a backfill, or a model that has historically taken more than 2 minutes — do not run it via the MCP's `execute_sql`. Route it through `dbt run --select <model>` (or the target's dbt Cloud/Core job runner) instead, which honours a much longer (3600s) timeout. A genuinely slow but successful build (e.g. 188 seconds) killed by the MCP's timeout is a false failure, not a real one — don't record it as a run failure in `loop_history` without first ruling out that the job was still running when the MCP gave up.

If run fails:
- Record: `{ iteration: N, stage: "run", error: "<message>", action: "auto-fix" }`
- Go to next iteration (3.1 auto-fix)

If run succeeds: proceed to 3.5.

#### 3.5 Three-check equivalency

Run these three checks using both the source platform MCP (read-only) and the target platform MCP (read-only). Do not run any write queries here. For a BigQuery side, route each query through `specs/utils/bigquery_mcp_fallback.md` (`operation: read`) on a connection failure.

**Baseline pin (when the strategy defines a frozen baseline).** If `migration.equivalency_baseline` is set in status.md (see the migration strategy's "frozen equivalency baseline" — instant `T`, the Snowflake zero-copy clone, the BigQuery Bronze watermark, and the expected type-translation allow-list), run these in-loop checks against the **pinned** states, not live tables: read the source from the `wire_baseline` clone at `T`, and restrict the target to rows with `_fivetran_synced <= T`. Apply the deterministic-build switch (suppress/fix `CURRENT_TIMESTAMP`, `CURRENT_DATE`-relative windows, and fix the sample seed) so the model materialises reproducibly at `T`. This keeps the per-model loop's pass/fail consistent with the later `equivalency-validate` tier-3 run, which uses the same baseline. When no baseline is defined, run against live tables as before.

**Check A — Row count** (tolerance ±0.5%):
```sql
-- Source
SELECT COUNT(*) AS row_count FROM {source_db}.{source_schema}.{table_name};
-- Target
SELECT COUNT(*) AS row_count FROM {target_project}.{target_schema}.{table_name};
```
PASS: `|source_count - target_count| / source_count ≤ 0.005`
FAIL: count outside tolerance — record source count, target count, and deviation.

**Check B — Schema (set + column order)**:
Compare column names, data types (per `type_mapping.md`), and nullability between source and target by querying `INFORMATION_SCHEMA.COLUMNS` on both platforms. Use the **deployment** warehouse types established in Step 0d as the target side wherever the validation warehouse differs from deployment — a schema check against a scratch warehouse's types passes while the deployment warehouse's types would fail. Apply the pair's "Deployment type-divergence patterns" (Step 0d) against the translated SQL and the deployment column types: any firing pattern (a `TIMESTAMP()` wrap on an already-typed column, a JSON function on a STRING/JSON-mismatched column, an implicit cross-type join coercion) is a Check B FAIL feeding the 3.1 auto-fix loop, not a silent pass.

**Column order (W6b).** Query both sides with `ORDER BY ordinal_position` and compare the **sequences**, not just the sets, per the pair's "Schema-parity / column-order" section: source columns first in source ordinal order, then the pair's migration-appended tail allow-list (audit/load-timestamp columns, then region/surrogate globalize keys — concrete names from the engagement override) stripped before the source-sequence comparison. An unexpected non-allow-listed column or a missing source column is the existing extra/missing-columns FAIL (a set mismatch), not this finding. `column_order_drift` is reserved for a **pure reorder** — the set already matches but the sequence differs — and feeds the auto-fix loop as a deterministic reorder to source order, unless the model carries a `column_order_waived: <reason>` waiver in the migration register / model `meta`.
PASS: all columns present with expected types (modulo documented type translations), no deployment type-divergence pattern fires, and the target column sequence equals the source ordinal order plus any allow-listed tail columns (or a waiver is recorded).
FAIL: missing columns, extra columns, unexpected type changes, nullability mismatches, a fired deployment type-divergence pattern, or a `column_order_drift` mismatch with no recorded waiver — record the specific column differences and the deployment column type.

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

#### 3.7 Update the migration register

When a model reaches a terminal state, upsert its row in `migration/migration_register.csv` (the per-model state store — see `migration-register-generate`). Write `source_path`, `source_layer`, `last_migrated_commit` (the source snapshot SHA from `migration_sources.dbt.commit`), `bq_target` (the `dataset.table` just built), and `state` — `migrated` on PASS, `failed` after 5 iterations, `deferred` if the model was skipped because its source object isn't built on target. Leave the equivalence columns to `equivalency-validate`. If the register doesn't exist yet, create it from `TEMPLATES/migration/migration_register.csv` first. This is what lets the drift gate later tell which source commit each model was built from.

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

4. **PII / column policy tags and `meta`** — if column-level protection is applied through dbt (e.g. BigQuery `policy_tags`), author the `policy_tags` references into the column YAML here, driven by the tag map loaded in Step 2:
   - For **every** column carrying a `meta.masking_policy` value in the source YAML, look up the target policy tag in the tag map using the **normalised** (lowercased, trimmed) policy name — never an exact-case match.
   - On a hit, write the resolved policy-tag resource path into the column's `policy_tags` list in the translated YAML. Count it as auto-resolved.
   - On a miss — no map entry even after normalisation — do **not** silently omit the tag. Leave the column untagged, flag it `MANUAL REVIEW REQUIRED`, and record the column name and the unresolved masking-policy value. These flags surface in the batch summary (Step 4) and in `manual_review_reasons` in the transformation log (Step 4d).
   - If no tag map was found in Step 2, fall back to manual authoring: resolve each `policy_tags` reference by hand, or defer with a note in the diff file.

   Confirm ownership with the security-migration scope first — do not apply tags in both dbt YAML and warehouse DDL.

Write the translated YAML alongside the model, preserving the same relative path: `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path_from_models_root_without_extension}.yml`. Note any `sources.yml` repoint, custom-test translation, or `policy_tags` change (auto-resolved or flagged) in the model's diff file.

### Step 3s: Translate and continue snapshots

Every snapshot in this batch/scope (an `object_type = snapshot` node from the migration register, cross-referenced to `audit/dbt_snapshots.csv`) is translated here. A snapshot is an SCD-2 history object, not a plain model — translate it under stricter rules, reading the SCD meta-column set and the `dbt_scd_id` continuation invariant from the active pair's **"Snapshot SCD mechanisms"** section (never hardcode the meta-column types).

1. **Translate the inner SELECT only.** The body between `{% snapshot %}` and `{% endsnapshot %}` (the SELECT that feeds the snapshot) is translated exactly like a model body: function swaps, type handling, source-to-ref resolution (Step 3.1 item a) and the Bronze-schema/market-gap check (item b), and Jinja/dispatch updates. Repoint every `ref()`/`source()` in the inner SELECT to the target as for a model.

2. **Keep the snapshot config byte-identical.** The hash-input config — `strategy`, `unique_key`, `updated_at` (timestamp strategy) or `check_cols` (check strategy), and `invalidate_hard_deletes` — must stay **exactly** as on the source. dbt computes `dbt_scd_id` by hashing these inputs; changing any of them re-hashes every row's `dbt_scd_id` and orphans the history copied by `bulk-copy-migration-generate`. Repoint **only** the relation namespace (`target_schema` / `target_database`) to the target platform's namespace for the same physical relation the copy landed at — that value does not feed `dbt_scd_id`. Do not "tidy", rename, or re-express the `unique_key`/`updated_at`/`check_cols` expressions, even cosmetically.

3. **Confirm the `dbt_scd_id` inputs stringify identically.** Per the pair's Snapshot SCD mechanisms section, verify the `unique_key` and `updated_at`/`check_cols` inputs cast to the same string on the target as on the source under the pair's type translations (watch `NUMBER`-scale rounding, `TIMESTAMP_NTZ → DATETIME` precision, NULL-vs-empty-string). If they cannot be made to stringify identically, the copied history's `dbt_scd_id` will not line up — flag the snapshot `-- MANUAL REVIEW` rather than silently continuing.

4. **Adopt and continue after the copy.** For a `copy_and_continue` snapshot, the built history is copied to the `target_schema` relation by `bulk-copy-migration-generate` **before** this step. Once the copy has landed, run `dbt snapshot --select <snap>` **once** against the target so dbt adopts the copied relation and appends only genuinely new/changed versions — never before the copy (a `dbt snapshot` against an empty target relation opens fresh version rows and orphans the copied history). For a `rebuild_from_T` snapshot (recorded sign-off only), there is no copy — run `dbt snapshot --select <snap>` against the empty target to start the history fresh at `T`.

5. **Test gate, not row equivalence.** A snapshot's pass criterion is the three-layer snapshot gate in `dbt-migration-validate` / `equivalency-validate` (copy-parity at `T`, continuation behaviour, SCD integrity) — a SELECT-only row-equivalence is never sufficient. The per-model loop's three-check equivalency (Step 3.5) applies to the inner SELECT's correctness but does not by itself pass the snapshot.

Write the translated snapshot to `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}` mirroring the source `snapshots/` (or `models/`) location, with a `.diff.md` showing the inner-SELECT changes and confirming the config is unchanged. Upsert the snapshot's register row (Step 3.7) with `object_type = snapshot`, leaving `snapshot_strategy` as seeded.

### Step 4: Generate batch summary

Write `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`:
- Models translated in this batch
- Translation patterns applied (counts by type)
- Confidence breakdown (count of high / medium / low)
- Per-model loop results: iterations taken, which checks failed, final status
- Models requiring manual review (every `FAILED` model and every `low` confidence model)
- **Companion YAML changes**: `sources.yml` repoints, custom/singular tests translated, `policy_tags` authored or deferred — including the count of policy tags auto-resolved from the tag map and the count of `MANUAL REVIEW REQUIRED` flags for unresolved masking policies, naming each flagged column and its unresolved policy value
- **Source-to-ref substitutions and Bronze-schema gaps** (Step 3.1 items a–b): count of `source(...)` calls rewritten to `ref(...)`, and every `MARKET GAP` column substitution — naming the model, column, synthesized type, and affected market(s)
- **Snapshots** (Step 3s): each snapshot translated, its `snapshot_strategy`, confirmation the hash-input config (`strategy`/`unique_key`/`updated_at`/`check_cols`) is unchanged, whether the `dbt_scd_id` inputs stringify identically, and whether the target adopt-and-continue `dbt snapshot` run was ordered after the history copy
- **Proactive deterministic-defect pass** (Step 3.1 "Proactive deterministic-defect pass"): counts of `auto` patterns rewritten inline (by pattern id) and every `propose`/`decision` pattern left flagged `-- MANUAL REVIEW`; plus the `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` coverage note when the deployment manifest is unconfigured
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

Engagements asked for a structured, queryable audit trail of what each model's translation changed — not just console output and `.diff.md` files. This step is **additive**: the diff files (Step 3.2) and batch summary (Step 4) are still written. It persists one structured record per migrated object to a BigQuery audit table.

**Configurable target table.** Read the audit table location from status.md:

```yaml
migration:
  transformation_log_table: null   # e.g. "<target-project>.wire_audit.dbt_transformation_log"
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
| `manual_review` | BOOL | True if the model is FAILED, `low` confidence, or carries an unresolved masking-policy flag (Step 3b item 4) |
| `manual_review_reasons` | JSON | Array of strings — which checks failed / why review is flagged (include each unresolved masking-policy value and column) |
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
    wave: "B01"                                 # set only when run with --wave; the wave id just processed
    waves_complete: ["B01"]                     # set only when run with --wave; accumulates across runs
    mcp_fallback_count: N                        # BigQuery target only; 0 when the MCP stayed up the whole run — see specs/utils/bigquery_mcp_fallback.md
```

If `--model`, `--select`, or `--wave` was used, update only the translated models' status. Do not advance `current_batch` — that field belongs to the `dbt_audit.batch_number` scheme, and a `--wave` run tracks its own progress via `wave` / `waves_complete` instead.

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

### Step 7: Chain the downstream gates (model path, default)

On the **model path** (a `--batch`/`--wave`/`--model`/`--models`/`--select` run, or the no-flag next-batch run), the batch is not done when translation is — the downstream gates still have to run, and a run that stops at "recommended next steps" lets a consultant hand off skipping them. Unless `--no-chain` was supplied, chain the gates over the scope just translated, in this order, each over the same resolved model set (pass through `--wave`/`--batch`/`--model`/`--models`/`--base` and any `--config`/overlay flags):

1. `dbt-migration-validate` — the compile + all-code-path coverage gate (writes the Check 5 coverage report).
2. `dbt-migration-lint` — the static silent-divergence backstop over the diff (writes the lint result). This is the independent backstop for anything the inline pass could not reach (a model hand-edited after generation, non-Wire code) — the inline pass and lint are complementary, not redundant.
3. `dbt-migration-fix` — auto-apply the deterministic findings and re-run the deterministic gate (writes the applied-fix summary). Because the inline pass (Step 3.1) already fixed the `auto` patterns it could during translation, this normally has little to do — it catches anything the inline pass could not (e.g. a `governance_regression` needing a tag-map entry that later landed) and re-converges.
4. `dbt-migration-pre-pr-review` — the pre-PR faithfulness synthesis (writes the findings file), leaving the consultant only the semantic `propose`/`decision` findings to adjudicate.

Run the chain over the whole batch/wave after the per-model loop completes (not per model). If any gate reports blocking (`error`-severity) findings, do not silently continue the chain past a hard failure — surface the failing gate's report and stop, so the consultant fixes it before the review. The chain edits only translated files under `migration/dbt/` and reads/writes only the test project (`dbt-migration-fix`'s own data-safety guard applies) — no production or source writes.

**Scope exclusions.** `--macros` and `--snapshots` do **not** chain — they are orthogonal, standalone passes with their own validate scopes (`--macros` / `--snapshots`), and their own next-command hints already point at those (`dbt-migration-validate $ARGUMENTS --macros` / `--snapshots`). Skip Step 7 entirely for those scopes regardless of `--no-chain`. `--snapshots` is a recently-added scope; like `--macros` it keeps its existing non-chaining behaviour.

With `--no-chain` on the model path, print the chain that was skipped and the command to run it manually:
```
[wire] --no-chain: skipped the downstream gate chain. Run it when ready:
/wire:dbt-migration-validate $ARGUMENTS --wave <id>
/wire:dbt-migration-lint $ARGUMENTS --wave <id>
/wire:dbt-migration-fix $ARGUMENTS --wave <id>
/wire:dbt-migration-pre-pr-review $ARGUMENTS --wave <id>
```

**Acceptance.** A default `generate` run over a batch leaves behind the validate coverage report, a lint result, an applied-fix summary, and a pre-PR review findings file — with no manual invocation. `--no-chain`, `--macros`, and `--snapshots` each leave none of those (the consultant drives the gates).

## Output Files

- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.sql` — subdirectory structure mirrors the source dbt project
- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.yml` — companion schema/properties YAML
- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.diff.md` — covers `.sql` and `.yml` changes
- `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`
- `.wire/releases/$ARGUMENTS/migration/dbt/acceptance_pack_batch_{N}.md` — generated when all batch models reach terminal state
- **`--macros` mode:** `.wire/releases/$ARGUMENTS/migration/dbt/macros/{relative_path}/{macro}.sql` (+ `.diff.md`) mirroring the source `macros/` tree, and `.wire/releases/$ARGUMENTS/migration/dbt/batch_zero_macros_summary.md`
- BigQuery table `migration.transformation_log_table` (when configured) — one structured row per migrated object; not a file
- `.wire/releases/$ARGUMENTS/artifacts/migration_strategy/dag_batch_{N}.md` — updated Mermaid DAG with current model states
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`. If `mcp_fallback_count > 0`, note it in the `Detail` column (e.g. `"...; 12 calls used bq CLI fallback (MCP flapped mid-run)"`) per `specs/utils/bigquery_mcp_fallback.md`'s Step 3 — do not write a separate log row per fallback.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_migration` as artifact_id, `dbt Migration` as artifact_name, and the `file` value from `artifacts.dbt_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_migration` as artifact, `generate` as action.

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
