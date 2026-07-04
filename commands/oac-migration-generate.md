---
description: Generate OAC migration runbook — translate physical-layer connection and joins, two-stage connection repoint
argument-hint: <release-folder>
---

# Generate OAC migration runbook — translate physical-layer connection and joins, two-stage connection repoint

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
description: Generate the OAC reporting-layer migration runbook — add the target connection pool, translate/re-validate physical joins and raw SQL constructs on a semantic-model Git branch, validate against a non-production copy of the repo, two-stage connection cutover with rollback
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: oac_migration` and `artifact_file_path: migration/oac_migration_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

Before modifying any OAC configuration, read `data_safety` from status.md and output this reminder:

```
⚠️  DATA SAFETY REMINDER

Source warehouse ([source_platform]): READ ONLY.
  Do NOT delete or repoint the production connection pool during the
  migration phase. The existing [source_platform] connection pool stays
  live as the rollback path until cutover.

Validation runs against a GIT BRANCH of the semantic-model repo, imported
  into a NON-PRODUCTION copy of the OAC environment. Production physical
  tables, subject areas, and their consumers are never touched during
  validation — because the logical and presentation layers are FQN-based
  and dialect-neutral, they resolve against whatever the physical layer
  points at automatically once the branch is merged, not before.

Target writes go to: [data_safety.target_project or migration.target_project]

[If data_safety.production_projects is non-empty:]
BLOCKED production projects (do not point any connection pool at these):
  [list each production project ID]
```

If any action would repoint or delete the production connection pool outside the cutover sequence, or run validation against a production OAC environment, stop and report the conflict before proceeding.

---

# OAC Migration — Generate

## Purpose

Generates the runbook for migrating the client's OAC reporting layer from the source warehouse to the target. The pivot is the **OAC connection pool** — the migration adds a target connection pool, translates the physical layer's raw SQL constructs by approach on a **Git branch of the semantic-model repo**, validates the branch by importing it into a **non-production copy of the OAC environment**, then merges the branch and cuts over the primary connection pool in **two stages with per-stage rollback**.

This is a **reporting-layer** migration, the OAC counterpart to Metabase and Omni migration. It is **not gated by `migration.scope`** — it runs for any migration where the client uses OAC.

Because SMML is committed to an ordinary Git repository, branching this migration's translation work is just Git branching — no special OAC feature is required to create it, unlike Omni's own in-product model-branch object. What is **not confirmed** by `wire/skills/smml-semantic-modeling/references/smml-schema.md` or the modeling-patterns reference is exactly how a given OAC environment picks up a specific branch for import (whether that's a dedicated non-production OAC instance pointed at the branch, a manual re-import in OAC Semantic Modeler, or some other mechanism specific to the client's OAC setup). This runbook therefore describes validation generically as **"a non-production copy of the semantic-model repo, imported into a non-production OAC environment"** rather than asserting a specific branch-to-environment feature — confirm the exact mechanics against the client's actual OAC setup before running Stage 1.

### Client-supplied inventory — judgement call

Metabase migration hard-blocks without a client-supplied card/SQL inventory, because Metabase's dialect-specific SQL is scattered across individually-authored native-SQL cards and inferring which ones are safe to translate isn't reliable at scale. OAC's physical layer doesn't have the same problem: dialect-specific SQL concentrates in a bounded set of physical tables and joins maintained by a small modeling team, and `oac_audit` already scans **every** physical table and every physical-layer raw SQL construct exhaustively, not a sample.

OAC's story is actually simpler than Omni's here: Omni versions its model and its dashboard content separately, so a raw-SQL tile can drift out of sync with the audit between commands. SMML has no equivalent split — physical, logical, and presentation layers all live in the **same** Git-versioned tree, so there is nothing that can change independently of a commit to that repo. This command does **not** hard-block on a separate client-supplied inventory the way Metabase does, and does not need Omni's live-recount reconciliation either. It does require pulling the semantic-model repo to its latest commit before translation starts (Step 1) and comparing physical table / raw SQL construct counts against `oac_audit`'s recorded counts — if the repo has moved since the audit ran, that's a straightforward Git diff to reconcile, not a drift risk hidden behind a separately-versioned surface.

## Prerequisites

- `target_setup review: approved` — target warehouse objects exist
- `oac_audit review: approved`
- `dbt_migration: complete` for any batch containing models referenced by in-scope physical tables
- Write access to the semantic-model Git repo (ability to create a branch and push commits)

## Inputs

- `.wire/releases/$ARGUMENTS/audit/oac_audit.md`
- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/status.md`
- Canonical platform pair files at `wire/platform_pairs/<source>_to_<target>/` (translation guide, type mapping)

## Workflow

### Step 1: Confirm prerequisites and reconcile the semantic-model repo

Confirm `target_setup review: approved` and `oac_audit review: approved`. Confirm `dbt_migration` batches referenced by in-scope physical tables are complete.

Activate the `smml-semantic-modeling` skill for schema reference. Pull `migration.oac_smml_repo_path` to its latest commit and recount physical tables and raw SQL constructs. Compare against `physical_table_count` and `raw_sql_construct_count` in `artifacts.oac_audit` (status.md). If they differ, stop:

```
The semantic-model repo has moved since the last audit (audit: N physical
tables / M constructs, current: N' / M'). Re-run /wire:oac-audit-generate
$ARGUMENTS to refresh scope, then re-run:
/wire:oac-migration-generate $ARGUMENTS
```

### Step 2: Add the target connection pool additively

Determine the target `databaseType` value for the new connection pool. Consult `smml-schema.md`'s `DatabaseType` enum first — but note that its list, taken from Oracle's F38574-15 JSON Schema, does **not** include a `BIGQUERY` value despite BigQuery being an OAC-supported connector. If the target platform's `databaseType` is not confirmed in the schema reference, verify the correct value directly against a live OAC Semantic Modeler's "Create Database" dialog or current Oracle connector documentation before setting it — do not guess a value from adjacent entries.

Add a new `database`/`connectionPool` entry for the target platform in `physical/<Database>.json` (or a new `physical/<New Database>.json` if the target uses a distinct database object), alongside the existing source database. This is additive — the source database and its connection pool stay in place and are not touched again until Stage 2.

### Step 3: Create a Git branch for translation work

Create a feature branch of the semantic-model repo (e.g. `migration/<release>-<target_platform>`). All physical-layer edits for this migration happen on the branch; the repo's main branch — whatever the production OAC environment imports from — is untouched until the branch is merged (Step 7).

### Step 4: Translate physical tables and raw SQL constructs by approach

Load the physical table catalog and the raw SQL construct catalog from `oac_audit` and process `repoint` first, then `rewrite_sql`, then `rebuild`, on the branch:

- **repoint** — `TABLE`-sourced physical tables with condition-based joins only: point the table (via its schema placement, or an explicit connection reference where SMML requires one) at the target connection pool on the branch. Verify column types still map cleanly using the platform-pair type mapping; if a `repoint` table fails, downgrade it to `rewrite_sql`.
- **rewrite_sql** — for each attached raw SQL construct classified `translate` in the audit (an expression-based join's `physicalExpression.expressionTemplate`, a `SELECT`/procedure-sourced table's SQL text, or a non-identity physical mapping expression), translate the SQL from the source dialect to the target using the platform-pair guide (`wire/platform_pairs/<source>_to_<target>/translation_guide.md`). Record a before/after SQL diff per construct in the runbook.
- **rebuild** — physical tables with an attached construct classified `redesign` are rebuilt against the target connection pool on the branch (e.g. replacing a UDF-backed `SELECT` with an equivalent target-platform routine, or restructuring an expression-based join as a plain condition-based join where the target's join key allows it); capture the original definition first.

**`manual-review-out-of-scope` constructs don't get mechanically translated.** Connection-pool scripts and other session/catalog operations flagged this way in the audit are called out in their own runbook section for the client or DBA to reauthor natively against the target connection pool — not translated construct-by-construct the way `translate`/`redesign` items are.

### Step 5: Refresh physical column metadata against the target connection

Once the new connection pool's details are set, use the OAC Semantic Modeler's physical-layer reimport/refresh action against it to confirm column presence and data types match what `smml-schema.md`'s `physicalColumn` shape expects, before validating joins on the branch. Note: unlike Omni's scriptable `omni-admin` schema refresh, the skill docs don't confirm a scripted equivalent for OAC — treat this as a manual Semantic Modeler step against the branch's physical layer, not an automated one, until a client-specific tool confirms otherwise.

### Step 6: Stage 1 — validate the branch against a non-production copy of the semantic-model repo

Import the branch into a non-production copy of the OAC environment (see the topology caveat above — confirm the exact mechanism with the client's OAC setup). Run each translated/rebuilt physical table's underlying query against the target connection pool and compare row count, key columns, and aggregates against a **frozen source baseline** (not moving production), per the migration strategy's equivalency section. For `manual-review-out-of-scope` constructs, confirm the client-side reauthoring has been applied to the non-production connection pool's script hooks and executes without error.

Nothing is promoted or repointed at this stage. If validation fails for a physical table or construct, iterate the translation on the branch and re-validate; the repo's main branch and the primary connection pool are untouched throughout.

**Rollback (Stage 1):** abandon or delete the branch, and tear down the non-production OAC import. The primary connection pool was never touched, so there is nothing else to revert.

### Step 7: Stage 2 — merge the branch and repoint the primary connection pool

Once Stage 1 validation passes:

1. **Merge the branch** into the repo's main branch (the one the production OAC environment imports from).
2. **Re-import the merged model** into the production OAC Semantic Modeler, per however the client's OAC environment picks up the repo's main branch.
3. **Repoint the primary connection pool** from source to target, so the merged model's physical tables resolve against the target warehouse in production. Because the logical and presentation layers reference physical columns by FQN, they need no edits of their own — they resolve against the target automatically once the physical tables underneath do.
4. **Apply the `manual-review-out-of-scope` reauthoring** confirmed in Stage 1 to the production connection pool's script hooks.

**Rollback (Stage 2):** revert the merge commit on the repo's main branch and re-import the pre-merge state into the production OAC environment; repoint the primary connection pool back to the source connection pool's details; restore any production connection-pool scripts from the saved before-state.

### Step 8: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/oac_migration_runbook.md`

Structure:
1. Topology and rationale (additive target connection pool + Git branch; connection pool is the cutover pivot; logical/presentation layers untouched since they're FQN-based; explicit caveat on the unconfirmed branch-to-environment import mechanism)
2. Build steps (add target connection pool — including the `databaseType` verification note — create the Git branch)
3. Pre-flight checklist (target objects exist, dbt batches complete, oac_audit approved, semantic-model repo reconciled to its latest commit, source baseline frozen, non-production OAC environment available)
4. Per-physical-table translation — repoint / rewrite_sql (with SQL diff per construct) / rebuild (with rebuild plan)
5. `manual-review-out-of-scope` construct table — construct, owning connection pool, required reauthoring, owner, applied at Stage 2
6. Branch validation procedure — Stage 1 result comparison against a frozen baseline, on the non-production OAC copy
7. **Two-stage cutover sequence with per-stage rollback**:
   - **Stage 1 — branch validation on a non-production copy of the semantic-model repo.** Validate translated/rebuilt physical tables against a frozen baseline. **Rollback:** abandon/delete the branch and the non-production import; the primary connection pool and production OAC environment are untouched.
   - **Stage 2 — merge the branch and repoint the primary connection pool.** Merge to main, re-import into production OAC, repoint the primary connection pool from source to target, apply confirmed manual-review reauthoring. **Rollback:** revert the merge commit and re-import the pre-merge state, repoint the connection pool back to the source connection pool's details, restore connection-pool scripts from the saved before-state.
8. Rollback procedures consolidated per stage, with the exact connection pool details and repo state needed to revert each.

The source connection pool stays live and untouched until Stage 2, and remains the rollback path through Stage 2.

### Step 9: Update status

```yaml
artifacts:
  oac_migration:
    generate: complete
    file: migration/oac_migration_runbook.md
    generated_date: "{{TODAY}}"
    repoint_count: N
    rewrite_sql_count: N
    rebuild_count: N
    manual_review_construct_count: N
    semantic_model_branch: "{{BRANCH_NAME}}"
    repo_reconciled: true
    target_database_type: "{{DATABASE_TYPE}}"
    target_database_type_confirmed: true | false
```

### Step 10: Output next command

```
/wire:oac-migration-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/oac_migration_runbook.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_migration` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_migration` as artifact_id, `OAC Migration` as artifact_name, and the `file` value from `artifacts.oac_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `oac_migration` as artifact, `generate` as action.

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
