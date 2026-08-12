---
description: Sync-level equivalence — old sync vs target twin at the sync grain (PK row set + changed-field hashes), tier-2 decoy diff where possible; promotion requires a tier-1 pass
argument-hint: <release-folder> [--syncs name1,name2] [--tier N]
---

# Sync-level equivalence — old sync vs target twin at the sync grain (PK row set + changed-field hashes), tier-2 decoy diff where possible; promotion requires a tier-1 pass

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
description: Sync-level equivalence — verify a repointed reverse-ETL sync would write the same rows to its destination, at the sync grain, before its promotion PR merges
argument-hint: <release-folder> [--syncs name1,name2] [--tier 1|2]
---

## Data Safety — Read Before Proceeding

Tier 1 reads both warehouses, SELECT only. Tier 2 runs syncs against **decoy destinations only** — the decoy ID-mapping table and scoped credential from `reverse-etl-migration`'s validation posture; production destination IDs are never present. If any step would run a sync against a production destination, stop and report.

---

# Reverse ETL Equivalency — Validate

## Purpose

Model equivalency proves the warehouse tables match; nothing proved a **repointed sync writes the same rows to its destination**. The register's sync rows carried no real equivalence result, and the gap was flagged to a client as an assurance hole at cutover (#179 item 5). This command closes it with a two-tier comparison, verdicts in the same taxonomy as models, and a gate the promotion flow consumes.

Like `equivalency-validate`, this is a repeatable loop command, not a generate/validate/review artifact.

## Prerequisites

- `reverse_etl_audit` complete (the sync inventory, each sync's model resolved)
- The target-side twin exists for each in-scope sync (`reverse-etl-migration` authored it)

## Workflow

### Step 1 — Resolve scope

Every migrated sync pair (old sync on the source warehouse, twin on the target warehouse) from the reverse-ETL audit and migration outputs; `--syncs name1,name2` narrows. Under `migration.scope == tenant_carveout`, each sync's model resolves its filter from the tenant predicate registry exactly as models do — an `unresolved` sync is verdict `fail`, reason `unresolved_predicate`, never compared unfiltered.

### Step 2 — Tier 1: model-output comparison at the sync grain (no destination access needed)

Per sync pair, run the OLD sync's model query against the source warehouse and the NEW twin's against the target warehouse, under the same pinned-vintage discipline as model equivalence (a pinned as-of, or the baseline `T`), and compare **at the sync grain**:

- **Row set by primary key** — the sync's configured PK. Every key present on exactly both sides; missing/extra keys are named.
- **Changed-field hashes** — per row, hash the synced field set (the sync's field mapping, canonically ordered and normalised per the equivalency edge-case rules). A key present on both sides with differing hashes is a differing row, named by key and field.

This is a real verdict on "would the destination receive the same rows": the destination write is a function of the model output and the field mapping, both of which this compares. Verdicts use the model taxonomy (`pass`, `pass_qualified` via the pair allow-list or a known-difference entry, `diff_*` with a named mechanism, `fail`). Tests mirror the comparison: `wire/tests/platform_migration/validate_reverse_etl_equivalency.py`.

### Step 3 — Tier 2: decoy-destination diff (where the destination or its API allows)

Run the twin against the **decoy** destination, export or read back what landed, and compare it to the tier-1 expectation. Tier 2 catches what tier 1 cannot — destination-side transformation, API-level field coercion — and is run where the destination offers a read-back path; where it does not, the verdict rests on tier 1 and the report says so. Tier 2 never runs against a production destination.

### Step 4 — Verdicts, register, and log

Each sync's verdict appends to `migration/migration_verdict_log.csv` (`object_type: reverse_etl_sync`, same single-writer merge as model lanes, per `specs/migration/equivalency/verdict_schema.md`) and updates the sync's register row where one exists — sync rows carry a **real** `last_equivalence_result` from here on; the status table's `n/a` disappears wherever tier 1 has run.

### Step 5 — Gate integration

Sync promotion (the reverse-ETL cutover PRs, or `dbt-migration-batch-raise` deriving sync twins) requires **tier-1 `pass`** for every sync in the batch — a sync's output leaves the warehouse by definition, so the external-exactness rule applies (`pass_qualified` is not sufficient). Go-live remains the client's call; this gate governs what RA raises, not what the client merges.

### Step 6 — Report and status

`.wire/releases/$ARGUMENTS/migration/reverse_etl_equivalency_report_{run_number}.md`: per sync — tier(s) run, PK counts both sides, missing/extra/differing keys (named), verdict. Update status:

```yaml
artifacts:
  reverse_etl_equivalency:
    last_run_date: "{{TODAY}}"
    syncs_checked: N
    tier1_pass: N
    tier2_run: N
    failing: N
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_equivalency` as artifact, `validate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_equivalency` as artifact, `validate` as action.

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
