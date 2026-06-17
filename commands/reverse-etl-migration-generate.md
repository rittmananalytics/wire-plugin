---
description: Generate Hightouch sync migration runbook — repoint, rewrite, rebuild
argument-hint: <release-folder>
---

# Generate Hightouch sync migration runbook — repoint, rewrite, rebuild

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
description: Generate Hightouch reverse ETL migration runbook — build a parallel target workspace (or re-point in place), translate models, and validate by preview before enabling syncs
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: reverse_etl_migration` and `artifact_file_path: migration/reverse_etl_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before modifying any Hightouch configuration, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source platform ([source_platform]): READ ONLY.
  Do NOT modify, disable, or re-point any source-backed Hightouch syncs.
  The source workspace and its syncs remain active as the rollback path
  throughout this entire phase.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not create syncs pointing to these):
  [list each production project ID]
```

If any action would modify the source Hightouch workspace, disable a live production sync, or create a sync pointing to a production project listed in `data_safety.production_projects`, stop and report the conflict before proceeding.

---

# Reverse ETL Migration — Generate

## Purpose

Generates a step-by-step runbook for migrating every in-scope Hightouch sync from the source warehouse to the target warehouse. The preferred topology is a **parallel workspace**: clone the Hightouch config into a new workspace pointed at the target warehouse, validate it with syncs disabled, then enable — leaving the production source-backed workspace untouched until cutover. For plans that do not support multiple workspaces, the runbook falls back to an **in-place re-point** of the existing syncs. Either way the runbook covers model SQL translation, Customer Studio rebuilds, Lightning schema provisioning, sync-level transformation review, and a preview-based validation procedure run against a frozen source baseline before any sync is enabled.

## Prerequisites

- `target_setup review: approved` — target warehouse schemas and objects exist
- `reverse_etl_audit review: approved`
- `dbt_migration: complete` for any batch containing models referenced by Hightouch dbt-type syncs (cannot validate those syncs until their dbt models exist on target)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Confirm prerequisites

Confirm `target_setup review: approved`. Confirm `reverse_etl_audit review: approved`. If `dbt_migration` exists, confirm which batches are complete and note which rewrite_model and dbt-type syncs are unblocked.

If prerequisites are not met, output the blockers and stop.

Activate the `hightouch` skill for API connection details and the workspace / GitHub Sync model.

### Step 2: Choose the migration topology

Decide and record which topology the runbook follows. Default to the parallel workspace.

- **Parallel workspace (preferred).** Available when the Hightouch plan supports multiple workspaces (Business and above). Build a new workspace for the target warehouse and validate there, leaving the production source-backed workspace running and unmodified. This is the safer approach and the one to recommend — production syncs are never touched during build and validation, and rollback is simply "don't enable the new workspace."
- **In-place re-point (fallback).** Only when the plan does not support a second workspace. The existing syncs' source connection is re-pointed from source to target warehouse within the one workspace. Higher risk: there is no parallel environment, and the production config is mutated. If this path is chosen, record why in the runbook.

Confirm the plan tier and chosen topology with the user before continuing.

### Step 3 — Parallel workspace: build the target environment

(Skip to Step 3b if the in-place fallback was chosen.)

GitHub Sync is configured per workspace — a repository reflects one workspace's configuration, not the whole organisation. Build the parallel environment:

1. **Clone the Hightouch config repository** the production workspace syncs to; rename the clone to mark it as the target-warehouse migration workspace.
2. **Create a new Hightouch workspace** for the target warehouse environment.
3. **Configure GitHub Sync** in the new workspace to point at the cloned repository.
4. **Create the target-warehouse source connection** in the new workspace.
5. Proceed to Step 4 — model translation is committed to the cloned repo and deployed into the new workspace via GitHub Sync (or applied via the API against the new workspace's objects).

The production workspace is not modified at any point in this path.

### Step 3b — In-place fallback: prepare the re-point

For the in-place fallback only: add the target-warehouse source connection to the existing workspace alongside the source one. Syncs will be re-pointed to it per Step 4, via:

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $HIGHTOUCH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"sourceId": "<TARGET_SOURCE_ID>"}' \
  "https://api.hightouch.com/api/v1/syncs/<SYNC_ID>"
```

Rollback: re-apply the original `sourceId` via the same endpoint. Keep syncs disabled until validated (Step 5).

### Step 4: Translate models by approach

Load all syncs from the audit with `include_in_migration: true` and group by migration approach. Process repoint first (lowest risk), then rewrite_model, then rebuild. In the parallel-workspace path these changes are committed to the cloned repo and deployed via GitHub Sync; in the in-place path they are applied to the existing models.

- **repoint** — model SQL is portable; no SQL change. The model resolves against the target-warehouse source. Verify the model SQL returns rows and a non-null primary key on the target; if it fails, downgrade to `rewrite_model`.
- **rewrite_model** — translate the model SQL using the platform-pair guide (`wire/platform_pairs/<source>_to_<target>/translation_guide.md`) and feature-tag translations. Test the translated SQL on the target warehouse — row count and primary-key integrity match the source model output. Record a before/after SQL diff in the runbook. Update via GitHub commit (parallel) or `PATCH /api/v1/models/<MODEL_ID>` (in-place).
- **rebuild** — Customer Studio audiences and Journeys are rebuilt against the target-warehouse source: new schema (parent + related models + events) on the target source, recreated audience filters, recreated Journeys, sync destinations re-mapped to the rebuilt audiences. Capture the existing definitions first via the `schemas`, `audiences`, and `journeys` endpoints.

**Keep all syncs disabled, and keep destination connections present but disabled** throughout Step 4 — see Step 5.

### Step 5: Validate by model output and preview — syncs disabled

Do **not** enable destination syncs to validate. Activating them writes to live downstream systems (Salesforce, HubSpot, Iterable, Braze, ad platforms, Google Sheets). Keep the destination connections present but **disabled** and validate via Hightouch's sync previews and record-level inspection — this confirms what *would* be written without writing it, and gives higher confidence than comparing SQL output alone.

Validate against a **frozen source baseline**, not moving production — the source warehouse keeps ingesting and rebuilding, so a moving comparison surfaces timing differences, not translation differences. Use the baseline defined in the migration strategy's equivalency section (e.g. a zero-copy snapshot of the source models at a fixed cutoff); align any target-side load to the same cutoff. Per in-scope model:

1. **Model output** — compare row count, primary-key uniqueness, aggregates, and representative samples between the target model and the frozen source baseline.
2. **Audience sizes** — where Customer Studio is in scope, compare audience membership and segment counts against the baseline (default tolerance ±2%).
3. **Sync preview** — run the sync in preview / dry-run with destinations disabled; confirm the planned record count and field-level payload match expectation. No live run.

### Step 6: Review sync-level transformation logic

A matching model output does not prove a matching sync — transformation logic lives on the sync as well as in the model. For each sync, review and test: field mappings, computed fields, sync filters, match rules and identity resolution, and audience inclusion/exclusion logic. Record the review per sync in the runbook; differences here are a common source of silent divergence even when model output is identical.

### Step 7: Lightning engine provisioning

For all Lightning syncs, confirm the target warehouse has the required schemas before any sync is enabled:

```sql
-- Run on target warehouse
CREATE SCHEMA IF NOT EXISTS hightouch_planner;
CREATE SCHEMA IF NOT EXISTS hightouch_audit;

-- Grant the Hightouch service account access
GRANT USAGE ON SCHEMA hightouch_planner TO ROLE hightouch_role;
GRANT CREATE TABLE ON SCHEMA hightouch_planner TO ROLE hightouch_role;
GRANT USAGE ON SCHEMA hightouch_audit TO ROLE hightouch_role;
GRANT CREATE TABLE ON SCHEMA hightouch_audit TO ROLE hightouch_role;
```

Note: Hightouch creates the actual tables in these schemas on the first sync run. The grant only needs to be in place before that first run.

### Step 8: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_etl_migration_runbook.md`

Structure:
1. Topology decision (parallel workspace vs in-place re-point) and the rationale
2. Parallel-workspace build steps (clone repo, new workspace, GitHub Sync, target source) — or in-place re-point prep
3. Pre-flight checklist (target warehouse ready, dbt batches complete, source baseline frozen, Lightning schemas provisioned)
4. Per-sync model translation — repoint / rewrite_model (with SQL diff) / rebuild (schema mapping + steps)
5. Validation procedure — model-output comparison vs frozen baseline, audience-size comparison, sync preview with destinations disabled
6. Sync-level transformation review — per sync: field mappings, computed fields, filters, match/identity rules, audience include/exclude
7. **Sign-off and enable sequence**: recreate workspace + GitHub integration → migrate source connection → translate models → validate model outputs → validate audience sizes + sync previews → review sync-level logic → business sign-off → enable syncs → monitor initial runs → decommission the source workspace once confidence is established
8. Rollback procedures for each approach (parallel: don't enable / disable new-workspace syncs and re-enable source workspace; in-place: re-apply original `sourceId`)

Source syncs (or the source workspace) stay active and untouched as the rollback path until cutover — never deactivate them during the migration phase.

### Step 9: Update status

```yaml
artifacts:
  reverse_etl_migration:
    generate: complete
    file: migration/reverse_etl_migration_runbook.md
    generated_date: "{{TODAY}}"
    topology: parallel_workspace | in_place_repoint
    repoint_count: N
    rewrite_model_count: N
    rebuild_count: N
```

### Step 10: Output next command

```
/wire:reverse-etl-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_etl_migration_runbook.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact_id, `Reverse ETL Migration` as artifact_name, and the `file` value from `artifacts.reverse_etl_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_migration` as artifact, `generate` as action.

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
