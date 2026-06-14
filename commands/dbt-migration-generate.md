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

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.5\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"dbt-migration-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.5\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Translate dbt models batch by batch to target dialect
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

---

# dbt Migration — Generate

## Purpose

Translates dbt models from the source platform dialect to the target platform dialect — both the model `.sql` **and the companion schema/properties YAML** (`schema.yml` / `_models.yml` / `sources.yml`). Works in batches as defined in the dbt audit. Each batch is translated, tested, and reviewed before the next begins. Supports `--batch N` to process a specific batch and `--model <name>` to process a single model.

## Prerequisites

- `ingestion_migration review: approved`
- `audit/dbt_audit.csv` exists with batch assignments

## Flags

- `--batch N` — process batch number N only
- `--model <name>` — process a single model by name (overrides batch)
- No flag — process the next incomplete batch (read from status.md `dbt_migration.current_batch`)

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
   - If `--model <name>` provided: process that single model
   - If `--batch N` provided: load all models with `batch_number = N` from `dbt_audit.csv`
   - Otherwise: read `dbt_migration.current_batch` from status.md (default: 1 if not set)
3. Confirm the batch/model has not already been translated (check for existing translated files). If already done, ask whether to re-translate.

### Step 2: Load translation context

Read the translation guide for the active platform pair. For the models in this batch, identify which feature tags are present and load the corresponding translation patterns.

### Step 3: Translate each model

For each model in the batch:

1. Read the source SQL from the dbt project
2. Apply translations in this order:
   a. Data type references (inline casts, SAFE_CAST equivalents)
   b. SQL function translations (per the translation guide)
   c. Configuration block updates (adapter profile, materialisation config)
   d. Jinja macro calls that need dispatch overrides
3. Write the translated SQL to `.wire/releases/$ARGUMENTS/migration/dbt/{model_name}.sql`
4. Write a side-by-side diff to `.wire/releases/$ARGUMENTS/migration/dbt/{model_name}.diff.md` showing source → target changes

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

Write the translated YAML alongside the model: `.wire/releases/$ARGUMENTS/migration/dbt/{model_name}.yml` (or the shared `sources.yml` / `_models.yml` as it is structured in the source project). Note any `sources.yml` repoint, custom-test translation, or `policy_tags` authored in the model's diff file and the batch summary.

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

If `--model` flag was used, update only the specific model's status. Do not advance `current_batch`.

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

- `.wire/releases/$ARGUMENTS/migration/dbt/{model_name}.sql` (for each model)
- `.wire/releases/$ARGUMENTS/migration/dbt/{model_name}.yml` (companion schema/properties YAML where the model has one; plus translated `sources.yml` / shared properties files)
- `.wire/releases/$ARGUMENTS/migration/dbt/{model_name}.diff.md` (for each model — covers `.sql` and `.yml` changes)
- `.wire/releases/$ARGUMENTS/migration/dbt/batch_{N}_summary.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

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
