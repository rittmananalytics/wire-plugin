---
wire_schema: "1.0"
command: review
artifact: metabase_carveout
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
  - artifact: metabase_carveout
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Human approval gate for the Metabase carve-out — adjudicate the layer decisions, sign off manifest rows, resolve manual-review cards; blocks on any unresolved card
argument-hint: <release-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Metabase Carve-out — Review

## Purpose

The human gate between the proposed carve and any write. The reviewer adjudicates the **layer decisions** (they are strategy: sandboxing vs warehouse view vs dashboard parameter vs card edit changes who can ever see other tenants' rows), signs off manifest rows, and resolves the manual-review queue. No card or dashboard is transformed until its row is signed off here.

## Prerequisites

- `metabase_carveout validate: pass`

## Workflow

### Step 1: Present the carve summary

Cards and dashboards in scope; the layer-decision distribution with reasons; dashcards removed (and why each card had no tenant data); shared-card decisions; the manual-review queue.

### Step 2: Adjudicate the layer decisions

Per card-set group, the reviewer confirms or overrides the proposed layer. An override re-routes the group (e.g. from `card_edit` to `sandboxing`) and sends the manifest back through generate for that group — the reviewer rules, the command re-derives.

### Step 3: Resolve the manual-review queue

Every `manual_review_required` card (unresolved tenant mechanism) blocks approval until resolved one of two ways: a registry ruling lands (route to `region-tagging-review` — the mechanism is an estate-wide fact, not a per-card fix) and the card re-runs through generate; or an explicit signed-off disposition is recorded here with a rationale (e.g. `remove_dashcard` for a card the tenant does not need).

Blocking message: `[wire] N manual-review card(s) unresolved. Address each before approving.`

### Step 4: Sign off manifest rows

The reviewer signs rows `proposed → signed_off` (individually or by group). Only signed rows are ever applied. A diff sample of edited card SQL (before/after around the injected filter) is presented so injections are confirmed by eye, not just by check result.

### Step 5: Record decision and update status

```yaml
artifacts:
  metabase_carveout:
    review: approved | changes_requested
    reviewed_by: "<name>"
    reviewed_date: "{{TODAY}}"
    rows_signed_off: N
    manual_review_dispositions: N
```

### Step 6: Output next command

On approval:

```
Apply the signed-off manifest (decoy copies first), then prove the carve:
/wire:metabase-equivalency-validate $ARGUMENTS
```

When the tenant runs on its own, separately-hosted Metabase instance, transport the signed-off objects onto it first, then prove the carve:

```
/wire:metabase-carveout-transport $ARGUMENTS
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `metabase_carveout` as artifact, `review` as action.

3. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `metabase_carveout` as artifact, `review` as action.
