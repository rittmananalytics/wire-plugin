---
wire_schema: "1.0"
command: review
artifact: data_residency_assessment
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
  - artifact: data_residency_assessment
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Sign-off gate for the data residency assessment — client DPO/legal determines the flagged items and signs off

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Data Residency Assessment — Review

## Purpose

The sign-off gate for the data residency assessment (Stage 1 deliverable D3). RA presents the structured assessment; the client's DPO/legal addresses every **[CLIENT DPO/LEGAL]** item — above all the lawful basis and the historical-window retention ruling — and signs off. RA does not own these determinations; the gate cannot be cleared by RA alone.

## Prerequisites

- `migration/data_residency_assessment.md` exists with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions of GDPR, data residency, retention, the historical data window, or the DPA.

### Step 2: Present the assessment for sign-off

Display:
- The processor-not-counsel framing and the controller/processor split
- The data inventory in scope and the historical window
- The residency constraints for the target region
- The consolidated **[CLIENT DPO/LEGAL]** items requiring the client's determination
- The processor safeguards RA will implement

### Step 3: Gather the client's determinations

Walk the client DPO/legal through each **[CLIENT DPO/LEGAL]** item and record their determination in the document — in particular:

1. The lawful basis for processing and retaining the data being migrated.
2. The retention ruling on the ~3-year historical window — migrate the full window, or trim it.
3. Any cross-border transfer mechanism required (e.g. SCCs), if data leaves the region.
4. Any additional safeguards the client requires of RA as processor.

RA records the client's answers; RA does not supply them.

### Step 4: Record decision and sign-off

Complete the sign-off block. Approve only when every **[CLIENT DPO/LEGAL]** item is addressed and the client DPO/legal has signed:

```markdown
## Sign-off

- All [CLIENT DPO/LEGAL] items addressed by the client: ☑ / ☐
- Historical-window retention basis confirmed by the client: ☑ / ☐

**Client DPO / legal sign-off**: {{CLIENT_DPO_NAME}}  **Date**: {{TODAY}}
**RA reviewer**: {{REVIEWER_NAME}}  **Date**: {{TODAY}}
**Decision**: approved | changes_requested
```

If any item is unresolved, record `changes_requested` and list what the client still owes before sign-off.

### Step 5: Update status

```yaml
artifacts:
  data_residency_assessment:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    client_signoff: "{{CLIENT_DPO_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:migration-strategy-generate $ARGUMENTS
```

## Review Gate

This is the GDPR / data-residency sign-off gate (Stage 1, D3). It clears only on the client DPO/legal's determination of the flagged items — RA cannot self-approve, because the lawful basis and retention ruling are the controller's to make. The carve-out's bulk copy of the historical window proceeds against the retention basis confirmed here.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact, `review` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact_id, `Data Residency Assessment` as artifact_name, and the `file` value from `artifacts.data_residency_assessment` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `data_residency_assessment` as artifact, `review` as action.
