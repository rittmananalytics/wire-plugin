---
description: Generate conceptual entity model from requirements
argument-hint: <project-folder>
---

# Generate conceptual entity model from requirements

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Telemetry

# Telemetry — Anonymous Usage Tracking

## Purpose

Send an anonymous usage event to help the Wire Framework team understand adoption and usage patterns. This runs at the start of every command, before the main workflow.

## Opt-Out

Check whether telemetry is disabled. Run this Bash command:

```bash
echo "${WIRE_TELEMETRY:-true}"
```

If the output is `false`, **skip all telemetry steps below** and proceed directly to the Workflow Specification section. Do not run any curl commands.

## Step 1: Determine User Identity

Check if the file `~/.wire/telemetry_id` exists by running:

```bash
cat ~/.wire/telemetry_id 2>/dev/null
```

### If the file does NOT exist (first run):

Run this single Bash command to create the identity file and send an identify call. Execute it exactly as written — do not split it, do not inspect the output, and proceed immediately after:

```bash
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"2.1.0\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"conceptual_model-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"2.1.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate conceptual entity model from requirements
argument-hint: <project-folder>
---

# Conceptual Model Generate Command

## Purpose

Generate a business-level conceptual entity model showing the core domain entities, their high-level attributes, and their relationships — without implementation detail such as column names, data types, or dbt layering. This model is presented to business stakeholders for approval before pipeline architecture and detailed data modelling begins.

The conceptual model captures *what the business cares about*, not *how the database stores it*. Its primary purpose is to ensure consultant and client agree on the entity landscape before design decisions are made.

## Usage

```bash
/wire:conceptual_model-generate YYYYMMDD_project_name
```

## Prerequisites

- `requirements`: `review: approved` — the conceptual model is derived from approved requirements

## Workflow

### Step 1: Verify Prerequisites and Read Inputs

1. Read `.wire/<project_id>/status.md`
2. Check `requirements.review == approved`. If not:
   ```
   Error: Requirements must be approved before generating the conceptual model.
   Run: /wire:requirements-review <project_id>
   ```
3. Read `.wire/<project_id>/requirements/requirements_specification.md`
4. Use Glob to find all files in `.wire/<project_id>/artifacts/**/*`
5. Read any source schema examples, ERDs, domain glossaries, or data dictionaries found in `artifacts/`

### Step 2: Extract Business Entities

From the requirements specification and artifacts, identify all **business entities** — the things the business tracks, measures, or cares about. Look for:
- Nouns in functional requirements (FR-* sections)
- Data sources named in the pipeline scope
- Reporting subjects mentioned in deliverables
- Entities implied by relationships (e.g. if "a student is enrolled on a course", both `Student` and `Course` are entities)

For each entity record:
- **Name**: Singular noun, PascalCase (e.g. `Student`, `Enrolment`, `PastoralNote`, `Invoice`)
- **Description**: One sentence explaining what this entity represents in business terms
- **Key business attributes**: 3–6 high-level attributes described in business language (not column names)
- **Approximate volume**: Row count or transaction frequency if known from requirements

Group entities by domain if the project spans multiple subject areas (e.g. Academic, Finance, HR).

### Step 3: Define Relationships

For each pair of related entities, define:
- **Relationship label**: Verb phrase describing the relationship from Entity A's perspective (e.g. "enrolled in", "authors", "generates", "is subject of")
- **Cardinality**: Standard ERD notation:
  - `||--||` : exactly one to exactly one
  - `||--o{` : exactly one to zero or more
  - `}|--||` : one or more to exactly one
  - `}o--o{` : zero or more to zero or more

Flag any relationships that are ambiguous or require business clarification — add them to Section 5 (Open Questions) rather than silently resolving them.

### Step 4: Generate Conceptual Model Document

Write to `.wire/<project_id>/design/conceptual_model.md`:

```markdown
# Conceptual Entity Model: [Project Name]

**Client**: [Client Name]
**Project ID**: [Project ID]
**Generated**: [Date]
**Version**: 1.0
**Status**: Draft — awaiting business stakeholder review

## 1. Entity Inventory

### [Entity Name]
**Description**: [One sentence business description]
**Key attributes**: [attribute 1], [attribute 2], [attribute 3], [attribute 4]
**Approximate volume**: [e.g. ~4,000 students; ~500 transactions/day; updated daily]

[Repeat for each entity, grouped by domain if applicable]

## 2. Entity Relationship Diagram

```mermaid
erDiagram
    ENTITY_A ||--o{ ENTITY_B : "relationship label"
    ENTITY_B }|--|| ENTITY_C : "relationship label"
    ENTITY_A ||--o{ ENTITY_C : "relationship label"
```

**How to read this diagram**:
- `||` = exactly one
- `o{` = zero or more
- `}|` = one or more
- Labels describe the relationship from left entity's perspective

## 3. Relationship Narrative

**[Entity A] → [Entity B]** ("relationship label"): [One sentence explaining the business meaning of this relationship and why it matters to the engagement. Include any business rules that govern it.]

[Repeat for each significant relationship]

## 4. Entities Considered But Out of Scope

| Entity | Reason excluded |
|--------|----------------|
| [Entity name] | [e.g. "Out of scope per SOW Section 8.2"] |

## 5. Open Questions

| # | Question | Impact |
|---|----------|--------|
| OQ-1 | [Entity boundary or relationship that needs business clarification] | [What design decision this blocks] |

[Leave empty if no open questions]
```

### Step 5: Update Status

Read and update `.wire/<project_id>/status.md` YAML frontmatter:

```yaml
conceptual_model:
  generate: complete
  validate: not_started
  review: not_started
  file: design/conceptual_model.md
  generated_date: [today]
```

If `current_phase` is still `requirements`, update to `design`.

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `conceptual_model`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7: Confirm and Suggest Next Steps

```
## Conceptual Model Generated

**File**: .wire/<project_id>/design/conceptual_model.md

**Entities identified**: [count]
**Relationships defined**: [count]
**Open questions**: [count — flag prominently if > 0]

### Next Steps

1. Validate the model:
   /wire:conceptual_model-validate <project_id>

2. After validation, review with business stakeholders:
   /wire:conceptual_model-review <project_id>

   NOTE: Review audience should include business stakeholders (not just technical
   leads) — the purpose is to confirm the entity landscape before design begins.
   Open questions must be resolved before the review can be approved.
```

## Edge Cases

### Ambiguous Entity Boundaries

If two concepts could reasonably be one entity or two (e.g. `Student` vs `Learner`; `Invoice` vs `Bill`; `Attendance` vs `AttendanceMark`):
- Use the client's own terminology from the SOW
- Document the ambiguity in Section 5 (Open Questions)
- Do not silently resolve — this is a business decision, not a technical one

### No Source Schema in Artifacts

If no schema examples are in `artifacts/`, generate entities from requirements alone and add:
```
Note: No source schema examples were found in artifacts/. Entities were derived
from requirements only. Adding source schema examples before review may reveal
additional entities or relationship corrections.
```

### Very Large Domain (20+ entities)

If the engagement spans a large domain:
1. Focus on entities that are **in scope** for this engagement
2. Show out-of-scope entities in Section 4 (greyed out in diagram if possible)
3. Consider grouping entities into subgraphs in the Mermaid diagram using `subgraph`

## Output

This command creates:
- `.wire/<project_id>/design/conceptual_model.md`
- Updates `.wire/<project_id>/status.md`

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
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> |
```

### Field Definitions

- **Timestamp**: Current date and time in `YYYY-MM-DD HH:MM` format (24-hour, local time)
- **Command**: The `/wire:*` command that was invoked (e.g., `/wire:requirements-generate`, `/wire:new`, `/wire:dbt-validate`)
- **Result**: The outcome of the command. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
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
