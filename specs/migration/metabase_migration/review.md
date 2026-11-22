---
wire_schema: "1.0"
command: review
artifact: metabase_migration
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
  - artifact: metabase_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of Metabase migration runbook

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Migration — Review

## Purpose

Internal RA review of the Metabase migration runbook before execution. Confirms SQL translations are correct, the permission-group remap is sound, validation is decoy-based, and the two-stage connection repoint and its per-stage rollback are agreed.

## Prerequisites

- `migration/metabase_migration_runbook.md` exists with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about Metabase, reporting cutover, dashboard owners, or BI access requirements.

### Step 2: Present runbook for review

Summary to present:
- Topology (additive target connection + decoy collection) and rationale
- Cards by approach (repoint / rewrite_sql / rebuild)
- Any SQL translations with non-trivial changes
- Permission-group remap table
- Decoy mapping (production card → decoy test copy; production connection → target connection)
- The two-stage cutover plan (pilot repoint → full connection repoint) and per-stage rollback

### Step 3: Gather reviewer feedback

1. Are the SQL translations correct and do they preserve the report's meaning?
2. Are the `rebuild` plans complete?
3. Is the permission-group remap correct — does every group land with the access the client expects, and is the before-state captured for rollback?
4. Is validation genuinely decoy-based — are production cards and dashboards confirmed untouched during validation?
5. Is the two-stage repoint agreed, and is each stage's rollback (connection details + permission graph + card SQL) workable? Who on the client side owns the cutover window?

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
  metabase_migration:
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

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_migration` as artifact_id, `Metabase Migration` as artifact_name, and the `file` value from `artifacts.metabase_migration` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_migration` as artifact, `review` as action.
