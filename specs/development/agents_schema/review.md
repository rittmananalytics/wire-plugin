---
wire_schema: "1.0"
command: review
artifact: agents_schema
domain: development
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - dashboard_extension
  - agentic_data_stack
  - bi_migration
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions:
  - artifact: agents_schema
    action: validate
    outcome: PASS
delegates_to:
  - utils/precondition_gate
  - utils/meeting_context
  - utils/atlassian_search
  - utils/docstore_fetch
  - utils/jira_sync
  - utils/docstore_sync
description: Review the Agents Schema publication with stakeholders — what the warehouse AGENTS schema now tells an agent, the skills published under the client's provider name, the workflow that keeps it current; approval or change requests recorded
argument-hint: <release-folder>
---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# agents_schema Review Command

## Purpose

Present the publication for stakeholder sign-off and record the outcome. The things a reviewer decides here are what an agent will be told about their warehouse: which providers describe it, what the skills say, and under whose name. A review is never run without a person's decision (`specs/utils/director_operating_model.md`, "Review as a ruling").

## Usage

```bash
/wire:agents_schema-review 01-dbt-foundation
```

## Prerequisites

- `agents_schema.validate == pass` (enforced by the precondition gate)

## Workflow

### Step 1: Verify Prerequisites

Read `status.md`. If the verdict was PASS WITH WARNINGS, list the warnings first: a `pending_ci` publication means the warehouse checks have not run, and the reviewer approves the plan and the files, not the warehouse contents.

### Step 2: Present for Review

```
## Agents Schema Review Session

**Project:**      [PROJECT_NAME]
**Destination:**  <type> · schema AGENTS · agents_schema <tag>
**Published:**    ran <date> | pending CI (first run after the secrets are added)
**Workflow:**     .github/workflows/agents-schema.yml
**Report:**       dev/agents_schema_generation_report.md

| Provider | Source | Rows published (or planned) | Tables |
|---|---|---|---|

| Skill | Source | uses: | Decisions |
|---|---|---|---|
```

Walk the reviewer through what an agent will see, in the order an agent reads it: the `AGENTS.ROOT` rows (the providers and their overview text, then the skill rows under the client's provider name), then the warehouse guide as published, then one worked example: the built-in analyst skill's own procedure, `SELECT provider, key, content FROM AGENTS.ROOT ORDER BY provider, key`, followed by the metric lookup a stakeholder's question would need. Where the publication is pending, show the guide and the skills from the repository and the `checks.sql` queries that will confirm the publication.

The things worth their attention are the ones a script could not decide: the business definitions and caveats written into the guide, the knowledge files published and the ones dropped, the provider name, and anything Check 9 listed as another publisher.

### Step 2.5: Retrieve External Context (Optional)

1. Follow `specs/utils/meeting_context.md` with artifact name `agents_schema`: decisions in recorded meetings about what agents may and may not be told, and about metric definitions.
2. Follow `specs/utils/atlassian_search.md` with artifact name `agents_schema`.
3. If a document store is configured, follow `specs/utils/docstore_fetch.md` for reviewer comments on the generation report.
4. If none is available, go to Step 3.

### Step 3: Gather Feedback

Use AskUserQuestion:

```json
{
  "questions": [{
    "question": "What is the review outcome?",
    "header": "Review Status",
    "options": [
      {"label": "Approved", "description": "The publication is complete and approved"},
      {"label": "Changes requested", "description": "The skills, the provider set or the workflow need revisions"},
      {"label": "Needs discussion", "description": "Requires clarification"}
    ],
    "multiSelect": false
  }]
}
```

### Step 4a: If Approved

Ask who approved (name and role). Update status:

```yaml
agents_schema:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "[Reviewer]"
  reviewed_date: "{{TODAY}}"
```

```

On Claude Code the same approval can be recorded with no model turn: `/wire-approve <artifact> --final [--as internal|client] [--evidence <url>]` (the Wire mod, wire#270) sets `review: approved`, `reviewed_by` and `reviewed_date` as this step does and appends the approval to the artifact's `review_events` list, which this command does not write. Without `--final` it records the event alone and leaves the review state to this command.

## Agents Schema publication approved

**Reviewed by:** [Reviewer]

### Next Steps
1. Commit the workflow, agents.yml and agents_schema/skills/ on the release branch and open the PR (/wire:utils-pr-create <release>); with lookml_repo set, also commit dev/agents_schema/lookml_repo/agents-schema-lookml.yml to that repository as .github/workflows/agents-schema-lookml.yml and make sure it has the WAREHOUSE_CREDENTIALS secret
2. If status.md has no secrets_set: the repository owner adds WAREHOUSE_CREDENTIALS [and DBT_PROFILES_YML] to the Actions secrets (or re-run generate and accept the Step 5.5 offer); the workflow runs on the next push to <branch>, or by hand from the Actions tab
3. After the first run: /wire:agents_schema-validate <release> to confirm the warehouse, then record published_date in status.md
4. Consumers install the agents-schema plugin (claude plugin marketplace add dbt-labs/agents_schema; claude plugin install agents-schema@agents-schema) and start from AGENTS.ROOT
```

### Step 4b: If Changes Requested

Record each change as a numbered item with the skill, provider or file it applies to, and who asked for it. Update status:

```yaml
agents_schema:
  review: changes_requested
  review_feedback:
    - "[Change 1]"
  reviewed_by: "[Reviewer]"
  reviewed_date: "{{TODAY}}"
```

```
## Agents Schema publication: changes requested

### Change requests
1. [skill / provider / file]: [change] (asked by [who])

### Next Steps
1. Apply the changes: a skill edit goes straight into agents_schema/skills/; a change to what a model exposes goes back to /wire:dbt-generate <release>; a provider added or removed re-runs /wire:agents_schema-generate <release> --force-workflow (never --force, which rewrites the completed guide)
2. /wire:agents_schema-validate <release>
3. /wire:agents_schema-review <release>
```

The guide and the skills are edited, never regenerated with `--force`, to apply a change to their text: `--force` rewrites the guide draft and loses the completed sections.

### Step 5: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` with artifact `agents_schema`, action `review`, and the outcome.

### Step 6: Sync to Document Store (Optional)

If a document store is configured, follow `specs/utils/docstore_sync.md` with `artifact_id: agents_schema`, `artifact_name: Agents Schema publication`, `file_path: .wire/releases/[release_folder]/dev/agents_schema_generation_report.md`.

## Output

The status update, the approval or change list, and:

```
Ran: /wire:agents_schema-review <release>
```
