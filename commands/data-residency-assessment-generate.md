---
description: Generate the GDPR and data-residency assessment, including the historical-window legal review (tenant carve-out)
argument-hint: <release-folder>
---

# Generate the GDPR and data-residency assessment, including the historical-window legal review (tenant carve-out)

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
description: Generate the GDPR and data-residency assessment for a tenant carve-out — including the legal review of the historical data window (RA prepares as processor; client DPO/legal determines and signs off)
---

## Auto-Delegation

Follow `specs/utils/migration_agent_delegate.md` before executing the workflow below.
Follow `specs/utils/stale_artifact_check.md` with `artifact_id: data_residency_assessment` and `artifact_file_path: migration/data_residency_assessment.md` before proceeding.

---

# Data Residency Assessment — Generate

## Purpose

Produces `data_residency_assessment.md`: the GDPR and data-residency assessment for a tenant carve-out, including a specific legal review of retaining and handling the historical data window being migrated. It is a Stage 1 contractual deliverable with its own sign-off gate.

**This is a document RA prepares as the data _processor_, not legal advice.** RA structures the assessment and captures the technical facts it owns — what data is in scope, its volumes, the source→target region movement, the historical window, and the safeguards already designed into the migration. It does **not** determine the lawful basis or give legal advice. Every point requiring a legal determination is flagged inline as **[CLIENT DPO/LEGAL]** — the client is the controller, and its DPO/counsel owns those answers and the sign-off. Put this framing as a banner at the top of the generated document so no reader mistakes it for counsel's opinion.

This command runs only in **tenant carve-out** scope (`migration.scope == tenant_carveout`).

## Prerequisites

- `migration.scope == tenant_carveout` in status.md
- `migration_inventory review: approved` — the in-scope data is known
- `region_tagging review: approved` — the region boundary is adjudicated (the assessment is scoped to the adjudicated region)

If `scope` is not `tenant_carveout`, stop: "Data residency assessment runs in tenant carve-out scope only."

## Inputs

- `.wire/releases/$ARGUMENTS/status.md` — `migration.scope`, `migration.tenant_predicate`, target region/location, target platform
- `.wire/releases/$ARGUMENTS/migration/migration_inventory.md` — the data in scope and volumes
- `.wire/releases/$ARGUMENTS/migration/region_tags.csv` — adjudicated region classification
- `.wire/releases/$ARGUMENTS/audit/db_object_audit.md` — objects, volumes, and the historical date range of the data being migrated
- `.wire/releases/$ARGUMENTS/audit/security_audit.md` — sensitive/PII data flags and the access controls in scope
- `.wire/releases/$ARGUMENTS/migration/target_setup_scripts/04_security.sql` (if present) — the safeguards (tenant-scoped GRANTs, RLS, masking) RA can cite as processor measures

## Workflow

### Step 1: Load context

Read the inputs. Establish the target region (and BigQuery location), the tenant predicate, the personal-data objects in scope from the security audit, and the **historical window** — the date range of the data being migrated (from the db_object audit's date ranges, or confirm with the client where the audit does not carry it). Record the window explicitly (e.g. "~3 years: 2023-07 to 2026-06").

### Step 2: Draft the assessment sections

Author each section as prose. Where a section needs a legal determination RA cannot make, write what RA knows, then flag the open question as **[CLIENT DPO/LEGAL]** rather than answering it.

1. **Scope and purpose** — the carve-out, the target region, and the historical window under assessment.
2. **Data inventory in scope** — the datasets/tables carrying personal data, their volumes, the historical date range, and the source→target region movement. Note special-category data if any is flagged in the security audit.
3. **GDPR scope and lawful basis** — territorial scope, the data subjects and categories of personal data, and the controller/processor split (the client is controller; RA is processor). State the lawful-basis question and mark the determination **[CLIENT DPO/LEGAL]** — RA does not assert it.
4. **Residency constraints for the target region** — where target data lands (BigQuery location, e.g. EU), any cross-border transfer exposure (does any data leave the region in transit or at rest?), and data-localisation requirements. Flag transfer-mechanism decisions (e.g. SCCs) as **[CLIENT DPO/LEGAL]**.
5. **Historical-window legal review** — the specific review of retaining and handling the ~3-year window being migrated: retention basis, data minimisation, and whether the full window has a lawful basis to migrate or should be trimmed. RA lays out the window and the options; the retention/lawful-basis ruling is **[CLIENT DPO/LEGAL]**.
6. **Processor safeguards** — the technical measures RA implements as processor: tenant-scoped access, row-level security and masking (cite `04_security.sql`), encryption in transit/at rest, scoped service accounts, and alignment with the DPA. These are RA's to state.
7. **Required client input / open legal questions** — a consolidated list of every **[CLIENT DPO/LEGAL]** item. This section must never be empty — at minimum the lawful basis and the historical-window retention ruling are the client's to make.

### Step 3: Write the document

**Output location**: `.wire/releases/$ARGUMENTS/migration/data_residency_assessment.md`

Lead with the processor-not-counsel banner, then the seven sections above, then a sign-off block (completed at review):

```markdown
## Sign-off

This assessment was prepared by Rittman Analytics as data processor. The lawful-basis
determination, the historical-window retention ruling, and all items marked
[CLIENT DPO/LEGAL] are the client's (controller's) responsibility.

- All [CLIENT DPO/LEGAL] items addressed by the client: ☐
- Historical-window retention basis confirmed by the client: ☐

**Client DPO / legal sign-off**: ____________  **Date**: ________
**RA reviewer**: ____________  **Date**: ________
**Decision**: approved | changes_requested
```

### Step 4: Update status

```yaml
artifacts:
  data_residency_assessment:
    generate: complete
    file: migration/data_residency_assessment.md
    generated_date: "{{TODAY}}"
    target_region: "{{REGION}}"
    historical_window: "{{WINDOW}}"
    client_legal_items: N      # count of [CLIENT DPO/LEGAL] items flagged
```

### Step 5: Output next command

```
/wire:data-residency-assessment-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/migration/data_residency_assessment.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`


## Post-Execution Hooks

After updating `status.md`, run these in sequence:

1. **Execution log** — Append one row to `.wire/releases/$ARGUMENTS/execution_log.md` following `specs/utils/execution_log.md`.

2. **Jira sync** — Follow `specs/utils/jira_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact, `generate` as action.

3. **Document store** — Follow `specs/utils/docstore_sync.md`. Pass `$ARGUMENTS` as project_folder, `data_residency_assessment` as artifact_id, `Data Residency Assessment` as artifact_name, and the `file` value from `artifacts.data_residency_assessment` in status.md as file_path.

4. **Auto-commit** — Follow `specs/utils/commit.md`. Pass `$ARGUMENTS` as release_folder, `data_residency_assessment` as artifact, `generate` as action.

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
