---
description: Validate relocated carve-out dbt models — files present, predicates re-derived from disk, target compiles
argument-hint: <release-folder> --target-dbt-project-path <path>
---

# Validate relocated carve-out dbt models — files present, predicates re-derived from disk, target compiles

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
description: Validate relocated carve-out dbt models — every carve_in model present, predicates independently re-derived from file contents, no bucket misclassification, target compiles
argument-hint: <release-folder> [--wave id | --batch N | --select selector] --target-dbt-project-path <path>
---

# dbt Carveout Relocate — Validate

## Purpose

Validates a `dbt-carveout-relocate-generate` run. Every check re-derives its answer independently from the adjudicated CSV and the files actually on disk under `--target-dbt-project-path` — it does not trust the manifest's (`dbt_carveout_relocate_manifest.md`, or `_{wave_id}.md` under `--wave`) own claims about what it did.

## Flags

- `--wave <id>` / `--batch N` / `--select <selector>` — same scope this generate run was invoked with; resolved identically (see `dbt-carveout-relocate-generate` Step 1). If omitted, validate every model recorded under `artifacts.dbt_carveout_relocate` in status.md across all prior runs for this release.
- `--target-dbt-project-path <path>` — **required.** The dbt project relocated models were written into.

## Validation Checks

Read `migration/region_tags_adjudicated.csv`, filter to `item_type == "dbt_model" AND adjudicated_ruling == "carve_in"`, intersected with the resolved scope — this is the ground-truth set every check below validates against, independent of what the manifest claims was relocated.

**Check 1 — Every carve_in model resolves to a file that exists**
For every model in the ground-truth set, confirm the corresponding `.sql` file exists under `--target-dbt-project-path` at the expected mirrored path.
PASS: every model has a file. FAIL: list models with no file — a silent drop during relocation.

**Check 2 — Every shared-row-level model actually contains the injected predicate**
For every model in the ground-truth set with `bucket == shared-row-level` whose `predicate_injection` is `injected`, read the relocated `.sql` file directly and independently confirm it contains a `WHERE` clause carrying that model's filter **from its registry row** (`migration/tenant_predicate_registry.csv`, not `migration.tenant_predicate` — from v3.11.3 the filter is per model) on the outermost `SELECT`. Do not read this from the manifest's own claim; re-derive it from the file text. Strip SQL comments before re-deriving, for the same reason generate does: a commented-out filter is not a filter.
PASS: filter confirmed present in the file for every such model. FAIL: list models where the manifest claims injection but the file doesn't show it (or shows it on the wrong query level).

**Check 2b — Inherited models carry no filter, and their resolving node does (v3.11.3)**
For every model whose `predicate_injection` is `not_applicable_inherited`, confirm two things independently of the manifest: the relocated file contains no injected filter, and the registry row's `resolving_node` names an item whose own registry row carries a mechanism other than `unresolved`. Follow `resolving_node` transitively and confirm the chain terminates — an inheritance chain that loops, or that ends at an unresolved node, means the model is unscoped while claiming to be resolved.
PASS: every inherited model's chain terminates at a resolved node. FAIL: name the model, the chain walked, and where it broke.

**Check 2c — Registry completeness and internal consistency (v3.11.3)**
Run the registry-wide checks in `specs/utils/tenant_predicate_registry.md` over `migration/tenant_predicate_registry.csv`: one row per `carve_in` item; expression present exactly for `row_predicate`/`derived_expr`/`account_cascade` and empty for the rest; `inherited` rows resolving to something; no inheritance cycle; `verified_date` accompanied by `provenance`.
PASS: all five hold. FAIL: list each violation with its row.

**Check 3 — No confident-region model carries an injected predicate**
For every model in the ground-truth set with `bucket == confident-region`, confirm its relocated `.sql` file does **not** contain a `WHERE` clause referencing `migration.tenant_predicate` that wasn't already present in the source file. A predicate showing up on a `confident-region` model indicates a bucket misclassification upstream (in `region-tagging-generate`/`-review`), not something this command should silently accept.
PASS: no unexpected predicate found. FAIL: list models with an unexpected predicate, flagged for region-tagging re-adjudication, not for re-running this command.

**Check 4 — Manual-review-required list is empty, or every entry is explicitly signed off**
Read the manifest's manual-review-required list. For each entry, confirm either it no longer applies (the file has since been hand-edited and Check 2 now passes for it) or `dbt-carveout-relocate-review` recorded an explicit sign-off for that specific model (see that spec's Step 3).
PASS: list is empty, or every entry has a matching sign-off record. FAIL: list any entry with neither.

**Check 4b — Proposed dispositions are not treated as rulings (v3.11.3)**
For every registry row with `resolved_by: row_distribution_probe` and `confidence: medium` (a Rung 4 proposal), confirm `dbt-carveout-relocate-review` recorded a ruling for it. A proposal is evidence for a decision, not the decision, and a model shipped on one has been scoped by a query nobody approved.
PASS: every proposal has a ruling, or there are none. FAIL: list each unruled proposal with its evidence query.

**Check 5 — Target project compiles cleanly**
Run `dbt parse` (or `dbt compile`) against `--target-dbt-project-path` for the ground-truth model set, via the same scratch-directory pattern as generate's Step 4.
PASS: all models compile without errors. FAIL: list compilation errors per model.

### Update status

```yaml
artifacts:
  dbt_carveout_relocate:
    validate: pass | fail
    validated_date: "{{TODAY}}"
    wave_validate:                # set only when run with --wave, keyed by wave id
      B01: pass | fail
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `dbt_carveout_relocate` as artifact_id, `dbt Carveout Relocate` as artifact_name, and the `file` value from `artifacts.dbt_carveout_relocate` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `dbt_carveout_relocate` as artifact, `validate` as action.

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
