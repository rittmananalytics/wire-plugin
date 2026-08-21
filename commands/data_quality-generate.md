---
description: Generate data quality tests
argument-hint: <project-folder>
---

# Generate data quality tests

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Generate data quality from design and requirements
argument-hint: <project-folder>
---

# data quality Generate Command

Follow `specs/utils/data_quality_engineer_delegate.md` before executing the workflow below.

## Purpose

Generate a data quality test plan for the release: confirm the baseline dbt schema-test coverage required by `wire/skills/dbt-development/testing-reference.md` is in place for every model, then propose supplemental statistical and distributional tests (using the `dbt_expectations` package) for business-critical models where uniqueness/not-null/relationships tests alone aren't enough to catch a bad refresh — a KPI silently going to zero, a distribution drifting, a date range with a gap.

## Usage

```bash
/wire:data_quality-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must be approved
- `dbt.generate` should be complete (this command reads the actual dbt project's models and `schema.yml` files — see Edge Cases if dbt isn't generated yet)

## Workflow

### Step 1: Read Inputs

**Process**:
1. Read `requirements/requirements_specification.md` — extract any named KPIs, metrics, or data quality expectations (e.g. "revenue should never be negative", "daily active users refreshed every day with no gaps")
2. Read `design/data_model.md` — expected entities, relationships, and grain
3. Read the dbt project's models and existing `schema.yml` files (`dbt/models/staging/`, `dbt/models/integration/`, `dbt/models/warehouse/`)
4. Read `dbt/packages.yml` (or equivalent) to check what test packages are already installed

### Step 2: Apply Baseline Test Coverage

Apply the minimum testing requirements from `wire/skills/dbt-development/testing-reference.md` as the floor for every model — this step never invents new test types, it only confirms the baseline is actually present:

| Layer | Primary key tests | Other required tests |
|-------|-------------------|----------------------|
| Staging | `unique` + `not_null` | `accepted_values` on enum/status fields |
| Integration | `unique` + `not_null` (or `dbt_utils.unique_combination_of_columns` for multi-source models) | `relationships` on foreign keys |
| Warehouse | `unique` + `not_null` | `relationships` on foreign keys, `accepted_values` on enum/status fields |

For every model missing baseline coverage, record it as a gap in the output document (Step 5) rather than silently fixing `schema.yml` — schema changes belong to `/wire:dbt-generate`/`/wire:dbt-validate`, not this command.

### Step 2.5: Confirm Unit Test Coverage

Unit tests are a distinct category from the schema tests in Step 2 and the dbt_expectations tests in Step 3 — they validate **transformation logic in isolation** (mock inputs → expected outputs), not production data quality. See `wire/skills/dbt-unit-testing/SKILL.md` for the Model-Inputs-Outputs pattern and format guidance.

Per the RA Convention in `wire/skills/dbt-development/testing-reference.md`: unit tests are **required** for warehouse-layer models containing business logic (case statements, window functions, multi-join logic, conditional aggregation, regex extraction, date-boundary calculations) and **recommended but optional** for staging models with non-trivial transformations.

Scan warehouse-layer models for these logic patterns and record any that lack a `unit_tests:` block as a gap in the output document — this command documents the gap, it does not author the unit test's mock inputs/outputs itself (that's a dbt-development task).

### Step 3: Propose Supplemental dbt-expectations Tests

For models that are **business-critical** — referenced by a named KPI/metric in `requirements/requirements_specification.md`, or a warehouse-layer fact table — baseline schema tests don't catch a bad refresh where the data is technically valid (unique, not null, in range) but wrong (a KPI collapsed to near-zero, a distribution shifted, a day's data never arrived). Propose tests from the [`dbt_expectations`](https://github.com/calogica/dbt-expectations) package, modeled on Great Expectations, to cover that gap:

| Category | Test | Use it for |
|----------|------|-------------|
| Table shape | `dbt_expectations.expect_table_row_count_to_be_between` | Sanity-check that a model's row count didn't collapse or explode between runs |
| Aggregate | `dbt_expectations.expect_column_mean_to_be_between` / `expect_column_sum_to_be_between` | KPI value sanity ranges (e.g. daily revenue sum stays within a plausible band) |
| Distributional | `dbt_expectations.expect_column_values_to_be_within_n_stdevs` | Anomaly detection on numeric KPI columns — flags a value that's statistically implausible even if in-range |
| Distributional | `dbt_expectations.expect_row_values_to_have_data_for_every_n_datepart` | Catches missing days/weeks in a time series — a silent gap that `not_null` tests can't see |
| Sets/ranges | `dbt_expectations.expect_column_values_to_be_between` | Numeric bounds beyond what a single `accepted_values` list can express (e.g. percentages must be 0–100) |
| String matching | `dbt_expectations.expect_column_values_to_match_regex` | Format validation on IDs, emails, or other structured string fields |

Only propose a supplemental test where there's a concrete signal to justify it (a named KPI, a known time-series grain, a documented format) — don't add statistical tests to every column indiscriminately. For each proposed test, record: model, column, test, package, purpose, and severity (`error` for KPIs named directly in requirements, `warn` for exploratory/nice-to-have checks — matching `testing-reference.md`'s severity conventions).

### Step 4: Check Package Prerequisites

If any test proposed in Step 3 uses `dbt_expectations` and the package isn't already declared in `dbt/packages.yml`:

```yaml
packages:
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]
```

Record this as a setup prerequisite in the output document — this command documents the requirement, it does not run `dbt deps` or edit `packages.yml` itself (that's a dbt-development task, done via `/wire:dbt-generate` or directly by the data team).

### Step 5: Generate Data Quality Test Plan

**File**: `.wire/releases/[release_folder]/test/data_quality.md`

```markdown
# Data Quality Test Plan: [Project Name]

**Generated**: [Date]
**dbt_expectations package required**: Yes | No
**dbt_expectations already installed**: Yes | No | N/A

## Baseline Coverage Gaps

Models missing required tests per `wire/skills/dbt-development/testing-reference.md` (to be fixed via `/wire:dbt-generate`/`/wire:dbt-validate`, not this document):

| Model | Layer | Missing Test | Required Test |
|-------|-------|---------------|----------------|
| [model_name] | staging | Primary key `unique` | `unique` |

*(Empty table means baseline coverage is already complete.)*

## Baseline Test Coverage (confirmed present)

| Model | Layer | Column | Test | Package | Severity |
|-------|-------|--------|------|---------|----------|
| [model]_pk | staging | [model]_pk | unique, not_null | dbt (native) | error |

## Unit Test Coverage Gaps

Warehouse-layer models with business logic (case statements, window functions, multi-join logic, conditional aggregation) that lack a `unit_tests:` block, per `wire/skills/dbt-unit-testing/SKILL.md`:

| Model | Logic Type | Required or Recommended |
|-------|------------|--------------------------|
| [model_fact] | Window function (row_number partition) | Required (warehouse layer) |

*(Empty table means unit test coverage is already complete for models with business logic.)*

## Supplemental dbt-expectations Tests (proposed)

| Model | Column | Test | Package | Purpose | Severity |
|-------|--------|------|---------|---------|----------|
| [kpi_fact] | [amount_column] | expect_column_values_to_be_within_n_stdevs | dbt_expectations | Anomaly detection on [KPI name] from requirements | warn |
| [kpi_fact] | [date_column] | expect_row_values_to_have_data_for_every_n_datepart | dbt_expectations | No missing days in daily-refreshed [KPI name] | error |

## Setup Prerequisites

- [ ] `dbt_expectations` package added to `packages.yml` and `dbt deps` run (only if any supplemental test above uses it)

## Next Steps

Apply the tests above to the corresponding `schema.yml` files, then run `dbt test` before validating this artifact.
```

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.data_quality section:
   ```yaml
   data_quality:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: 2026-02-13
     tests_count: [baseline tests confirmed + supplemental tests proposed]
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `data_quality`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `data_quality`
- `artifact_name`: `Data Quality Tests`
- `file_path`: `.wire/releases/[release_folder]/test/data_quality.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

**Output**:
```
## Data Quality Test Plan Generated Successfully

**Baseline coverage gaps found**: [N]
**Unit test coverage gaps found**: [N]
**Supplemental dbt-expectations tests proposed**: [N]
**dbt_expectations package required**: Yes | No

**File(s):** .wire/releases/[release_folder]/test/data_quality.md

### Next Steps

1. **Apply baseline coverage gaps** (if any) via `/wire:dbt-generate <project>`
2. **Add unit tests** for warehouse models with business logic (see `wire/skills/dbt-unit-testing/SKILL.md`)
3. **Add proposed schema.yml test entries** for the supplemental tests above
4. **Validate data quality**: `/wire:data_quality-validate <project>`
5. After validation, review: `/wire:data_quality-review <project>`
```

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### dbt Not Yet Generated

If `dbt.generate != complete`:
```
dbt models haven't been generated yet, so this command can't read real schema.yml files or model structure.

You can still generate a test plan from requirements alone (KPIs and expected grain), but baseline coverage confirmation (Step 2) will be skipped and re-run once /wire:dbt-generate completes.

Proceed with a requirements-only test plan? (y/n)
```

### No KPIs or Quality Expectations Named in Requirements

If `requirements_specification.md` names no specific KPIs or quality expectations:
```
No specific KPIs or data quality expectations found in requirements.

Generating baseline test coverage confirmation only (Step 2) — no supplemental dbt_expectations tests proposed, since there's no concrete signal (named KPI, stated grain, documented format) to justify one.

If there are quality expectations that should be added to requirements, note them now:
```

## Output

This command creates:
- `.wire/releases/[release_folder]/test/data_quality.md` — baseline coverage confirmation, gaps, and proposed supplemental dbt_expectations tests
- Updates `status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

## Log File Location

```
<DP_PROJECTS_PATH>/<project_folder>/execution_log.md
```

Where `<project_folder>` is the project directory passed as an argument (e.g., `20260222_acme_platform`).

## Format

If the file does not exist, create it with the header:

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail |
|-----------|---------|--------|--------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe |
```
