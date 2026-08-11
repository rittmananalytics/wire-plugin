---
description: Generate deployment artifacts
argument-hint: <project-folder>
---

# Generate deployment artifacts

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
description: Generate deployment from design and requirements
argument-hint: <project-folder>
---

# deployment Generate Command

Follow `specs/utils/delivery_lead_delegate.md` before executing the workflow below.

## Purpose

Generate a deployment plan that takes the platform from "built" to "live": environment and credentials setup, a pre-flight pipeline health check, an ordered cutover sequence, and — for every step in that sequence — an explicit rollback action. `deployment/validate.md` already gates on pipeline connection health being checked before go-live; this command is what produces the plan that gate validates.

## Usage

```bash
/wire:deployment-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements must be approved
- Relevant design artifacts should be complete
- At least one of `pipeline`, `orchestration`, `dbt`, `semantic_layer`, `dashboards` should be complete (there's nothing to deploy otherwise)

## Workflow

### Step 1: Read Inputs

**Process**:
1. Read `requirements/requirements_specification.md` — extract environment names, access/credential requirements, and any stated go-live date or maintenance window
2. Read `status.md` to identify which development artifacts (`pipeline`, `orchestration`, `dbt`, `semantic_layer`, `dashboards`) are complete and need to be included in the cutover sequence
3. If `pipeline.generate == complete`, follow `wire/specs/utils/pipeline_tool_status.md` to get the current pipeline connection list and health — the deployment plan's connection references must match this, not be independently re-derived

### Step 2: Generate Environment & Credentials Section

- List each environment (e.g. dev/staging/prod, or client-specific names from requirements)
- List the credentials/access required per environment (warehouse service account, BI tool admin access, pipeline tool API keys) — sourced from `requirements_specification.md`'s stated scope, not invented
- Flag any credential requirement mentioned in requirements that has no corresponding environment entry yet

### Step 3: Generate Cutover Sequence

For every development artifact that's complete, add an ordered cutover step. Each step **must** have a paired rollback action — a step with no way to undo it needs an explicit "no rollback possible; requires [specific manual recovery]" note rather than a blank:

| Order | Step | Artifact | Rollback |
|-------|------|----------|----------|
| 1 | Verify pipeline connections healthy | pipeline | N/A — pre-flight check, not a cutover action |
| 2 | Deploy dbt models to production schema | dbt | `dbt run --target prod` failure: revert to previous production schema snapshot / re-point views to prior dataset |
| 3 | Switch orchestration schedule to production cadence | orchestration | Revert schedule to previous cadence / pause new jobs |
| 4 | Publish semantic layer / LookML to production | semantic_layer | Revert to previous LookML project commit |
| 5 | Point dashboards at production semantic layer | dashboards | Repoint dashboards at previous explore/model |

Order matters: pipeline health is always checked first (nothing downstream is trustworthy if ingestion is broken), dbt before semantic layer (the semantic layer depends on the warehouse), semantic layer before dashboards (dashboards depend on the semantic layer).

### Step 4: Generate Deployment Plan

**File**: `.wire/releases/[release_folder]/deploy/deployment_plan.md`

```markdown
# Deployment Plan: [Project Name]

**Generated**: [Date]
**Go-live date**: [from requirements, if stated]

## Environments & Credentials

| Environment | Purpose | Credentials Required |
|--------------|---------|------------------------|
| [prod] | [Live client-facing platform] | [Warehouse service account, BI admin access] |

## Pre-flight: Pipeline Connection Health

Per `wire/specs/utils/pipeline_tool_status.md`, current connection status:

| Connection | Status | Last Sync |
|------------|--------|-----------|
| [from pipeline_tool_status.md] | | |

**Gate**: deployment must not proceed past this section if any connection is `unhealthy` (see `deployment/validate.md` Step 2).

## Cutover Sequence

[Table from Step 3, in dependency order]

## Post-Cutover Verification

- [ ] Confirm dbt models materialized in production schema
- [ ] Confirm orchestration ran successfully on new schedule
- [ ] Confirm dashboards load and reflect production data
- [ ] Confirm no pipeline connection health regression since pre-flight
```

### Step 5: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.deployment section:
   ```yaml
   deployment:
     generate: complete
     validate: not_started
     review: not_started
     generated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `deployment`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `deployment`
- `artifact_name`: `Deployment Plan`
- `file_path`: `.wire/releases/[release_folder]/deploy/deployment_plan.md`
- `project_id`: the release folder path

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## deployment Generated Successfully

**Cutover steps**: [N]
**Steps with no rollback path**: [N] (flagged for manual recovery)

**File(s):** .wire/releases/[release_folder]/deploy/deployment_plan.md

### Next Steps

1. **Validate deployment**: `/wire:deployment-validate <project>`
2. After validation, review: `/wire:deployment-review <project>`
```

## Edge Cases

### Prerequisites Not Met

If requirements not approved:
```
Error: Requirements must be approved first.

Current status: [status]

Complete requirements approval: /wire:requirements-review <project>
```

### No Development Artifacts Complete

If none of `pipeline`, `orchestration`, `dbt`, `semantic_layer`, `dashboards` are complete:
```
Error: No development artifacts are complete yet, so there's nothing to deploy.

Complete at least one development artifact before generating a deployment plan.
```

### Pipeline Connections Already Unhealthy at Generation Time

If `pipeline_tool_status.md` reports `unhealthy` connections while generating the plan:
```
Warning: One or more pipeline connections are currently unhealthy: [list]

The deployment plan will still be generated, but /wire:deployment-validate will fail its pre-flight check until these are fixed. Fix connections now, or proceed with plan generation? (y/n)
```

## Output

This command creates:
- `.wire/releases/[release_folder]/deploy/deployment_plan.md` — environments/credentials, pipeline pre-flight status, ordered cutover sequence with paired rollback actions, and post-cutover verification checklist
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
6. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

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
