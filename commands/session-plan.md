---
description: Optional planning ritual — propose a focused 3–5 step plan before starting work
argument-hint: (optional: release-folder)
---

# Optional planning ritual — propose a focused 3–5 step plan before starting work

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command

## Workflow Specification

---
description: Optional session planning ritual — propose a focused 3–5 step plan before starting work
---

# Wire Plan Command

## Purpose

An optional planning ritual. Enters Plan Mode, reads current release and engagement state, then proposes a focused 3–5 step session plan for explicit approval before any work begins. Useful for complex sessions or when multiple paths are possible.

Unlike the deprecated `session:start`, this command is not part of the mandatory session lifecycle — it is an on-demand tool for consultants who want a structured plan before proceeding.

## Inputs

**Optional**: `$ARGUMENTS` — release folder name (e.g. `releases/01-discovery`). If not provided, uses the most recently modified release.

## Workflow

### Step 1: Enter Plan Mode

Immediately enter Plan Mode. Do not perform any file edits, run any commands, or generate any artifacts until the session plan has been explicitly approved.

### Step 2: Load Release and Engagement Context

1. Locate the active release (by argument, or most recently modified `status.md`)
2. Read `status.md` — current phase, artifact states, session history (last 3 rows), blockers
3. Read `engagement/context.md` if present — engagement overview and objectives
4. Scan `.wire/research/sessions/*/summary.md` — surface any recent research relevant to the current phase

### Step 3: Scope Alignment Check (discovery releases only)

If `release_type` is `discovery` and `primary_analytical_focus` is set in `status.md`, display it prominently and evaluate any stated objective against it. If the objective is adjacent to the primary focus, surface a challenge before proposing the plan.

If `release_type` is `sop_discovery`, display the current Maturity Curve pin (under `sponsor_validation.maturity_pin` once recorded) and the count of completed stakeholder interviews vs the stakeholder map total. Surface any interviews that are missing the mandatory four-tag set before proposing the plan — those gaps block the consolidation step.

### Step 4: Ask What the Consultant Wants to Accomplish

Output a brief context summary, then ask:

```
What do you want to accomplish in this session?
(Or press Enter to follow the suggested next focus from the last session)
```

### Step 5: Propose Session Plan

Based on release state, research, and the stated objective, propose a focused plan:

```
## Proposed Session Plan

**Objective**: [stated objective or derived from suggested next focus]

**Steps**:
1. [Specific action with file paths or Wire commands]
2. [Next step]
3. [Validation or review step]

**Blocked by** (if applicable): [What needs resolving first]

Does this plan look right? (yes / adjust)
```

### Step 6: Wait for Approval

- **Yes**: exit Plan Mode and execute Step 1 of the plan
- **Adjust**: incorporate feedback and re-present
- **Different objective**: regenerate the plan

## Output

No files are created or modified during planning. After approval, executes the approved steps.

Execute the complete workflow as specified above.
