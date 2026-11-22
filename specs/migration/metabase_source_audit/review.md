---
wire_schema: "1.0"
command: review
artifact: metabase_source_audit
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
    path: "audit/metabase_source_audit.md"
    description: "Review section appended with the decision and reviewer notes"
preconditions:
  - artifact: metabase_source_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Internal RA review of the Metabase source audit before the migration plan is built on it"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Source Audit: Review

## Purpose

> **Experimental.** The `metabase_to_looker` pair is experimental. It has run end to end once, on a Metabase Cloud trial instance: four BigQuery questions converted, deployed to Looker and matched row for row. It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Internal RA review of the Metabase source audit. The reviewer confirms the content is fully captured, agrees the redesign register, and decides which native SQL questions and models are remodelled onto shared views and which stay as views on their SQL.

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about Metabase, dashboards, saved questions, models, metrics, native SQL and the databases behind them.

### Step 2: Gather reviewer feedback

1. Is the content fully captured (every collection in scope, personal collections, archived items excluded on purpose)?
2. Are all databases in scope synced in Metabase, and can Looker connect to each one?
3. For each native SQL question and model: remodel onto shared views, or keep as a view on its SQL? Are the lifted fields worth keeping?
4. Which metrics carry numbers the client relies on, and do their filters (for example a rolling date window) belong in the measure?
5. Is usage good enough to rank by?

### Step 3: Record decision

Append to `audit/metabase_source_audit.md`:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Corrections, native SQL and model rulings, metric findings, follow-up actions]
```

### Step 4: Update status

```yaml
artifacts:
  metabase_source_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved: `/wire:bi-migration-plan-generate $ARGUMENTS`. If changes requested: apply them and re-run `/wire:metabase-source-audit-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_source_audit` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_source_audit` as artifact_id, `Metabase Source Audit` as artifact_name, and the `file` value from `artifacts.metabase_source_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_source_audit` as artifact, `review` as action.
