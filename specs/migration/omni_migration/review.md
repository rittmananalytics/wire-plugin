---
wire_schema: "1.0"
command: review
artifact: omni_migration
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
  - artifact: omni_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of Omni migration runbook

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Migration — Review

## Purpose

Internal RA review of the Omni migration runbook before execution. Confirms view SQL translations are correct, raw-SQL tile translations are sound and their scope is current, validation is genuinely branch-based, and the two-stage connection cutover and its per-stage rollback are agreed.

## Prerequisites

- `migration/omni_migration_runbook.md` exists with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about Omni, reporting cutover, dashboard owners, or BI access requirements.

### Step 2: Present runbook for review

Summary to present:
- Topology (additive target connection + model branch) and rationale
- Views by approach (repoint / rewrite_sql / rebuild)
- Any SQL translations with non-trivial changes
- Raw-SQL tile translations and their `omni-query` test results
- The two-stage cutover plan (branch validation on a pilot scope → branch promotion + primary connection repoint) and per-stage rollback

### Step 3: Gather reviewer feedback

1. Are the view SQL translations correct and do they preserve the report's meaning?
2. Are the `rebuild` plans complete for views with no direct translation path?
3. Are the raw-SQL tile translations correct, and was the tile scope genuinely reconfirmed live rather than taken on trust from the original audit?
4. Is validation genuinely branch-based — are the primary connection and production content confirmed untouched until Stage 2?
5. Is the two-stage cutover agreed, and is each stage's rollback (branch abandon/revert, connection details, tile SQL restore) workable? Who on the client side owns the cutover window?

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
  omni_migration:
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

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_migration` as artifact_id, `Omni Migration` as artifact_name, and the `file` value from `artifacts.omni_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_migration` as artifact, `review` as action.
