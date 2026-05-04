---
description: Demo and stakeholder approval for conversational assistant
argument-hint: <release-folder>
---

# Demo and stakeholder approval for conversational assistant

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.17\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_conversational_assistant-review\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.17\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Review conversational shopping assistant with stakeholders for approval
argument-hint: <project-folder>
---

# Agentic Commerce — Conversational Assistant Review Command

## Purpose

Demo the conversational shopping assistant to stakeholders, walk through the validation report, and capture approval or change requests. The demo should showcase multi-turn conversation, intent adaptation, inline product recommendations, and cart integration.

## Usage

```bash
/wire:ac_conversational_assistant-review YYYYMMDD_project_name
```

## Prerequisites

- `conversational_assistant.validate: pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Check `conversational_assistant.validate == pass`

If not:
```
Warning: Conversational assistant has not passed validation.
Run `/wire:ac_conversational_assistant-validate <project>` first.
Proceed anyway? (y/n)
```

### Step 2: Present for Review

```
## Conversational Assistant Review Session

**Project:** [PROJECT_NAME]
**Feature:** Multi-Turn Conversational Shopping Assistant
**Validation Report:** .wire/[project_id]/conversational_assistant/validation_report.md

### What to Review

Please evaluate the conversational assistant against these criteria:

**Conversation Quality**
- [ ] The assistant understands natural language product requests
- [ ] Multi-turn context is preserved (refinements work correctly)
- [ ] Intent detection feels accurate (product search vs general chat vs checkout)
- [ ] Replies are concise and helpful (not verbose or robotic)
- [ ] Shortcut pills are relevant to the product catalog

**Product Recommendations**
- [ ] Products recommended are genuinely relevant to the request
- [ ] Product cards render cleanly inline with the conversation
- [ ] Prices and images are correct
- [ ] Add to Cart works from within the chat

**User Experience**
- [ ] The modal opens smoothly from all three entry points (hero, Cmd+K, mobile button)
- [ ] Loading state is clear and not jarring
- [ ] The conversation feels natural enough for a real customer
- [ ] The UI adapts appropriately to different intent types

**Integration**
- [ ] Cart updates correctly after chat-initiated adds
- [ ] No visible errors or rough edges during the demo
```

### Step 3: Retrieve External Context (Optional)

1. Follow the meeting context retrieval workflow in `specs/utils/meeting_context.md`
   - Pass project folder and artifact `conversational_assistant`
   - Surface any prior discussions about chat UX, AI tone of voice, or product recommendation quality
2. Follow the Atlassian search workflow in `specs/utils/atlassian_search.md`
   - Search for any brand voice guidelines or customer experience requirements in Confluence

### Step 4: Demo Script

Guide the reviewer through this live demo sequence. Adapt the example queries to the actual product catalog before the session.

**Demo Scenario: Assisted Purchase Journey**

1. **Open assistant via hero button**
   - Point out the three ways to open: hero button, Cmd+K, mobile floating button

2. **Show shortcut pills**
   - Click "Summer gear" shortcut pill
   - Expected: message sent automatically, products appear

3. **Multi-turn refinement**
   - Say: "Something more lightweight and breathable"
   - Expected: product list narrows, context from first message retained
   - Point out: the assistant did not reset — it remembered "summer gear"

4. **Price refinement**
   - Say: "Under £50 please"
   - Expected: product list filtered to lower price points

5. **Add to Cart from chat**
   - Click "Add to Cart" on one of the recommended products
   - Open the cart drawer — show the item is there
   - Expected: cart updates without leaving the conversation

6. **Intent switch — general question**
   - Ask: "What's your return policy?"
   - Expected: GENERAL intent — text reply, no product cards rendered

7. **Checkout intent**
   - Say: "I'm ready to buy"
   - Expected: CHECKOUT intent — cart summary or checkout prompt shown

**Optional: Mobile demo**
- Resize browser to mobile width
- Show the floating action button
- Open the assistant and show the full-screen experience

### Step 5: Gather Feedback

```
Please provide your feedback:

1. **Reviewer name and role:**

2. **Decision:**
   - [ ] Approved — proceed to next feature
   - [ ] Approved with minor notes — proceed, address notes during enablement
   - [ ] Changes requested — list below before proceeding
   - [ ] Needs discussion — schedule follow-up

3. **Conversation quality rating (1-5):**
4. **Recommendation relevance rating (1-5):**
5. **UX and design rating (1-5):**

6. **Specific feedback:**
   (Describe any issues, wording concerns, product mismatches, or UX rough edges)

7. **Queries that didn't work well (if any):**
   (List any test queries that produced poor or irrelevant results)
```

### Step 6: Record Outcome

**If approved:**
```yaml
conversational_assistant:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  conversation_quality_rating: [1-5]
  relevance_rating: [1-5]
  ux_rating: [1-5]
  review_notes: "[notes]"
```

**If changes requested:**
```yaml
conversational_assistant:
  review: changes_requested
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  review_notes: "Changes: [list]"
```

### Step 7: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` — artifact: `conversational_assistant`, action: `review`.

### Step 8: Suggest Next Steps

**If approved:**
```
## Conversational Assistant Review: Approved ✓

### Suggested Next Features

- **Virtual Try-On** (extends the assistant with image generation):
  `/wire:ac_virtual_tryon-generate <project>`

- **Personalisation Engine** (personalised greetings and shortcuts):
  `/wire:ac_personalisation-generate <project>`

- **LLM Tools** (autonomous tool-calling layer):
  `/wire:ac_llm_tools-generate <project>`
```

**If changes requested:**
```
## Conversational Assistant Review: Changes Requested

Changes needed before approval:
[list from reviewer feedback]

**Steps:**
1. Apply changes via Claude Code in the repo
2. Re-run validation: `/wire:ac_conversational_assistant-validate <project>`
3. Re-run review: `/wire:ac_conversational_assistant-review <project>`
```

## Output

- Updated `.wire/<project_id>/status.md` with review outcome
- Optional Jira ticket status update

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
