---
description: Estate-wide defect-class sweep — enumerate one root-caused pattern across delivery tree, client main and open PRs, classify each site, close by encoding the lint rule
argument-hint: <release-folder> --pattern <rule-id> [--dry-run]
---

# Estate-wide defect-class sweep — enumerate one root-caused pattern across delivery tree, client main and open PRs, classify each site, close by encoding the lint rule

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
description: Estate-wide defect-class sweep — given one root-caused defect pattern, enumerate every occurrence across the delivery tree, the client main, and open PRs, classify each site, and close by encoding the pattern as a lint rule
argument-hint: <release-folder> --pattern <rule-id> [--dry-run]
---

## Data Safety — Read Before Proceeding

The sweep's static scan writes nothing anywhere. Its probe queries (DEFECT-MERGED quantification) are SELECT-only, against the target platform. Fixes land only in the delivery tree; anything merged is escalated to a fix-forward PR via `dbt-migration-batch-raise`, never edited in the client repo directly.

---

# Equivalency — Sweep

## Purpose

`equivalency-investigate`/`-fix` handle one model. But a root-caused defect is rarely alone: the same translation pattern that broke one comparison is usually sitting in every model that shares the shape — some still in the delivery tree, some already merged to the client's main. The loop that kills a defect class in one day is: root-cause one failing comparison → encode the rule → **statically sweep every translated model in both trees** → classify each site → fix, escalate, or clear with evidence → re-verify. This command is that loop as a gate (#179). A sweep that does not end in a lint rule is incomplete: the rule is what blocks the class prospectively.

## Input — the defect-class definition

`--pattern <rule-id>` names a rule carrying:

- a **detection pattern** — regex or AST-shaped match over source+target SQL pairs (what shape to find);
- a **semantic rule** — the condition that makes a hit an actual defect (e.g. "row-selecting window `ORDER BY` over a nullable key without a `NULLS` qualifier"), since a pattern hit in a harmless position is CORRECT, not a defect.

The rule id resolves against the active platform pair's lint rules and the engagement's own additions (`migration/lint_rules.md`). A `--pattern` naming no known rule aborts with the known rule ids listed; a brand-new class is first written down as an engagement rule, then swept — the definition is the input, not the output.

## Workflow

### Step 1 — Enumerate the estate

Collect every (source, target) SQL pair in scope, across **three locations**:

1. the **delivery tree** (`migration/dbt/` translated models);
2. the **client main** — a fresh read of each `migration.client_repos` checkout's base branch (live state, never the register's memory of it);
3. **open PRs** — each unmerged batch branch's files (`gh pr list --state open`).

### Step 2 — Detect and classify (deterministic)

Tests mirror this classification exactly (`wire/tests/platform_migration/validate_equivalency_sweep.py`). Per model, per location, apply the detection pattern, then the semantic rule:

| Pattern hit | Semantic rule violated | Location | Classification | Action |
|---|---|---|---|---|
| no | — | any | **CORRECT** | None. Recorded so the sweep's coverage is provable |
| yes | no | any | **CORRECT** | The shape is present but harmless here; recorded with the reason |
| yes | yes | delivery tree / open PR (not merged) | **DEFECT-FREE-MODEL** | Fix in the tree now, mark the model **re-verify owed** (its standing verdict is void) |
| yes | yes | client main (merged) | **DEFECT-MERGED** | **Quantified probe** — a SELECT that measures the defect's real impact (rows affected, delta size) — then escalate to a **fix-forward batch** via `/wire:dbt-migration-batch-raise`, the probe figures in the PR body |
| yes | yes | source only — model not yet translated | **NOT-TRANSLATED-YET** | Note for the translation guide: the pattern must be handled when this model is translated |

### Step 3 — Apply the tree fixes

For each DEFECT-FREE-MODEL site (unless `--dry-run`): fix the delivery-tree file, re-run the deterministic gate over it (`dbt-migration-lint`), and record the fix in the sweep report. Open-PR sites are fixed on their branch only when the PR is ours and unmerged; otherwise they classify as merged for safety.

### Step 4 — Register integration

- Every DEFECT-FREE-MODEL and DEFECT-MERGED model's standing verdict is **superseded**: blank `last_equivalence_result` (the register's audit note in `notes` names this sweep and the pattern id). The verdict log is untouched — history is history; the blanking says "no longer current evidence", not "never happened".
- DEFECT-MERGED escalations carry their probe figures into the fix-forward batch (`dbt-migration-batch-raise` derives them as candidates once fixed and re-verified).
- Re-verify-owed models re-enter the equivalency loop; the sweep is not complete until they carry fresh verdicts.

### Step 5 — Close with the lint rule

Confirm the pattern is encoded as an error-severity rule in the engagement lint rules (`migration/lint_rules.md`), firing in `dbt-migration-lint` — so the class is blocked at translation time from now on. **A sweep whose pattern is not in the lint rules at the end is incomplete**; the report's final line states the rule id and where it landed.

### Step 6 — Write the sweep report and update status

`.wire/releases/$ARGUMENTS/migration/equivalency_sweep_<rule-id>.md`: the pattern and semantic rule; per-location site counts by classification; the fixes applied; the probe figures and escalations; the re-verify-owed list; the closing lint rule.

```yaml
artifacts:
  equivalency:
    sweeps:
      - pattern: "<rule-id>"
        date: "{{TODAY}}"
        sites_correct: N
        defect_free_model: N
        defect_merged: N
        not_translated_yet: N
        reverify_owed: N
        lint_rule_landed: true
```

## Cross-release note (tenant carve-out, #180)

When the swept release has carve-outs relocated **from** it, the sweep's DEFECT-MERGED and DEFECT-FREE-MODEL model lists feed the carve-out's drift gate: relocated copies of a hit model are re-verify-owed in the carve-out too, resolved via the register's `parent_release`/`parent_model` linkage (`migration-drift-generate` Step 5c).

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `equivalency` as artifact, `sweep` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `equivalency` as artifact, `sweep` as action.

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
