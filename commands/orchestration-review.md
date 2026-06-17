---
description: Review orchestration setup with stakeholders
argument-hint: <project-folder>
---

# Review orchestration setup with stakeholders

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
description: Review the orchestration layer with stakeholders — covers approach, asset/job coverage, and operational readiness
argument-hint: <project-folder>
---

# Orchestration Review Command

## Purpose

Present the orchestration layer design to the technical lead or client for approval. This review covers the chosen orchestration tool, the asset/job graph, schedule cadences, and operational considerations.

## Prerequisites

- `orchestration` validate must be complete (status: `complete` not `failed`)

## Workflow

### Step 1: Load Context

1. Read `.wire/<project_id>/status.md` — confirm `orchestration.validate: complete`
2. Read the tool-specific setup doc depending on `orchestration_tool`:
   - `dagster`: read `dagster_setup.md`
   - `dbt_cloud`: read `dbt_cloud_config.md`
   - `airflow`: read `airflow_setup.md`, `airflow_connections.md`, `airflow_variables.md`
3. Read `.wire/<project_id>/development/orchestration/.orchestration_validation.md` for validation findings
4. Read `.wire/<project_id>/design/pipeline_design.md` for run cadences and source systems

### Step 2: Search Meeting Context

Search for relevant meeting context using the Fathom MCP server (`specs/utils/meeting_context.md`):
- Search terms: "orchestration", "dagster", "dbt cloud", "airflow", "scheduling", "pipeline execution", "job scheduling", "data freshness"
- Note any prior decisions or concerns about orchestration tool choice

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `orchestration`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `orchestration`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - This retrieves any reviewer comments added to the document store page since generation, and flags any edits made directly to the document store version vs the canonical GitHub version
   - Surface the returned "Document Store Context" block to the reviewer alongside Fathom and Confluence context
4. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Present Review Summary

Present a structured summary for the reviewer:

```markdown
## Orchestration Review: <project_name>

**Tool chosen**: <Dagster | dbt Cloud | Airflow>
**Validation**: PASS
**Meeting context**: [any relevant prior discussions]

### What Was Built

[2-3 sentence summary of the orchestration setup]

### Asset / Job Coverage

<For Dagster>
| Asset Group | Assets | Cadence |
|------------|--------|---------|
[one row per group]

<For dbt Cloud>
| Job | Trigger | Models in scope |
|-----|---------|----------------|
[one row per job]

<For Airflow>
| Task ID | Type | Upstream tasks | Cadence |
|---------|------|---------------|---------|
[one row per task]

### Schedule Cadences

[Table: cadence name, frequency, assets/models, timezone]

### Operational Considerations

- **Monitoring**: [how failures will be detected and alerted]
- **Retry policy**: [any retry/backfill strategy]
- **Secrets management**: [how credentials are handled]
- **Local dev**: [how developers run the pipeline locally]

### Open Questions

[Any items requiring stakeholder input before approval]
```

### Step 4: Gather Review Feedback

Ask the reviewer:

```
Please review the orchestration setup above.

1. Is the orchestration tool choice (Dagster / dbt Cloud / Airflow) correct for this project?
2. Do the schedule cadences match the agreed SLAs from the requirements?
3. Are there any missing source systems or dbt models that should be orchestrated?
4. Any concerns about operational readiness?

Outcome:
- Approved — orchestration is ready for deployment
- Changes requested — describe what needs to change
- Needs discussion — flag the topic for a follow-up conversation
```

### Step 5: Record Outcome

**If Approved**:

Update `.wire/<project_id>/status.md`:
```yaml
orchestration:
  review: approved
  review_date: <today>
  reviewer: <reviewer_name>
```

Output:
```
## Orchestration Approved ✓

Orchestration layer is approved and ready for deployment.

Next step: `/wire:deployment-generate <project>` — include orchestration setup in the deployment runbook
```

**If Changes Requested**:

Record the feedback in status.md notes, set `review: not_started`, and output required changes.

**If Needs Discussion**:

Record the open topics in status.md notes and output next steps for resolution.

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `orchestration`
- Action: `review`
- Status: `approved` / `changes_requested` / `discussion`

### Step 7: Sync to Document Store (Optional)

If a document store is configured and the review outcome is **Approved**, follow `specs/utils/docstore_sync.md` to overwrite the document store page with the canonical file. This ensures the document store reflects the approved version.

- If the outcome is Changes Requested or Needs Discussion, do not overwrite — the document store retains the reviewed version for reference until the next generate run.

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
