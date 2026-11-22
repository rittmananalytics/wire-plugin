---
wire_schema: "1.0"
command: review
artifact: oac_migration
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
  - artifact: oac_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of OAC migration runbook

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# OAC Migration — Review

## Purpose

Internal RA review of the OAC migration runbook before execution. Confirms physical table and raw SQL construct translations are correct, `manual-review-out-of-scope` items have an agreed owner and are genuinely reauthored rather than skipped, validation is genuinely branch-based via a non-production OAC copy, and the two-stage connection-pool cutover and its per-stage rollback are agreed.

## Prerequisites

- `migration/oac_migration_runbook.md` exists with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about OAC, reporting cutover, semantic model owners, or BI access requirements.

### Step 2: Present runbook for review

Summary to present:
- Topology (additive target connection pool + Git branch) and rationale, including the target `databaseType` verification
- Physical tables by approach (repoint / rewrite_sql / rebuild)
- Any SQL translations with non-trivial changes
- `manual-review-out-of-scope` constructs, their required reauthoring, and assigned owners
- The two-stage cutover plan (branch validation via a non-production OAC copy → branch merge + primary connection-pool repoint) and per-stage rollback

### Step 3: Gather reviewer feedback

1. Are the physical table and raw SQL construct translations correct and do they preserve each report's meaning?
2. Are the `rebuild` plans complete for physical tables with no direct translation path?
3. Are the `manual-review-out-of-scope` constructs correctly scoped, and does the client know who owns reauthoring each one against the target connection pool?
4. Is validation genuinely branch-based — is the primary connection pool, and the production OAC environment, confirmed untouched until Stage 2?
5. Is the two-stage cutover agreed, and is each stage's rollback (branch abandon/delete, connection pool details, connection-pool script restore) workable? Who on the client side owns the cutover window and the non-production OAC environment used for validation?

### Step 4: Apply feedback and record decision

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Capture corrections, agreed cutover window, rollback ownership]
```

### Step 5: Update status

```yaml
artifacts:
  oac_migration:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:equivalency-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_migration` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `oac_migration` as artifact_id, `OAC Migration` as artifact_name, and the `file` value from `artifacts.oac_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `oac_migration` as artifact, `review` as action.
