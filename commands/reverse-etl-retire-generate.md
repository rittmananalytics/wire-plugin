---
description: Generate the reverse-ETL retirement runbook — superseded and retire-classified syncs, ordered, with the evidence each replacement has run cleanly and the rollback
argument-hint: <release-folder> [--wave id] [--min-clean-days N]
---

# Generate the reverse-ETL retirement runbook — superseded and retire-classified syncs, ordered, with the evidence each replacement has run cleanly and the rollback

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
description: Generate the reverse-ETL retirement runbook — which superseded or retire-classified syncs come out, in what order, on what evidence the replacement has been running cleanly, and the rollback if it has not
argument-hint: <release-folder> [--wave id] [--min-clean-days N]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: reverse_etl_retire` and `artifact_file_path: migration/reverse_etl_retirement_runbook.md` before proceeding.

---

## Data Safety — Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command produces a RUNBOOK. It disables and deletes nothing.

  Retirement is executed by the client, through a merged PR, in the order
  this runbook sets out. RA does not disable, pause, or delete a sync.

  A sync listed here is one whose replacement has already been proven, or
  one the audit classified decommission. Nothing else is listed.
```

If any generated step would disable, delete, or mutate a sync outside a client-merged PR, stop and report the conflict.

---

# Reverse ETL Retire — Generate

## Purpose

After switchover both the old sync and its twin exist, and nothing removed the old one. On one engagement, 84 of 643 syncs were classified `decommission`, and on its sister release 98 of 726, before counting those superseded by their own twins — and nothing in the command set tracked which were owed retirement or on what evidence. The estate quietly doubles: two syncs per destination, one live and one dormant, with no record of which is which.

This command produces the retirement runbook and the state tracking. Execution stays a client action, in the same PR-gated posture as every other reverse-ETL change.

## Prerequisites

- `reverse_etl_audit review: approved` — the source of `decommission` classifications (`specs/utils/reverse_etl_approach.md`)
- `migration/reverse_etl_twin_manifest.csv` exists where any sync is being retired **because it was superseded** (a supersession claim needs the twin it names)
- `migration/migration_verdict_log.csv` exists — the evidence a replacement actually passed

## Flags

- `--wave <id>` — restrict to the syncs `migration/migration_batching.csv` assigns to this wave, resolved identically to `reverse-etl-migration-generate`'s Step 1w. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative). Wave-labelled runbook.
- `--min-clean-days N` — how long a replacement must have been running cleanly before its predecessor is listed. Default `7`. Record the value used in the runbook; a shorter window is a judgment the client should see stated, not one buried in a flag.

## Who is eligible (deterministic)

Tests mirror this table exactly (`wire/tests/platform_migration/validate_reverse_etl_retire.py`). A sync is listed for retirement when it matches **either** row, and is refused otherwise with the recorded reason.

| # | Ground | Condition | Refusal reason when unmet |
|---|---|---|---|
| 1 | **Classified decommission** | The audit's `migration_approach` is `decommission` (the closed vocabulary in `specs/utils/reverse_etl_approach.md`; there is no `retire` value) | — (no replacement is expected; nothing to prove) |
| 2 | **Superseded by its twin** | A twin exists in the manifest for this sync id, the twin's `delivery_stage` is `production_verified`, its latest `reverse_etl_sync` verdict is `pass`, and it has been running cleanly for at least `--min-clean-days` | `no_twin` · `twin_not_production_verified` · `no_passing_verdict` · `verdict_not_pass` · `clean_window_too_short` |

**A sync whose replacement has no passing verdict is never listed.** `pass_qualified` is not sufficient here, for the same reason it is not sufficient at `batch-raise`: a reverse-ETL sync's output leaves the warehouse, so the external-exactness rule applies. Retiring the old sync on a qualified verdict removes the rollback path while the qualification is still unexplained.

**Clean running is evidence, not an assumption.** "Running cleanly" means, per replacement: its scheduled runs over the window all completed, none errored, and the planned row counts are within the tolerance the plan recorded — read from the sync-run history, not inferred from the absence of a complaint. A replacement that has never run cannot be clean, however good its verdict: record `clean_window_too_short` with the run count actually seen.

## Workflow

### Step 1: Resolve the candidate set

Read the audit for `decommission`-classified syncs, and the twin manifest for `authored` twins. Join on the normalised sync id (`reverse-etl-twin-generate`'s Step 0 rule — the same key throughout). Read the verdict log for each twin's latest `object_type: reverse_etl_sync` verdict, and each twin's `delivery_stage` (from the register once wire#191 lands; from the twin manifest and a live repo read until then, and say which in the runbook).

Apply the eligibility table. Print the resolved list and, separately, every refused candidate with its reason — the refusals are the more useful half of the output, because each one names the evidence still owed.

### Step 2: Order the retirements

Order is not arbitrary and not alphabetical:

1. **`decommission`-classified syncs first.** They have no replacement to keep watching, so nothing is learned by waiting, and removing them shrinks the set everything else is reasoned about.
2. **Then superseded syncs, longest-clean first.** The most-proven replacement is the safest predecessor to remove, and going in that order means the earliest steps build confidence for the later ones.
3. **Group by destination.** All syncs writing to one destination retire together, so no destination is left served by a mix of old and new for longer than one step. A destination whose syncs are not all eligible retires none of them yet — record it as **held** with the blocking sync named.

### Step 3: State the evidence per sync

For each listed sync, the runbook records, in this order: the replacement twin's id, its verdict and verdict date, its `delivery_stage` and the live-repo evidence for it, the clean-run window observed (runs, errors, row-count range), and the destination it serves. A retirement step with no evidence block is not a step; it is a request.

For a `decommission`-classified sync, the evidence block instead records the classification, its adjudication note from the audit, and the confirmation that no twin exists — so a reader can tell the two grounds apart at a glance.

### Step 4: The rollback

Per sync, the rollback if the replacement turns out to be wrong after its predecessor is retired: revert the retirement PR to restore the old sync's config, confirm its source connection still resolves (the source warehouse may have been decommissioned on a different schedule — if it has, say so, because then this rollback does not exist and the runbook must say that plainly), and re-pause the replacement.

**Where the source warehouse is already gone, there is no rollback and the runbook says so per sync**, rather than describing a revert that would restore a sync pointing at nothing. That is the point at which retirement becomes irreversible, and a client is entitled to see it marked.

### Step 5: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_etl_retirement_runbook.md` (`_{wave_id}.md` under `--wave`)

Structure:
1. Scope and the `--min-clean-days` value used
2. Summary counts: listed (by ground), refused (by reason), held (by destination)
3. The ordered retirement steps, each with its evidence block and its rollback (or its explicit no-rollback statement)
4. **Refused candidates**, each with the reason and the command that produces the missing evidence (`/wire:reverse-etl-equivalency-validate` for a missing verdict, `/wire:equivalency-post-merge-verify` for a twin not yet production-verified)
5. Held destinations, with the blocking sync named
6. The PR sequence: one retirement PR per ordered group, client-merged, with the monitoring window between groups

### Step 6: Update status

```yaml
artifacts:
  reverse_etl_retire:
    generate: complete
    generated_date: "{{TODAY}}"
    file: migration/reverse_etl_retirement_runbook.md   # or _{wave_id}.md under --wave
    min_clean_days: 7
    listed_decommission_classified: N
    listed_superseded: N
    refused: N
    refused_reasons: {no_twin: N, twin_not_production_verified: N, no_passing_verdict: N, verdict_not_pass: N, clean_window_too_short: N}
    held_destinations: N
    no_rollback_available: N     # syncs whose source warehouse is already decommissioned
    wave: "B01"                  # set only when run with --wave
    waves_complete: ["B01"]      # set only when run with --wave; accumulates across runs
```

### Step 7: Output next step

```
Retirement runbook: <n> syncs listed, <m> refused pending evidence.
The client executes it as PR-gated steps; nothing here disables a sync.
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_etl_retirement_runbook.md` (`_{wave_id}` suffix under `--wave`)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_retire` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_retire` as artifact_id, `Reverse ETL Retirement` as artifact_name, and the `file` value from `artifacts.reverse_etl_retire` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_retire` as artifact, `generate` as action.

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
