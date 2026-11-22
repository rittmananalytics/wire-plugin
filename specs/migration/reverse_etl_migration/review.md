---
wire_schema: "1.0"
command: review
artifact: reverse_etl_migration
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
  - artifact: reverse_etl_migration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Internal RA review of reverse ETL migration runbook
argument-hint: <release-folder> [--wave id]
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Reverse ETL Migration — Review

## Purpose

Internal RA review of the reverse ETL migration runbook before execution. Confirms SQL translations are correct, rebuild plans are feasible, the destination mapping is sound (decoy rows, and gate evidence for any `destination_mode: dedicated` rows), and the PR-gated cutover sequence is agreed (two client-merged PRs, or one under the `additive_dedicated_destination` topology).


The `migration_approach` vocabulary is the closed set in `specs/utils/reverse_etl_approach.md` (normative): `repoint`, `rewrite_model`, `rebuild`, `decommission`. There is no `retire` value.

## Flags

- `--wave <id>` — review the wave-labelled runbook (`reverse_etl_migration_runbook_{wave_id}.md`) instead of the unscoped one. Required once more than one wave's runbook exists.

## Prerequisites

- `migration/reverse_etl_migration_runbook.md` (or `_{wave_id}.md` under `--wave`) exists with `validate: pass`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about Hightouch, data activation, destination credentials, or sync cutover timing.

### Step 2: Present runbook for review

Summary to present:
- Topology (default: additive PR-gated syncs in the existing repo) and the rationale
- Total syncs in runbook by approach (repoint / rewrite_model / rebuild), plus any reclassified by the approach re-verification and any deferred by the scope gate
- Any SQL translations with non-trivial changes, and any drift-adjusted columns
- Customer Studio rebuilds and their estimated effort
- Lightning schema requirements and service account permissions
- Destination mapping (production → decoy IDs per decoy-mode sync; gate evidence per dedicated-mode sync) and the scoped credential
- The cutover plan: two PRs for decoy-mode syncs (PR B disable source-origin, PR C enable target-origin, merged together by the client), or one PR for dedicated-mode syncs (add new paused syncs + disable old, together)

### Step 3: Gather reviewer feedback

1. Are the SQL translations correct and do they preserve business logic — including any drift-adjusted columns?
2. Are the Customer Studio rebuild plans complete — are there any trait definitions, related models, or Journey steps that are missing?
3. Is the warehouse service account scoped correctly, and is the decoy-destination credential restricted to decoy targets only (no production-destination grant)?
4. Is the destination mapping complete — one decoy of the same destination type per in-scope decoy-mode sync, and per dedicated-mode sync the gate evidence that the destination exists and no existing sync writes to it — and are production destination IDs confirmed absent from the decoy-mode test syncs?
5. Is the cutover sequence agreed (two PRs for decoy-mode syncs: PR B disable source-origin, PR C enable target-origin, merged together; one PR for dedicated-mode syncs), and who on the client side owns the merge?

### Step 4: Apply feedback and record decision

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}}
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Capture corrections, agreed parallel-run period, credential rotation tasks]
```

### Step 5: Update status

```yaml
artifacts:
  reverse_etl_migration:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    wave_review:                 # set only when run with --wave, keyed by wave id
      B01: approved | changes_requested
```

### Step 6: Output next command

If approved:
```
/wire:equivalency-validate $ARGUMENTS
```
