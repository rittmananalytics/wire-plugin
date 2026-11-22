---
wire_schema: "1.0"
command: generate
artifact: problem_definition
domain: discovery
release_types:
  - discovery_shape_up
action_type: artifact
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
preconditions: []
description: Generate structured problem definition for a discovery release

---

# Problem Definition Generate Command

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Generates a structured problem definition document that frames the business problem, current state, desired outcome, and constraints before any solution is proposed. This is the first artifact in a discovery release and feeds directly into the pitch document.

A good problem definition resists the temptation to jump to solutions. Its job is to articulate the problem so clearly and completely that the right solution becomes obvious — not to prescribe one.

## Inputs

**Required**:
- Release folder: `.wire/releases/$ARGUMENTS/` (or `.wire/$ARGUMENTS/` for legacy layout)

**Helpful (read if present)**:
- `engagement/context.md` — engagement overview, client background, objectives
- `engagement/sow.md` — statement of work
- `engagement/calls/` — call transcripts and meeting notes
- Any documents in the release's `artifacts/` folder

## Workflow

### Step 1: Locate the Release

**Process**:
1. Try `.wire/releases/$ARGUMENTS/` first (two-tier layout)
2. Fall back to `.wire/$ARGUMENTS/` (legacy layout)
3. If neither exists, output an error listing available releases and stop

### Step 2: Read Engagement and Release Context

**Process**:
1. Read `engagement/context.md` if it exists — extract client background, engagement objectives, key stakeholders
2. Read `engagement/sow.md` if it exists — extract scope, constraints, budget context
3. Read any files in `.wire/releases/$ARGUMENTS/artifacts/` or `.wire/$ARGUMENTS/artifacts/`
4. Read any call transcripts in `engagement/calls/` — look for problem statements, pain points, current-state descriptions

If no source material is found, proceed to Step 3 (interactive mode) immediately.

### Step 3: Interactive Problem Framing

Ask directly in chat — one question at a time:

**Q1:**
```
Who is experiencing this problem? (Role, team, or group)
```

**Q2:**
```
What are they trying to do? (The job or goal they're trying to accomplish)
```

**Q3:**
```
What is getting in their way right now? (The specific friction or gap)
```

**Q4:**
```
How are they currently working around it? (Workarounds, manual processes, or tools they're using instead)
```

**Q5:**
```
What does "solved" look like? (The outcome when this problem no longer exists — not how to get there)
```

**Q6:**
```
What constraints must any solution respect? (Budget, timeline, technology, compliance, team capacity)
```

**Q7:**
```
What have we already tried or ruled out? (Failed approaches, rejected solutions, non-starters)
```

**Q8:**
```
What are we likely to discover during this engagement that we should observe and document — but NOT attempt to fix ourselves?
(Think: adjacent organisational problems, root causes that belong to the client's internal roadmap, governance issues that are real but outside our delivery scope)
```

If source material was read in Step 2, pre-populate answers from the documents and show them to the user for confirmation rather than asking from scratch.

### Step 4: Generate Problem Definition Document

**Output location**: `.wire/releases/$ARGUMENTS/planning/problem_definition.md`
(Legacy layout: `.wire/$ARGUMENTS/design/problem_definition.md`)

**Document structure**:

```markdown
# Problem Definition: [Engagement Name]

**Release**: [release_folder]
**Client**: [client_name]
**Date**: [generation_date]
**Version**: 1.0

---

## 1. Who Has This Problem

[Role, team, or group experiencing the problem. Be specific — avoid "the business" or "users".]

## 2. What They Are Trying to Do

[The underlying job-to-be-done — the goal the person is trying to accomplish, independent of any solution.]

## 3. What Is Getting in Their Way

[The specific friction, gap, or obstacle. Be concrete. Avoid abstract descriptions like "lack of visibility".]

**Current workarounds**:
[How they cope today — manual processes, spreadsheets, alternative tools, tribal knowledge]

## 4. Impact of the Problem

| Dimension | Current State | Desired State |
|-----------|---------------|---------------|
| Time | | |
| Quality | | |
| Cost / Risk | | |
| Decision making | | |

## 5. What "Solved" Looks Like

[Outcome description — not a solution, but what the world looks like when this problem no longer exists. Write in present tense as if the problem is already solved.]

## 6. Constraints

- **Budget**: [known budget ceiling or "to be determined"]
- **Timeline**: [desired completion or constraint — appetite]
- **Technology**: [must-use or must-avoid platforms/tools]
- **Compliance**: [regulatory, security, or data governance constraints]
- **Team capacity**: [available people and their skills]

## 7. Scope Constraints

### 7a. What this engagement will not produce
[A comprehensive data strategy / full operating model / resolution of problems outside the analytical delivery function — be specific to the engagement]

### 7b. What we will observe but not attempt to resolve
[Organisational capability gaps, governance issues, product definition gaps, team structure problems — things the delivery team will surface and hand back to the client, not fix]

### 7c. Escalation, not investigation
Where the team encounters blockers — missing data, undefined product terminology, access gaps — these will be surfaced to the client engagement lead immediately for resolution. The team will not investigate or work around blockers independently. The team's job is to find the critical path to the first deliverable and name what stands in the way of it.

## 8. Previously Tried or Ruled Out

[Approaches that have been attempted or rejected, and why. Avoids repeating failed paths.]

## 9. Open Questions

| Question | Why It Matters | Owner | Status |
|----------|----------------|-------|--------|
| [question] | [why] | [name] | Open |

## 10. References

[Links to SOW sections, call transcripts, or other source material used in this document]
```

### Step 5: Update Release Status

**Process**:
1. Read `.wire/releases/$ARGUMENTS/status.md`
2. Update the `problem_definition` artifact:
   ```yaml
   problem_definition:
     generate: "complete"
     validate: "not_started"
     review: "not_started"
     file: "planning/problem_definition.md"
     generated_date: [today's date]
   ```
3. Update `last_updated`
4. Write updated status.md

### Step 6: Sync to Document Store (Optional)

If a document store is configured for this project, follow the workflow in `specs/utils/docstore_sync.md`:
- `artifact_id`: `problem_definition`
- `artifact_name`: `Problem Definition`
- `file_path`: `.wire/releases/[release_folder]/artifacts/problem_definition.md`
- `project_id`: the release folder path (e.g. `releases/01-discovery`)

If docstore sync fails, log the error and continue — do not block the generate command.

### Step 7: Confirm and Suggest Next Steps

```
## Problem Definition Generated

File: .wire/releases/[folder]/planning/problem_definition.md

### Summary
- Problem owner: [role/team]
- Core friction: [one-line summary]
- Open questions: [count]

### Next Steps

1. Validate the problem definition:
   /wire:problem-definition-validate [folder]

   Checks: is the problem well-framed? Are constraints specific? Is "solved" measurable?

2. Review with stakeholders:
   /wire:problem-definition-review [folder]

3. When approved, generate the pitch:
   /wire:pitch-generate [folder]
```

## Edge Cases

### No source material and user provides minimal answers
If answers are very thin (single words, unclear), ask follow-up probing questions:
- "Can you give me a concrete example of when this happens?"
- "What does that cost the team in hours per week, or in dollars?"
- "Who is the person most affected by this today?"

### Problem is already well-defined (client has a clear brief)
If the engagement context already contains a clear problem statement, generate the document directly from that material and show it for confirmation rather than stepping through each question.

## Output Files

- `.wire/releases/[folder]/planning/problem_definition.md`
- Updated `.wire/releases/[folder]/status.md`
