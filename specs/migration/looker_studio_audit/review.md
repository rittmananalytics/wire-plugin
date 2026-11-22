---
wire_schema: "1.0"
command: review
artifact: looker_studio_audit
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
    path: "audit/looker_studio_audit.md"
    description: "Review section appended with reviewer, date, decision and notes"
preconditions:
  - artifact: looker_studio_audit
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Internal RA review of the Looker Studio audit before the metric catalogue is built on it"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Looker Studio Audit: Review

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. The same steps serve `looker_studio_to_looker` (experimental), which has run end to end once into Looker on two reports, not on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

Internal RA review of the Looker Studio audit. The reviewer confirms the estate is fully captured, agrees the classes, decides what to do about access gaps and data sources with no warehouse copy, and checks that the report families are right. Under the release director model the orchestrating session presents this review as a ruling and records the outcome; the questions below are what it asks.

## Prerequisites

- `audit/looker_studio_audit.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md`
- `.wire/releases/$ARGUMENTS/audit/looker_studio/content_catalog.csv` and `datasource_catalog.csv`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about Looker Studio, Data Studio, reports, dashboards, Funnel, GA4, metric definitions, or specific report names. Surface relevant extracts: which reports the client calls critical, reports already retired, owners who have left.

### Step 2: Present audit for review

Display a summary:
- Reports captured, failed, and the revision read for each (published or draft, unpublished changes)
- Pages (visible and hidden), components by kind and class
- Data sources by connector and class; the pipeline needs; the blocked list
- Report families (copies of one template)
- Usage from Route A, or `unknown`
- Access requests still open

### Step 3: Gather reviewer feedback

1. Is the estate fully captured? Any reports, embedded reports or scheduled email reports not in the list?
2. Blocked data sources: request Edit access and re-capture, or proceed without their definitions (their charts stay `blocked` in parity)?
3. Pipeline data sources: is there already a warehouse copy of this data (for example a Funnel.io or GA4 BigQuery export)? If yes, record the table so the plan can map to it.
4. Hidden pages: in scope, or treated as retired?
5. Report families: do the grouped reports really share one template, so the plan can merge them into one Omni dashboard with a filter?
6. Is the usage data good enough to rank by, or is it partial (cache hits leave no job; non-BigQuery charts have none)?

### Step 4: Apply feedback and record decision

Incorporate corrections into `audit/looker_studio_audit.md`. Record warehouse copies named by the reviewer in the Pipeline needs section with the table. Record:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Comments, access requests sent, warehouse copies identified, follow-up actions]
```

### Step 5: Update status

```yaml
artifacts:
  looker_studio_audit:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:metric-catalogue-generate $ARGUMENTS
```

If changes requested:
```
Apply the corrections (re-capture if access changed), then re-run:
/wire:looker-studio-audit-validate $ARGUMENTS
```

## Review Gate

The Looker Studio audit review is an internal RA gate. Approval confirms the estate is fully captured or its gaps accepted, every class is agreed, and the pipeline and access gaps have an owner. The metric catalogue and the plan read the two catalogs as the complete inventory.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/audit/looker_studio_audit.md` (Review section)
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `looker_studio_audit` as artifact_id, `Looker Studio Audit` as artifact_name, and the `file` value from `artifacts.looker_studio_audit` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `looker_studio_audit` as artifact, `review` as action.
