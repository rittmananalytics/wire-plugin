---
description: Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work
argument-hint: <release-folder> [--wave id 
---

# Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work

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
description: Carry merged client changes back into the delivery tree — four-way classification per merged model, never clobbering unraised local work, recorded in the register
argument-hint: <release-folder> [--wave id | --models list] [--repo-role transformation] [--dry-run]
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.

---

## Data Safety — Read Before Proceeding

```
⚠️  DATA SAFETY REMINDER

This command WRITES into the delivery tree. It never writes to the client repo.

  Direction of travel: client default branch  ->  delivery tree.
  One direction only. Nothing here raises, pushes, or amends anything on
  the client side.

  A model whose delivery-tree copy is AHEAD of the client's is never
  overwritten. That is unraised work, not stale work.
```

If any step would write to the client repo, or would overwrite a delivery-tree file that is ahead of the client's, stop and report the conflict before writing anything.

---

# dbt Migration — Reverse Port

## Purpose

After a model's PR merges, the version on the client's default branch can differ from the delivery tree's copy: a CI fix applied in the PR, a reviewer's change, a conflict resolved during the merge. Nothing carried that back. The delivery tree, which the next wave's translations read from and which every later comparison and lint pass treats as the authored truth, quietly stops being true.

On one release **86 of 94 models drifted** this way, because the sweep existed only as a habit in an engagement process document. This command makes it a step with a state.

**This is a different axis from `migration-drift`.** That gate compares the **live source platform** against `last_migrated_commit`, asking "has the thing we translated changed underneath us". This asks "has the thing we shipped changed after we shipped it". Both can be true at once and neither substitutes for the other.

## Prerequisites

- `migration/migration_register.csv` exists with at least one row at `delivery_stage: merged` or `production_verified`
- `migration.client_repos` configured for the `--repo-role` (default `transformation`)
- The delivery tree is committed, or has only changes you are willing to have reported: this command reads working-tree state to tell delivery-ahead from stale

## Flags

- `--wave <id>` — restrict to that wave's models. Wave-id form and normalisation follow the shared contract in `specs/utils/wave_resolution.md` (normative).
- `--models a,b` — restrict to named models. Mutually exclusive with `--wave`.
- `--repo-role <role>` — which client repo to read (default `transformation`).
- `--dry-run` — classify and report, write nothing. Produces exactly the same classification as a real run.
- No flag — every register row at `merged` or `production_verified`.

## The four-way classification (deterministic)

Tests mirror this table exactly (`wire/tests/platform_migration/validate_reverse_port.py`). For each in-scope model, compare three things: the file on the client's default branch (live read), the file in the delivery tree, and the delivery-tree file's content at `last_reverse_ported_commit` (or `last_migrated_commit` on the first sweep) as the common ancestor.

| # | Condition | Class | Action |
|---|---|---|---|
| 1 | Client and delivery identical | `in_sync` | Record the check. Write nothing |
| 2 | Client differs from delivery; delivery matches the ancestor | `client_ahead` | **Copy the client's version into the delivery tree.** Record the client commit |
| 3 | Client matches the ancestor; delivery differs from it | `delivery_ahead` | **Flag. Never write.** This is a local edit that was never raised |
| 4 | Both differ from the ancestor, and from each other | `diverged` | **Flag as a conflict.** Emit both diffs. A person resolves it |

**The never-clobber rule on `delivery_ahead` is mechanical, with no override flag.** A sweep that overwrites unraised local work in order to "fix" drift has destroyed more than the drift cost: the drift was a stale copy of something that exists in the client repo, while the local edit exists nowhere else. If the local edit is genuinely unwanted, deleting it is a deliberate act for a person, not a side effect of a sync.

`diverged` is likewise never auto-resolved. Two edits to the same file from two directions is the one case where the right answer needs to know why each was made.

## Workflow

### Step 1: Resolve scope and read both sides

Resolve the model set per **Flags**. Fetch the client repo live (`git fetch` plus a read of the default branch) for each model's target path; read the delivery tree's copy; resolve the ancestor content from `last_reverse_ported_commit`, falling back to `last_migrated_commit` on a model's first sweep.

If the client repo is unreachable, stop. Do not classify from the register's memory of what was merged: this command exists because the register's memory and the client's reality diverge, so trusting the former defeats it.

A model whose register row is `merged` but whose file is **absent** from the client's default branch is reported as `merge_state_stale` and skipped, not classified. The register believes something the repo does not, and that is a register correction (`migration-status` re-derives merge state live), not a port.

### Step 2: Classify

Apply the table above, per model. Normalise nothing before comparing: no whitespace trimming, no reformatting. A whitespace-only change made by the client's formatter in CI is a real change to the authored file and the delivery tree should carry it, or the next lint pass will keep proposing to undo it.

### Step 3: Port the `client_ahead` models

Copy each `client_ahead` model's client version into the delivery tree at its mirrored path, along with any companion schema/properties YAML the PR changed. Under `--dry-run`, skip this step entirely.

Do not reformat, re-lint, or "improve" the ported file in passing. It is the version the client merged and it is now the authored version; a change made during the port is a change nobody reviewed.

### Step 4: Update the register

For every ported model, set `last_reverse_ported_commit` to the client commit the content came from. Leave every other column alone: a port changes what the authored file is, not the model's delivery stage or its verdict.

**A ported model's standing equivalence verdict is superseded.** The verdict bound to a specific file version and the file has changed. Blank `last_equivalence_result` with an audit note naming the port, exactly as `equivalency-sweep` does when it supersedes a verdict, and emit the re-verify as owed. A port that silently keeps a verdict for a file that no longer exists is worse than no port at all.

### Step 5: Report

**Output location**: `.wire/releases/$ARGUMENTS/migration/reverse_port_report_{run_number}.md`

- Counts per class, and the scope resolved
- `client_ahead`: model, client commit, a diff summary, and the re-verify now owed
- `delivery_ahead`: model, the local diff, and the observation that this work has never been raised. This list is a to-do, not an error
- `diverged`: model, both diffs, and the ancestor reference
- `merge_state_stale`: model and the register row that needs correcting
- `in_sync`: a count, not a list

### Step 6: Update status

```yaml
artifacts:
  reverse_port:
    last_run_date: "{{TODAY}}"
    last_run_number: N
    models_checked: N
    in_sync: N
    client_ahead: N          # ported
    delivery_ahead: N        # flagged, never written
    diverged: N              # flagged as conflicts
    merge_state_stale: N
    reverify_owed: N         # verdicts blanked by a port
```

### Step 7: Output next step

```
Ported <n> models from the client's default branch.
<m> verdicts superseded and owed re-verification:
/wire:equivalency-validate $ARGUMENTS --models <list>
<k> models are ahead in the delivery tree and have never been raised.
<j> diverged and need a person.
```

## When to run it

After every merge, before the next wave's translation starts. The cost of skipping it compounds: the next wave's models are translated against a delivery tree that is already wrong, so the drift is inherited rather than merely persisted. `migration-status exceptions` lists models at `merged` whose `last_reverse_ported_commit` is blank, which is the standing reminder.

## Output Files

- `.wire/releases/$ARGUMENTS/migration/reverse_port_report_{run_number}.md`
- Ported `.sql` and companion YAML files in the delivery tree
- Updated `.wire/releases/$ARGUMENTS/migration/migration_register.csv`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `reverse_port` as artifact, `generate` as action.

Execute the complete workflow as specified above.
