---
description: Static pre-warehouse equivalence lint — dialect parse-check plus silent-behaviour-change rules on translated models
argument-hint: <release-folder> [--batch N] [--model name] [--severity LEVEL] [--format FORMAT]
---

# Static pre-warehouse equivalence lint — dialect parse-check plus silent-behaviour-change rules on translated models

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
description: Static pre-warehouse equivalence lint — dialect parse-check plus silent-behaviour-change rules on translated dbt models
---

# dbt Migration — Lint (Tier 1 equivalence pre-flight)

## Purpose

A static, offline first pass over translated dbt models that catches the translations which **compile cleanly on the target and still return the wrong answer**. It does not connect to either warehouse and does not run any SQL. It runs after `dbt_migration-generate` and before the live `equivalency-validate` loop, so the cheap, high-frequency divergences are caught before anyone pays for a parallel run.

This is **Tier 1** of the three-tier equivalence approach in `wire/platform_pairs/dbt_neutral_translation.md`:

- **Tier 1 — this command.** Dialect parse-validation + silent-behaviour-change lint. Offline, seconds, no warehouse, no data.
- **Tier 2 — logical smoke test.** Same seed data through both logics in a local engine (DuckDB). Catches structural/grain breakage, *not* dialect semantics. Optional, separate.
- **Tier 3 — `equivalency-validate`.** The real parallel run on both warehouses with real data. The source of truth.

**What this command does not do:** it does not prove output equivalence. Every rule here flags a *risk* a naive translation would miss; clearing the lint means the model is free of known silent-divergence patterns, not that its output matches. Tier 3 remains mandatory. Say so in the report header so a green lint is never mistaken for a pass.

## Relationship to `dbt_migration-validate`

The two are complementary and must not be merged:

| | `dbt_migration-validate` | `dbt_migration-lint` (this) |
|---|---|---|
| Question | Does the translated model *compile* and is the translation *complete*? | Does the translated model *mean the same thing*? |
| Catches | Untranslated source-platform functions, missing files, Jinja errors, `dbt compile` failures | Valid target SQL that diverges silently — arg-order flips, NULL-handling, timezone, boundary semantics, hash mismatch |
| Needs target profile | Optionally (for `dbt compile`) | Never |
| Example miss if absent | `DATEADD(...)` left untranslated | `DATE_DIFF(start, end, DAY)` — compiles, wrong sign |

`validate` Check 2 ("no source-platform functions remain") is about completeness. This command assumes translation happened and asks whether it was *correct*.

## Flags

- `--batch N` — lint batch N only (default: `current_batch` in status.md). Reads `dbt_audit.csv`'s `batch_number` — the topological, finer-grained translation batch. Use it for a topological-only or re-run slice.
- `--wave <id>` — **the intended execution unit for a normal run.** Lint every dbt-model row `migration/migration_batching.csv` assigns to this wave (`batch_id`), cross-referenced against `dbt_audit.csv` for the actual model set. Accepts zero-padded (`B01`) or bare (`1`) forms; both normalise the same way. See Step 1w below — it mirrors `dbt_migration-generate`'s Step 1w exactly, reusing the same resolution so the two commands never disagree about what "wave B01" means. `--wave` and `--batch` are different numbering schemes — abort if both are supplied: `[wire] --wave and --batch read different numbering schemes and cannot be combined. Pick one.`
- `--model name` — lint a single translated model
- `--macros` — lint the translated **macro definitions** instead of the model tree; see **Macro Mode** below.
- `--severity error|warn|info` — minimum severity to report (default: `info`)
- `--format md|json` — report format (default: `md`; `json` for CI gating)
- `--config <path>` — load a per-run config overlay file overriding status.md-sourced fields (`migration.dbt_project_path`, `migration.source_platform`/`migration.target_platform`, `migration.materialization_overrides_path`, etc.) for this invocation only — never written back to status.md. Mirrors `dbt_migration-generate`'s `--config` overlay exactly; see that spec's **Config overlay** section for the mechanism and the `data_safety.production_projects` exclusion. Orthogonal to scope — combine freely with `--batch`, `--wave`, `--model`, or `--macros`.
- `--tag-map <path>` / `--target-dataset <name>` / `--dbt-project-path <path>` — discrete single-field overlay shorthands (for `migration.pii_tag_map_path` / `migration.target_schema` / `migration.dbt_project_path` respectively). Mirror `dbt_migration-generate`'s equivalents exactly; see that spec's **Config overlay** section.

`--macros` is a standalone scope — abort if combined with `--batch`, `--wave`, or `--model`: `[wire] --macros is a standalone scope. Run it on its own; do not combine with --batch/--wave/--model.`

## Inputs

- Translated model SQL in `migration/dbt/` (output of `dbt_migration-generate`)
- Source model SQL at `migration.dbt_project_path` (for the before/after pair) — resolved via `specs/utils/dbt_manifest_parse.md` Steps 1–2 (nested/multi-project aware; see Step 1 below), not by assuming a single project sits directly at that path
- `.wire/releases/$ARGUMENTS/migration/migration_batching.csv` — consumed only by `--wave` mode
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — cross-referenced by `--wave` mode
- `--macros` mode: translated macro files under `migration/dbt/macros/` (output of `dbt_migration-generate --macros`) in place of the model tree
- Active platform pair, resolved from `status.md` `source_platform` / `target_platform` (or the `--config` overlay's equivalents, if loaded):
  - `wire/platform_pairs/{pair}/feature_detection.md` — the tag regexes the rules build on
  - `wire/platform_pairs/{pair}/translation_reference.md` — the §11 gotcha checklist this rule set is derived from; the authoritative description for every rule
  - `wire/platform_pairs/{pair}/translation_guide.md` — pattern table
- Engagement overrides at `.wire/engagement/platform_pair_overrides/{pair}/lint_rules.md`, if present — extra rules or per-engagement severity overrides, layered on top (override wins on the same rule id)
- The resolved source manifest(s) (per Step 1's `dbt_manifest_parse.md` resolution) — the source `config.materialized` per model, for `MATERIALIZATION_DRIFT`; when the manifest is unavailable, fall back to the `dbt_project.yml` + in-file config scan and note the reduced confidence per model
- The engagement's materialisation overrides file at `migration.materialization_overrides_path` (status.md, or the `--config` overlay), if set — declared overrides suppress `MATERIALIZATION_DRIFT` hits
- **`--config <path>` overlay (optional)**: see `dbt_migration-generate`'s **Config overlay** section — same mechanism, same fields, held in memory for this invocation only
- **`--tag-map <path>` / `--target-dataset <name>` / `--dbt-project-path <path>` (optional)**: discrete single-field overlay shorthands — see `dbt_migration-generate`'s **Config overlay** section

## Engines

Two detection engines, in preference order. The command uses whichever is available and records which in the report.

1. **AST (preferred) — `sqlglot`.** Parse each translated model in the *target* dialect and each source model in the *source* dialect. This gives two things regex cannot:
   - **Parse-validation**: a model that fails to parse in its declared dialect is an immediate `error` (rule `PARSE`). This is the "is it even valid target SQL" gate, offline.
   - **Structural rules**: argument counts and order, function names, presence of clauses (`IGNORE NULLS`, `WHERE` before `QUALIFY`) read off the parse tree rather than guessed from text. Far fewer false positives than regex.
   sqlglot also transpiles, so where a rule has a deterministic fix the report can show sqlglot's suggested rewrite as a starting point (never auto-applied here — that's `dbt_migration-generate`'s job).
2. **Regex fallback.** When sqlglot is not installed, fall back to line-based regex from `feature_detection.md` plus the rule patterns below. Lower precision (multi-line constructs and context are missed — see the `feature_detection.md` note on line-based matching), so the report header must state "regex mode — reduced precision; install sqlglot for AST checks."

Jinja first: render or strip `{{ ... }}` / `{% ... %}` before parsing. A model that is mostly macros may be unparseable as raw SQL — lint the compiled SQL if a `target/compiled/` artifact exists, otherwise lint the static SQL spans between Jinja tags and note the coverage gap per model.

## Rule catalogue

Rules are derived from `translation_reference.md` §11 and the per-pair `feature_detection.md`. Each rule has: a stable `id`, a `severity`, the `detect` signal, and a `fix` hint. Severity reflects likelihood of a *silent* wrong answer, not how hard it is to fix.

`error` = compiles and is almost certainly wrong. `warn` = compiles and is wrong unless a specific precondition holds (check it). `info` = review-worthy, often fine.

### Snowflake → BigQuery rules

| id | severity | detect (on translated BigQuery SQL) | fix hint | ref |
|---|---|---|---|---|
| `PARSE` | error | Fails to parse as GoogleSQL | Not valid BigQuery — re-translate | — |
| `BARE_UNION` | error | `UNION` not followed by `ALL`/`DISTINCT` | BigQuery requires `UNION DISTINCT` | §1.4 |
| `LEFTOVER_CAST_OP` | error | `::` cast operator present | No `::` in BigQuery — use `CAST(...)`/`SAFE_CAST(...)` | §1.5 |
| `DATEDIFF_ARGORDER` | warn | `DATE_DIFF`/`TIMESTAMP_DIFF` whose args look reversed vs the source `DATEDIFF(part, a, b)` | BigQuery is `(end, start, part)` — sign flips if not reversed | §5.5 |
| `TS_DIFF_BOUNDARY` | warn | `TIMESTAMP_DIFF`/`DATETIME_DIFF` translated from a Snowflake `DATEDIFF` on timestamps | SF counts boundaries crossed; BQ counts whole units. Truncate both sides to match | §5.5 |
| `ARRAY_AGG_NULLS` | error | `ARRAY_AGG(` without `IGNORE NULLS` (and not provably non-null) | Add `IGNORE NULLS` — BQ errors on a NULL element at runtime | §5.6 |
| `NAIVE_CURRENT_DATE` | warn | `CURRENT_DATE()`/`CURRENT_TIMESTAMP()` with no timezone, translated from session-tz Snowflake | Make the zone explicit (`CURRENT_DATE('Europe/London')`); BQ is UTC | §1.3 |
| `TS_TO_DATE_TZ` | warn | `DATE(<timestamp expr>)` with no zone | Pass the zone or values shift by the UTC offset | §1.3 |
| `DOW_NUMBERING` | warn | `EXTRACT(DAYOFWEEK FROM ...)` used in arithmetic/compare | BQ fixes 1=Sunday; SF depends on `WEEK_START`. Compare day names instead | §5.5 |
| `WEEK_TRUNC_START` | warn | `DATE_TRUNC(d, WEEK)` | BQ week starts Sunday; use `WEEK(MONDAY)`/`ISOWEEK` to match SF | §5.5 |
| `QUALIFY_NO_WHERE` | error | `QUALIFY` with no `WHERE`/`GROUP BY`/`HAVING` in the same query | Add `WHERE TRUE` | §1.4 |
| `HASH_CROSS_PLATFORM` | warn | `FARM_FINGERPRINT`/`MD5`/`SHA*` on a key compared across platforms | HASH values never match across engines; rebuild keys from source columns; wrap MD5/SHA in `TO_HEX` | §5.4 |
| `LOG_ARGORDER` | warn | `LOG(` with two args | BQ is `LOG(x, base)`, reverse of Snowflake's `LOG(base, x)` | §5.2 |
| `SPLIT_PART_OFFSET` | warn | `SPLIT(...)[OFFSET(...)]` translated from `SPLIT_PART` | SPLIT_PART is 1-based, OFFSET 0-based; missing part returns '' vs NULL | §5.3 |
| `CONTAINS_SUBSTR_CASE` | warn | `CONTAINS_SUBSTR(` translated from `CONTAINS` | `CONTAINS_SUBSTR` is case-insensitive; use `STRPOS(...) > 0` for exact | §5.3 |
| `REGEXP_ANCHOR` | warn | `REGEXP_CONTAINS` translated from `REGEXP_LIKE`/`RLIKE` | REGEXP_LIKE anchors the whole string; wrap pattern `^(?:...)$` | §5.3 |
| `BOOL_STRING_CAST` | warn | `CAST(... AS BOOL)` on a string literal not `'true'`/`'false'` | BQ accepts only true/false; `'yes'`/`'1'` error | §1.5 |
| `FLOAT_NULL_SORT` | info | `ORDER BY` on a float/nullable column feeding a window/rank, no explicit `NULLS FIRST/LAST` | NaN and default NULL position differ; make it explicit | §19 |
| `ARRAY_TO_STRING_NULLS` | warn | `ARRAY_TO_STRING(a, sep)` with no null_text arg | BQ drops NULL elements; SF rendered empties — key columns diverge | §13 |
| `MERGE_NO_PRUNE` | info | `MERGE` into a partitioned target with no partition predicate in `ON`/`WHEN` | Scans whole target each run; add a target partition predicate | §10 |
| `CLUSTER_BY_ORDER_BY_CONFLICT` | error | Model's resolved config has `cluster_by` set **and** `materialized` is `table` or `incremental` (the first-run/full-refresh path issues the same CTAS shape), **and** the compiled SQL's outermost query has a top-level trailing `ORDER BY` — not an `ORDER BY` nested inside `OVER (...)`, `QUALIFY ... OVER (...)`, or an aggregate like `ARRAY_AGG(x ORDER BY y)` | Strip the trailing `ORDER BY` on the outer query — clustering doesn't preserve physical row order, so it does nothing on a clustered table and BigQuery rejects the DDL outright (`Result of ORDER BY queries cannot be clustered`) | §11.26 |

**`CLUSTER_BY_ORDER_BY_CONFLICT` is a pure static check — no BigQuery connection is needed and none is used.** It fires deterministically every time the model in question goes through a real `CREATE TABLE ... CLUSTER BY (...) AS (compiled_sql)`, so it belongs in this offline lint pass rather than being left to surface (inconsistently — see below) at materialisation time.

- **Config resolution.** Read `cluster_by` and `materialized` from the model's resolved config exactly the way `MATERIALIZATION_DRIFT` and `dbt-migration-generate`'s materialisation hook do — the manifest node's `config` block, not a fallback re-derivation from `dbt_project.yml` + in-file blocks. Skip the model entirely (not even a `PASS`) if `cluster_by` is unset — an `ORDER BY` with no clustering is legal BigQuery and does nothing wrong.
- **Distinguishing a real conflict from a false positive.** Do not simply grep for the `ORDER BY` keyword — track parenthesis depth over the compiled SQL (after Jinja rendering) and record the depth at which each `ORDER BY` keyword occurs. Only an `ORDER BY` at **depth 0** — outside every paren, i.e. the query's own outermost, unwrapped trailing clause — is a real conflict. An `ORDER BY` inside `OVER (...)`, `QUALIFY ... OVER (...)`, an aggregate call like `ARRAY_AGG(x ORDER BY y)`, or a CTE's own subquery (`WITH x AS (SELECT ... ORDER BY ...)`) is always nested inside at least one paren opened by that construct, so it never reaches depth 0 and must not be flagged. This is the exact false-positive shape a from-scratch keyword search hits on window-function-heavy models.
- **Suggested fix, never auto-applied here.** This rule has a fully deterministic fix (delete the outer `ORDER BY` clause) — per the **Engines** section above, where sqlglot is available the report shows the rewritten SQL as a suggested starting point. Applying it is `dbt-migration-generate`'s job (re-translate) or a hand edit, then re-lint, the same as every other rule in this catalogue; this command stays read-only.
- **Why this belongs in the static lint, not the equivalency loop.** A model carrying this pattern can "pass" `dbt-migration-generate`'s inline materialisation step and later `equivalency-validate`'s row-count/schema/sampling checks in one session and still fail outright the next time the same SQL runs through a real `dbt-bigquery` CTAS — whether the failure surfaces depends on incidental DDL-wrapping choices in how a given session executed the write, not on anything about the data. Catching it here, before any materialisation is attempted, removes that inconsistency; it is not a gap in equivalency validation; equivalency correctly validates data that already materialised; the gap is that nothing checked the DDL shape before materialisation was attempted at all.

### BigQuery → Snowflake rules

| id | severity | detect (on translated Snowflake SQL) | fix hint | ref |
|---|---|---|---|---|
| `PARSE` | error | Fails to parse as Snowflake SQL | Not valid Snowflake — re-translate | — |
| `ARRAY_CONTAINS_ARGORDER` | warn | `ARRAY_CONTAINS(` translated from `IN UNNEST` | Snowflake is `(value, array)` — reverse of BQ; value must be `::variant` | §13 |
| `STRUCT_LEFTOVER` | error | `STRUCT(` present (no Snowflake STRUCT literal) | Use `OBJECT_CONSTRUCT('k', v, ...)` | §6 |
| `SAFE_PREFIX_LEFTOVER` | error | `SAFE.` prefix or `SAFE_CAST` left untranslated | Snowflake uses `TRY_CAST`/`TRY_TO_*` | §1.5 |
| `OFFSET_ORDINAL` | warn | `[OFFSET(n)]`/`[ORDINAL(n)]` array access | Snowflake arrays are 0-based `a[n]`; ORDINAL is 1-based | §13 |
| `DOW_NUMBERING` | warn | `DAYOFWEEK` arithmetic | Snowflake honours `WEEK_START`; confirm the account default | §5.5 |
| `MEDIAN_WINDOW` | info | `PERCENTILE_CONT(... ) OVER ()` translated to Snowflake | Snowflake `MEDIAN`/`PERCENTILE_CONT ... WITHIN GROUP` is a true aggregate | §5.6 |

### Direction-agnostic rules

These run in both directions and in both engines. `MATERIALIZATION_DRIFT` reads model config, not the SQL parse tree, so it works identically under AST and regex; `UNPINNED_SELECT_STAR` reads the model's final output projection (AST preferred, regex fallback via the same paren-depth scan the cluster-by rule uses).

| id | severity | detect (on translated model config or output projection) | fix hint | ref |
|---|---|---|---|---|
| `MATERIALIZATION_DRIFT` | warn | Translated model's resolved materialisation (in-file `{{ config(...) }}` / companion YAML) differs from the source manifest node's `config.materialized`, and no rule in the engagement's materialisation overrides file declares the change | Restore the preserved source materialisation, or declare the change as an override rule so it is on the record | `generate.md` "Materialisation config" |
| `UNPINNED_SELECT_STAR` | error | The model's **final/output** `SELECT` projection — the depth-0 outermost query, not an import/staging CTE — is an unpinned star: `SELECT *`, `SELECT <alias>.*`, or `SELECT * EXCEPT(...)` | Expand to an explicit column list in source ordinal order. A lift-and-shift's output schema must be authored and reviewable: an unpinned `*` silently gains, loses, or reorders columns as the upstream evolves — breaking positional consumers (UNION/INSERT by position, CSV/SAR exports, BI and reverse-ETL pinned to column order) and defeating the `column_order_drift` parity check | §11.27 |

`MATERIALIZATION_DRIFT` exists precisely because `dbt-migration-generate`'s materialisation hook (preserve-by-default plus declarative overrides) cannot catch every case: a model hand-edited after generation, or a model where no override was declared and the written materialisation is simply wrong. The hook is proactive, this rule is the after-the-fact backstop — both are intentionally kept; they are complementary, not redundant. A hit is not automatically a defect: when the overrides file declares the change (the model matches a rule's `select`, is not caught by its `exclude`, and the written materialisation equals that rule's `force_materialized`), the rule stays silent — a declared override is the hook working as designed, never a lint finding. Severity is `warn` because an undeclared change compiles fine and silently re-shapes the build: an incremental flattened to `table` changes cost and freshness, and with late-arriving data can change results.

`UNPINNED_SELECT_STAR` targets the model's **output** projection only. Import/staging CTEs may `SELECT *` internally — that is idiomatic and safe; the rule fires only on the outermost, depth-0 `SELECT` that produces the model's output.

- **Finding the output projection.** Track parenthesis depth over the compiled/static SQL exactly as `CLUSTER_BY_ORDER_BY_CONFLICT` does. A `*` inside a CTE body, a scalar/`IN` subquery, or `EXISTS(SELECT *)` is always inside at least one paren, never reaches depth 0, and is **not** flagged. Only a star in the depth-0 outermost `SELECT` list — the projection that becomes the model's schema — is a hit.
- **All three forms are unpinned.** `SELECT *`, `SELECT <alias>.*`, and `SELECT * EXCEPT(col, ...)` are equally implicit: the emitted column set still depends on the upstream shape at run time rather than being authored in the model. All three are `error` on the output projection.
- **Why `error`, not `warn`.** In a lift-and-shift the target's output schema is a contract. An unpinned star means a column added, dropped, or reordered upstream silently changes this model's output — and because the rows still match, no row-level equivalency check sees it. It also makes `column_order_drift` (W6b) unenforceable: there is no authored order to compare against.
- **Deterministic fix — applied by `dbt-migration-fix`, never here.** Expand the star into the explicit source column list, in source ordinal order (per §11.27), so the projection is reviewable and `column_order_drift` can then verify it. Where sqlglot and the resolved upstream schema are available, the report attaches the expanded list as a suggested starting point.

### Deployment-integration rules (pair-declared)

These read the pair's **"Deployment-integration / provenance defect patterns"** section, not a rule hardcoded here — a new pair inherits them by declaring the section. They catch the deploy-time defects that pass a co-located validation warehouse and break under the real deployment project split or against the live source. All three are deterministic, and each has a deterministic auto-fix that `dbt-migration-generate`'s inline pass applies and `dbt-migration-fix` re-applies; this lint is the independent backstop for hand-edited or non-Wire code.

| id | severity | detect | fix hint | ref |
|---|---|---|---|---|
| `MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` | error | The model's dataset/folder is absent from the deployment orchestrator's model-selection manifest, resolved via the pair's `deployment_manifest` pointer in status.md | Add the folder to the manifest's selection | pair "Deployment-integration / provenance defect patterns" (rule 1) |
| `HARDCODED_TARGET_DATABASE_XPROJECT` | error | A cross-project relation reference built from `{{ target.database }}` or a hardcoded target-project literal that should be a `source()` call | Rewrite to `source('<source>', '<table>')` resolving to the correct deployment source database | pair section (rule 2) |
| `CDC_SOURCE_NO_SOFT_DELETE_FILTER` | error | A read of a CDC source carrying the pair's soft-delete marker (`_fivetran_deleted`) with no soft-delete filter | Inject the pair's soft-delete filter macro (`{{ filter_soft_deletes() }}` / `WHERE NOT COALESCE(_fivetran_deleted, FALSE)`) | pair section (rule 3) |

**`MODEL_NOT_REGISTERED_FOR_DEPLOYMENT` is a documented no-op when unconfigured.** Read the `migration.deployment_manifest` pointer from status.md (or the `--config` overlay). If it is unset or its `path` does not resolve, do **not** emit a PASS for this rule — record it in the report's **Coverage gaps** section (`deployment manifest not configured — MODEL_NOT_REGISTERED_FOR_DEPLOYMENT not checked`) so a clean result is never mistaken for a checked one. The `STALE_NULL_PAD_BRONZE_PRESENT` pattern (rule 4 in the same pair section) is **not** a lint rule — it needs the live source warehouse and each model's `last_migrated_commit`, so it lives in `migration-drift`, not here.

Engagement override files may add rows (e.g. a client-specific UDF that has no target equivalent) or downgrade a severity with a documented reason.

## Workflow

### Step 0 — Load config overlay, resolve project(s)
If `--config <path>` was supplied, load it exactly as `dbt_migration-generate` Step 0c describes — held in memory for this invocation only, never written back to status.md, `data_safety.production_projects` never overridable. Then resolve the dbt project(s) at `migration.dbt_project_path` (or the overlay's equivalent) via `specs/utils/dbt_manifest_parse.md` Steps 1–2 — nested/multi-project aware, hard-fail on an unresolvable path — rather than assuming a single project sits directly at that path. Where a model or macro's manifest node is needed below, locate it by its project-qualified node ID (`model.<package_name>.<model_name>` / `macro.<package_name>.<macro_name>`) in whichever resolved project's manifest contains it.

### Step 1 — Resolve scope and pair
Determine the lint scope:
- `--macros` provided: this is not a model scope — skip Steps 2–4 below and run **Macro Mode** instead.
- `--wave <id>` provided: resolve the model set per **Step 1w**.
- `--model <name>` provided: lint that single model.
- `--batch N` provided: load all models with `batch_number = N` from `dbt_audit.csv`.
- Otherwise: read `current_batch` from status.md.

`--wave` and `--batch` read different numbering schemes (the authoritative execution schedule vs. the topological micro-batch) — never combine them; see Flags.

Resolve the platform pair from status.md (or the `--config` overlay). Load the pair's `feature_detection.md`, `translation_reference.md`, and any engagement `lint_rules.md` overrides. Detect whether `sqlglot` is importable; pick the engine and note it.

### Step 1w — Resolve `--wave` (only when `--wave` is used)

Identical resolution to `dbt_migration-generate`'s Step 1w — the two commands must never disagree about what a given wave id resolves to:

1. Normalise the wave id: zero-padded (`B01`) or bare (`1`) both resolve to the same `batch_id`, e.g. `B01`. Reject anything else.
2. Load `migration/migration_batching.csv`; abort if missing (`run /wire:migration-batching-generate $ARGUMENTS first`).
3. Filter to rows where `batch_id` matches the normalised wave id and `object_type` indicates a dbt model (`dbt_model`). Abort if the wave id matches no rows at all; print-and-stop cleanly (not an error) if it matches rows but none are dbt-model rows.
4. Cross-reference each matched `object_id` against `dbt_audit.csv`'s `model_name` to resolve the actual model set (and its `file_path` for locating the translated SQL). List, rather than silently drop, any `object_id` with no matching audit row.
5. Print the resolved model-count preview before lint runs, same posture as a `--batch` run.

The resolved model list flows into Step 2 unchanged. Where Step 3 below names the report file with the batch number `N` (`batch_N_lint.md`), substitute the wave id (`wave_B01_lint.md`) when the scope is `--wave`.

### Step 2 — Per-model lint
For each model in scope:
1. Strip/render Jinja; obtain the largest parseable SQL (compiled artifact if available).
2. **Parse-check** in the target dialect → `PARSE` rule on failure.
3. Run every rule for the active direction, plus the direction-agnostic rules. AST rules read the tree; regex rules apply the pattern; config rules (`MATERIALIZATION_DRIFT`) compare the translated model's config against the source manifest and the declared overrides; `CLUSTER_BY_ORDER_BY_CONFLICT` reads the resolved `cluster_by`/`materialized` config the same way and then tracks paren depth over the compiled SQL to find a real top-level trailing `ORDER BY`; `UNPINNED_SELECT_STAR` tracks paren depth the same way to find an unpinned star in the depth-0 output projection. Each hit records: `model`, `rule_id`, `severity`, line/span, the offending snippet, the fix hint, and the `translation_reference.md` section.
4. Where a rule has a deterministic rewrite and sqlglot is present, attach the suggested fix (informational).

### Step 3 — Write the report
Write `migration/lint/batch_N_lint.md` (and `.json` if `--format json`) — or `migration/lint/wave_{id}_lint.md` when the scope is `--wave`. Structure:
- **Header**: engine used, direction, batch (or wave id), model count, the "Tier 1 — not an equivalence pass; Tier 3 still required" disclaimer.
- **Summary**: counts by severity; models clean vs flagged.
- **Findings**: grouped by model, ordered by severity. Each finding shows snippet, fix hint, and reference link.
- **Coverage gaps**: models that could only be partially parsed (heavy Jinja, no compiled artifact), so a clean result there is "not fully checked", not "clean".

### Step 4 — Update status
```yaml
artifacts:
  dbt_migration:
    lint: pass | fail
    linted_date: "{{TODAY}}"
    batch_N_lint: pass | fail
    batch_N_lint_findings:
      error: <n>
      warn: <n>
      info: <n>
    wave_lint:                    # set only when run with --wave, keyed by wave id
      B01: pass | fail
```
`fail` when any `error`-severity finding remains unresolved (warn/info do not fail the gate by default; `--severity` can tighten this for CI).

## Macro Mode (`--macros`)

Runs instead of Steps 1–4 above when `--macros` is supplied. Mirrors `dbt_migration-generate`'s `--macros` batch-zero pass: that command's compile check confirms a translated macro *compiles*, but never runs this command's static dialect/behaviour-change rule catalogue against it — a translated macro gets compile-validation without ever getting the same silent-divergence scrutiny a model gets. This mode closes that gap.

### Macro Step 1 — Resolve macro scope and pair
Point the rule engine at the translated macro files under `migration/dbt/macros/` (the exact output tree `dbt_migration-generate --macros` writes, mirroring the source project's `macros/` subdirectory structure per that command's Macro Mode Workflow) instead of the model tree under `migration/dbt/`. Resolve the platform pair and load `feature_detection.md` / `translation_reference.md` / engagement `lint_rules.md` overrides exactly as Step 1 does for models. Detect the before/after pair from the source project's `macros/` tree at the same relative path (resolved per Step 0), the macro equivalent of the model before/after pair.

### Macro Step 2 — Per-macro lint
For each translated macro file:
1. Strip/render Jinja around the macro body; obtain the largest parseable SQL span (a macro is a template, not a standalone statement, so expect more coverage gaps here than for models — note them the same way).
2. **Parse-check** in the target dialect where the macro body is parseable SQL → `PARSE` rule on failure.
3. Run the same rule catalogue used for models — every rule in **Rule catalogue** applies identically to a macro body; there is no separate macro rule set. `MATERIALIZATION_DRIFT` does not apply (macros carry no `config.materialized`); skip it here.
4. Record findings in the same shape as Step 2 for models: `macro` (in place of `model`), `rule_id`, `severity`, line/span, snippet, fix hint, reference section.

### Macro Step 3 — Write the report
Write `migration/lint/macros_lint.md` (and `.json` if `--format json`), same structure as Step 3 for models, with "macro" in place of "model" throughout and the tier (from `batch_zero_plan.json`) shown alongside each macro.

### Macro Step 4 — Update status
```yaml
artifacts:
  dbt_migration:
    macros_lint: pass | fail
    macros_linted_date: "{{TODAY}}"
    macros_lint_findings:
      error: <n>
      warn: <n>
      info: <n>
```

## CI gating

With `--format json --severity error`, the command exits non-zero when any `error` finding exists, so it drops into a pre-merge check on the migration repo. The intent is to stop a translated batch (or, in `--macros` mode, a translated macro pass) reaching the (paid) Tier 3 parallel run while it still carries a known silent-divergence pattern. Document any rule deliberately suppressed for a batch in the batch summary, the same way `-- MANUAL REVIEW` flags are tracked — silent suppression reads as "clean" when it isn't.

## Notes for the implementer

- The rule catalogue is the contract; `translation_reference.md` §11 is the prose behind it. When the reference gains a gotcha, add a rule here with the same section ref — keep them in lockstep.
- Prefer AST over regex for anything with arguments (`DATEDIFF_ARGORDER`, `LOG_ARGORDER`, `ARRAY_AGG_NULLS`). Regex versions are a fallback and should be conservative — a false `error` that blocks CI is worse than a missed `warn`.
- This command is read-only over the translated SQL. It never edits models. Fixes flow back through `dbt_migration-generate` (re-translate) or a hand edit, then re-lint.

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
