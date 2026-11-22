---
wire_schema: "1.0"
command: utility
artifact: session
domain: session
release_types: []
action_type: lifecycle
logs_execution: false
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
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

Based on release state, research, and the stated objective, propose a focused plan. **Every executable step names the Wire command that performs it**, or the skill when no command covers the step. A step that names neither is not a plan step; it is a description of an outcome, and it is how work ends up done by hand instead of through the command (wire#265).

```
## Proposed Session Plan

**Objective**: [stated objective or derived from suggested next focus]

| # | Step | Type | Command or skill | Scope | Produces |
|---|------|------|------------------|-------|----------|
| 1 | [what, in method terms] | command | /wire:<command> <release-folder> [flags] — the command in full, as it would be typed | [objects this step may touch] | [file, report, PR, decision] |
| 2 | [what] | skill | <skill-identifier> — no command covers this because [reason] | [scope] | [output] |
| 3 | [validation or review step] | command | /wire:<artifact>-validate <release-folder> | [scope] | PASS/FAIL report |
| 4 | [approval or hand-off] | human | external | decision | [who] | [what they decide] |

**Left out, and why**: [steps of the method this plan does not include, with the reason]

**Blocked by** (if applicable): [What needs resolving first]

Approve / Changes / Explain <step> / Cancel?
```

Step types: `command` (a `/wire:` command), `skill` (a Wire skill, only where no command covers the work; say why), `human` (something the consultant does), `external` (a client action, e.g. PR review), `decision` (a ruling by a named owner), `investigation` (read-only; nothing written).

On **Explain**, give the consequence of skipping that step in this release's own terms, not a general principle.

### Step 6: Wait for Approval

- **Approve**: exit Plan Mode and execute step 1 of the plan. **The approved commands are what runs.** Do not do by hand what a named command does. If a step's result changes what should happen next, stop, propose the amendment and wait; never add a step, widen a scope or substitute a command silently. A step that ran differently from the plan is recorded in the execution log's Detail as `deviation: <what differed>` (see `specs/utils/execution_log.md`), so `/wire:status-sync` can report it.
- **Changes**: incorporate feedback and re-present
- **Cancel** or a different objective: regenerate the plan, or stop

## Output

No files are created or modified during planning. After approval, executes the approved steps by running the commands the plan names. When invoked from `/wire:work`, the approved plan is also written to the iteration file (see `specs/work.md`).
