---
description: Review conceptual model with business stakeholders
argument-hint: <project-folder>
---

# Review conceptual model with business stakeholders

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.3.0\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"conceptual_model-review\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.3.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Review conceptual model with business stakeholders
argument-hint: <project-folder>
---

# Conceptual Model Review Command

## Purpose

Present the conceptual entity model to business stakeholders for approval. This is a **business-level review, not a technical review**. The goal is to confirm:
- The right entities are included and named in the client's own terminology
- No important entities are missing
- Relationships correctly reflect how the business works
- The model aligns with the SOW scope

**Review audience**: Business stakeholders, client subject matter experts, and the project sponsor — not solely the technical team. The pipeline architecture, data model specification, and all dbt code that follow will be constrained by what is approved here. Getting this right now prevents expensive rework later.

## Usage

```bash
/wire:conceptual_model-review YYYYMMDD_project_name
```

## Prerequisites

- `conceptual_model`: `validate: pass`

## Workflow

### Step 1: Verify Prerequisites

Check `conceptual_model.validate == pass` in `status.md`.

If validation has not passed:
```
Error: Conceptual model must pass validation before stakeholder review.
Run: /wire:conceptual_model-validate <project_id>
```

If there are unresolved Open Questions (Section 5 of conceptual_model.md is non-empty), flag this to the consultant:
```
Warning: [N] open questions remain in the conceptual model (Section 5).
These should be resolved in the review session or in a workshop before approval.
```

### Step 2: Present the Conceptual Model

Display `design/conceptual_model.md` in full, including:
- Entity inventory (Section 1)
- erDiagram (Section 2)
- Relationship narrative (Section 3)
- Out-of-scope entities (Section 4)
- **Open questions (Section 5) — highlight prominently**

Suggest the consultant shares this document with stakeholders directly (e.g. in a screen-share, printed, or via a shared link) rather than reading it aloud.

### Step 2.5: Retrieve External Context (Optional)

**Process**:
1. Follow the meeting context retrieval workflow defined in `specs/utils/meeting_context.md`
   - Pass the project folder and artifact name `conceptual_model`
   - If Fathom MCP is available and relevant meetings found, present the meeting context summary
2. Follow the Atlassian search workflow defined in `specs/utils/atlassian_search.md`
   - Pass the project folder and artifact name `conceptual_model`
   - If Atlassian MCP is available, search Confluence for design docs and Jira for issue comments
   - Present any relevant findings
3. If neither service is available, proceed directly to Step 3

This step enriches the review with context from meeting recordings, Confluence documents, and Jira issue comments.

### Step 3: Gather Feedback

Use AskUserQuestion to collect the review outcome:

**Question**: "Has the conceptual model been reviewed with business stakeholders? What is the outcome?"

**Options**:
1. **Approved** — All entities and relationships are correct and complete. No open questions remain. Proceed to pipeline design and data model specification.
2. **Changes requested** — Entities or relationships need updating. Capture the specific changes needed.
3. **Needs discussion** — Further clarification required before approval (open questions unresolved, or significant disagreement on scope).

If "Changes requested": prompt "Please describe the required changes (which entities to add/remove/rename, which relationships to correct):" and capture as notes.

If "Needs discussion": suggest running a workshop.
```
Suggested next step: generate workshop materials to facilitate the discussion.
/wire:workshops-generate <project_id>
```

### Step 4: Update Status

**If approved**:
```yaml
conceptual_model:
  review: approved
  reviewed_by: [name and/or role of approver]
  reviewed_date: [today]
```
Add to status notes: `"Conceptual model approved [date] by [reviewer] — [entity count] entities, [relationship count] relationships confirmed"`

**If changes requested**:
```yaml
conceptual_model:
  review: changes_requested
  reviewed_date: [today]
```
Add to status notes: `"Conceptual model: changes requested [date] — [one-line summary of changes needed]"`

**If needs discussion**:
```yaml
conceptual_model:
  review: pending
```
Add to status blockers: `"Conceptual model review pending — open questions require workshop resolution"`

### Step 5: Suggest Next Steps

**If approved**:
```
## Conceptual Model Approved ✅

The entity model is confirmed by business stakeholders. Downstream design
artifacts are now unblocked.

### Next Steps (can be run in parallel or either order)

Design the data pipeline architecture:
  /wire:pipeline_design-generate <project_id>

Begin the data model specification (dbt layers):
  /wire:data_model-generate <project_id>

Both commands will read the approved conceptual model as a primary input.
```

**If changes requested**:
```
## Changes Required

Update design/conceptual_model.md with the requested changes:
[list changes captured]

Then re-validate and re-review:
  /wire:conceptual_model-validate <project_id>
  /wire:conceptual_model-review <project_id>
```

### Step 6: Sync to Jira (Optional)

Follow the Jira sync workflow in `specs/utils/jira_sync.md`:
- Artifact: `conceptual_model`
- Action: `review`
- Status: the review state just written to status.md (approved/changes_requested/pending)
- If approved, include reviewer name in Jira comment
- If changes_requested, include feedback text in Jira comment

## Edge Cases

### Stakeholder Not Available for Synchronous Review

If the review must be conducted asynchronously (e.g. by email or shared document):
- Record the date the document was sent and expected response date
- Set status to `pending` with a note
- Add to blockers: `"Conceptual model review pending stakeholder response — sent [date]"`

### Partial Approval (Some Entities Agreed, Others Disputed)

If stakeholders approve some entities but dispute others:
- Do not record as fully approved
- Record as `changes_requested`
- Note specifically which entities/relationships are agreed vs disputed
- Only disputed items need rework — don't regenerate the whole document

### Significant Scope Change Revealed During Review

If the review surfaces a major scope change (e.g. an entirely new domain added, or a core entity removed):
- Record as `changes_requested`
- Note: a significant scope change may also require updating the requirements specification
- Check whether the SOW needs to be amended before proceeding

## Output

- Updates `.wire/<project_id>/status.md` with review outcome, reviewer name, and date
- Notes added to status.md recording the decision and any change requests

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
