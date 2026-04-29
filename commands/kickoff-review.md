---
description: Review kick-off deck internally and export to PDF on approval
argument-hint: [release-folder]
---

# Review kick-off deck internally and export to PDF on approval

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.10\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"kickoff-review\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.10\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Review kick-off deck internally and record approval for PDF export
argument-hint: "[release-folder]"
---

# Kickoff Deck — Review

## Purpose

Conducts an internal review of the kick-off deck before it is presented to the client. Surfaces meeting context from Fathom (if available), collects reviewer feedback, records the review outcome, and on approval instructs the consultant how to export the PDF.

## Inputs

- Engagement-level: `.wire/kickoff-deck.html`
- Release-enriched: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`

`kickoff_deck.validate` must be `complete`. If not: stop — "Run `/wire:kickoff-validate` first."

## Workflow

### Step 1: Locate the deck file

Resolve in order:
1. If `<release-folder>` supplied: `.wire/releases/<release-folder>/artifacts/kickoff-deck.html`
2. Else: `.wire/kickoff-deck.html`

Read the EDITMODE block. Extract `clientName`, `engagementType`, and `presenters` for the review header.

### Step 2: Surface meeting context (Fathom)

Attempt to retrieve Fathom meeting context via the meeting context utility (`wire/specs/utils/meeting_context.md`). Search for recent meetings related to the kickoff or scoping discussion with this client.

If Fathom is available and meetings are found, surface:
- Any client-stated priorities or expectations from scoping calls
- Any concerns or preferences about the kick-off format
- Any changes to team composition or timeline mentioned since the SoW

If Fathom is unavailable, proceed without — note this in the review header.

### Step 3: Present the review summary

Display:

```
KICKOFF DECK INTERNAL REVIEW
Client: [clientName]
Engagement type: [engagementType]
Deck: [file path]
Presenters: [names and roles]

Slide-by-slide content summary:
  Slide 01 (Title):    [clientName] — [engagementDate]
  Slide 04 (Diagnosis): [first 80 chars of slide4LeftCache or "EMPTY"]
  Slide 05 (Metric):   [slide5Number][slide5Suffix] — [slide5Bold or "EMPTY"]
  Slide 07 (Problems): [slide6Count] problems
  Slide 09 (Outcomes): [slide8Count] outcomes
  Slide 11 (Architecture): [slide10Headline or "EMPTY"]
  Slide 13 (Timeline): W1 — [slide12W1Focus or "EMPTY"] / W2 — [slide12W2Focus or "EMPTY"]
  Slide 15 (Access):   [slide14Count] categories
  Slide 16 (Team):     [presenter count] presenter(s)

[Fathom context, if available]
```

### Step 4: Collect reviewer feedback

Ask:

```
Please review the deck at [file path] in your browser, then answer:

1. Are all slides accurate and complete?
2. Are there any content changes needed before presenting?
3. Is the presenter list correct?
4. Approved to export as PDF and present?

Enter feedback, or type "approved" to record approval.
```

### Step 5: Handle feedback

**If changes are needed**:
- Record the feedback verbatim
- Set `kickoff_deck.review: "in_progress"` in status
- Instruct consultant: "Update the EDITMODE block in [file path] using the tweaks panel or by editing the JSON directly, then re-run `/wire:kickoff-validate` and `/wire:kickoff-review`."

**If approved**:
- Set `kickoff_deck.review: "complete"` in status
- Record the reviewer name and date in status

### Step 6: PDF export instructions (on approval)

```
✅ KICKOFF DECK APPROVED

To export as PDF, run one of the following:

macOS (Google Chrome):
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless \
    --print-to-pdf="kickoff.pdf" \
    --print-to-pdf-no-header \
    "file://$PWD/[deck-path]"

macOS (Chromium via Homebrew):
  /opt/homebrew/bin/chromium \
    --headless \
    --print-to-pdf="kickoff.pdf" \
    --print-to-pdf-no-header \
    "file://$PWD/[deck-path]"

Linux / CI:
  chromium --headless --no-sandbox \
    --print-to-pdf="kickoff.pdf" \
    --print-to-pdf-no-header \
    "file://$PWD/[deck-path]"

If the architecture diagram (slide 11) appears blank in the PDF, add:
  --virtual-time-budget=5000

Fallback (interactive browser):
  Open [deck-path] in Chrome → Cmd+P (Mac) or Ctrl+P (Linux/Windows)
  → Destination: Save as PDF → Layout: Landscape → Margins: None → Background graphics: ON

The PDF will be saved to the current working directory. Move it alongside the HTML:
  mv kickoff.pdf [deck-dir]/kickoff-deck.pdf
```

### Step 7: Sync to issue tracker

If Jira or Linear are configured, update the kickoff_deck sub-issue/task to "Done".

## Status transitions

| Outcome | `review` field |
|---------|---------------|
| Changes requested | `in_progress` |
| Approved | `complete` |

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
