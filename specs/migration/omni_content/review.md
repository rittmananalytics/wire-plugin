---
wire_schema: "1.0"
command: review
artifact: omni_content
domain: migration
release_types:
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
produces:
  - type: status_update
    description: "Records reviewer name and decision in status.md and the Review section of omni_content.md"
preconditions:
  - artifact: omni_content
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review of the rebuilt Omni dashboards by URL, the skipped-tile and hand-finish lists, and the fidelity items, with the release director's ruling on whether the batch is ready for parity and client review
argument-hint: <release-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Content: Review

## Purpose

The rebuilt dashboards are now real documents in Omni. This review looks at them as a user would, by URL, and rules on what the programmatic rebuild left behind: skipped tiles, table fallbacks, styling, text tiles awaiting a hand rewrite. Numbers are not adjudicated here; that is `/wire:bi-equivalency-validate`'s job and its verdicts are the cutover gate. This gate is about whether the dashboards are complete enough to put in front of the client during the parallel run.

Two audiences are separated on purpose. This command is the internal RA ruling. Client sign-off happens through the parallel run recorded in the cutover runbook, dashboard by dashboard, and is captured as a ruling in `decisions.md` rather than by re-running this command under a client's name.

## Prerequisites

- `artifacts.omni_content.validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_content/omni_content.md`
- `.wire/releases/$ARGUMENTS/migration/omni_content/*/manifest.csv` (target URLs)
- `.wire/releases/$ARGUMENTS/migration/omni_content/*/plan.json` (skipped and fidelity lists)
- `.wire/releases/$ARGUMENTS/audit/looker_content_catalog.csv` (usage rank per dashboard)
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve Fathom recordings relevant to this release. Search for discussions naming specific dashboards, tiles, or reporting complaints. Surface extracts that bear on which dashboards matter most and what users said was wrong with the Looker versions.

### Step 2: Present the batch for review

Display, ordered by usage rank:
- Each created dashboard: title, Omni URL, Looker source id, tiles created, tiles skipped (by reason), fidelity notes
- The hand-finish list across the batch: text tiles with Liquid, unsupported calculations, table fallbacks, styling
- Dashboards parked on a redesign or collision ruling
- Any dashboard whose usage rank is in the top quartile and carries a skipped tile: these are the ones a client will notice first

### Step 3: Gather the ruling

1. Open the top five dashboards by usage. Does each read as the Looker original would to its owner? Note anything a user would call missing.
2. For each skipped tile on a prioritised dashboard: hand-finish now, hand-finish before cutover, or accept as dropped? Record the choice per tile.
3. Are the table fallbacks acceptable for the parallel run, or does any need a chart type added to the pair's mapping table (an engagement override) and a re-plan?
4. Any redesign rulings still parked that should be made now?
5. Which dashboards go into the client parallel run first?

Use `AskUserQuestion` for the outcome: Approved, Changes requested.

### Step 4: Apply feedback and record the decision

Record in `migration/omni_content/omni_content.md`:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Per-tile hand-finish rulings, fallbacks accepted, parallel-run order]
```

Append each ruling to `decisions.md` as it is made.

### Step 5: Update status

```yaml
artifacts:
  omni_content:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    hand_finish_open: N
```

### Step 6: Output next command

If approved:
```
/wire:bi-equivalency-validate $ARGUMENTS
```
(parity may already have started per batch; this confirms the full scope)

If changes requested:
```
/wire:omni-content-generate $ARGUMENTS --batch <batch_id>
```

## Review Gate

Approval confirms every created dashboard is complete enough for the parallel run, every skipped tile has a hand-finish ruling, and the parallel-run order is set. It does not assert the numbers match; `bi_equivalency` does that, and cutover waits on both.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_content` as artifact_id, `Omni Content` as artifact_name, and the `file` value from `artifacts.omni_content` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_content` as artifact, `review` as action.
