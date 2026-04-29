---
description: Start a working session — scan release context, propose session plan
argument-hint: (optional: release-folder)
---

# Start a working session — scan release context, propose session plan

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.13\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"session-start\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.13\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Start a working session — scan release context, check research, propose a focused session plan
---

# Session Start Command

## Purpose

Opens a working session on any Wire release. Enters Plan Mode, scans the current release's status and the engagement-level research store, then proposes a focused 3–5 step session plan for explicit approval before any work begins. Ensures every session starts intentionally, grounded in current state.

## Inputs

**Required**: A `.wire/` directory must exist in the current repository.

**Optional**: `$ARGUMENTS` — release folder name (e.g. `releases/01-discovery`). If not provided, looks for the most recently modified release.

## Workflow

### Step 1: Enter Plan Mode

Immediately enter Plan Mode. Do not perform any file edits, run any commands, or generate any artifacts until the session plan has been explicitly approved by the user.

Output:
```
🔵 Wire Session Starting — Plan Mode Active
Reading current release state and engagement context...
```

### Step 2: Locate the Active Release

**Process**:
1. If `$ARGUMENTS` was provided, use that as the release path:
   - First try `.wire/releases/$ARGUMENTS/status.md`
   - Then try `.wire/$ARGUMENTS/status.md` (legacy project layout)
2. If no argument provided, use Glob to find status files:
   - `.wire/releases/*/status.md` — two-tier layout
   - `.wire/*/status.md` — legacy layout
   - Sort by last modified time; use the most recently modified
3. If no status file is found, output:
   ```
   No release found in .wire/. Run /wire:new to create an engagement and first release.
   ```
   Exit Plan Mode and stop.

### Step 3: Read Current Release State

Read the located `status.md` file. Extract:
- Release name, type, client, and current phase
- Artifact completion state (which artifacts are done, in progress, blocked)
- Any blockers or notes
- The `session_history` table (last 3 rows) — what was done in recent sessions and what was suggested as next focus
- The `current_phase` field

### Step 4: Check Engagement Context

Look for engagement-level context:
1. Try to read `.wire/engagement/context.md` — engagement overview, client, objectives
2. If not found, note "No engagement context file found" (non-blocking)

#### Step 4b: Surface Client Satisfaction Signals

1. In `engagement/context.md`, look for a `client_satisfaction` or `nps_signals` field
2. If found and non-empty, surface it prominently in the session header:
   ```
   📊 Last client satisfaction signal: [value] — [date if available]
   ```
3. If not found — and the release has been active for more than 7 days — add a prompt to the session plan output:
   ```
   ⚠️  No client satisfaction signal recorded. Have there been any signals (NPS, informal feedback, check-in tone)
   worth noting? You can record these in engagement/context.md as:
     client_satisfaction: "6/10 — Josh, 2026-03-28. Seemed positive but brief."
   ```
4. If the recorded signal is below 7/10, add a highlighted note to the session header:
   ```
   ⚠️  Client satisfaction is below threshold ([value]). Consider: are there alignment gaps worth checking
   before committing to today's session plan?
   ```

### Step 5: Check Research Store

Scan for prior research:
1. Use Glob to list `.wire/research/sessions/*/summary.md`
2. If files found, read the most recent 2–3 summaries (limit to recent sessions to avoid token overuse)
3. Note any findings relevant to the current release type or phase

### Step 6: Ask What the Consultant Wants to Accomplish

Output what you found from the status scan:

```
## Current Release: [Release Name]
Type: [release_type] | Phase: [current_phase] | Client: [client_name]

### Artifact Status
[Brief summary: X artifacts complete, Y in progress, Z blocked]

### Previous Session (if any)
[Last session date and what was accomplished]
[Suggested next focus from last session]
```

Then ask directly in chat:
```
What do you want to accomplish in this session?
(Or press Enter to follow the suggested next focus from last session)
```

Wait for user response.

### Step 6.5: Scope Alignment Check (discovery releases only)

**Apply if**: `release_type` is `discovery` AND `primary_analytical_focus` is set in `status.md` or `planning/release_brief.md`.

**Process**:
1. Read `primary_analytical_focus` from `status.md` (set by `release-brief-generate`)
2. Display it at the top of the session context block:
   ```
   🎯 Primary focus for this release: [primary_analytical_focus]
   ```
3. Evaluate the user's stated objective against the primary focus:
   - **Aligned**: the work directly produces or enables the primary use case (e.g. drafting the entity model for the funnel, auditing data sources needed for funnel metrics, drafting the stakeholder interview for the funnel domain owner)
   - **Prerequisite**: the work is not the use case itself but is a direct unblocking step (e.g. access setup, resolving a data dependency)
   - **Adjacent**: the work addresses something real and legitimate but not in service of the primary focus (e.g. org capability assessment, comprehensive data quality audit, root-cause analysis of governance issues)
4. If the objective is **Adjacent**, surface a challenge before proposing the plan:
   ```
   ⚠️  Scope alignment check: the proposed work ([objective]) sits outside the primary analytical focus
   ([primary_analytical_focus]).

   Is this:
   (a) A direct blocker that must be cleared to reach the focal use case?
   (b) A legitimate secondary workstream agreed with the client?
   (c) Scope drift — work that should be noted and deferred?

   (If unsure, default to: document the finding, hand it back to the client, return to the focal use case)
   ```
5. Wait for user response before proposing the session plan
6. Record the alignment classification in the session plan header: `[Aligned | Prerequisite | Adjacent — [reason]]`

**Do not apply** this check for non-discovery releases (pipeline_only, dashboard_first, etc.) — scope is already well-defined by the artifact lifecycle in those release types.

### Step 7: Propose Session Plan

Based on the release state, research context, and the user's stated objective, propose a focused session plan. The plan must:
- Contain 3–5 concrete steps (no more — focused sessions produce better results)
- Reference specific Wire commands or artifact paths where relevant
- Identify any blockers or missing inputs that need to be resolved first
- Be achievable within a typical 2–3 hour working session

Format:
```
## Proposed Session Plan

**Objective**: [User's stated objective or derived from suggested next focus]

**Steps**:
1. [Specific action — e.g. "Read requirements_specification.md and identify any gaps before generating the pipeline design"]
2. [Specific Wire command — e.g. "Run /wire:pipeline_design-generate [release_folder]"]
3. [Specific validation or review step]
...

**Blocked by** (if applicable): [What needs to be resolved first]

**Research available**: [Any relevant prior research summaries]

Does this plan look right? (yes / adjust)
```

### Step 8: Wait for Plan Approval

Wait for the user to approve or adjust the plan.

- If user says **yes** or accepts: exit Plan Mode and output:
  ```
  ✅ Session plan approved. Starting work...
  ```
  Then begin executing Step 1 of the plan.

- If user wants to **adjust**: incorporate their feedback and re-present the plan. Repeat until approved.

- If user provides a **completely different objective**: regenerate the plan around their stated objective.

## Edge Cases

### First session (no session history)
If there is no `session_history` in `status.md` and no prior sessions, skip the "previous session" section. Propose a plan based on the current phase and the first incomplete artifact.

### Multiple releases
If multiple releases exist and no argument was provided, show a brief list and ask the user which release they want to work on before proceeding to Step 3.

### Engagement without two-tier structure (legacy)
If `.wire/releases/` doesn't exist but `.wire/[folder]/` does, use the legacy layout. Everything else works the same — the "engagement context" check will simply find nothing.

### No incomplete work
If all artifacts in the release are complete, propose:
```
All artifacts in this release are complete.

Options:
1. Start a new release (/wire:new)
2. Archive this release (/wire:archive [folder])
3. Review any artifact again

What would you like to do?
```

## Output

This command does not create or modify files during the planning phase. After plan approval, it executes the approved steps (which may involve other Wire commands that create files).

Execute the complete workflow as specified above.
