---
description: Generate requirements specification from SOW
argument-hint: <project-folder>
---

# Generate requirements specification from SOW

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"requirements-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"2.1.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate requirements specification from SOW, artifacts, and stakeholder inputs
---

# Requirements Generate Command

## Purpose

Extract and structure requirements from Statement of Work (SOW), requirements documents, and other artifacts. Creates a comprehensive requirements specification that serves as the foundation for design and development.

## Inputs

**Required**:
- Project folder: `.wire/<project_id>/`
- SOW or requirements documents in `artifacts/` folder

**Optional**:
- Workshop outputs
- Meeting transcripts
- Technical specifications
- User stories

## Workflow

### Step 1: Read Source Materials

**Process**:
1. Use Glob to find all artifacts: `.wire/<project_id>/artifacts/**/*`
2. Identify document types:
   - PDF files (SOW, proposals) - use Read tool for PDFs
   - Markdown files (notes, transcripts) - use Read tool
   - Word documents (.docx) - prompt user to convert or extract key points
3. Read each relevant document

**Priority order:**
1. SOW/Proposal (primary source of truth)
2. Requirements documents
3. Workshop outputs
4. Meeting notes/transcripts
5. Technical specs

### Step 2: Extract Key Elements

**Parse the SOW/artifacts for:**

#### Business Context
- Client background
- Business problem statement
- Strategic goals
- Success criteria
- Key stakeholders

#### Technical Outcomes
- Specific deliverables (from SOW Section 3 or equivalent)
- Technical requirements
- Platform/technology constraints
- Integration requirements
- Performance requirements

#### Deliverables
- List of deliverables (D1, D2, etc. from SOW Section 6 or equivalent)
- Acceptance criteria for each
- Dependencies between deliverables
- Out of scope items (from Section 8.2 or equivalent)

#### Timeline & Resources
- Project duration
- Key milestones
- Resource allocation
- Constraints and dependencies

#### Assumptions & Risks
- Stated assumptions
- Identified risks
- Mitigation strategies

### Step 3: Structure Requirements Document

**Process**:
1. Read template: `TEMPLATES/requirements-template.md` (in the framework root directory)
2. Populate sections with extracted information
3. Organize by categories:
   - **Functional Requirements**: What the system must do
   - **Non-Functional Requirements**: Quality attributes (performance, security, etc.)
   - **Data Requirements**: Data sources, volumes, refresh rates
   - **Technical Requirements**: Platforms, tools, integrations
   - **User Requirements**: Who will use it and how
   - **Deliverables**: Concrete outputs and acceptance criteria

### Step 4: Map Deliverables to Artifacts

**Process**:

For each deliverable in the SOW, determine which agent artifacts are needed:

**Example mapping:**

| SOW Deliverable | Agent Artifacts Required |
|----------------|-------------------------|
| Data pipeline deliverable | pipeline_design, pipeline, data_quality |
| Semantic layer deliverable | data_model, dbt, semantic_layer |
| Dashboard deliverable | mockups, dashboards |
| Data team enablement deliverable | training (technical) |
| End user training deliverable | training (end-user) |

Update the requirements document with this mapping so the team knows which artifacts to generate.

### Step 5: Generate Requirements Document

**Output Location**: `.wire/<project_id>/requirements/requirements_specification.md`

**Document Structure**:

```markdown
# Requirements Specification: [Project Name]

**Client**: [Client Name]
**Project ID**: [Project ID]
**Date**: [Generation Date]
**Version**: 1.0

## 1. Executive Summary

[Brief overview of the project]

## 2. Business Context

### 2.1 Background
[Client background and current situation]

### 2.2 Business Problem
[Problem statement]

### 2.3 Strategic Goals
[Business objectives]

### 2.4 Success Criteria
[Measurable success criteria]

## 3. Stakeholders

| Role | Name | Responsibilities | Contact |
|------|------|------------------|---------|
| ... | ... | ... | ... |

## 4. Functional Requirements

### FR-1: [Requirement Name]
**Priority**: High/Medium/Low
**Description**: [What the system must do]
**Acceptance Criteria**:
- [ ] Criterion 1
- [ ] Criterion 2

[Repeat for each functional requirement]

## 5. Non-Functional Requirements

### NFR-1: Performance
[Performance requirements]

### NFR-2: Security
[Security requirements]

### NFR-3: Availability
[Availability requirements]

[Additional non-functional requirements]

## 6. Data Requirements

### 6.1 Data Sources
| Source | Type | Refresh Rate | Volume | Owner |
|--------|------|--------------|--------|-------|
| ... | ... | ... | ... | ... |

### 6.2 Data Quality Requirements
[Data quality expectations]

### 6.3 Data Governance
[Governance and compliance requirements]

## 7. Technical Requirements

### 7.1 Platform
[Cloud platform, database, BI tool]

### 7.2 Integrations
[Required integrations]

### 7.3 Tools & Technologies
[Specific tools required]

## 8. User Requirements

### 8.1 User Personas
[Who will use the system]

### 8.2 Use Cases
[Key use cases]

## 9. Deliverables

[From SOW Section 6]

| ID | Deliverable | Description | Acceptance Criteria | Agent Artifacts |
|----|------------|-------------|---------------------|-----------------|
| D1 | ... | ... | ... | pipeline_design, pipeline |
| D2 | ... | ... | ... | semantic_layer |

## 10. Timeline & Milestones

| Milestone | Date | Deliverables |
|-----------|------|--------------|
| ... | ... | ... |

## 11. Scope Management

### 11.1 In Scope
[From SOW]

### 11.2 Out of Scope
[From SOW Section 8.2]

### 11.3 Assumptions
[From SOW Section 8.1]

### 11.4 Dependencies
[Dependencies and prerequisites]

## 12. Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ... | ... | ... | ... |

## 13. Appendices

### Appendix A: Glossary
[Technical terms and definitions]

### Appendix B: References
[Links to SOW, technical docs, etc.]
```

### Step 6: Update Status

**Process**:
1. Read current status file: `.wire/<project_id>/status.md`
2. Update artifacts.requirements section:
   ```yaml
   requirements:
     generate: complete
     validate: not_started
     review: not_started
     file: requirements/requirements_specification.md
     generated_date: 2026-02-13
   ```
3. Update `last_updated` timestamp
4. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Confirm and Suggest Next Steps

**Output**:

```
## Requirements Generated Successfully

**File**: `.wire/<project_id>/requirements/requirements_specification.md`

### Summary

Extracted requirements from:
- SOW: [filename]
- [Other artifacts if applicable]

**Deliverables Identified**: [count]
**Functional Requirements**: [count]
**Non-Functional Requirements**: [count]

### Key Deliverables → Artifact Mapping

| Deliverable | Agent Artifacts Required |
|------------|-------------------------|
| D1: ... | pipeline_design, pipeline, data_quality |
| D2: ... | semantic_layer |
| D3: ... | mockups, dashboards |

### Next Steps

1. **Validate the requirements**:
   /wire:requirements-validate <project_id>

   This will check for:
   - Completeness (all sections filled)
   - Clear acceptance criteria
   - Feasibility within timeline

2. **Review with stakeholders**:
   /wire:requirements-review <project_id>

   Present the requirements to the client for approval.

3. **Generate workshop materials** (if requirements need clarification):
   /wire:workshops-generate <project_id>

### Quick Links

- View requirements: `.wire/<project_id>/requirements/requirements_specification.md`
- View status: `/wire:status <project_id>`
- Edit requirements: Make changes in the file, then re-validate
```

## Edge Cases

### No SOW Found

If no SOW or requirements documents found in artifacts/:

```
No SOW or requirements documents found in artifacts folder.

Options:
1. Add SOW/requirements docs to `.wire/<project_id>/artifacts/`
2. Create requirements from scratch (I'll ask you questions)
3. Reference an existing SOW file (provide path)

Which would you prefer?
```

Use AskUserQuestion to get user choice, then proceed accordingly.

### Incomplete SOW

If SOW is missing critical sections:

1. Generate what's available
2. Add notes in requirements document:
   ```markdown
   **NOTE**: [Section] not found in SOW. This needs to be clarified with client.
   ```
3. Flag in validation step

### Multiple Documents with Conflicting Info

If artifacts contain conflicting requirements:

1. Flag conflicts in requirements document
2. Create a "Clarifications Needed" section
3. Suggest workshop to resolve: `/wire:workshops-generate <project_id>`

### Very Large SOW

If SOW is extremely long (>50 pages):

1. Process in sections
2. Focus on key sections (deliverables, technical outcomes, scope)
3. Summarize less critical sections
4. Link to full SOW for reference

## Validation Checks (for next step)

The validate command will check:
- [ ] All required sections completed
- [ ] Each deliverable has acceptance criteria
- [ ] Timeline is realistic
- [ ] Stakeholders identified
- [ ] Out of scope items documented
- [ ] Technical requirements are specific
- [ ] Data sources identified

## Output Files

This command creates:
- `.wire/<project_id>/requirements/requirements_specification.md`
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
