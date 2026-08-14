---
description: Validate reverse ETL migration runbook completeness, plus the authored twins — primaryKey casing (error) and destination-set safety
argument-hint: <release-folder> [--wave id] [--twins-only]
---

# Validate reverse ETL migration runbook completeness, plus the authored twins — primaryKey casing (error) and destination-set safety

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
description: Validate reverse ETL migration runbook completeness and sync coverage
argument-hint: <release-folder> [--wave id]
---

# Reverse ETL Migration — Validate

## Purpose

Checks the reverse ETL migration runbook for completeness — the migration topology is recorded, every in-scope sync has migration steps, SQL translations are present for rewrite_model syncs, rebuild plans cover all Customer Studio audiences and Journeys, validation is preview-based against a frozen baseline with syncs disabled, sync-level transformation logic is reviewed, and Lightning schema provisioning is documented. Produces a PASS/FAIL report.

From v3.11.6 it also validates the **authored twins themselves**, not only the plan: the `primaryKey` casing rule (Check 13) and the destination-set safety check (Check 14). Both read the config files on the branch, so they cover twins authored by hand as well as those `reverse-etl-twin-generate` wrote.

## Flags

- `--wave <id>` — validate the wave-labelled runbook (`reverse_etl_migration_runbook_{wave_id}.md`) against the syncs `migration/migration_batching.csv` assigns to this wave, resolved identically to `reverse-etl-migration-generate`'s Step 1w. Every check below reads "in-scope sync" as this resolved set instead of every `include_in_migration: true` sync.
- `--twins-only` — run Checks 13 and 14 only, against the twin configs on the branch. For the tight loop after `reverse-etl-twin-generate`, and for a pre-raise gate on a hand-authored batch, without re-validating the whole runbook.

## Prerequisites

- `migration/reverse_etl_migration_runbook.md` (or `_{wave_id}.md` under `--wave`) exists — not required under `--twins-only`
- For Checks 13 and 14: the Hightouch config repo is reachable, on the working branch, and its default branch can be read

## Validation Checks

**Check 1 — Topology recorded**
The runbook states the chosen topology (additive PR-gated repo — the default — or parallel workspace, or in-place API re-point) with a rationale. For the default additive path, it documents the repo branch, the additive target-warehouse source connection, the new decoy-bearing test syncs, and PR A. For the parallel-workspace path, it documents the repo clone, new workspace, GitHub Sync configuration, destination re-authentication, and target-warehouse source connection.
PASS: Topology and its setup steps present. FAIL: Topology not stated or build steps missing.

**Check 2 — All in-scope syncs covered**
Every sync with `include_in_migration: true` in the audit has a section in the runbook.
PASS: All syncs present. FAIL: List missing syncs.

**Check 3 — rewrite_model syncs have SQL diffs**
Every `rewrite_model` sync includes a before/after SQL diff showing the original and translated query.
PASS: All diffs present. FAIL: List syncs missing SQL diff.

**Check 4 — Translated SQL verified on target**
Each rewrite_model sync documents the result of running the translated SQL against the target warehouse (row count, primary key check).
PASS: All verifications present. FAIL: List unverified translations.

**Check 5 — Rebuild plans documented**
Every `rebuild` sync has a documented schema mapping and step-by-step rebuild plan.
PASS: All rebuild plans present. FAIL: List missing rebuild plans.

**Check 6 — Validation is preview-based against a frozen baseline, decoy destinations only**
The validation procedure compares model outputs and audience sizes against a frozen source baseline (not live production) and uses sync previews / record inspection. Test syncs carry decoy destination IDs only — production destination IDs are absent. It does not enable a sync against a production destination to validate.
PASS: Validation is preview-based against a baseline; test syncs carry decoy IDs only. FAIL: Validation relies on live runs to production destinations, compares against moving production, or test syncs carry production destination IDs.

**Check 7 — Sync-level transformation logic reviewed**
The runbook records a per-sync review of sync-level logic — field mappings, computed fields, sync filters, match/identity-resolution rules, and audience inclusion/exclusion — separate from model-output comparison.
PASS: Sync-level review present for all in-scope syncs. FAIL: List syncs missing the review.

**Check 8 — Lightning schema provisioning documented**
If any Lightning syncs are in scope, the runbook includes the `CREATE SCHEMA` and `GRANT` statements.
PASS: Present, or no Lightning syncs. FAIL: Missing.

**Check 9 — Rollback procedures present**
The runbook includes a rollback procedure for the chosen topology and each approach type used (additive: revert PR C — disable target syncs / restore decoy IDs — and revert PR B to re-enable source syncs; parallel: don't enable / disable new-workspace syncs and re-enable the source workspace; in-place: re-apply original `sourceId`).
PASS: Rollbacks present. FAIL: List missing rollbacks.

**Check 10 — Source left active until cutover, cutover is two client-merged PRs**
The runbook does not disable the source syncs (or source workspace) during the migration phase — only at cutover, via a client-merged PR, once confidence is established. For the default additive topology, cutover is two PRs merged together by the client: PR B disables every source-origin sync and PR C enables every target-origin sync (swapping decoy IDs back to production). RA does not enable/disable syncs directly.
PASS: Source disable / decommission appears only in the cutover/sign-off section, gated behind client-merged PRs; the two-PR cutover is documented (additive topology). FAIL: Source disable appears in the migration or validation steps, or cutover mutates the workspace outside a client-merged PR.

**Check 11 — Decoy destination mapping present**
For the additive topology, the runbook includes a decoy mapping table (one row per in-scope sync: production destination ID → decoy ID of the same destination type), references a scoped credential with write access to decoy targets only, and confirms production destination IDs are absent from the test syncs until cutover.
PASS: Mapping table, scoped credential, and the absent-production-IDs statement present (or topology is parallel/in-place). FAIL: Missing for the additive topology.

**Check 12 — Scope gate and approach re-verification recorded**
The runbook lists any syncs deferred because their source model is not yet built on target ("Deferred — source model not built on target"), and any syncs reclassified from `repoint` to `rewrite_model` by the approach re-verification, with the construct found.
PASS: Both lists present (empty lists stated explicitly). FAIL: Either omitted.

---

Checks 13 and 14 read the **twin config files on the branch**, not the runbook. Checks 1–12 validate the plan; these two validate what was actually authored, whether by `reverse-etl-twin-generate` or by hand. Hand-authored twins are the population every known defect of this class came from, so the checks deliberately do not care which produced them.

**Check 13 — `primaryKey` casing (`REVERSE_ETL_PRIMARY_KEY_CASE`, error severity)**

For every twin config on the branch whose source is the target warehouse, read its `primaryKey` and fail if it contains **any** upper-case character.

A BigQuery-source Hightouch sync whose `primaryKey` is not lower-case runs successfully and sends **nothing**. There is no error, no partial send, and no alert: the run is green and the destination receives zero rows. That is the whole reason this sits at error severity rather than warn — it is the failure mode indistinguishable from success, and the only signal is a destination quietly going stale.

The rule was written down at error severity in an engagement rule set and **no command evaluated it**. `dbt-migration-lint` loads engagement rules but operates on the dbt project and contains no reverse-ETL path, so it never opened the files the rule describes. A by-hand sweep of 621 authored twins later found **22 with upper-case keys**, including every sync in one open PR; all 22 would have sent nothing. Check 13 is where that rule now actually runs.

PASS: every twin's `primaryKey` is entirely lower-case. FAIL (error severity, blocks the gate): list each offending **file path and key**, with the target model's actual column casing where it can be resolved. Report the count separately from other findings — this one is worth seeing on its own line.

**Check 14 — Destination safety, as a set comparison**

Build, **once per run**, the complete set of destination ids referenced by every source-warehouse sync on the client repo's **default branch**. Then test each twin's destination id against that set. A twin whose destination is in the set fails.

The set is built once and tested against, and per-file lookups are banned, because a per-file check cannot see the whole and the wrong rule follows naturally from inspection. The first attempt at this on one engagement was a fixed list of Google Sheets destination ids — correct for 151 of 776 syncs and silently passing the other 625, which went to Google Ads customer match, DV360, Salesforce, Facebook custom audiences, Slack and Iterable. A destination type is not a safety property; membership of the live-destination set is.

No destination type appears anywhere in this check. If a check ever needs to name a destination type to decide safety, that is the bug this check exists to prevent.

Also report, as **information** rather than a failure: any destination id shared by two or more twins. Fan-in is legitimate in some designs (several models feeding one audience) and a copy-paste mistake in others, and the check cannot tell which — so it names them and leaves the reading to a person.

PASS: no twin's destination appears in the source-warehouse destination set. FAIL (error severity): list each twin, its destination id, and the source-warehouse sync that also writes there. If the default branch cannot be read, the check is `unverified`, never `pass` — an unreadable branch means the set is unknown, and an unknown set cannot clear a twin.

### Write validation report

Append a `## Validation` section to `migration/reverse_etl_migration_runbook.md` following the standard format.

Update status:
```yaml
artifacts:
  reverse_etl_migration:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    twins_checked: N                     # Checks 13/14 scope
    primary_key_case_failures: N         # REVERSE_ETL_PRIMARY_KEY_CASE, error severity
    production_destination_failures: N   # twin pointing into the live destination set
    shared_destination_twins: N          # information only, not a failure
    destination_set_source: default_branch | unverified
    wave_validate:               # set only when run with --wave, keyed by wave id
      B01: pass | fail
```

If PASS: `/wire:reverse-etl-migration-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `reverse_etl_migration` as artifact_id, `Reverse ETL Migration` as artifact_name, and the `file` value from `artifacts.reverse_etl_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_etl_migration` as artifact, `validate` as action.

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
