---
wire_schema: "1.0"
command: review
artifact: omni_source_audit
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
    path: "audit/omni_source_audit.md"
    description: "Review section appended with the decision and reviewer notes"
preconditions:
  - artifact: omni_source_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Internal RA review of the Omni source audit before the migration plan is built on it"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Source Audit: Review

## Purpose

> **Experimental.** The `omni_to_looker` pair is experimental. It has run end to end once, on Rittman Analytics' own Omni model on BigQuery: three dashboards converted, deployed to Looker and matched tile by tile (39 of 39). It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Internal RA review of the Omni source audit. The reviewer confirms the estate is fully captured, agrees the redesign register, and decides how workbook-only fields, query views and templated views move.

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about Omni, the shared model, topics, dashboards, workbook fields, AI context and the warehouse behind them.

### Step 2: Gather reviewer feedback

1. Is the estate fully captured (every folder in scope; workbooks with no dashboard skipped on purpose; documents on other models)?
2. Which tiles use fields defined only in a workbook, and should those fields move into the shared model first or be rebuilt in Looker?
3. For each query view built from a topic query and each view with Mustache in its SQL: a LookML native derived table, a Liquid rewrite, or a dbt model?
4. Do the topics' default filters and AI context carry rules the client relies on (they have no LookML equivalent and are not emitted)?
5. Were column types read for every table (`column_gaps` empty), or are some dimensions typed by default?
6. Is usage good enough to rank by?

### Step 3: Record decision

Append to `audit/omni_source_audit.md`:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Corrections, workbook field and query view rulings, default filter findings, follow-up actions]
```

### Step 4: Update status

```yaml
artifacts:
  omni_source_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved: `/wire:bi-migration-plan-generate $ARGUMENTS`. If changes requested: apply them and re-run `/wire:omni-source-audit-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_source_audit` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_source_audit` as artifact_id, `Omni Source Audit` as artifact_name, and the `file` value from `artifacts.omni_source_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_source_audit` as artifact, `review` as action.
