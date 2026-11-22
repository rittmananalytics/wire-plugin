---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
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
