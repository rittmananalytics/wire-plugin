---
description: Card-level equivalence — migrated/carved cards return the same rows, model verdict taxonomy; gates the connection cutover
argument-hint: <release-folder> [--cards id1,id2] [--dashboard id]
---

# Card-level equivalence — migrated/carved cards return the same rows, model verdict taxonomy; gates the connection cutover

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
description: Card-level equivalence — prove a migrated or carved Metabase card returns the same rows, in the model verdict taxonomy, gating the connection cutover
argument-hint: <release-folder> [--cards id1,id2 | --dashboard <id>]
---

## Data Safety — Read Before Proceeding

All card executions for comparison run against the decoy collection's test copies (or directly as read-only queries against the two warehouse connections). No production card is repointed or edited to compare. Source-platform reads are SELECT only.

---

# Metabase Equivalency — Validate

## Purpose

`metabase-migration`'s decoy validation confirms cards **run**; nothing proved they return the **same rows** (#184). This command closes that with card-level verdicts in the model taxonomy — the reporting-layer analogue of `reverse-etl-equivalency-validate` — and it is the gate the Stage 2 connection cutover consumes: **every in-scope card must hold `pass` or `pass_qualified` before the production connection repoints.**

Like `equivalency-validate`, this is a repeatable loop command, not a generate/validate/review artifact.

## Prerequisites

- `metabase_audit review: approved`
- The migrated (or carved) card versions exist as decoy test copies, or the manifest rows are `applied`

## Workflow

### Step 1: Resolve scope and comparison sides

Scope: every in-scope card from the migration manifest (and the carve-out manifest under `tenant_carveout`); `--cards id1,id2` or `--dashboard <id>` (its deduped card set) narrows. Comparison sides are scope-dependent:

| Scope | Source side | Target side |
|---|---|---|
| `full_migration` (or absent) | The card's **source-dialect query** on the **source connection** | The **translated query** on the **target connection** |
| `tenant_carveout` | The **parent connection's** result with the card's **resolved registry filter** applied (`migration.parent_target_project` connection) | The **tenant connection's** result, unscoped (single-tenant by construction) |

**MBQL cards** compare by executing the same MBQL against both connections — there is no translated SQL to distrust, but the two databases' data still has to match at the card grain. **Native cards** compare the source text against the manifest's proposed/applied text. Under `tenant_carveout`, a card whose registry mechanism is `unresolved` is **verdict `fail`, reason `unresolved_predicate`** — never compared unfiltered (the source side would return every tenant's rows and the comparison would fail for a reason unrelated to the carve).

### Step 2: Compare at the card grain

Both sides run under the pinned-vintage discipline (a pinned as-of, or the baseline `T`). Compare the result sets: row count, the row set keyed by the card's grain columns, and column-value hashes over the card's `result_metadata` columns (canonicalised per the equivalency edge-case rules). Parameterised cards (field-filter template tags) compare at a declared parameter binding recorded in the report — an unbound field filter compares the card's unfiltered default.

### Step 3: Verdicts

The model taxonomy applies unchanged: `pass`, `pass_qualified` (the pair type allow-list, or a known-differences entry on the card's underlying tables — the declared-window rules apply where the underlying tables carry them), `diff_*` with a named mechanism, `fail`. Explanations qualify a fail; they never upgrade it.

### Step 4: Verdict log and register

Each card's verdict appends to `migration/migration_verdict_log.csv` (`object_type: metabase_card`, same single-writer merge as every lane — `specs/migration/equivalency/verdict_schema.md`) and updates the card's register row where one exists. Carve-out verdicts carry `scope` and the resolved predicate hash like every other carve-out verdict.

### Step 5: The cutover gate

`metabase-migration`'s Stage 2 (production connection repoint) requires every in-scope card at `pass`/`pass_qualified` from this command; under `tenant_carveout`, so does the tenant instance's go-live. A `fail` or unresolved card blocks the repoint — a dashboard that renders wrong numbers after cutover is discovered by the client, which is the most expensive place to find it.

### Step 6: Report and status

`.wire/releases/$ARGUMENTS/migration/metabase_equivalency_report_{run_number}.md`: per card — query type, comparison sides, parameter bindings, counts both sides, differing keys/columns (named), verdict. Update status:

```yaml
artifacts:
  metabase_equivalency:
    last_run_date: "{{TODAY}}"
    cards_checked: N
    passing: N
    failing: N
    unresolved: N          # tenant_carveout only — unresolved predicate, never compared
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_equivalency` as artifact, `validate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_equivalency` as artifact, `validate` as action.

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
