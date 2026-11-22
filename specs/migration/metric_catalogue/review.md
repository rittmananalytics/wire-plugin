---
wire_schema: "1.0"
command: review
artifact: metric_catalogue
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
    path: "audit/metric_catalogue.md"
    description: "Review section appended; rulings recorded in decisions.md and in the catalogue CSV"
  - type: report
    path: "audit/metric_catalogue.csv"
    description: "ruling, canonical_formula and target_name filled for every group"
preconditions:
  - artifact: metric_catalogue
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: "Experimental: Client ruling on the metric catalogue: one agreed definition and name per metric, recorded as decisions the Omni model implements"
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metric Catalogue: Review

## Purpose

> **Experimental.** The `looker_studio_to_omni` pair is experimental in 4.2.2. It reads undocumented Looker Studio endpoints and has not yet been run end to end into Omni on a client estate. The same steps serve `looker_studio_to_looker` (experimental), which has run end to end once into Looker on two reports, not on a client estate. At the start of every run of this command, tell the consultant this in one sentence, and record `experimental: true` against this artifact in `status.md`. Do not present its output to a client as final without the consultant's review.

The client's ruling on what each metric means. This is the gate that turns report-level definitions into one agreed set. The person ruling is the owner of the definitions (often a head of marketing or finance), not only the consultant. Under the release director model the orchestrating session presents each conflict as a ruling and records the outcome.

## Prerequisites

- `audit/metric_catalogue.md` exists with `validate: pass`

## Inputs

- `.wire/releases/$ARGUMENTS/audit/metric_catalogue.md` and `.csv`
- `.wire/releases/$ARGUMENTS/decisions.md`
- `.wire/releases/$ARGUMENTS/status.md`

## Workflow

### Step 1: Load meeting context

Follow `specs/utils/meeting_context.md`. Search for discussions about metric definitions, KPIs, attribution, revenue, ROAS, CTR, CPC, conversion rate, or numbers that "don't match" between reports.

### Step 2: Present the rulings

For each conflict, then each alias group, then the copies table, show the formulas, where each is used, and the proposal. For each `sum_of_ratio` finding, show the current and corrected forms and say that the reported number will change.

### Step 3: Record each ruling

For each group, record in `decisions.md` (one entry per conflict or alias group, using the standard ruling format with `Applies to: metric_catalogue`) and fill the CSV:

| Column | Value |
|---|---|
| `ruling` | `merge`, `rename`, `choose`, `keep_both` or `drop` |
| `canonical_formula` | the agreed formula, written over warehouse column names |
| `target_name` | the measure name in the target model (Omni, or LookML for `looker_studio_to_looker`), following the warehouse naming convention |

Clear the matching `parked_decisions` entries in `status.md`. If `business_rules.yaml` exists, add or update the agreed definitions there so later releases read the same set.

A group the client cannot rule on yet stays parked. The plan cannot be generated while a `conflict` is parked, because the model batch has nothing to build.

### Step 4: Record decision

```markdown
## Review

**Reviewed by**: {{REVIEWER_NAME}} (definition owner: {{OWNER_NAME}})
**Review date**: {{TODAY}}
**Decision**: approved | changes_requested

### Reviewer notes
[Rulings made, rulings parked, numbers the client has been told will change]
```

### Step 5: Update status

```yaml
artifacts:
  metric_catalogue:
    review: approved | changes_requested
    reviewed_by: "{{REVIEWER_NAME}}"
    reviewed_date: "{{TODAY}}"
    rulings_made: N
    rulings_parked: N
```

### Step 6: Output next command

If approved:
```
/wire:bi-migration-plan-generate $ARGUMENTS
```

If changes requested:
```
Apply the changes, then re-run:
/wire:metric-catalogue-validate $ARGUMENTS
```

## Review Gate

Approval means every metric in scope has one agreed definition and name, every conflict is ruled, and the client knows which numbers will change and why. `bi_equivalency` records a chart whose metric changed under a ruling as an accepted difference citing the ruling.

## Output Files

- Updated `.wire/releases/$ARGUMENTS/audit/metric_catalogue.md` (Review section)
- Updated `.wire/releases/$ARGUMENTS/audit/metric_catalogue.csv`
- Updated `.wire/releases/$ARGUMENTS/decisions.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log**: append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync**: follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metric_catalogue` as artifact, `review` as action.

3. **Document store**: follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `metric_catalogue` as artifact_id, `Metric Catalogue` as artifact_name, and the `file` value from `artifacts.metric_catalogue` in status.md as file_path.

4. **Auto-commit**: follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metric_catalogue` as artifact, `review` as action.
