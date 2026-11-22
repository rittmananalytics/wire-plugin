---
wire_schema: "1.0"
command: review
artifact: migration_batching
domain: migration
release_types:
  - platform_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: migration_batching
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Human/client adjudication gate — turn the proposed domain-batch partition into a committed schedule

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Migration Batching — Review

## Purpose

Generate proposed a partition; this is where the team and client turn it into a committed schedule. The reviewer can rename, merge, or split batches, and assign target dates/sprints and owners. But any change that would violate a dependency edge from validate's Check 3 must either be rejected or explicitly accepted as a documented risk — record the risk acceptance with its rationale. Never silently let the DAG be violated.

## Prerequisites

- `migration/migration_batching.md` with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to surface any Fathom recordings touching scheduling, domain ownership, or sprint sequencing.

### Step 2: Present the batching summary

Display:
- The partition mode (`domain`, `build_ordered_waves`, or `readiness_waves`) — if the SCC fallback fired, explain that the estate is a single dependency SCC, so the plan is build-ordered waves rather than domain batches, and the domain column is a rollup tag not the build order. In readiness mode, explain that waves are readiness bands (shipped / ready / per-approval-group gated / waiting on parent / residue, plus holding pens), that each gated wave unlocks whole when the client approves its rule group (recorded via `region-tagging-review` or a `resolved_by: manual` registry edit, then a re-run), and that `B00` is shipped history, not schedulable work
- The batch summary table (batch_id, name, domain, object count, effort hours, depends_on_batches, batch-zero prerequisite)
- The batch-level dependency DAG
- The parallel-safe groupings (none in build-ordered mode — waves are strictly sequential)
- The seed-reconciliation note from generate

Reaffirm to the reviewer that these are candidates — no batch has a committed date, owner, or approval yet. This gate is where that happens. In build-ordered mode the reviewer still schedules and owns each wave, but reordering waves against the build order is a dependency violation — treat it like any Check 3 violation (withdraw or record an explicit risk acceptance).

### Step 3: Adjudicate

For each batch, confirm or change its name, composition, and domain grouping, then assign a target date/sprint and an owner.

If a requested change (a merge, split, object move, or scheduling two dependent batches in parallel) would violate a dependency edge from validate's Check 3, surface it immediately: show the edge (objects, batches, direction) and require the reviewer to either **withdraw the change** or **record an explicit risk acceptance** with rationale before proceeding. Do not apply the change without one or the other.

### Step 4: Apply adjudication and record decision

Update `migration_batching.md` (and the affected `migration_batching.csv` rows, e.g. renamed or reassigned batches) to reflect the adjudicated outcomes. Append:

```markdown
## Review — Adjudication

**Internal reviewer**: {{RA_REVIEWER}}
**Client attendees**: {{CLIENT_NAMES}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Final batch schedule
| Batch | Name | Target date / sprint | Owner | Depends on |
|-------|------|---------------------|-------|-----------|

### Adjudicated changes
[Per change: batch, what changed (rename / merge / split / move / reschedule), and rationale]

### Risk acceptances
[Per acceptance: the dependency edge being overridden, who accepted it, and the rationale — or "none"]
```

### Step 5: Record a provenance marker, then update status

Step 4 may have rewritten `migration_batching.csv` rows in place (renames, merges, moves) with no marker distinguishing an adjudicated CSV from a freshly-generated candidate. That silence is what let a re-run of `/wire:migration-batching-generate` overwrite a hand-corrected plan without warning — including a hand-fix for exactly the kind of defect Fix W-7 addresses (an object generate misclassified that a human moved by hand at this gate). Close that gap here: after Step 4's edits are written to disk, compute a checksum of the final `migration_batching.csv` (e.g. `shasum -a 256 migration/migration_batching.csv`) and record it as `reviewed_checksum` alongside the review outcome. This is what `/wire:migration-batching-generate`'s idempotency guard reads before it will overwrite anything.

```yaml
artifacts:
  migration_batching:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    reviewed_checksum: "{{SHA256_OF_MIGRATION_BATCHING_CSV}}"
```

### Step 6: Output next command

If approved:
```
/wire:migration-strategy-generate $ARGUMENTS
```

## Review Gate

This review is the point where the batch plan becomes a committed schedule. The migration strategy and sprint sequencing are built against the adjudicated batches. Re-running `migration-batching-generate` after this gate re-proposes candidates and requires re-adjudication.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_batching` as artifact_id, `Migration Batching` as artifact_name, and the `file` value from `artifacts.migration_batching` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_batching` as artifact, `review` as action.
