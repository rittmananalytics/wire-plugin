---
description: Generate training materials
argument-hint: <project-folder>
---

# Generate training materials

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
description: Generate training materials and session plans for data team and end users
---

# Training Generate Command

## Purpose

Generate comprehensive training materials, session plans, and hands-on exercises for both technical teams (data team enablement) and end users. Training is treated as a first-class deliverable with structured content and measurable outcomes.

## Prerequisites

**Required Artifacts (should be complete)**:
- `requirements`: Understanding of user personas and use cases
- At least one of:
  - `dbt`: For technical/data team training
  - `dashboards`: For end-user training
  - `semantic_layer`: For BI developer training

## Training Types

Based on SOW deliverables, determine training types needed:

| Training Type | Audience | Focus | Artifacts Used |
|--------------|----------|-------|----------------|
| Data Team Enablement | Data engineers, analytics engineers | How to maintain and extend models | dbt, pipeline, data_quality |
| BI Developer Training | BI developers, analysts | Semantic layer and dashboard development | semantic_layer, dashboards |
| End User Training | Business users, operational staff, analysts | How to use dashboards and reports | dashboards, requirements |
| Admin Training | Platform admins | Configuration, monitoring, troubleshooting | deployment, documentation |

## Workflow

### Step 1: Determine Training Scope

**Process**:
1. Read requirements: `.agent_v2/<project_id>/requirements/requirements_specification.md`
2. Extract from SOW deliverables section:
   - D4: Data Team Enablement Session
   - D5: End User Training Session
   - Or similar training deliverables
3. Identify:
   - Training audiences
   - Training objectives
   - Duration (e.g., "One 2-hour session")
   - Format (hands-on, presentation, workshop)

### Step 2: Analyze Completed Artifacts

**Process**:

For each training type, read relevant artifacts to understand what needs to be taught:

**For Data Team Enablement:**
- Read dbt models to understand structure
- Read pipeline code to understand data flows
- Read data quality tests
- Identify: layers, naming conventions, testing strategy, how to extend

**For End User Training:**
- Read dashboard specifications
- Read semantic layer (what metrics/dimensions available)
- Identify: key use cases, navigation, filters, drill-downs, interpretation

### Step 3: Generate Training Session Plan

**For each training type, create:**

**File**: `.agent_v2/<project_id>/enablement/training_<type>_session_plan.md`

**Template**:

```markdown
# Training Session Plan: [Training Type]

**Audience**: [Target audience]
**Duration**: [e.g., 2 hours]
**Format**: [Hands-on workshop / Presentation / Hybrid]
**Delivery Date**: [From project timeline]
**Location**: [Remote / In-person / Hybrid]

## Learning Objectives

By the end of this session, participants will be able to:
1. [Objective 1 - specific, measurable]
2. [Objective 2 - specific, measurable]
3. [Objective 3 - specific, measurable]

## Prerequisites

**Required:**
- [e.g., Access to dbt Cloud, BigQuery access, etc.]
- [e.g., Basic SQL knowledge]

**Recommended:**
- [e.g., Familiarity with Git/GitHub]

## Session Agenda

### Part 1: Introduction (15 minutes)

**Objectives**:
- Set context for the training
- Overview of what was built
- How it fits into daily workflows

**Activities**:
- Brief presentation: Platform overview
- Demo: Quick walkthrough of end-to-end data flow

**Materials**:
- Slides: Platform architecture diagram
- Demo environment access

### Part 2: [Core Topic 1] (30 minutes)

**Objectives**:
- [Specific learning objectives for this section]

**Activities**:
- Presentation: [Topic] concepts and best practices (10 min)
- Hands-on Exercise: [Specific task] (15 min)
- Group Discussion: Common scenarios (5 min)

**Materials**:
- Slides: [Topic] concepts
- Exercise handout: Step-by-step instructions
- Sample code/queries

### Part 3: [Core Topic 2] (30 minutes)

[Repeat structure]

### Part 4: [Core Topic 3] (30 minutes)

[Repeat structure]

### Part 5: Q&A and Next Steps (15 minutes)

**Objectives**:
- Address remaining questions
- Provide resources for continued learning

**Activities**:
- Open Q&A
- Share documentation and resources
- Discuss support channels

**Materials**:
- Resource list handout
- Documentation links

## Hands-On Exercises

### Exercise 1: [Exercise Name]

**Objective**: [What participants will learn]

**Scenario**: [Real-world scenario]

**Steps**:
1. [Step 1 with specific instructions]
2. [Step 2 with specific instructions]
3. [Step 3 with specific instructions]

**Expected Outcome**: [What participants should achieve]

**Solution**: [Available in appendix]

[Repeat for each exercise]

## Assessment

**How to measure learning outcomes:**
- [ ] Participants can successfully [complete exercise 1]
- [ ] Participants can explain [key concept]
- [ ] Participants can troubleshoot [common issue]

## Post-Session Support

**Resources provided:**
- Documentation: [Link to user guide]
- Reference materials: [Cheat sheets, quick references]
- Support channels: [Slack, email, office hours]

**Follow-up:**
- Office hours: [Schedule]
- Check-in meeting: [1 week post-training]

## Appendix A: Exercise Solutions

[Detailed solutions for all hands-on exercises]

## Appendix B: Additional Resources

- [Documentation links]
- [Video tutorials]
- [External resources]

## Appendix C: Troubleshooting Guide

[Common issues participants might encounter and solutions]
```

### Step 4: Generate Training Slides

**For each training type, create:**

**File**: `.agent_v2/<project_id>/enablement/training_<type>_slides.md`

**Format**: Markdown slides (can be converted to Google Slides, PowerPoint, or Marp)

```markdown
---
marp: true
theme: default
paginate: true
---

# [Training Session Title]

**[Client Name]**
**[Date]**

Presented by: Rittman Analytics

---

## Agenda

1. Introduction & Platform Overview
2. [Core Topic 1]
3. [Core Topic 2]
4. [Core Topic 3]
5. Hands-On Exercises
6. Q&A and Resources

---

## Learning Objectives

By the end of this session, you will be able to:

- [Objective 1]
- [Objective 2]
- [Objective 3]

---

# Part 1: Platform Overview

---

## What We Built

[Architecture diagram or summary]

- **Data Pipeline**: [Brief description]
- **dbt Models**: [Brief description]
- **Dashboards**: [Brief description]

---

## How It Fits Into Your Workflow

[Diagram showing where the platform fits into daily work]

---

# Part 2: [Core Topic 1]

---

## [Key Concept]

[Explanation with diagrams/visuals]

---

## [Best Practices]

- [Practice 1]
- [Practice 2]
- [Practice 3]

---

## 🧑‍💻 Hands-On Exercise 1

**Scenario**: [Real-world scenario]

**Your Task**: [What to do]

**Time**: 15 minutes

---

[Continue for all sections]

---

# Resources & Next Steps

---

## Documentation

- User Guide: [Link]
- Technical Documentation: [Link]
- FAQ: [Link]

---

## Support

- Office Hours: [Schedule]
- Slack Channel: [Channel name]
- Email: [Support email]

---

## Thank You!

Questions?
```

### Step 5: Generate Exercise Workbook

**File**: `.agent_v2/<project_id>/enablement/training_<type>_exercises.md`

```markdown
# Training Exercises: [Training Type]

**Instructions**: Work through these exercises during the training session. Solutions are provided at the end.

---

## Exercise 1: [Exercise Name]

**Objective**: [Learning objective]

**Scenario**:
[Realistic scenario that participants can relate to]

**Your Task**:
[Clear, specific instructions]

**Starting Point**:
[Any code, data, or setup they start with]

**Steps**:
1. [Detailed step 1]
   - [Sub-step if needed]
2. [Detailed step 2]
3. [Detailed step 3]

**Expected Result**:
[What they should see/achieve]

**Questions to Consider**:
- [Thought-provoking question related to the exercise]
- [Another question]

---

## Exercise 2: [Exercise Name]

[Repeat structure]

---

# Solutions

## Exercise 1 Solution

**Step-by-step solution**:

[Detailed solution with code/screenshots]

**Explanation**:
[Why this approach works, what to learn from it]

[Repeat for all exercises]
```

### Step 6: Generate Reference Materials

**Quick Reference Guide**

**File**: `.agent_v2/<project_id>/enablement/training_<type>_quick_reference.md`

```markdown
# Quick Reference: [Training Type]

---

## Common Tasks

### Task 1: [Task Name]

**When to use**: [Context]

**Steps**:
```
[Code or step-by-step instructions]
```

**Example**:
```
[Concrete example]
```

---

### Task 2: [Task Name]

[Repeat structure]

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| [Common issue 1] | [Why it happens] | [How to fix] |
| [Common issue 2] | [Why it happens] | [How to fix] |

---

## Useful Links

- [Link 1]
- [Link 2]
- [Link 3]
```

### Step 7: Example Training Content by Type

> **Note**: The examples below use generic placeholders. When generating training materials, adapt all content based on the project's `status.md` (client name, project type) and `requirements/requirements_specification.md` (deliverables, audiences, use cases).

#### Data Team Enablement Example

```markdown
# Data Team Enablement Session Plan

**Audience**: Client data team (adapt from requirements - names and roles from SOW)
**Duration**: 2 hours
**Format**: Hands-on workshop

## Learning Objectives

By the end of this session, participants will be able to:
1. Understand the dbt project structure (staging → integration → warehouse)
2. Add new staging models for additional data sources
3. Run dbt models and tests in dbt Cloud
4. Safely extend existing models without breaking downstream dependencies

## Session Agenda

### Part 1: dbt Project Structure (20 minutes)
- Overview of layered architecture
- Walkthrough of existing models
- Naming conventions and folder structure

### Part 2: Adding New Staging Models (30 minutes)
- Demo: Adding a new staging model
- Exercise: Participants add a staging model for a new table
- Testing the new model

### Part 3: Integration and Warehouse Layers (30 minutes)
- How integration models work
- When to use ephemeral vs view vs table
- Exercise: Extend an existing integration model

### Part 4: Running and Testing (30 minutes)
- Using dbt Cloud
- Running models selectively (dbt run -s model_name)
- Data quality tests
- Exercise: Add custom tests

### Part 5: Best Practices and Q&A (10 minutes)
- Version control workflow
- When to ask for help
- Resources and documentation

## Hands-On Exercises

### Exercise 1: Add a New Staging Model

**Scenario**: You need to add a new data source (<new_table> table) to the platform.

**Your Task**: Create a staging model following the existing conventions.

**Steps**:
1. Navigate to `dbt/models/staging/<source_name>/`
2. Create a new file: `stg_<source_name>__<new_table>.sql`
3. Use the template provided in the training
4. Add source definition to `stg_<source_name>.yml`
5. Run the model: `dbt run -s stg_<source_name>__<new_table>`
6. Add tests for primary key

[Continue with detailed steps]
```

#### End User Training Example

```markdown
# End User Training Session Plan

**Audience**: [Adapt from SOW - e.g., operational staff, analysts, end users]
**Duration**: 90 minutes
**Format**: Interactive demonstration with Q&A

## Learning Objectives

By the end of this session, participants will be able to:
1. Navigate the operational dashboard
2. Identify key items requiring attention using data signals
3. Drill into underlying detail
4. Interpret live data signals responsibly

## Session Agenda

### Part 1: Platform Introduction (10 minutes)
- What the platform does
- How it fits into daily workflow

### Part 2: Dashboard Navigation (20 minutes)
- Accessing the dashboard in Looker
- Overview of main visualizations
- Filter panel and how to use it

### Part 3: Understanding Data Signals (20 minutes)
- What each signal means
- Key metrics and thresholds
- How signals are calculated (transparency)

### Part 4: Taking Action (20 minutes)
- Drilling into detail views
- Identifying items requiring follow-up
- Prioritizing workload

### Part 5: Best Practices and Responsible Use (15 minutes)
- Data freshness and when to trust the data
- Privacy and appropriate use
- When to use the dashboard vs other tools

### Part 6: Q&A (5 minutes)

## Demo Scenarios

### Scenario 1: Identifying Items Requiring Attention

[Walk through finding records with key signal flags]

### Scenario 2: Following Up on Alerts

[Walk through checking alerts without follow-up]

[Continue with demo scenarios]
```

### Step 8: Create Training Delivery Checklist

**File**: `.agent_v2/<project_id>/enablement/training_delivery_checklist.md`

```markdown
# Training Delivery Checklist

## Pre-Session (1 week before)

- [ ] Confirm training date and time with participants
- [ ] Send calendar invites with Zoom/Teams link
- [ ] Verify all participants have required access (Looker, dbt Cloud, etc.)
- [ ] Send pre-session materials (agenda, prerequisites)
- [ ] Test demo environment
- [ ] Prepare any accounts or sample data needed

## Pre-Session (1 day before)

- [ ] Send reminder email with session link and materials
- [ ] Test screen sharing and recording setup
- [ ] Print/prepare any physical materials (if in-person)
- [ ] Review session plan and timing

## During Session

- [ ] Start recording (with participant consent)
- [ ] Share session agenda
- [ ] Check if everyone can access materials
- [ ] Take notes on questions and feedback
- [ ] Monitor time and adjust pace as needed

## Post-Session

- [ ] Share recording and materials
- [ ] Send follow-up email with resources
- [ ] Update training status in `.agent_v2/<project_id>/status.md`
- [ ] Schedule office hours or check-in meeting
- [ ] Gather feedback (survey or informal)

## Materials to Share

- [ ] Session recording
- [ ] Slide deck
- [ ] Exercise workbook with solutions
- [ ] Quick reference guide
- [ ] Documentation links
- [ ] Support contact information
```

### Step 9: Update Status

**Process**:
1. Read current status file
2. Update artifacts.training section:
   ```yaml
   training:
     generate: complete
     validate: not_started
     review: not_started
     session_plans: [list of types]
     duration_hours: [total hours]
     generated_date: 2026-02-13
   ```
3. Write updated status.md

### Step 10: Sync to Jira (Optional)

Follow the Jira sync workflow in `dp/utils/jira_sync.md`:
- Artifact: `training`
- Action: `generate`
- Status: the generate state just written to status.md

### Step 11: Confirm and Suggest Next Steps

**Output**:

```
## Training Materials Generated Successfully

**Training Types Created**:
- Data Team Enablement (2 hours)
- End User Training (1.5 hours)

### Files Created

```
.agent_v2/<project_id>/enablement/
├── training_data_team_session_plan.md
├── training_data_team_slides.md
├── training_data_team_exercises.md
├── training_data_team_quick_reference.md
├── training_end_user_session_plan.md
├── training_end_user_slides.md
├── training_end_user_quick_reference.md
└── training_delivery_checklist.md
```

### Next Steps

1. **Review the training materials**:
   /dp:training:review <project_id>

   Share with team for feedback on content and timing.

2. **Schedule the training sessions**:
   - Coordinate with client on dates
   - Send calendar invites
   - Verify access for all participants

3. **Prepare the environment**:
   - Set up demo accounts
   - Prepare sample data
   - Test all exercises

4. **Deliver the training**:
   - Follow session plan
   - Record sessions (with consent)
   - Take notes on feedback

5. **Follow up**:
   - Share materials and recording
   - Schedule office hours
   - Update status after delivery

### Quick Links

- Session plans: `.agent_v2/<project_id>/enablement/`
- Delivery checklist: `.agent_v2/<project_id>/enablement/training_delivery_checklist.md`
- View status: `/dp:status <project_id>`
```

## Edge Cases

### No Dashboard or dbt Artifacts Complete

If required artifacts not complete:

```
Error: Cannot generate training materials yet.

Required artifacts not complete:
- [dashboards]: not_started
- [dbt]: in_progress

Please complete development artifacts before generating training materials.

You can generate training materials once these are ready:
/dp:training:generate <project_id>
```

### Multiple Training Audiences

If SOW has multiple distinct training deliverables:

1. Generate separate materials for each
2. Ask user which to generate first (if not clear from requirements)

### Custom Training Requirements

If requirements specify unique training needs:

```
I found these training requirements:
- D4: Data Team Enablement (2 hours)
- D5: End User Training (90 minutes)

Are there any additional training needs not listed in the SOW?
(e.g., Admin training, BI developer training)
```

## Validation Checks (for next step)

The validate command will check:
- [ ] All session plans have clear learning objectives
- [ ] Exercises are relevant and achievable
- [ ] Duration is realistic for content
- [ ] Prerequisites are clearly stated
- [ ] Post-session support is defined

## Output Files

This command creates:
- Session plan for each training type
- Slide deck for each training type
- Exercise workbook for each training type
- Quick reference guides
- Delivery checklist
- Updates `.agent_v2/<project_id>/status.md`

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
