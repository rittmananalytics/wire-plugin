---
description: Validate requirements matrix completeness and tag consistency
argument-hint: <release-folder>
---

# Validate requirements matrix completeness and tag consistency

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Validate the requirements matrix for completeness and tag consistency
---

# Requirements Matrix — Validate

## Purpose

Checks that the requirements matrix is internally consistent, has no missing tags, and accurately reflects the source interviews. Flags rows where the source-stakeholder count looks wrong, where domain/tag combinations are inconsistent, and where conflicts have been silently picked instead of surfaced.

## Inputs

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix.md`
- All `.wire/releases/$ARGUMENTS/planning/interviews/*.md`

## Workflow

### Step 1: Locate

Resolve `$ARGUMENTS`. Read the matrix and every interview file.

### Step 2: Row-level checks

For every row in the matrix:
- [ ] `Req ID` matches `^R-[A-Z][A-Z0-9-]+-\d{2}$` and is unique
- [ ] `Domain` matches the domain tag in the row (and is in the in-scope domain list)
- [ ] `Type` is one of `pain` `requirement` `kpi` `risk` `existing-asset`
- [ ] `Hierarchy` is one of `collect` `clean` `define-track` `analyse` `optimise-predict`
- [ ] `PPT axis` is one of `people` `process` `technology`
- [ ] `Title` is non-empty
- [ ] `Description` is non-empty and does not contain TODO or `<placeholder>`
- [ ] `Verbatim quote` is non-empty AND can be found verbatim (case-insensitive) in at least one source interview file
- [ ] `Source stakeholders` list is non-empty
- [ ] Every named source stakeholder appears in the stakeholder map
- [ ] `Count` matches the number of source stakeholders listed
- [ ] `Sponsor backing` is `Y` iff one of the source stakeholders is the sponsor
- [ ] `MoSCoW` and `Phase` are `TBD` (must remain unset until after the three analyses)
- [ ] `Confidence` is one of `High` `Medium` `Low`

### Step 3: Cross-row checks

- [ ] Every interview file is referenced as a source on at least one row (else the file contributed nothing — investigate)
- [ ] No two rows have an identical `Title` + `Domain` (would indicate failed de-duplication)
- [ ] **Coverage**: every in-scope domain has at least one row tagged to it. Domains with fewer than 3 rows are flagged WARNING.
- [ ] **Conflict surfacing**: every contradiction noted in any individual interview write-up (look for phrases like "disagrees", "differs from", "conflicts with") appears in the Conflicts log, OR explicitly in the `Conflicts / open questions` column of a row

### Step 4: Tag distribution sanity

- [ ] At least one row at each Hierarchy tier OR an explicit note in the matrix body saying "no requirements at tier X — foundations are fine / not yet reached"
- [ ] All three PPT axes have at least one row
- [ ] If 80%+ of rows are at a single Hierarchy tier (e.g. all `clean`), this is flagged WARNING — it may be diagnostically correct, but the analyses prose should call this out explicitly

### Step 5: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/requirements_matrix_validation.md`

```markdown
# Requirements Matrix Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}
**Rows checked**: {{N}}

## Result: PASS / FAIL / PASS WITH WARNINGS

## Row-level failures

| Req ID | Issue |
|---|---|
| R-RETAIL-03 | Verbatim quote not found in any source interview file |
| R-FINANCE-02 | Count = 3 but only 2 source stakeholders listed |

## Coverage

| Domain | Row count | Status |
|---|---|---|
| Retail | 12 | ✅ |
| Fulfilment | 2 | ⚠️ Under-represented |
| Finance | 7 | ✅ |

## Tag distribution

[Hierarchy and PPT count tables as shown in the matrix, repeated here for the report. Flag any axis or tier with 0 rows.]

## Conflicts log audit

- 4 conflict mentions found in interview files
- 4 appear in the matrix Conflicts log → ✅

## Next Steps

[If PASS]:
Internal RA review of the matrix:
/wire:requirements-matrix-review $ARGUMENTS

[If FAIL]:
Fix the listed row issues and re-run validation.
```

### Step 6: Update status

```yaml
artifacts:
  requirements_matrix:
    validate: complete   # or "failed"
```

### Step 7: Output summary

Show top 3 issues with Req IDs.

## Output Files

- `.wire/releases/$ARGUMENTS/planning/requirements_matrix_validation.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

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
