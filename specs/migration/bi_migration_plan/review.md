---
wire_schema: "1.0"
command: review
artifact: bi_migration_plan
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
mcp_contextual:
  - fathom
produces:
  - type: document
    path: "migration/bi_migration_plan.md"
    description: "Review section appended with the director's decisions"
preconditions:
  - artifact: bi_migration_plan
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Release director review of the BI migration plan: close every parked ruling, approve scope, batches and the parallel-run window"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# BI Migration Plan: Review

## Purpose

The release director's review. This is where the rulings the plan could not make are made: parity or redesign per tier, the drop list, PDT disposition, permission mapping, topic architecture, parallel-run window and parity scope. Every ruling made here is written to `decisions.md` the moment it is given, so a later session applies it without asking again. Approval releases Omni target setup.

## Prerequisites

- `migration/bi_migration_plan.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md`
- `.wire/releases/$ARGUMENTS/migration/bi_migration_batches.csv`
- `.wire/releases/$ARGUMENTS/decisions.md`
- `.wire/releases/$ARGUMENTS/status.md` (`parked_decisions`)

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve Fathom recordings relevant to this release. Search for the client's stated priorities: dashboards they call critical, content they want retired, the go-live date, permission requirements.

### Step 2: Present the plan for review

Display:
- Scope totals and the drop list, by object type
- The usage tiers and the 80% cut
- Each ruling: made (decision, by whom, when) or parked (the question)
- Model batches and content batches with their dependencies, in run order
- PDT dispositions
- The permission map
- Parallel-run window and parity scope, with the number of tiles that will be compared

### Step 3: Close the parked rulings

For each `parked_decisions` entry with `artifact: bi_migration_plan`, ask the question as worded. Record each answer in `decisions.md` in the ruling format from `specs/utils/director_operating_model.md`, with `Applies to: bi_migration_plan`, and remove the entry from `parked_decisions`. Then re-read the plan's affected sections and update them (batches for a changed drop list; the model scope for a changed PDT disposition).

### Step 4: Gather reviewer feedback

1. Is the drop list right? Anything stale that the client will want back, or anything in tier 1 that should go?
2. Are the batch sizes and order workable for the team and the client's calendar?
3. Does the permission map hold for every group with row-level access today?
4. Is the parallel-run window long enough to cover a full business cycle (month end, a weekly batch)?
5. Is the parity scope enough to sign off cutover? If only tier 1 is compared, is the client content with that?

### Step 5: Apply feedback and record decision

Incorporate corrections into `migration/bi_migration_plan.md` and `migration/bi_migration_batches.csv`. If batches changed, re-run `/wire:bi-migration-plan-validate $ARGUMENTS` before recording approval. Record:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Rulings recorded
[One line per ruling: id, decision, reference to decisions.md]

### Reviewer notes
[Comments, corrections, follow-up actions]
```

### Step 6: Update status

```yaml
artifacts:
  bi_migration_plan:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    rulings_parked: 0
```

### Step 7: Output next command

If approved:
```
/wire:omni-target-setup-generate $ARGUMENTS
```

If changes requested:
```
Apply the corrections, then re-run:
/wire:bi-migration-plan-validate $ARGUMENTS
```

## Review Gate

Approval means: the scope is agreed, every ruling is recorded with a name and date, the batches are the order the work will run in, and the register rows are the objects that will be tracked to cutover. No Omni write happens before this gate.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (Review section)
- Updated `.wire/releases/$ARGUMENTS/decisions.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `bi_migration_plan` as artifact_id, `BI Migration Plan` as artifact_name, and the `file` value from `artifacts.bi_migration_plan` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `bi_migration_plan` as artifact, `review` as action.
