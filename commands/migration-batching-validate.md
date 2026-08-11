---
description: Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared
argument-hint: <release-folder>
---

# Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared

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
description: Validate domain batching — every object classified once, DAG acyclic, every real cross-batch edge declared, parallel-safe claims hold
---

# Migration Batching — Validate

## Purpose

Independently re-derives the ground truth for every check — the inventory object list, the object-level dependency graph, the macro flags — rather than trusting generate's self-report. This independence is the entire point: it is what catches a batch plan that has drifted out of sync with the real dependency graph.

## Validation Checks

Read `migration/migration_batching.csv`, `migration/migration_batching.md`, `migration/migration_inventory.md`, `audit/dbt_audit.csv`, and status.md.

**Read the partition mode first.** Take `artifacts.migration_batching.partition_mode` from status.md (`domain` or `build_ordered_waves`; treat absent as `domain` for backward compatibility). The mode changes what Checks 3, 5, 8, and 9 expect — Checks 1, 2, 4, 6, 7 are identical in both modes. Both modes must still pass C2 (acyclic) and C3 (every cross-batch edge declared); build-ordered waves satisfy both trivially via the full-prefix dependency, which is the whole reason the fallback exists.

**Check 1 — Every inventory object classified exactly once**
Rebuild the union of objects from `migration_inventory.md`'s unified catalog. Confirm a 1:1 match against `migration_batching.csv` rows — no object missing, none duplicated, no CSV row without a matching inventory object. A row with `batch_id: NO-DEP` counts as classified — it is a deliberate, named bucket for objects with no model consumer (Check 3 confirms none exist), not a gap. Do not flag `NO-DEP` rows as missing, duplicate, or orphaned on that basis alone.
PASS: one-to-one match. Report the `NO-DEP` count alongside the pass (e.g. "168 objects, 1:1 match, 12 routed to NO-DEP") so it's visible in the check output, not just the narrative.
FAIL: list missing objects, duplicates, and orphan CSV rows, with counts of each.

**Check 2 — Batch dependency DAG is acyclic**
Rebuild the batch-level dependency graph from the CSV's `depends_on_batches` column alone. Confirm no cycles.
PASS: acyclic.
FAIL: list the cycle (the sequence of batch_ids).

**Check 3 — Every real cross-batch graph edge is declared**
Independently rebuild the object-level dependency graph from `migration_inventory.md`'s adjacency list plus `dbt_audit.csv`'s manifest-derived model dependencies. Do **not** read `migration_batching.md`'s own DAG as ground truth. For every graph edge whose two endpoints land in different batches (per the CSV's `batch_id` assignments), confirm the dependency direction is represented in `depends_on_batches` for the dependent batch. This is the check that directly answers "does this batch plan actually hold against the real dependencies."

For every object classified `NO-DEP`, independently confirm it genuinely has **zero** graph edges to any model in the Check 3 graph. `NO-DEP` is for objects with no real consumer, not an escape hatch for skipping a batch/wave assignment on an object that does have one — a `NO-DEP` object with an actual model edge is a FAIL on this check, same as an undeclared cross-batch edge.

PASS: every cross-batch edge declared, and every `NO-DEP` object confirmed edge-free.
FAIL: list every undeclared cross-batch edge — the two objects, their batches, and the correct direction — and separately list any `NO-DEP` object that in fact has a model consumer (the object, the model, and the edge).

**Check 4 — Batch-zero macro dependency present where required**
For every batch containing a model with a non-empty `platform_macros` value (re-read from `dbt_audit.csv`, not from generate's output), confirm the narrative declares the batch-zero macro translation pass as a prerequisite of that batch.
PASS: all affected batches declare it.
FAIL: list batches missing the prerequisite.

**Check 5 — Parallel-safe claims hold**
For every batch pair listed as parallel-safe in the narrative, confirm zero graph edges (either direction) between their member objects, per the Check 3 graph.
PASS: no parallel-safe claim contradicted.
FAIL: list each contradicted claim with the edge (objects, batches, direction) that breaks it.
In `build_ordered_waves` mode the parallel-safe set must be **empty** (full-prefix dependencies make every wave sequential) — a non-empty parallel-safe list in that mode is a FAIL. `NO-DEP` must never appear in a parallel-safe grouping in either mode — it is a holding pen, not a batch, and having zero edges to everything is not evidence it's safe to schedule; a parallel-safe claim naming `NO-DEP` is a FAIL.

**Check 6 — Every CSV row complete**
Each row has a non-empty `object_id`, `object_type`, `source_audit`, `domain`, `batch_id`, and `batch_name`. `depends_on_batches` may be empty. A row with `batch_id: NO-DEP` and `batch_name: "No model dependency — review"` is complete on the same terms as any other row — `NO-DEP` is a valid classification, not a placeholder for a missing one, and must not be flagged incomplete on that basis. `depends_on_batches` empty on a `NO-DEP` row is expected, not a defect.
PASS/FAIL with incomplete rows listed.

**Check 7 — Candidates only, no premature lock-in**
Neither `migration_batching.md` nor `status.md` marks any batch "approved" or "final", and no batch carries a committed date or owner — that is `/wire:migration-batching-review`'s job.
PASS: no lock-in language.
FAIL: quote the offending lines.

**Check 8 — Build-ordered waves are well-formed (only when `partition_mode: build_ordered_waves`)**
Skip in `domain` mode. When the SCC fallback fired, independently confirm the waves are a valid build order:
- **Fallback is justified and recorded** — re-derive the domain-level SCC condition from the Check 3 object graph (a single SCC spanning the domains). Confirm the narrative and status (`scc_fallback: true`) record it. A build-ordered partition emitted when a viable acyclic *domain* partition existed is a FAIL (the fallback should only fire when it must).
- **Topological order holds** — for every object edge, the dependency's wave id ≤ the dependent's wave id (0 forward references across waves).
- **Full-prefix dependencies** — each wave `Bk`'s `depends_on_batches` is exactly `B01;…;B(k-1)` (wave 1 empty). A missing or partial prefix is a FAIL.
- **Domain tag retained** — every CSV row still carries a non-empty `domain` value for rollup.
PASS/FAIL with the specific violation(s) listed.

**Check 9 — Cutover partition present (only when `partition_mode: build_ordered_waves`)**
Skip in `domain` mode. Confirm `migration_batching.md` has a non-empty `### Cutover partition (secondary view)` section: a domain-grouped rollup, independently re-derivable from the CSV's `domain` and `batch_id` columns, showing which wave(s) each domain's objects actually landed in. Confirm it states — in words, not just implied by the table — that build order and cutover/domain order diverge because the SCC fallback fired, and names at least the domains whose objects are split across the most waves. An empty or missing section, or one that just repeats the wave DAG without the domain rollup, is a FAIL — this is the check that stops a reader from mistaking a wave number for a client milestone grouping.
PASS: section present, non-empty, domain/wave mapping independently reproducible from the CSV, divergence stated explicitly.
FAIL: state which of the above is missing.

### Update status

```yaml
artifacts:
  migration_batching:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact_id, `Migration Batching` as artifact_name, and the `file` value from `artifacts.migration_batching` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_batching` as artifact, `validate` as action.

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
