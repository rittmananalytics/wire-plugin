---
description: Retrieve Fathom meeting context for artifact reviews
argument-hint: <project-folder> [artifact-name]
---

# Retrieve Fathom meeting context for artifact reviews

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.agent_v2` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.agent_v2/` in specs refers to the `.agent_v2/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Retrieve relevant meeting context from Fathom for artifact reviews
argument-hint: <project-folder> [artifact-name]
---

# Meeting Context Retrieval Utility

## Purpose

Search Fathom meeting transcripts to find feedback, decisions, concerns, and action items from stakeholder meetings relevant to the artifact currently under review. Provides reviewers with context from past discussions before they give their verdict.

## Usage

```bash
/dp:utils:meeting-context YYYYMMDD_project_name [artifact-name]
```

Can also be invoked automatically by review commands (Step 2.5).

## Prerequisites

- Fathom MCP server must be configured (if not, skip gracefully)
- Project must exist with a valid `status.md`

## Workflow

### Step 1: Extract Search Context from Project

**Process**:
1. Read the project's `status.md`
2. Extract from YAML frontmatter:
   - `client_name` (e.g., "Acme Corporation")
   - `project_name` (e.g., "acme_marketing_analytics")
   - `current_phase` (e.g., "design", "development")
3. Determine `artifact_name` from the second argument or calling context (e.g., "requirements", "data_model", "pipeline")
4. Determine the search start date:
   - If the artifact has a `reviewed_date`, use that (find meetings since last review)
   - Otherwise use `created_date` from the project
5. Look up additional search keywords from the artifact keyword mapping table (see below)

### Step 2: Search for Relevant Meetings

Execute a two-phase search to maximize coverage.

#### Phase 1: Keyword Search

Use `search_meetings` (via the Fathom MCP server) with targeted terms. Run up to 3 searches and deduplicate results by recording ID.

**Search 1 — Client + artifact type:**
```
search_term: "[client_name] [artifact_name]"
```
Example: `"Acme requirements"` or `"Hunky Moller data model"`

**Search 2 — Project name:**
```
search_term: "[project_name]"
```
Example: `"acme_marketing_analytics"`

**Search 3 — Client + review keyword:**
```
search_term: "[client_name] review"
```
Example: `"Acme review"`

Deduplicate all results by `recording_id` across the three searches.

#### Phase 2: Date-Filtered Listing

Use `list_meetings` to find recent meetings within the relevant time window.

**Client-facing meetings:**
```
created_after: [search_start_date in ISO 8601]
limit: 20
```

**Internal meetings:**
```
created_after: [search_start_date in ISO 8601]
meeting_type: "internal"
limit: 20
```

Filter internal meeting results to those whose titles contain any of:
- The client name
- "review"
- "design"
- The artifact name or its keywords

Merge Phase 1 and Phase 2 results, deduplicating by recording ID.

#### Phase 3: Retrieve Key Transcripts

For the top 3-5 most relevant meetings (prioritize by title match to artifact, then recency, then client attendee presence), retrieve transcripts:

```
get_meeting_transcript:
  recording_id: [meeting_id]
```

### Step 3: Extract and Summarize Relevant Context

From the retrieved transcripts and meeting summaries, extract:

**Decisions Made:**
- Decisions about this artifact or related design choices
- Approvals or rejections from past review sessions

**Concerns Raised:**
- Stakeholder concerns about approach, scope, or quality
- Technical concerns from internal team discussions
- Client questions or objections

**Action Items:**
- Outstanding actions related to this artifact
- Follow-ups promised but not yet completed

**Feedback Themes:**
- Recurring themes across multiple meetings
- Priority shifts or scope changes discussed

### Step 4: Present Meeting Context

Output the following between the review command's "Present Artifact" and "Gather Feedback" steps:

```markdown
---

## Meeting Context from Fathom

**Meetings analyzed**: [count] meetings from [start_date] to today
**Relevance**: [High/Medium/Low] based on number of direct references found

### Key Decisions from Previous Meetings
- [Decision 1] — [Meeting title], [Date]
- [Decision 2] — [Meeting title], [Date]

### Outstanding Concerns
- [Concern 1] — raised by [Who] in [Meeting] on [Date]
- [Concern 2] — raised by [Who] in [Meeting] on [Date]

### Open Action Items
- [ ] [Action item] — Owner: [Name], Due: [Date]
- [ ] [Action item] — Owner: [Name], Due: [Date]

### Feedback Themes
- **[Theme]**: [Brief summary of recurring feedback]

### Relevant Meeting References
| Date | Meeting | Key Points |
|------|---------|------------|
| [Date] | [Title] | [1-line summary] |

---
```

### Step 5: Handle Edge Cases

**Fathom MCP not available:**
```
Note: Fathom meeting context is not available (MCP server not configured).
Proceeding with standard review.
```

**No relevant meetings found:**
```
Note: No relevant meeting recordings found for this project/artifact in Fathom.
Proceeding with standard review.
```

**API errors or timeouts:**
```
Note: Could not retrieve meeting context from Fathom.
Proceeding with standard review.
```

In all edge cases, the review command continues normally — meeting context is additive, never blocking.

## Artifact Keyword Mapping

Use these additional keywords when searching for meetings related to specific artifacts:

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
- Presents meeting context to the reviewer before they provide feedback
- Does NOT modify any files or update status.md
- Is purely informational and additive to the review flow
- Fails gracefully if Fathom is unavailable
- Can be run standalone via `/dp:utils:meeting-context` for ad-hoc use

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Post-Command Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file.

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
| YYYY-MM-DD HH:MM | /dp:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/dp:*` command that was invoked (e.g., `/dp:requirements:generate`, `/dp:new`, `/dp:dbt:validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/dp:new` created a new project
  - `archived` — `/dp:archive` archived a project
  - `removed` — `/dp:remove` deleted a project
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name

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
| 2026-02-22 14:35 | /dp:new | created | Project created (type: full_platform, client: Acme Corp) |
| 2026-02-22 14:40 | /dp:requirements:generate | complete | Generated requirements specification (3 files) |
| 2026-02-22 15:12 | /dp:requirements:validate | pass | 14 checks passed, 0 failed |
| 2026-02-22 16:00 | /dp:requirements:review | approved | Reviewed by Jane Smith |
| 2026-02-23 09:15 | /dp:conceptual_model:generate | complete | Generated entity model with 8 entities |
| 2026-02-23 10:30 | /dp:conceptual_model:validate | fail | 2 issues: missing relationship, orphaned entity |
| 2026-02-23 11:00 | /dp:conceptual_model:generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) |
| 2026-02-23 11:15 | /dp:conceptual_model:validate | pass | 12 checks passed, 0 failed |
| 2026-02-23 14:00 | /dp:conceptual_model:review | changes_requested | Reviewed by John Doe — add Customer entity |
| 2026-02-23 15:30 | /dp:conceptual_model:generate | complete | Regenerated entity model (9 entities, added Customer) |
| 2026-02-23 15:45 | /dp:conceptual_model:validate | pass | 14 checks passed, 0 failed |
| 2026-02-23 16:00 | /dp:conceptual_model:review | approved | Reviewed by John Doe |
```
