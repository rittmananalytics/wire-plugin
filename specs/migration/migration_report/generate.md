---
wire_schema: "1.0"
command: generate
artifact: migration_report
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
  - artifact: cutover
    action: review
    outcome: approved
delegates_to:
  - utils/precondition_gate
description: Generate post-migration report

---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: migration_report` and `artifact_file_path: migration/migration_report.md` before proceeding.

---

# Migration Report — Generate

## Purpose

Generates the post-migration report summarising what was migrated, the final equivalency state, any known differences accepted, lessons learned, and recommendations for decommissioning the source platform. This is the final deliverable of the platform_migration release.

## Prerequisites

- `cutover review: approved`
- Cutover runbook executed (manual confirmation required)

## Flags

- `--lens defects` — produce the **defect-provenance lens** (see below) instead of the default post-migration summary. Reads the per-wave structured findings the migration gates already wrote and aggregates them; it does not re-run any gate. Writes a separate file (`migration/migration_report_defects.md`), leaving the default report untouched.
- `--client-caught <path>` — optional. A client-PR-review findings file (or a manual `client_caught` tally) logged back against a wave, feeding the client-caught count in the defects lens. When absent, client leakage is reported as "not tracked", never as 0. Ignored without `--lens defects`.

With no `--lens` flag the command behaves exactly as the Workflow below describes — the default post-migration report is unchanged.

## Workflow

### Step 1: Confirm cutover is complete

Ask: "Has the production cutover been executed?" Wait for explicit confirmation before proceeding.

### Step 2: Gather final state

Read:
- All 5 audit files — source platform object counts
- Migration inventory — scoped object counts and effort estimates
- Latest equivalency report — final check results
- Cutover runbook — actual cutover date and duration
- Loop history from status.md — how many equivalency cycles were required

### Step 3: Write the report

**Output location**: `.wire/releases/$ARGUMENTS/migration/migration_report.md`

Use the template at `TEMPLATES/migration/migration_report.md`. Include:

**Executive summary**:
- Migration completed on [date] from [source] to [target]
- N objects migrated: X connectors, Y tables, Z dbt models, W jobs
- Final equivalency state: N/N passing, N accepted differences
- Actual vs estimated effort
- Cutover duration

**What was migrated**:
- Per-category counts matching the migration inventory
- Key decisions made during migration (from audit reviews and strategy sign-offs)

**Equivalency outcomes**:
- Final equivalency report summary
- Accepted differences table (object, difference, business justification)
- Equivalency loop history (how many runs were needed)

**Issues encountered**:
- Issues discovered during migration with how they were resolved
- Any issues deferred to post-migration cleanup

**Lessons learned**:
- What worked well
- What would be done differently
- Recommendations for future migrations

**Source platform decommission plan**:
- Recommended timeline for decommissioning source platform
- Objects to retain on source platform (if any)
- Cost savings expected after decommission

### Step 4: Update status

```yaml
artifacts:
  migration_report:
    generate: complete
    file: migration/migration_report.md
    generated_date: "{{TODAY}}"
migration:
  status: complete
  completed_date: "{{TODAY}}"
```

### Step 5: Output next command

```
/wire:migration-report-validate $ARGUMENTS
```


## Defect-provenance lens (`--lens defects`)

Runs instead of Steps 2–3 above when `--lens defects` is supplied (Steps 1, 4, 5 and the hooks still apply). It answers one question across the migration: **where in the pipeline was each defect caught, and is the point of capture shifting left over successive waves?** It is a read-only aggregation over findings the gates already emit — it runs no gate and makes no fix/rule decisions.

### Inputs (whatever exists — a gate that never ran contributes nothing)

Per wave, read the structured findings each gate writes:
- `dbt-migration-lint` results — `migration/lint/wave_{id}_lint.md` / `.json` (rule-id findings).
- `dbt-migration-validate` Check 5 coverage report — the per-model all-code-path coverage table; an unchecked surface is a coverage gap, not a clean pass.
- `equivalency-validate` results — failing objects and their reason (`column_order_drift`, `governance_regression`, `deployment_type_divergence`, value/checksum drift, …).
- `dbt-migration-pre-pr-review` findings — `migration/pre_pr_review/wave_{id}_pre_pr_review.json` (Checks 1–6).
- `dbt-migration-fix` applied-fix summaries — `migration/pre_pr_review/{scope}_fix_report.md` (auto-fixed / escalated-propose / escalated-decision counts).
- **generate-inline** findings — defects `dbt-migration-generate` caught and resolved inline (Check B column-order, materialisation-hook drift, `-- MANUAL REVIEW REQUIRED` flags it raised), where recorded against the wave.
- **Optional** — the `--client-caught` input (a client-PR-review findings file logged back to the migration register, or a manual `client_caught` tally).

Pattern ids (`UNGUARDED_JSON_PARSE`, `DIV0_NULL_COERCION`, `COLUMN_ORDER_DRIFT`, …) and defect classes come from the **active platform pair** — treat them as data. Never hardcode a dialect's pattern list here; the lens aggregates whatever the gates emitted, so a new pair works unchanged.

### Aggregation (per wave)

1. **Stage-of-capture breakdown.** Attribute every distinct defect to the **earliest** gate that caught it, in pipeline order:

   `generate_inline < lint < validate < equivalency < pre_pr_review`

   A defect is identified by its `defect_id` if a gate emitted one, else by `model` + pattern id. The same defect legitimately recurs in several gates' outputs (a later gate re-detecting what an earlier one could have caught) — count it **once**, at its earliest sighting, so the breakdown measures where defects are actually being caught rather than double-counting. Break the counts down by defect class / pattern id. The subset attributed to `pre_pr_review` is the count that survived every earlier gate — the "reached the last internal gate" figure.

2. **Auto-fixed vs escalated split.** From the wave's `dbt-migration-fix` summary: `auto_fixed`, `escalated_propose`, `escalated_decision` (and their `escalated_total`).

3. **Client-caught count.** From the optional `--client-caught` input: the count of findings recorded against the wave **after our gates passed**. If the input is absent, record it as **"not tracked"** — never a silent 0. Leakage-to-client is stated explicitly, so a wave with no tracking is never mistaken for a wave with zero leakage.

4. **Wave-over-wave trend.** Emit the per-wave figures in wave order (total defects, reached-pre_pr_review, auto-fixed, escalated-total, client-caught) so the leftward shift — more caught at generate-inline/lint, fewer surviving to pre-PR review, zero reaching the client — or a regression is visible at a glance.

**Rule candidates (surface only).** A pattern that leaks to the client across two or more waves is listed as a rule candidate — a prompt for a human to consider a new gate rule. The lens never decides that a new defect class warrants a rule; that stays a human decision. It only surfaces the pattern and its wave history.

### Output

Write `.wire/releases/$ARGUMENTS/migration/migration_report_defects.md`. Structure:
- **Header**: the pipeline order used for earliest-gate attribution, the waves covered, and the note that this aggregates existing gate findings — it runs no gate.
- **Per-wave section**: the stage-of-capture table (by stage, broken down by pattern id / defect class), the auto-fixed vs escalated split, and the client-caught figure (integer or "not tracked").
- **Trend**: the wave-ordered rollup table.
- **Rule candidates**: patterns reaching the client in ≥2 waves, with their wave history — flagged for human review, not auto-actioned.
- **Coverage gaps**: any gate whose findings were unavailable for a wave — recorded as "not checked", never folded into a clean count.

### Status (defects lens)

```yaml
artifacts:
  migration_report:
    generate_defects: complete
    file_defects: migration/migration_report_defects.md
    generated_date: "{{TODAY}}"
```

## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_report` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `migration_report` as artifact_id, `Migration Report` as artifact_name, and the `file` value from `artifacts.migration_report` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `migration_report` as artifact, `generate` as action.
