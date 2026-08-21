---
description: Validate the Metabase carve-out — filters re-derived from the registry, no unfiltered card, dashcard-level removals, explicit shared-card decisions
argument-hint: <release-folder>
---

# Validate the Metabase carve-out — filters re-derived from the registry, no unfiltered card, dashcard-level removals, explicit shared-card decisions

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
description: Validate the Metabase carve-out — layer decisions recorded, filters re-derived from the predicate registry, no unfiltered card, dashcard-not-card removals, shared-card decisions explicit
argument-hint: <release-folder>
---

# Metabase Carve-out — Validate

## Validation Checks

Ground truth is `migration/region_tags_adjudicated.csv` (the carve-in set), `migration/tenant_predicate_registry.csv` (the mechanism per card), and the actual card/dashboard state (decoy copies or serialization export) — the manifest's own claims are re-derived, never trusted, mirroring `dbt-carveout-relocate-validate`.

**Check 1 — Every carve-in item has a manifest row**
Every `metabase_card` / `metabase_dashboard` item ruled `carve_in` (within the run's scope) appears in `migration/metabase_carveout_manifest.csv` exactly once; no manifest row exists for an item without a `carve_in` ruling.
PASS/FAIL with missing/extra items.

**Check 2 — Layer decisions recorded and consistent**
Every card row carries a layer decision (`sandboxing` | `warehouse_layer` | `dashboard_parameter` | `card_edit`) with a reason; sandboxing rows have a permission-group policy spec; warehouse-layer rows name the tenant view/model; dashboard-parameter rows have per-dashcard mappings; only `card_edit` rows carry an injected filter.
PASS/FAIL with offending rows.

**Check 3 — Card-edit filters re-derive from the registry**
For every `card_edit` card, re-read the card's actual query (decoy copy / export) and independently re-derive its filter from its registry row: MBQL cards carry the filter clause; native cards carry the expression injected at the **outermost SELECT** (strip comments before re-deriving; a set operation is checked per branch). The filter must match the registry expression, not `migration.tenant_predicate`. A registry expression that is non-empty but fails the well-formedness check in `specs/utils/tenant_predicate_registry.md` is FAIL, reason `malformed_expression`, before any re-derivation (#200): a truncated rule is not a basis to check a card against.
PASS/FAIL with offending cards.

**Check 4 — No unfiltered card, no guessed mechanism**
Every card whose registry mechanism is `unresolved` (or that has no row) is `manual_review_required` and untransformed; no card was carved with a filter that has no registry provenance. An `object_carve`/`inherited` card carries no injected filter and records which of the two it was.
PASS/FAIL with offending cards.

**Check 5 — Removals are dashcard-level**
Every `remove_dashcard` action deleted dashcards only: each affected card still exists in its collection; the pruned dashboards no longer reference it.
PASS/FAIL with offending cards.

**Check 6 — Shared-card decisions explicit**
Every carved card that out-of-scope dashboards also reference (per the audit reverse index) carries an explicit `edit_in_place`/`clone` decision; every `clone` is noted as forked maintenance.
PASS/FAIL with offending cards.

**Check 7 — Dashboard parameter mappings remapped**
Every carved dashboard's filter parameter mappings resolve against the tenant connection's field ids; `dashboard_parameter`-layer dashboards carry the tenant parameter mapped on every surviving dashcard (native cards have the required field-filter tag).
PASS/FAIL with offending dashboards.

### Update status

```yaml
artifacts:
  metabase_carveout:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

### Output next command

```
/wire:metabase-carveout-review $ARGUMENTS
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout` as artifact, `validate` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout` as artifact, `validate` as action.

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
