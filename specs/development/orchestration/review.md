---
wire_schema: "1.0"
command: review
artifact: orchestration
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
  - enablement
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: orchestration
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
description: Review the orchestration layer with stakeholders — covers approach, asset/job coverage, and operational readiness
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

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

For Airflow, add the review tables of `wire/specs/development/pipeline/airflow/review.md` (review rules C6): rule findings with their dispositions, never blocking; the requirements table (`met`, `not met`, `can't tell`, with evidence), each `not met` raised as a question; and the tested-in-dev verdict if `/wire:utils-dev-test-evidence` has run.

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
