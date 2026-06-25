---
description: Validate the data residency assessment — all required sections present and non-empty
argument-hint: <release-folder>
---

# Validate the data residency assessment — all required sections present and non-empty

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
description: Validate the data residency assessment — all required sections present and non-empty, processor-not-counsel framing intact
---

# Data Residency Assessment — Validate

## Purpose

Checks the data residency assessment for completeness: every required section is present and non-empty, the processor-not-counsel framing is intact, and the legal determinations are flagged for the client rather than asserted by RA. Produces a PASS/FAIL report.

## Prerequisites

- `migration/data_residency_assessment.md` exists (data_residency_assessment generate: complete)

## Validation Checks

**Check 1 — All required sections present and non-empty**
The document contains all seven sections, each with substantive content (not a placeholder heading):
1. Scope and purpose
2. Data inventory in scope
3. GDPR scope and lawful basis
4. Residency constraints for the target region
5. Historical-window legal review
6. Processor safeguards
7. Required client input / open legal questions
PASS: all seven present and non-empty. FAIL: list missing or empty sections.

**Check 2 — Processor-not-counsel framing present**
The document leads with the banner stating RA prepared it as data processor and that it is not legal advice; the controller/processor split is stated in the GDPR section.
PASS/FAIL.

**Check 3 — Legal determinations flagged, not asserted**
The lawful basis and the historical-window retention ruling are marked **[CLIENT DPO/LEGAL]**, not answered by RA. RA must not state a lawful basis as fact.
PASS: determinations flagged. FAIL: RA asserts a lawful basis or retention ruling without flagging it as the client's.

**Check 4 — Required client input section non-empty**
Section 7 lists at least the lawful basis and the historical-window retention ruling. It must never be empty.
PASS/FAIL.

**Check 5 — Target region and historical window stated**
The document states the target region (and BigQuery location) and the specific historical window (date range) being assessed, matching status.md.
PASS/FAIL.

**Check 6 — Historical-window review is specific**
Section 5 reviews the actual window being migrated — its date range, retention basis, and minimisation options — not a generic retention statement.
PASS/FAIL.

**Check 7 — Sign-off block present**
The document contains the sign-off block with both a client DPO/legal line and an RA line.
PASS/FAIL.

### Write validation report

Append a `## Validation` section to `migration/data_residency_assessment.md` with a per-check PASS/FAIL table and a "Gaps to address" list.

Update status:
```yaml
artifacts:
  data_residency_assessment:
    validate: pass | fail
    validated_date: "{{TODAY}}"
```

If PASS: `/wire:data-residency-assessment-review $ARGUMENTS`
If FAIL: fix gaps and re-run validate.


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact, `validate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact_id, `Data Residency Assessment` as artifact_name, and the `file` value from `artifacts.data_residency_assessment` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `data_residency_assessment` as artifact, `validate` as action.

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
