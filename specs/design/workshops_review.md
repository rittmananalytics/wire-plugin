---
wire_schema: "1.0"
command: review
artifact: workshops
domain: design
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
preconditions:
  - artifact: workshops
    action: generate
    outcome: complete
delegates_to:
  - utils/precondition_gate
description: Record workshop outcomes and update requirements
argument-hint: <project-folder>

---

## Auto-Delegation

Follow `specs/utils/precondition_gate.md` before proceeding.

---

# Workshops Review Command

## Purpose

Record outcomes from requirements clarification workshop and update the requirements document with decisions made.

## Usage

```bash
/wire:workshops-review YYYYMMDD_project_name
```

## Prerequisites

- Workshop materials generated (`/wire:workshops-generate` complete)
- Workshop conducted with stakeholders

## Workflow

### Step 1: Locate Workshop Materials

**Process**:
1. Verify workshop materials exist:
   - `requirements/workshop_agenda.md`
   - `requirements/workshop_decision_matrix.md`

### Step 1.5: Retrieve External Context (Optional)

The workshop itself is usually a recorded meeting, so this step is unusually likely to have direct evidence — run it before asking the consultant for details in Step 2, so a found transcript can pre-fill/confirm the date and attendees instead of asking from scratch.

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `workshops`
   - If Fathom MCP is available and a matching meeting is found, present the meeting context summary and extract the workshop date and attendee list from it
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `workshops`
   - If Atlassian MCP is available, search Confluence for prior workshop notes and Jira for related issue comments
   - Present any relevant findings
3. If a document store is configured, follow `specs/utils/docstore_fetch.md`:
   - Pass `artifact_id`, `artifact_name`, `file_path`, and `project_id` for this artifact
   - Surface any reviewer comments or edits made directly to the document store version
4. If none of these are available, proceed directly to Step 2 and ask for the workshop date and attendees as normal

### Step 2: Record Workshop Details

**Ask for basic info**:
```
When was the workshop held? (YYYY-MM-DD)
```

**Then ask**:
```
Who attended the workshop? (List names and roles)
```

### Step 3: Fill Decision Matrix

**Output**:
```
## Recording Workshop Decisions

Let's go through each decision point from the workshop.

**Topic 1: Data refresh rate**
Options: Real-time, Near-real-time, Hourly

What was decided?
```

For each topic in the decision matrix:
1. Show the topic and options
2. Ask what was decided
3. Ask for rationale
4. Ask who owns any follow-up actions

### Step 4: Capture Action Items

**Ask**:
```
Were there any action items from the workshop?

List them in this format:
- Action: [description]
- Owner: [name]
- Due date: [YYYY-MM-DD]

(Type 'none' if no action items, or list them)
```

### Step 5: Update Decision Matrix

**Process**:
1. Read `requirements/workshop_decision_matrix.md`
2. Fill in all the decision columns based on responses
3. Add action items section
4. Add workshop metadata (date, attendees)
5. Write updated file

**Output preview**:
```
## Workshop Decisions Matrix - UPDATED

**Workshop Date:** [Date]
**Facilitator:** [Delivery lead]
**Attendees:** [Names and roles from workshop]

| # | Topic | Decision | Rationale | Owner | Follow-up |
|---|-------|----------|-----------|-------|-----------|
| 1 | [Topic 1] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |
| 2 | [Topic 2] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |
| 3 | [Topic 3] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |
| 4 | [Topic 4] | [Decision made] | [Why this was chosen] | [Owner] | [Any follow-up needed] |

## Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action from workshop] | [Owner] | [Date] | Pending |
| [Action from workshop] | [Owner] | [Date] | Pending |
| [Action from workshop] | [Owner] | [Date] | Pending |
```

### Step 6: Update Requirements Document

**Ask**:
```
Should I update the requirements document with these workshop decisions? (y/n)
```

If yes:
1. Read `requirements/requirements_specification.md`
2. Find sections with [NEEDS CLARIFICATION] or [TBD]
3. Replace with workshop decisions
4. Save updated requirements

### Step 7: Update Status

**Process**:
1. Read `status.md`
2. Update artifacts.workshops section:
   ```yaml
   workshops:
     generate: complete
     review: approved
     workshop_date: 2026-02-03
     decisions_count: 4
     action_items: 3
     reviewed_date: 2026-02-03
   ```
3. Also update requirements artifact if modified:
   ```yaml
   requirements:
     ...
     notes: "Updated with workshop decisions from 2026-02-03"
     last_updated: 2026-02-03
   ```
4. Write updated status.md

### Step 7.5: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `workshops`
- Action: `review`
- Status: `approved`
- Include workshop date and decisions count in Jira comment

### Step 7.6: Sync to Linear (Optional)

Follow the Linear sync workflow in `specs/utils/linear_sync.md`:
- Artifact: `workshops`
- Action: `review`
- Status: `approved`

### Step 7.7: Sync to Document Store (Optional)

If a document store is configured, follow the workflow in `specs/utils/docstore_sync.md` to re-sync the final workshop materials (agenda, decision matrix) to the configured store. This ensures any updates captured during the workshop are reflected in the client-accessible version.

Fail gracefully if the document store is unavailable.

### Step 8: Confirm and Suggest Next Steps

**Output**:
```
## Workshop Outcomes Recorded ✅

**Workshop Date:** 2026-02-03
**Decisions Made:** 4
**Action Items:** 3

**Updated Files:**
- .wire/[folder]/requirements/workshop_decision_matrix.md
- .wire/[folder]/requirements/requirements_specification.md

### Key Decisions

1. **[Topic 1]**: [Decision]
2. **[Topic 2]**: [Decision]
3. **[Topic 3]**: [Decision]
4. **[Topic 4]**: [Decision]

### Next Steps

1. **Complete action items** (3 items pending)

2. **Re-validate requirements** with workshop decisions:
   /wire:requirements-validate [folder]

3. **Get final approval**:
   /wire:requirements-review [folder]

4. **Once approved, proceed to design**:
   /wire:pipeline_design-generate [folder]
```

## Edge Cases

### Workshop Not Held Yet

If workshop hasn't happened:
```
Workshop materials exist but workshop hasn't been held yet.

Schedule and conduct the workshop first, then run this command to record outcomes.
```

### Workshop Materials Not Found

If no workshop materials:
```
Error: Workshop materials not found.

Generate workshop materials first: /wire:workshops-generate [folder]
```

### Some Decisions Not Made

If workshop couldn't decide on some topics:
```
Warning: Not all decisions were made in the workshop.

Record partial decisions? These items remain unresolved:
- Topic 3: [Unresolved topic]
- Topic 5: [Unresolved topic]

You can:
1. Record partial decisions now
2. Schedule follow-up workshop
3. Make decisions offline and come back
```

## Output

This command:
- Updates `requirements/workshop_decision_matrix.md` with decisions
- Updates `requirements/requirements_specification.md` (optional)
- Records action items
- Updates `status.md` with workshop completion
