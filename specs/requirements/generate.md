---
wire_schema: "1.0"
command: generate
artifact: requirements
domain: requirements
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
preconditions: []
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

Apply the reference-legibility convention (`specs/utils/reference_legibility.md`): every code minted here (FR-n, NFR-n, D-n) is defined at its minting site — the heading or table row that carries its plain-language name. If the document cites a code defined in another artifact, add a Reference key section in the canonical format from that spec.

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

[From SOW Section 6. The ID column mints the D-codes: first cell the code, second cell its plain-language name, per specs/utils/reference_legibility.md.]

| ID | Deliverable | Description | Acceptance Criteria |
|----|------------|-------------|---------------------|
| D1 | [Deliverable name] | [What it is] | [How acceptance is judged] |
| D2 | [Deliverable name] | [What it is] | [How acceptance is judged] |

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

## Reference key

[Only if this document cites codes defined in other artifacts — see specs/utils/reference_legibility.md. Omit this section when every code used is minted in this document.]

| Code | Meaning | Defined in |
|------|---------|------------|
| [code] | [plain-language name from the defining document] | [path relative to the project root] |
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
