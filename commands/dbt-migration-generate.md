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
description: Translate dbt models batch by batch to target dialect
argument-hint: <release-folder> [--batch N] [--model name] [--select selector] [--exclude selector]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_migration` and `artifact_file_path: migration/dbt/batch_1_summary.md` before proceeding.

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

Translates dbt models from the source platform dialect to the target platform dialect — both the model `.sql` **and the companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`). Works in batches as defined in the dbt audit. Normally the auto-delegation layer handles splitting a batch into parallel groups and spawning one agent per group — this spec executes on whatever scope it is handed. Supports `--batch N` to process a specific batch, `--model <name>` to process a single model, and `--models <name1,name2,...>` to process a specific subset (used by parallel agents within a batch).

## Prerequisites

- `ingestion_migration review: approved`
- `audit/dbt_audit.csv` exists with batch assignments

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
- Source dbt model SQL files **and their companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`) at `migration.dbt_project_path`
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
  - Used in addition to (and prioritised over) the canonical files. Overrides exist so teams can carry forward bespoke translations from one engagement to the next at the same client without modifying the framework.

## Workflow

### Step 1: Determine scope

1. Read `migration.dbt_project_path` and `migration.source_platform` from status.md
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

The resolved model list then flows into Step 3 (Translate each model) unchanged.

### Step 2: Load translation context

Read the translation guide for the active platform pair. For the models in this batch, identify which feature tags are present and load the corresponding translation patterns.

### Step 3: Translate each model

For each model in the batch:

1. Read the source SQL from the dbt project
2. Record the model's **relative path within the source dbt project** (e.g. `models/staging/stripe/stg_stripe_charges.sql`). This path will be mirrored in the output.
3. Apply translations in this order:
   a. Data type references (inline casts, SAFE_CAST equivalents)
   b. SQL function translations (per the translation guide)
   c. Configuration block updates (adapter profile, materialisation config)
   d. Jinja macro calls that need dispatch overrides
4. Write the translated SQL to `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path_from_models_root}` — preserving the exact subdirectory structure from the source project. For example, a source model at `models/staging/stripe/stg_stripe_charges.sql` becomes `.wire/releases/$ARGUMENTS/migration/dbt/staging/stripe/stg_stripe_charges.sql`. Do **not** flatten all models into a single directory.
5. Write a side-by-side diff to `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path_from_models_root_without_extension}.diff.md` showing source → target changes

For Complex models: add inline comments explaining each non-trivial translation decision.

**Optional automated first pass (snowflake → bigquery only)**: for mechanical, function-heavy models, translating the model's *compiled* SQL through the BigQuery Migration Service first can surface the dialect changes quickly — then port those changes back into the dbt model by hand, applying macros and config per the translation guide. Never feed raw Jinja to BQMS; it cannot parse `ref()`, `source()`, or macro calls. See `wire/platform_pairs/snowflake_to_bigquery/bqms_first_pass.md`. For small or macro-heavy projects, hand translation against the guide is usually faster than wiring up the service.

**Translation safeguards** — apply to every model, automated pass or not:

- **Confidence rating**: assign each translated model a confidence of `high`, `medium`, or `low`. `high` = only simple, table-driven replacements applied. `medium` = a pattern was applied that has engagement-specific nuance. `low` = a construct with no clean equivalent, a lossless-conversion flag, or a translation the guide marks "manual". Record it in the model's diff file and the batch summary.
- **Mandatory human review**: every `low` confidence model is flagged `-- MANUAL REVIEW` regardless of whether it compiles. Compiling is not the same as being correct.
- **Guard against silent record loss**: a translation must never quietly drop or duplicate rows. Watch the known traps — `JOIN` semantics where NULL handling differs, `QUALIFY`/window changes, implicit `DISTINCT`, and filters that behave differently on NULLs. Flag any model where row-affecting logic changed.
- **Guard against silent value drift**: do not introduce timezone assumptions, currency conversions, or precision changes that were not in the source. These are the classic hallucinated "helpful" edits. If a timestamp's timezone or a numeric's precision is ambiguous, flag `low` and leave a `-- MANUAL REVIEW` note rather than guessing.
- **Wide schemas**: for models with very large schemas or long SQL, translate in sections rather than one pass — truncation mid-model produces plausible-looking but incomplete output. Confirm the translated model has the same column count and CTE structure as the source.

### Step 3b: Translate the companion schema / properties YAML

Model `.sql` is only half the model. For each model in the batch, also migrate its schema/properties YAML — most of it is dialect-neutral and carries over unchanged, but three parts need handling and are easy to miss because they don't live in the `.sql`:

1. **Column definitions and descriptions** — dialect-neutral; copy across unchanged. Confirm the column list still matches the translated model (a dropped column in either place is a defect).

2. **`sources.yml`** — the source `database`/`schema` must resolve to the target platform's namespace (for BigQuery, `database` → GCP project, `schema` → dataset). Prefer parameterising both through `vars` so one `sources.yml` resolves on either platform during a parallel run, rather than duplicating the file per target. This is real migration work, not a copy.

3. **Tests** — generic tests (`not_null`, `unique`, `accepted_values`, `relationships`) are portable and need no change. **Singular/custom tests, `where:` filters, and `dbt_utils`/`dbt_expectations` test arguments that contain source-dialect SQL get the same translation as model bodies** (Step 3, per the translation guide). Translate them with their model — they are a common silent gap because the batch loop is "model-shaped" and these hide in YAML and in `tests/`.

4. **PII / column policy tags and `meta`** — if the engagement applies column-level protection through dbt rather than warehouse DDL (e.g. BigQuery `policy_tags` on a column, or a `meta` masking flag), that config lives in the schema YAML. When the security/target-setup workstream provisions the tag taxonomy and IDs, author the `policy_tags` references into the column YAML here so dbt applies and re-asserts them on every build. **Confirm ownership with the security-migration scope first** — column tagging is either dbt-managed (this step authors it into YAML) or warehouse-side (DDL/Terraform owns it); do not apply it in both. Where the source platform's masking has no portable YAML form, flag it `-- MANUAL REVIEW` and leave it to the security workstream.

Write the translated YAML alongside the model, preserving the same relative path: `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path_from_models_root_without_extension}.yml` (or the shared `sources.yml` / `_models.yml` in the same subdirectory as the source project). The translated output directory structure must mirror the source project exactly — not a flat dump. Note any `sources.yml` repoint, custom-test translation, or `policy_tags` authored in the model's diff file and the batch summary.

### Step 4: Generate batch summary

Write `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`:
- Models translated in this batch
- Translation patterns applied (counts by type)
- Confidence breakdown (count of high / medium / low)
- Models requiring manual review (every `low` confidence model, plus anything flagged with `-- MANUAL REVIEW` in the SQL)
- **Companion YAML changes**: `sources.yml` repoints, custom/singular tests translated, and any `policy_tags`/`meta` authored (or deferred to the security workstream)
- Recommended test commands

### Step 5: Update status

```yaml
artifacts:
  dbt_migration:
    generate: complete
    generated_date: "{{TODAY}}"
    current_batch: N
    batches_complete: [1, 2, ..., N]
    models_translated: total_count
```

If `--model` or `--select` was used, update only the translated models' status. Do not advance `current_batch`.

### Step 6: Output summary

Print: models translated in this run, count of manual review flags, and next command:

```
/wire:dbt-migration-validate $ARGUMENTS --batch N
```

If all batches are complete:
```
All N batches translated.
/wire:orchestration-migration-generate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.sql` — subdirectory structure mirrors the source dbt project (e.g. `staging/stripe/stg_stripe_charges.sql`)
- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.yml` — companion schema/properties YAML at the same relative path
- `.wire/releases/$ARGUMENTS/migration/dbt/{relative_path}/{model_name}.diff.md` — covers `.sql` and `.yml` changes
- `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`
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
