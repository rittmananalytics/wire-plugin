---
description: Search Confluence and Jira for project context
argument-hint: <project-folder> [artifact-name]
---

# Search Confluence and Jira for project context

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
description: Search Confluence pages and Jira issue comments for project context
argument-hint: <project-folder> [artifact-name]
---

# Atlassian Search Utility

## Purpose

Search Confluence for design documents, stakeholder feedback, and project context. Also search Jira issue comments for relevant discussions. Used alongside `meeting_context.md` during reviews, or standalone for ad-hoc document searches.

## Usage

```bash
/wire:utils-atlassian-search YYYYMMDD_project_name [artifact-name]
```

Can also be invoked automatically by review commands (Step 2.5).

## Prerequisites

- Atlassian MCP server must be configured (if not, skip gracefully)
- Project must exist with a valid `status.md`

## Workflow

### Step 1: Extract Search Context from Project

**Process**:
1. Read the project's `status.md`
2. Extract from YAML frontmatter:
   - `client_name` (e.g., "Acme Corporation")
   - `project_name` (e.g., "acme_marketing_analytics")
   - `current_phase` (e.g., "design", "development")
   - `jira.project_key` (if configured, e.g., "ACME")
   - `jira.epic_key` (if configured, e.g., "ACME-123")
3. Determine `artifact_name` from the second argument or calling context
4. Look up additional search keywords from the artifact keyword mapping table (same mapping as `meeting_context.md`)

### Step 2: Search Confluence

Execute CQL queries to find relevant pages. Run up to 3 searches and deduplicate results.

#### Search 1 — Client + artifact keywords:

```
searchConfluenceUsingCql:
  cql: "text ~ \"[client_name]\" AND text ~ \"[artifact_keyword]\""
  limit: 10
```

Example: `text ~ "Acme" AND text ~ "requirements"`

#### Search 2 — Project name:

```
searchConfluenceUsingCql:
  cql: "text ~ \"[project_name]\""
  limit: 10
```

Example: `text ~ "acme_marketing_analytics"`

#### Search 3 — Client + design/review context:

```
searchConfluenceUsingCql:
  cql: "text ~ \"[client_name]\" AND (text ~ \"design\" OR text ~ \"review\" OR text ~ \"feedback\")"
  limit: 10
```

Deduplicate all results by page ID across the three searches.

### Step 3: Read Top Confluence Pages

For the top 3-5 most relevant pages (prioritize by title match to artifact, then recency):

```
getConfluencePage:
  pageId: [page_id]
```

Extract key content sections relevant to the artifact under review.

### Step 4: Search Jira Issue Comments (if configured)

If `jira.epic_key` exists in status.md:

#### Search for issues with comments:

```
searchJiraIssuesUsingJql:
  jql: "project = [project_key] AND \"Epic Link\" = [epic_key] AND comment ~ \"[artifact_keyword]\""
  limit: 20
```

If the artifact has a `task_key` in the jira section:

```
searchJiraIssuesUsingJql:
  jql: "key = [task_key] OR parent = [task_key]"
  limit: 10
```

Read comments from matching issues to find feedback, decisions, and discussions.

### Step 5: Extract and Summarize Relevant Context

From the retrieved Confluence pages and Jira comments, extract:

**Design Decisions:**
- Decisions documented in Confluence pages
- Approach choices and rationale

**Stakeholder Feedback:**
- Feedback from Jira comments
- Review notes from Confluence pages

**Requirements & Constraints:**
- Requirements referenced in design documents
- Technical constraints or dependencies noted

**Open Questions:**
- Unresolved questions from Jira comments
- Items flagged for discussion in Confluence

### Step 6: Present Atlassian Context

Output the following (typically after the Fathom meeting context block):

```markdown
---

## Context from Confluence & Jira

**Confluence pages found**: [count] relevant pages
**Jira comments reviewed**: [count] comments across [count] issues

### Relevant Confluence Pages
| Page | Space | Last Updated | Key Points |
|------|-------|--------------|------------|
| [Title] | [Space] | [Date] | [1-line summary] |

### Design Decisions from Documentation
- [Decision 1] — from [Page title]
- [Decision 2] — from [Page title]

### Feedback from Jira Comments
- [Feedback 1] — [Commenter] on [Issue key], [Date]
- [Feedback 2] — [Commenter] on [Issue key], [Date]

### Open Questions
- [Question 1] — [Source]

---
```

### Step 7: Handle Edge Cases

**Atlassian MCP not available:**
```
Note: Atlassian context is not available (MCP server not configured).
Proceeding without Confluence/Jira context.
```

**No relevant pages or comments found:**
```
Note: No relevant Confluence pages or Jira comments found for this project/artifact.
Proceeding without Atlassian context.
```

**API errors or timeouts:**
```
Note: Could not retrieve context from Atlassian.
Proceeding without Confluence/Jira context.
```

In all edge cases, the calling command continues normally — Atlassian context is additive, never blocking.

## Artifact Keyword Mapping

Uses the same mapping as `meeting_context.md`:

| Artifact | Additional Search Keywords |
|----------|---------------------------|
| requirements | "requirements", "scope", "SOW", "deliverables", "acceptance criteria" |
| workshops | "workshop", "discovery", "kickoff", "clarification" |
| conceptual_model | "entities", "conceptual", "ERD", "business objects" |
| pipeline_design | "pipeline", "architecture", "data flow", "ETL", "ELT", "ingestion" |
| data_model | "dbt", "staging", "warehouse", "dimensions", "facts", "data model" |
| mockups | "dashboard", "mockup", "wireframe", "visualization", "layout" |
| pipeline | "pipeline", "code review", "data pipeline", "extraction" |
| dbt | "dbt", "models", "transformations", "SQL", "code review" |
| semantic_layer | "LookML", "semantic", "metrics", "measures", "explores" |
| dashboards | "dashboard", "report", "visualization", "Looker", "charts" |
| data_quality | "data quality", "testing", "validation", "dbt test", "accuracy" |
| uat | "UAT", "user acceptance", "sign-off", "stakeholder testing" |
| deployment | "deployment", "go-live", "production", "release", "cutover" |
| training | "training", "enablement", "workshop", "handover", "onboarding" |
| documentation | "documentation", "runbook", "handover", "knowledge transfer" |

## Output

This utility:
- Presents Confluence and Jira context to the reviewer before they provide feedback
- Does NOT modify any files or update status.md
- Is purely informational and additive to the review flow
- Fails gracefully if Atlassian is unavailable
- Can be run standalone via `/wire:utils-atlassian-search` for ad-hoc use

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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration_inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
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
