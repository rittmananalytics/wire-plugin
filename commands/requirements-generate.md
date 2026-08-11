---
description: Generate requirements specification from SOW
argument-hint: <release-folder>
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
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Workflow Specification

---
description: Generate requirements specification from SOW, artifacts, and stakeholder inputs
argument-hint: <project-folder>
---

# Requirements Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

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

### Step 2b: Prioritise Goals Before Extracting Requirements

**Process**:
1. List all engagement goals extracted from the SOW/pitch
2. Check `status.md` for `primary_analytical_focus` and `goal_hierarchy_captured` (set by `release-brief-generate`)
3. If `goal_hierarchy_captured` is true, use the existing hierarchy from `brief.md` — do not re-ask
4. If not set, ask:
   ```
   The SOW lists [N] goals. Before extracting requirements, we need to prioritise them:

   - Which goals are PRIMARY (must achieve in this engagement)?
   - Which are SECONDARY (assess and recommend only — no build)?
   - Which are FUTURE (note and defer)?
   ```
5. Tag every requirement extracted in Step 2 with its parent goal's priority label: `[Primary]`, `[Secondary]`, or `[Future]`
6. Requirements tagged `[Future]` go into Section 11.3 (Not This Engagement) rather than Section 4 (Functional Requirements)

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

## 0. Goal Hierarchy

| Goal | Priority | Scope in this engagement |
|------|----------|--------------------------|
| [Goal 1] | Primary | Full requirements, design, and delivery |
| [Goal 2] | Secondary | Assessment and recommendation only |
| [Goal 3] | Future | Noted; out of scope this engagement |

**Primary analytical focus**: [value from brief.md or captured in Step 2b]

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

### 11.3 Not This Engagement (Future Goals)

The following goals from the SOW are acknowledged but explicitly deferred to a future release. They will not be designed, scoped, or partially addressed during this engagement:

| Goal | Why deferred | Suggested future release |
|------|-------------|--------------------------|
| [Goal name] | [reason] | [release type or TBD] |

### 11.4 Assumptions
[From SOW Section 8.1]

### 11.5 Dependencies
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

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `requirements`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 8: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `requirements`
- `artifact_name`: `Requirements Specification`
- `file_path`: `.wire/releases/[release_folder]/requirements/requirements_specification.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 9: Confirm and Suggest Next Steps

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
