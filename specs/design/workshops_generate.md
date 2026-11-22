---
wire_schema: "1.0"
command: generate
artifact: workshops
domain: design
release_types:
  - full_platform
  - dbt_development
  - dashboard_first
  - pipeline_only
  - dashboard_extension
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Generate workshop materials for requirements clarification
argument-hint: <project-folder>

---

# Workshops Generate Command

## Purpose

Generate structured workshop materials when requirements need clarification or there are multiple technical approaches to discuss with stakeholders.

## Usage

```bash
/wire:workshops-generate YYYYMMDD_project_name
```

## Prerequisites

- Requirements should be generated (ideally with [NEEDS CLARIFICATION] markers)

## Workflow

### Step 1: Analyze Requirements for Clarification Needs

**Process**:
1. Read `requirements/requirements_specification.md`
2. Identify sections with:
   - `[NEEDS CLARIFICATION]` markers
   - `[TBD]` markers
   - Multiple options or approaches mentioned
   - Ambiguous acceptance criteria

**Count issues**:
```
Found 7 items needing clarification:
- 3 in functional requirements
- 2 in data sources
- 2 in technical approach
```

### Step 2: Categorize Workshop Topics

**Group clarifications by category:**

| Category | Topics | Priority |
|----------|--------|----------|
| Requirements | Ambiguous functional requirements | High |
| Data | Data source ownership, access, refresh rates | High |
| Technical | Technology choices, architecture decisions | Medium |
| Timeline | Milestone dependencies, resource constraints | Medium |
| Scope | In/out of scope boundary questions | High |

### Step 3: Generate Workshop Agenda

**File**: `.wire/<project>/requirements/workshop_agenda.md`

```markdown
# Requirements Clarification Workshop

**Project:** [PROJECT_NAME]
**Date:** [Proposed date - TBD]
**Duration:** 90-120 minutes (recommend 2 hours)
**Attendees:**
- [Client stakeholders]
- [Technical team]
- [Delivery lead]

## Objectives

By the end of this workshop, we will have:
1. Clarified all ambiguous requirements
2. Made decisions on technical approaches
3. Confirmed data source details
4. Aligned on scope boundaries
5. Updated requirements document

## Agenda

### Part 1: Requirements Clarification (45 minutes)

**Topic 1: [Adapt from requirements - e.g., Data Refresh Rates]**
- **Current State**: [What the requirements say - identify ambiguity]
- **Question**: [Specific question to resolve]
- **Options**:
  - A) [Option A]
  - B) [Option B]
  - C) [Option C]
- **Decision Needed**: [What must be decided]

**Topic 2: [Adapt from requirements - e.g., Business Logic Definitions]**
- **Current State**: [What the requirements say - identify ambiguity]
- **Question**: [Specific question to resolve]
- **Options**:
  - A) [Option A]
  - B) [Option B]
  - C) [Option C]
- **Decision Needed**: [What must be decided]

[Additional topics from [NEEDS CLARIFICATION] markers...]

### Part 2: Data Source Details (30 minutes)

**Topic N: [Source System Access]**
- **Current State**: [Source system known but access method unclear]
- **Questions**:
  - Is there an API or database access needed?
  - Who owns this data?
  - What privacy/security constraints apply?
- **Decision Needed**: Confirm access method and security requirements

[Additional data topics...]

### Part 3: Technical Approach (30 minutes)

**Topic 6: Data Pipeline Implementation**
- **Options**:
  - A) Cloud Function triggered by Cloud Scheduler
  - B) Python script in Cloud Run
  - C) Built-in BigQuery data transfer
- **Trade-offs**: [Discuss pros/cons of each]
- **Decision Needed**: Select approach

[Additional technical topics...]

### Part 4: Wrap-up (15 minutes)

- Review decisions made
- Confirm next steps
- Schedule follow-up if needed

## Pre-Workshop Preparation

**For stakeholders:**
- Review requirements document
- Prepare any questions
- Bring subject matter experts for data topics

**For technical team:**
- Review clarification items
- Prepare technical options analysis
- Have architecture diagrams ready

## Workshop Materials Included

1. This agenda
2. Requirements document (for reference)
3. Decision matrix (to be filled during workshop)
4. Technical options comparison (for Part 3)

## Post-Workshop

After the workshop:
1. Update requirements document with decisions
2. Run `/wire:requirements-validate [folder]`
3. Get final approval: `/wire:requirements-review [folder]`
```

### Step 4: Generate Decision Matrix

**File**: `.wire/<project>/requirements/workshop_decision_matrix.md`

```markdown
# Workshop Decisions Matrix

**Workshop Date:** [Date]
**Facilitator:** [Name]
**Attendees:** [Names]

## Decisions Made

| # | Topic | Options Considered | Decision | Rationale | Owner | Follow-up |
|---|-------|-------------------|----------|-----------|-------|-----------|
| 1 | [Topic from workshop] | [Options considered] | [TBD] | [TBD] | [TBD] | [TBD] |
| 2 | [Topic from workshop] | [Options considered] | [TBD] | [TBD] | [TBD] | [TBD] |
| 3 | [Topic from workshop] | [Options considered] | [TBD] | [TBD] | [TBD] | [TBD] |
| 4 | [Topic from workshop] | [Options considered] | [TBD] | [TBD] | [TBD] | [TBD] |

[Additional rows for each clarification item]

## Open Questions

[List any questions that couldn't be resolved in the workshop]

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | [Date] | [Pending/Done] |
| [Action 2] | [Name] | [Date] | [Pending/Done] |

## Next Steps

1. Complete any open action items
2. Update requirements document with workshop decisions
3. Re-validate requirements
4. Proceed to design phase
```

### Step 5: Generate Technical Options Analysis (if needed)

**File**: `.wire/<project>/requirements/workshop_technical_options.md`

```markdown
# Technical Options Analysis

## Data Pipeline Implementation Options

### Option A: Cloud Function + Cloud Scheduler

**Pros:**
- Serverless, auto-scaling
- Pay-per-invocation
- Simple to deploy

**Cons:**
- 9-minute execution timeout
- Cold start latency
- Complex for long-running extracts

**Cost:** ~$X/month
**Complexity:** Low
**Recommended for:** Quick, frequent extracts

### Option B: Cloud Run + Cloud Scheduler

**Pros:**
- No execution timeout
- Containerized (flexible runtime)
- Auto-scaling

**Cons:**
- Higher cost for continuous running
- More complex deployment

**Cost:** ~$Y/month
**Complexity:** Medium
**Recommended for:** Long-running extracts

### Option C: BigQuery Data Transfer

**Pros:**
- Fully managed
- Native BigQuery integration
- Simple configuration

**Cons:**
- Limited to supported sources
- Less flexible

**Cost:** ~$Z/month
**Complexity:** Low
**Recommended for:** Standard sources (Salesforce, GA4, etc.)

## Recommendation

[Based on requirements analysis, recommend an option with reasoning]
```

### Step 6: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.workshops section:
   ```yaml
   workshops:
     generate: complete
     review: not_started
     clarification_count: 7
     generated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 7: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `workshops`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7.5: Sync to Linear (Optional)

Follow the Linear sync workflow in `specs/utils/linear_sync.md`:
- Artifact: `workshops`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 7.6: Sync to Document Store (Optional)

If a document store is configured for this engagement, follow the workflow in `specs/utils/docstore_sync.md`:
- Artifact: `workshops`
- Primary file: `.wire/[release_folder]/requirements/workshop_agenda.md`
- Also sync: `workshop_decision_matrix.md` and `workshop_technical_options.md` (if generated)

Fail gracefully if the document store is unavailable — this step is optional and additive.

### Step 8: Confirm and Suggest Next Steps

**Output**:

```
## Workshop Materials Generated Successfully

**Workshop Agenda:** .wire/[folder]/requirements/workshop_agenda.md
**Decision Matrix:** .wire/[folder]/requirements/workshop_decision_matrix.md
**Technical Options:** .wire/[folder]/requirements/workshop_technical_options.md

### Clarifications Identified

7 items need clarification across:
- Requirements: 3 items
- Data sources: 2 items
- Technical approach: 2 items

### Next Steps

1. **Schedule the workshop** with stakeholders
   - Suggested duration: 2 hours
   - Recommend including: [key stakeholders]

2. **Review workshop materials** before the session
   - Share agenda with attendees in advance
   - Ensure technical SMEs are available

3. **After the workshop**:
   - Fill in decision matrix
   - Update requirements document with decisions
   - Re-validate: `/wire:requirements-validate [folder]`
   - Get approval: `/wire:requirements-review [folder]`
```

## Edge Cases

### No Clarifications Found

If requirements are clear:
```
No major clarifications needed in requirements.

Requirements appear complete. Consider:
1. Review requirements directly: `/wire:requirements-review [folder]`
2. Generate workshop anyway for stakeholder alignment

Proceed with workshop generation? (y/n)
```

### Requirements Not Generated

If requirements don't exist:
```
Error: Requirements not found.

Generate requirements first: /wire:requirements-generate [folder]
```

## Output

This command creates:
- `.wire/<project>/requirements/workshop_agenda.md`
- `.wire/<project>/requirements/workshop_decision_matrix.md`
- `.wire/<project>/requirements/workshop_technical_options.md` (if technical decisions needed)
- Updates `.wire/<project>/status.md`
