---
wire_schema: "1.0"
command: generate
artifact: cutover
domain: migration
release_types:
  - platform_migration
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: dynamic
delegates_to:
  - utils/precondition_gate
description: Generate cutover runbook (SAFETY GATE — point of no return)

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: cutover` and `artifact_file_path: migration/cutover_runbook.md` before proceeding.

---

# Cutover — Generate

## Purpose

Generates the production cutover runbook — the step-by-step procedure for redirecting all production workloads from the source platform to the target platform. This is the point-of-no-return document. Once executed, the source platform is no longer the production system.

## Prerequisites

- `equivalency_validation.status: complete` (checks_failing == 0)
- OR explicit override in status.md with business justification for known differences

Under the verdict taxonomy (`equivalency-validate`), `checks_failing` counts objects whose latest verdict is `fail` or any `diff_*` with no recorded acceptance; `pass` and `pass_qualified` both count as passing. A `diff_*` verdict names its mechanism, which is exactly what the accepted-difference override documents — an object with no named mechanism (`fail`) should be investigated, not accepted.

## Inputs

- `.wire/releases/$ARGUMENTS/migration/migration_strategy.md`
- `.wire/releases/$ARGUMENTS/migration/ingestion_migration_runbook.md`
- `.wire/releases/$ARGUMENTS/migration/orchestration_migration_runbook.md`
- Latest equivalency report

## Workflow

### Step 1: Confirm prerequisites

Check `equivalency_validation.status` in status.md. If not `complete`:

If `checks_failing > 0` with no accepted_difference override:
```
Cutover is blocked: N equivalency checks are still failing.
All checks must pass (or be formally accepted) before the cutover runbook can be generated.

Run: /wire:equivalency-validate $ARGUMENTS
```

If there are accepted_difference objects: display a summary and confirm the user wants to proceed with known differences before continuing.

### Step 2: Build the pre-cutover checklist

Assemble from the migration strategy and all approved runbooks:

- [ ] All equivalency checks passing (or accepted differences formally documented)
- [ ] Fivetran target connectors active and syncing on schedule
- [ ] Target dbt project tested and passing all tests
- [ ] Target orchestration jobs created and passing manual test runs
- [ ] **Grants-first-or-pause** for any new project's DAGs (#219): where the orchestration platform deploys DAGs unpaused on merge, the new project's warehouse grants (DAG service account, datasets, write paths) are verified in place before any unpaused DAG deploys; otherwise the DAG ships paused and is unpaused only after grants are verified. An unpaused DAG deployed before its grants fails or half-builds the new project on its first scheduled tick.
- [ ] BI tool connection strings identified for update
- [ ] Client stakeholders notified of maintenance window
- [ ] **Full cutover rehearsal completed** on staging at production scale (see Step 2a)
- [ ] Rollback decision point agreed (time limit after which rollback is no longer viable)
- [ ] Source-platform decommission scheduled for after the rollback window (default 7–14 days post-cutover)

### Step 2a: Rehearsal (the single biggest de-risker)

The most common migration failure is a cutover that has never been run end to end before the live window. Before the real cutover, execute the entire timed sequence against a staging copy at production scale — same data volumes, same connection-string swaps, same orchestration activation, same smoke tests. Time each step.

The rehearsal proves three things: the sequence is correct and complete, the timings in the runbook are realistic, and the rollback procedure actually works. Record actual step durations and feed them back into the timed sequence below — replace the default T+ offsets with rehearsal-measured timings. A rehearsal that surfaces no surprises is the goal; one that does has paid for itself.

### Step 3: Build the cutover sequence

Generate a time-ordered runbook with:

1. **T-48h**: Final equivalency run and sign-off
2. **T-24h**: Notify all users and downstream consumers of the maintenance window
3. **T-0 (maintenance window start)**: Pause all writes to source platform
4. **T+15min**: Final row count comparison (source vs target)
5. **T+30min**: Update connection strings in BI tools and application configs
6. **T+45min**: Activate target orchestration job schedules
7. **T+60min**: Pause / archive source Fivetran connectors
8. **T+75min**: Smoke test — run key reports on target, compare outputs
9. **T+90min**: Open target platform to all users
10. **T+120min**: Go/no-go decision: full cutover confirmed OR rollback initiated

#### bi_migration releases

On a `bi_migration` release the warehouse does not change, so the sequence is about access and content, not connections and writes. Read `bi_migration.parallel_run_days` and the parity gate from `status.md`, then build:

1. **Parity gate**: every in-scope tile holds `pass` or `pass_qualified` in the register from `/wire:bi-equivalency-validate`. A `fail` or unresolved tile blocks the runbook; list them and stop.
2. **Parallel run**: Looker and Omni both live for `parallel_run_days` days (default 60). Omni content is published; Looker is unchanged. The register's dashboard rows carry `delivery_stage: in_pr` until users are switched.
3. **Access switch, group by group**: add users to the Omni groups from the permission map one group at a time, in the plan's order, with a check-in after each group. Record each switch in the runbook with its date.
4. **Schedules and alerts**: recreate each Looker schedule and alert against its Omni dashboard (from the content catalog's `schedule` and `alert` rows) and disable the Looker original once its Omni copy has delivered once.
5. **Looker read-only**: at the end of the parallel run, set Looker content to read-only and record the date. Nothing is deleted.
6. **Decommission**: a separate, scheduled step after the read-only period: export and archive the LookML repo and content, then remove Looker access.

### Step 4: Build the rollback procedure

**The true point of no return is the first successful production write to the target — not the clock.** Once a downstream system has written data to the target that does not exist on the source, a clean rollback is no longer possible; from that point, issues are resolved by fixing forward. The T+120min decision point is the deadline for making the rollback call *before* that happens. Order the sequence so smoke tests and validation complete before any production write lands on the target.

Document the full rollback procedure (valid until the first production write, and no later than T+120min):
1. Reactivate source Fivetran connectors
2. Revert BI tool connection strings
3. Pause target orchestration jobs
4. Notify users of rollback
5. Root cause analysis before retry

#### bi_migration releases

Rollback on a `bi_migration` release is re-enabling Looker access for the affected group, because nothing in the warehouse changed and Looker content was never edited. Order the rollback by the same groups as the access switch. A parity failure found after a group has switched is triaged like a data discrepancy above: fix forward in the Omni model or content when the tile can be corrected on the branch, roll the group back to Looker when it cannot. The decommission step never runs while any group is on Looker.

**Rollback decision tree** — not every issue warrants a rollback. Triage by type:

- **Data loss or corruption** → roll back immediately. No evaluation, no negotiation.
- **Performance regression** → evaluate, don't reflexively roll back. Under ~2× slower: optimise in place (clustering, partitioning, slot allocation). Over ~2× slower with no quick fix: roll back and investigate.
- **Minor data discrepancy** (within or near an accepted-difference tolerance) → fix forward. Run a reconciliation job; do not roll back for something a targeted fix resolves.
- **Cosmetic / non-blocking** (a non-critical report renders oddly) → log it, fix forward, proceed.

**Rollback window**: keep the source platform live and in a rollback-ready state for 7–14 days after cutover, not just until T+120min. The T+120min point ends the *fast* rollback option; the extended window covers issues that only surface under a full business cycle (month-end close, a weekly batch). Decommission the source only after the window closes with no rollback triggered — make decommission a distinct, scheduled step, never part of the cutover itself.

### Step 5: Write the runbook

**Output location**: `.wire/releases/$ARGUMENTS/migration/cutover_runbook.md`

Use the template at `TEMPLATES/migration/cutover_runbook.md`. Include:
- Pre-cutover checklist
- Timed cutover sequence
- Rollback procedure
- Communication templates (maintenance window notification, go-live announcement)
- Post-cutover monitoring checklist

### Step 6: Update status

```yaml
artifacts:
  cutover:
    generate: complete
    file: migration/cutover_runbook.md
    generated_date: "{{TODAY}}"
```

### Step 7: Output summary

```
Cutover runbook generated. This is the point-of-no-return document.

Review carefully before proceeding:
/wire:cutover-validate $ARGUMENTS
```


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `cutover` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `cutover` as artifact_id, `Cutover Runbook` as artifact_name, and the `file` value from `artifacts.cutover` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `cutover` as artifact, `generate` as action.
