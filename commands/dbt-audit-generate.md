---
description: Catalog dbt models with complexity classification and feature detection
argument-hint: <release-folder>
---

# Catalog dbt models with complexity classification and feature detection

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
description: Catalog dbt models with complexity classification and feature detection
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: dbt_audit` and `artifact_file_path: audit/dbt_audit.md` before proceeding.

---

# dbt Audit — Generate

## Purpose

Catalogs every model, source, test, macro, seed, and snapshot in the dbt project. Classifies each model by complexity based on SQL feature usage, line count, and dependency depth. The audit also flags platform-specific macro usage across the macro layer and produces a batch-zero macro translation plan — the macros that must be translated before model batch 1 starts. The output drives the batching strategy for dbt_migration and the complexity weighting in the migration inventory.

## Prerequisites

- Release folder with `release_type: platform_migration` in `status.md`
- dbt project path accessible at `migration.dbt_project_path` (default: `./dbt`)

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — dbt_project_path, source_platform
- dbt project files at `migration.dbt_project_path`

## Workflow

### Step 1: Locate the release and dbt project

Confirm `release_type: platform_migration`. Read `migration.dbt_project_path` (default: `./dbt`).

Run `specs/utils/dbt_manifest_parse.md` Step 1 (project resolution). If it hard-fails, stop here with the exact blocker message it produces — do not catch the failure and fall back to a prior artifact, another release's catalogue, or any cached file.

### Step 2: Parse the dbt manifest and build dependency graphs

Run `specs/utils/dbt_manifest_parse.md` Steps 2–5. Carry forward for the rest of this workflow:

- The resolved project list (path + package name per project)
- The model dependency graph (full node IDs, enabled models only)
- The macro dependency graph (macro→macro edges)
- The per-model transitive macro-usage set

If the utility used its text-scan fallback, mark every count and ordering below as medium confidence and record the fallback in the audit's Notes, per the utility spec.

### Step 3: Inventory project components

Walk each resolved project's filesystem directly. The manifest gives dependency edges; the filesystem is the ground truth for what exists — validate's disk-reconciliation check compares the catalogue against files on disk, so do not source the model list from the manifest alone.

**Models**: For each `.sql` (or `.py`) file under `models/`:
- File path and model name
- Layer (staging, intermediate, mart — inferred from path or prefix)
- Line count
- Number of `ref()` calls (upstream dependencies)
- Number of `source()` calls
- Number of CTEs
- SQL feature tags (see Step 4)
- `enabled` — cross-reference the file's path against the manifest's model nodes: present in `nodes` → `enabled=true`; present in `disabled` → `enabled=false`; on disk but absent from the manifest entirely → flag the model for investigation in the audit output rather than silently defaulting to `enabled=true`.

**Sources**: Count and list all sources defined in `schema.yml` files.

**Tests**: Count generic and singular tests. Note which models have no tests.

**Macros**: List all macros in each project's `macros/` directory. Platform-specific flagging happens in Step 5.

**Seeds**: List all seed files with row counts.

**Snapshots**: List all snapshots with their strategy (timestamp / check).

**Analyses**: List any files in `analyses/`.

### Step 4: Detect platform-specific SQL features per model

For each model SQL file, apply the feature detection patterns from the platform pair file:

- BigQuery source: load `wire/platform_pairs/bigquery_to_snowflake/feature_detection.md`
- Snowflake source: load `wire/platform_pairs/snowflake_to_bigquery/feature_detection.md`

Tag each model with every feature pattern that matches. A model with no matches gets an empty tag list.

### Step 5: Detect platform-specific SQL in the macro layer

For every macro file across all resolved projects' `macros/` directories — plus any shared macros directory referenced in a `dbt_project.yml` `macro-paths:` entry or a sibling `shared/macros` directory — apply the same feature-detection patterns from Step 4 (including the macro-layer patterns: `create_function_udf`, `object_agg`, `within_group`, `colon_path`, `ilike`, `ilike_any`, `like_all`, `rlike`, `regexp_substr_multiarg`) to the macro's SQL body. Any macro with at least one hit joins the **NEEDS-translation set**.

Classify each NEEDS macro's `action`:

- `translate` (default) — a target-platform equivalent exists; the macro is rewritten in the batch-zero pass.
- `redesign` — no direct equivalent (e.g. a Snowpark or JavaScript UDF with no BigQuery analogue). Needs an architectural decision — surface at the human review gate, do not tier it.
- `manual-review-out-of-scope` — source-platform session, catalog, or dev-tooling operations (`ALTER SESSION`, external-table refresh, clone/drop schema and the like). Not model-build SQL; no target equivalent as written.

Treat the pattern match as a **shortlist**, then apply judgement per macro body to assign `action` and a coarse `category` tag (e.g. scalar-function, VARIANT/OBJECT_CONSTRUCT, fn_-UDF, ILIKE/RLIKE). This is feature-detection-rules-plus-review, not a one-shot mechanical scan. Record in the audit's Notes that the classification is a single specialist-pass read of every macro body — a floor count, not independently re-verified.

For every model, intersect its transitive macro-usage set (from Step 2) with the NEEDS set to populate that model's `platform_macros` value: comma-separated macro names, blank if none. Per the `dbt_manifest_parse.md` Step 5 caveat, schema-qualified UDF calls in model SQL are invisible to this intersection — `platform_macros` and any macro model-reach count is a floor for those macros.

### Step 6: Classify complexity

Assign each model a complexity rating:

**Simple**:
- ≤100 lines
- 0 platform-specific feature tags
- ≤3 upstream refs
- No window functions or recursive CTEs

**Moderate**:
- 101–300 lines, OR
- 1–3 platform-specific feature tags, OR
- 4–10 upstream refs, OR
- Uses window functions but no nested STRUCT/ARRAY operations

**Complex**:
- >300 lines, OR
- >3 platform-specific feature tags, OR
- >10 upstream refs, OR
- Uses UNNEST, STRUCT, FLATTEN, LATERAL, ML functions, or GEOGRAPHY operations

### Step 7: Build migration batches

Order buildable (`enabled=true`) models via a **topological sort** (Kahn's algorithm or DFS-based) over the model dependency graph from Step 2. Do not use `ref_count` or a depth-then-pack heuristic — `ref_count` is a count, not an edge, and the heuristic it drove produced hundreds of forward-reference violations. Every model's `ref()` parents must sit in an earlier-or-equal batch.

Sort key when multiple valid orderings exist:

1. A project that is `source()`'d by another resolved project sorts before the project that reads it
2. Topological layer (leaf-first depth in the dependency graph)
3. Simple before Moderate before Complex
4. Name

Pack into batches of at most 20 models, preserving that order. A parent and its child may share a batch — dbt builds in dependency order within a run, so this is safe; do not fragment into smaller batches just to force strict parent-in-an-earlier-batch.

Assign each buildable model a `batch_number` (1-indexed). Disabled models get a **null** `batch_number` and are excluded from batching, but remain catalogued.

Count forward references in the result (a model whose graph parent sits in a later batch). This should be 0 — state the count in the audit's Notes.

### Step 8: Generate the batch-zero macro translation plan

Restrict the macro dependency graph (from Step 2) to the NEEDS-translation set from Step 5, then compute tiers:

- **Tier 0** — NEEDS macros with no NEEDS-macro dependency
- **Tier N** — NEEDS macros that depend only on tiers <N

`redesign` and `manual-review-out-of-scope` macros are listed in their own buckets and get no tier.

Write:
- `.wire/releases/$ARGUMENTS/audit/batch_zero_plan.json` — from `TEMPLATES/migration/batch_zero_plan.json`
- `.wire/releases/$ARGUMENTS/audit/batch_zero_macro_plan.md` — from `TEMPLATES/migration/batch_zero_macro_plan.md`

Mark the output **provisional**, and carry both caveats into the markdown output's caveat callout: (1) the classification is a single specialist-pass read — a floor count, not independently re-verified; (2) schema-qualified UDF calls in model SQL are invisible to the scan, so UDF-layer model-reach figures and dependency edges understate reality.

State the rule in the plan: translate all of tier 0 (any order), then tier 1, then tier 2, etc. — entirely before model batch 1 begins. A widely-used macro can be referenced by 200+ models scattered across every batch; it must be rewritten once, up front.

### Step 9: Write the audit report and CSV

**Output locations**:
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md` — narrative report with summary statistics
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv` — machine-readable model catalog

Use the templates at `TEMPLATES/migration/dbt_audit.md` and `TEMPLATES/migration/dbt_audit.csv`.

The CSV must contain:
`model_name, file_path, layer, line_count, ref_count, source_count, cte_count, complexity, feature_tags, batch_number, has_tests, migration_notes, enabled, platform_macros`

### Step 10: Update status

```yaml
artifacts:
  dbt_audit:
    generate: complete
    file: audit/dbt_audit.md
    generated_date: "{{TODAY}}"
    model_count: N
    enabled_count: N
    disabled_count: N
    simple_count: N
    moderate_count: N
    complex_count: N
    batch_count: N
    macro_count: N
    macros_needing_translation_count: N
    batch_zero_plan: audit/batch_zero_plan.json
    source_count: N
    test_count: N
```

### Step 11: Output summary

Print: total models, breakdown by complexity, disabled-model count, number of batches, macros needing translation, confirmation the batch-zero plan was generated, most common feature tags, and next command:

```
/wire:dbt-audit-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/audit/dbt_audit.md`
- `.wire/releases/$ARGUMENTS/audit/dbt_audit.csv`
- `.wire/releases/$ARGUMENTS/audit/batch_zero_plan.json`
- `.wire/releases/$ARGUMENTS/audit/batch_zero_macro_plan.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_audit` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_audit` as artifact_id, `dbt Audit` as artifact_name, and the `file` value from `artifacts.dbt_audit` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_audit` as artifact, `generate` as action.

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
