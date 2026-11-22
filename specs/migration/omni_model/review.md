---
wire_schema: "1.0"
command: review
artifact: omni_model
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
    description: "Records reviewer name and decision in status.md and the Review section of omni_model.md"
preconditions:
  - artifact: omni_model
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Release director review of the translated Omni model: per-batch summary, needs_human resolutions, topic design decisions, and the ruling that content migration may start"
argument-hint: <release-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Omni Model: Review

## Purpose

The release director's ruling on the translated model before any dashboard is built on it. The reviewer sees what was emitted, what the converter refused and how each refusal was resolved, and the topic design the batches settled on. Approval means content migration may start against these topics. A field or topic changed after approval sends its content batch back to generate, so this gate is worth the time.

This is an internal RA review under the release director model: one ruling, approve or changes. Client-side review of the model happens through the dashboards in `omni_content-review`, where the business sees numbers rather than YAML.

## Prerequisites

- `artifacts.omni_model.validate: pass` (every batch validated)

## Inputs

- `.wire/releases/$ARGUMENTS/migration/omni_model/omni_model.md`
- `.wire/releases/$ARGUMENTS/migration/omni_model/*/needs_human.json`
- `.wire/releases/$ARGUMENTS/migration/bi_migration_plan.md` (the rulings the batches applied)
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md` to retrieve any Fathom recordings relevant to this release. Search for discussions about the Looker model, explores, metric definitions, topic design or Omni. Surface extracts that bear on a topic's shape or a field's definition.

### Step 2: Present the model for review

Display:
- Batches: total, written, validated; views, topics and relationships emitted per batch
- needs_human: resolved by ruling, confirmed at validate, changed by hand, parked (with parked decision ids)
- Topic design: one topic per explore or a consolidated design, and where the batches departed from the plan's topic architecture
- Views emitted with `sql:` (derived tables) and views written by hand (query views for PDTs), each with its ruling reference
- Fields dropped (`redesign` with no emission) and the dashboards in `audit/looker_content_catalog.csv` that reference them
- Validator warnings carried over from validate

### Step 3: Gather the ruling

1. Do the topics match how the business asks questions, or did the explore-to-topic translation carry Looker's shape where a different one would serve better?
2. Is every parked `needs_human` item either resolved now or accepted as a known gap for content migration to work around? Name the decision for each.
3. Are the hand-written query views (PDT replacements) the right disposition, or should any move to dbt before content starts?
4. Do the dropped fields block any prioritised dashboard? If so, the ruling is changes, not approve.
5. Any field whose definition should go to `business_rules` before it is trusted?

Use `AskUserQuestion` for the outcome: Approved, Changes requested.

### Step 4: Apply feedback and record the decision

Incorporate corrections into `migration/omni_model/omni_model.md`. Record:

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Rulings on parked items, topic design decisions, known gaps accepted]
```

Every ruling made here is also appended to `decisions.md` at the moment it is made, so the gates that read rulings find it.

### Step 5: Update status

```yaml
artifacts:
  omni_model:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
```

### Step 6: Output next command

If approved:
```
/wire:omni-content-generate $ARGUMENTS --batch <first content batch id>
```

If changes requested:
```
Re-run the affected batch after applying the rulings:
/wire:omni-model-generate $ARGUMENTS --batch <batch_id>
```

## Review Gate

Approval confirms the model on the branch is the one dashboards will be built against: every in-scope field exists, every refusal has a recorded disposition, and the topic design is the release director's choice rather than the converter's default. Content migration reads the approved model; a later model change reopens the content batches that depend on it.

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `omni_model` as artifact_id, `Omni Model` as artifact_name, and the `file` value from `artifacts.omni_model` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `omni_model` as artifact, `review` as action.
