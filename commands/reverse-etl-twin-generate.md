---
description: Author the target-warehouse twin config per in-scope sync — additive, paused, decoy-pointed, model translated, manifest keyed on the normalised sync id
argument-hint: <release-folder> [--wave id] [--syncs a,b] [--dry-run]
---

# Author the target-warehouse twin config per in-scope sync — additive, paused, decoy-pointed, model translated, manifest keyed on the normalised sync id

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
description: Author the target-warehouse twin config for each in-scope reverse-ETL sync — additive, paused, decoy-pointed, model translated, with a manifest keyed on the normalised sync id
argument-hint: <release-folder> [--wave id] [--syncs a,b] [--dry-run]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: reverse_etl_twin` and `artifact_file_path: migration/reverse_etl_twin_manifest.csv` before proceeding.

---

## Data Safety — Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command WRITES config files. Three things it never does:

  1. It never modifies an existing sync's config file. The existing
     source-warehouse sync is the rollback path until cutover.
  2. It never writes a production destination id into a twin. Twins carry
     decoy ids only, and the decoy must be the same destination type.
  3. It never enables or unpauses a sync. Every twin is authored paused.
     Enabling is the client's decision and is not a command's side effect.

Target warehouse: [migration.target_project]
```

If any step would modify an existing sync file, write a production destination id, or set a twin to enabled, stop and report the conflict before writing anything.

---

# Reverse ETL Twin — Generate

## Purpose

`reverse-etl-migration-generate` produces the plan: topology, target source connection, decoy mapping, the additive first PR. Nothing then wrote the copies. On one engagement, **575 of 643 twins were written by hand**, one file at a time, across unmerged branches — the single largest cost in the reverse-ETL path and the only step in the sequence with no command behind it. Because nothing generated them, nothing validated them either: a later by-hand sweep of 621 branch copies found 22 with an upper-case `primaryKey`, each of which would have run successfully and sent nothing.

This command authors the twins. It is deliberately narrow: it writes new config files and a manifest, and it does not enable, promote, or validate. Validation is `reverse-etl-migration-validate` (the `primaryKey` casing rule and the destination-set check), equivalence is `reverse-etl-equivalency-validate`, and enabling is the client's.

## Prerequisites

- `reverse_etl_migration review: approved` — the plan this command executes against
- `migration/reverse_etl_decoy_mapping.csv` exists (`_{wave_id}.csv` under `--wave`), with a non-blank `decoy_destination_id` for every sync in scope
- The Hightouch config repo is checked out on the working branch `reverse-etl-migration-generate` Step 3 created — twins are committed there, never to the default branch
- `topology: additive_repo`. Under `parallel_workspace` or `in_place_repoint` there are no additive twin files to author: stop with `[wire] reverse-etl-twin-generate authors additive twin configs; topology is <topology>. Nothing to author.`

## Flags

- `--wave <id>` — restrict to the syncs `migration/migration_batching.csv` assigns to this wave, resolved identically to `reverse-etl-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Wave-labelled manifest (`migration/reverse_etl_twin_manifest_{wave_id}.csv`).
- `--syncs a,b` — author only the named syncs (original sync ids, normalised per Step 0). Mutually exclusive with `--wave`; abort if both are supplied: `[wire] --wave and --syncs cannot be combined. Pick one.`
- `--dry-run` — print the per-sync plan (source file, twin path, decoy id, approach, translated-model summary) and write nothing.
- No flag — every sync the plan carries with `include_in_migration: true` that is not already twinned.

## Inputs

- `.wire/releases/$ARGUMENTS/audit/reverse_etl_audit.csv` — the sync inventory: `sync_id`, `model_*`, `destination_*`, `primaryKey` where recorded, `warehouse_objects`, `migration_approach`
- `.wire/releases/$ARGUMENTS/migration/reverse_etl_migration_runbook.md` — the approved plan: topology, per-sync approach, translations recorded there
- `.wire/releases/$ARGUMENTS/migration/reverse_etl_decoy_mapping.csv` — production → decoy destination id per sync, same destination type
- The Hightouch config repo working branch — existing sync/model config files, read to mirror their shape
- `.wire/releases/$ARGUMENTS/migration/tenant_predicate_registry.csv` — under `migration.scope == tenant_carveout` only

## The sync id join key (Step 0)

Every artifact in the reverse-ETL path keys on the **normalised original sync id**, and this command is where that normalisation is pinned, because a twin's own filename carries a marker the audit's key does not:

1. Take the config file basename and strip the extension.
2. Strip a trailing target-warehouse marker: `-bq`, `_bq`, `-bigquery`, `_bigquery` (case-insensitive).
3. Lower-case the result.

A raw-string join between authored twins and the audit matched 6 of 609 on one engagement; the normalised join matched 575 of 643, with the residual explained (syncs classified `decommission` never get a twin). Record both the original id and the twin id in the manifest so no consumer has to re-derive the rule, and so the join to the register's `reverse_etl_sync` rows, which `migration-register-generate` seeds on the same key (wire#191), works unchanged.

## Workflow

### Step 1: Resolve scope and refuse to re-author

Resolve the sync set per **Flags**. Read any existing manifest and skip syncs already twinned unless their source config has changed since (compare the recorded source-file hash). Print the resolved list — sync id, approach, twin path, decoy id — before writing anything.

Route every sync by its `migration_approach`, per the closed vocabulary in `specs/utils/reverse_etl_approach.md`. A sync whose approach is **`decommission`** is **not twinned**: print it as skipped (`[wire] <sync>: approach decommission — no twin authored.`) and carry it to `reverse-etl-retire-generate`, which lists it on the classified-retirement ground. Twinning a sync that is being switched off is work with a negative return, and on one release that would have been 98 of them. An approach outside the closed set is an error naming the value and the sync, never a fall-through to authoring.

### Step 2: Author one twin per sync

For each in-scope sync, write a **new** config file alongside the existing one, at the same relative path with the twin id as its basename. Never open the existing file for writing.

1. **Source connection** — the target-warehouse source added by the plan's Step 3. Never the source-warehouse connection.
2. **Destination** — the `decoy_destination_id` from the decoy mapping, whose `decoy_destination_type` must equal the sync's `production_destination_type`. A blank decoy id, or a type mismatch, is a hard stop for that sync: record it under **Not authored — decoy missing or wrong type** and continue with the rest. Do not substitute a different type, and do not fall back to the production id.
3. **Paused** — whatever the config format's disabled/paused representation is, the twin is authored in it. This is not a default that a later step flips: no command in Wire enables a reverse-ETL sync.
4. **Model** — by approach, from the approved plan: `repoint` carries the model SQL unchanged against the target source; `rewrite_model` carries the translated SQL the runbook recorded (do not re-derive it here — the runbook's translation is the reviewed one); `rebuild` is out of scope for this command, since a Customer Studio rebuild is not a file copy. List `rebuild` syncs as **Not authored — rebuild approach** and leave them to the runbook's rebuild steps.
5. **`primaryKey`** — carry the sync's configured key through, applying the casing rule below.
6. **Field mapping, filters, computed fields, match rules** — carried through unchanged. This command copies sync-level logic; it does not redesign it. `reverse-etl-migration`'s Step 6 review and `reverse-etl-equivalency-validate`'s changed-field hashes are what confirm it.

Under `migration.scope == tenant_carveout`, resolve the sync's tenant filter from the predicate registry exactly as models do (`specs/utils/tenant_predicate_registry.md`). A sync whose registry row is `unresolved` is **not authored** — recorded under **Not authored — unresolved predicate**, never authored unfiltered.

### Step 2a: The `primaryKey` casing rule (error severity)

On a BigQuery-source Hightouch sync, a `primaryKey` containing any upper-case character makes the sync run successfully and send **nothing**. It is the failure mode that looks exactly like success, which is why it is error severity and why it is applied at authoring time as well as in validation.

Resolve the key's correct casing from the target model's actual column list (the compiled schema, not the source config's spelling). If the target column exists in a different case, write the target's casing and record the correction in the manifest (`primary_key_corrected: true`). If the key cannot be resolved against the target's columns at all, **do not author the twin**: record it under **Not authored — primaryKey unresolvable on target** with the key and the columns that were searched. Guessing a casing here is the same defect with an extra step.

Rule id `REVERSE_ETL_PRIMARY_KEY_CASE`, evaluated here at authoring time and again by `reverse-etl-migration-validate` Check 13 over what is actually on the branch — the second pass exists because twins written by hand, before or outside this command, are exactly the population the 22 defects came from.

### Step 3: Write the twin manifest

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_etl_twin_manifest.csv` (`_{wave_id}.csv` under `--wave`)

```
sync_id,twin_id,twin_path,source_path,source_file_sha,approach,
target_source_id,decoy_destination_id,decoy_destination_type,
production_destination_type,primary_key,primary_key_corrected,
paused,model_translated,tenant_mechanism,authored_date,state,not_authored_reason
```

`sync_id` is the normalised original id from Step 0 — the join key to the audit, and to the register's `reverse_etl_sync` rows (wire#191). `state` is `authored | not_authored`. Every `not_authored` row carries its reason; a blank reason on a `not_authored` row is itself a defect.

### Step 4: Summarise and hand off

Print counts: authored, skipped (already twinned / retire approach), not authored by reason. Then:

```
Twins authored: <n> (paused, decoy destinations)
Validate them before raising anything:
/wire:reverse-etl-migration-validate $ARGUMENTS
```

Do not open a PR here. The plan's PR sequence (Step 8 of the runbook) owns that, and a twin batch that has not been through Check 13 and Check 14 is not ready to raise.

### Step 5: Update status

```yaml
artifacts:
  reverse_etl_twin:
    generate: complete
    generated_date: "{{TODAY}}"
    file: migration/reverse_etl_twin_manifest.csv   # or _{wave_id}.csv under --wave
    twins_authored: N
    twins_skipped: N
    not_authored: N
    not_authored_reasons: {decoy_missing_or_wrong_type: N, rebuild_approach: N, unresolved_predicate: N, primary_key_unresolvable: N}
    primary_key_corrections: N
    all_paused: true          # false is a defect, not a state — investigate before proceeding
    wave: "B01"               # set only when run with --wave
    waves_complete: ["B01"]   # set only when run with --wave; accumulates across runs
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_etl_twin_manifest.csv` (`_{wave_id}` suffix under `--wave`)
- New twin config files on the Hightouch config repo's working branch, alongside the existing sync configs
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_twin` as artifact, `generate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_twin` as artifact, `generate` as action.

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
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
