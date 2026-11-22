---
wire_schema: "1.0"
command: review
artifact: looker_audit
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
    path: "audit/looker_audit.md"
    description: "Review section appended with reviewer, date, decision and notes"
preconditions:
  - artifact: looker_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Internal RA review of the Looker audit before the migration plan is built on it"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Audit: Review

## Purpose

Internal RA review of the Looker audit. The reviewer confirms the model and content are fully captured, agrees the redesign register is right (a `redesign` row is a cost the plan will have to carry or a candidate to drop), checks that usage is trustworthy enough to rank by, and flags constructs that need a spike before the plan is drafted. Under the release director model the orchestrating session presents this review as a ruling and records the outcome; the questions below are what it asks.

## Prerequisites

- `audit/looker_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_model_catalog.csv`
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about Looker, Omni, dashboards, reporting, metric definitions, or specific dashboard names. Surface relevant extracts: which dashboards the client calls critical, known broken content, owners who have left.

### Step 2: Present audit for review

Display a summary:
- Totals: views, explores, fields, joins; dashboards, Looks, tiles, schedules, alerts
- Model rows by class and complexity
- The redesign register grouped by construct, with counts
- Usage: the dashboards that carry 80% of views, and the count with zero views in 90 days; the usage source
- Explores with the most dependent content
- Unresolved references and text tiles

### Step 3: Gather reviewer feedback

1. Is the estate fully captured? Any LookML projects, personal spaces, or embedded dashboards not in the repo or the API scope?
2. Does the redesign register look right? Is any `redesign` row a mis-detection (for example, Liquid in a comment) that should be re-classified?
3. Which redesign constructs need a spike before the plan: Liquid-heavy views, PDTs the client relies on, parameters that drive dashboard behaviour?
4. Is the usage data trustworthy enough to rank by, or is System Activity known to be partial (embedded use, API use, scheduled deliveries)?
5. Are there dashboards or Looks the client has already said must move regardless of usage, or must not move?

### Step 4: Apply feedback and record decision

Incorporate corrections into `audit/looker_audit.md` and, where a class changes, into `audit/looker_model_catalog.csv` with the reason updated. Record:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Comments, corrections, spikes agreed, follow-up actions]
```

### Step 5: Update status

```yaml
artifacts:
  looker_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:bi-migration-plan-generate $ARGUMENTS
```

If changes requested:
```
Apply the corrections, then re-run:
/wire:looker-audit-validate $ARGUMENTS
```

## Review Gate

The Looker audit review is an internal RA gate. Approval confirms the estate is fully captured, every construct's class is agreed, the redesign register is the accepted list of what will not translate mechanically, and usage is good enough to rank by. The plan reads the two catalogs as the complete inventory.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/audit/looker_audit.md` (Review section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_audit` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_audit` as artifact_id, `Looker Audit` as artifact_name, and the `file` value from `artifacts.looker_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_audit` as artifact, `review` as action.
