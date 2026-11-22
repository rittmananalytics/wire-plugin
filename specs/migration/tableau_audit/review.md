---
wire_schema: "1.0"
command: review
artifact: tableau_audit
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
    path: "audit/tableau_audit.md"
    description: "Review section appended with reviewer, date, decision and notes"
preconditions:
  - artifact: tableau_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Internal RA review of the Tableau audit before the migration plan is built on it"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Tableau Audit: Review

## Purpose

> **Experimental.** The `tableau_to_looker` pair is experimental. It has run end to end once, on a Tableau Cloud trial site: one BigQuery sheet converted, deployed to Looker and matched row for row. It has not run on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Internal RA review of the Tableau audit. The reviewer confirms the estate is fully captured, agrees the redesign register (LOD, table calculations, blends, extracts), and checks the fingerprint groups are true duplicates before the plan proposes shared explores.

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about Tableau, workbooks, extracts, Prep flows, published data sources and critical dashboards.

### Step 2: Gather reviewer feedback

1. Is the estate fully captured (all sites and projects, personal spaces, embedded views)?
2. Are the fingerprint groups real duplicates, and is any near-duplicate (one extra column) worth merging by ruling?
3. For each extract: does a live connection to the warehouse give the same data, or is the extract fed by a Prep flow or a file?
4. Which LOD expressions and table calculations carry numbers the client relies on?
5. Is usage good enough to rank by?

### Step 3: Record decision

Append to `audit/tableau_audit.md`:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Corrections, near-duplicates to merge, extract findings, follow-up actions]
```

### Step 4: Update status

```yaml
artifacts:
  tableau_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 5: Output next command

If approved: `/wire:bi-migration-plan-generate $ARGUMENTS`. If changes requested: apply them and re-run `/wire:tableau-audit-validate $ARGUMENTS`.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `tableau_audit` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `tableau_audit` as artifact_id, `Tableau Audit` as artifact_name, and the `file` value from `artifacts.tableau_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `tableau_audit` as artifact, `review` as action.
