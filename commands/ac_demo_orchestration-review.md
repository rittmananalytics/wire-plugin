---
description: Live demo run-through and stakeholder approval
argument-hint: <release-folder>
---

# Live demo run-through and stakeholder approval

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_demo_orchestration-review\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.17\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Review demo orchestration with stakeholders — run the full automated demo and capture approval
argument-hint: <project-folder>
---

# Agentic Commerce — Demo Orchestration Review Command

## Purpose

Run the automated demo with stakeholders and gather feedback on the demo flow, timing, narrative quality, and overall impact. This is typically the final review of the agentic commerce release — a successful approval here means the engagement is complete and ready for client handoff or enablement.

## Usage

```bash
/wire:ac_demo_orchestration-review YYYYMMDD_project_name
```

## Prerequisites

- `demo_orchestration.validate: pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Check `demo_orchestration.validate == pass`

If not:
```
Warning: Demo orchestration has not passed validation.
Run `/wire:ac_demo_orchestration-validate <project>` first.
Proceed anyway? (y/n)
```

### Step 2: Prepare for Review

Before the session:
1. Read the validation report at `.wire/<project_id>/demo_orchestration/validation_report.md`
2. Check which demo modes are implemented and validated
3. Pre-warm the demo:
   - Deploy the latest code (or confirm local dev server is running cleanly)
   - Run the full demo once in a private window to warm any caches
   - Note average duration of each demo mode
4. Prepare the demo environment:
   - Full-screen browser, browser console hidden
   - Screen sharing ready
   - Sound/audio disabled (demos should be silent)
5. Have the feature summary ready (which AI features are shown in each demo mode)

### Step 3: Pre-Demo Context Briefing

Present the following to stakeholders before running the demo:

```
## Agentic Commerce Demo Briefing

**What you're about to see:**

This is an automated demo of all the AI commerce features we've built.
The demo runs entirely on its own — no clicking, no typing. The system is
simulating a realistic customer journey.

**Features in this demo:**

[Adapt based on which modes are available]

?demo=shopping:
- Conversational shopping assistant (multi-turn AI chat)
- AI-powered semantic product search
- Inline product recommendations with add-to-cart

?demo=tryon (if implemented):
- All of the above, plus
- AI virtual try-on (product composited onto user photo)

?demo=full (if implemented):
- Full end-to-end journey across all features

**Duration:** approximately [N] minutes per demo mode

**What to observe:**
- The AI's ability to understand natural language (not keyword matching)
- Multi-turn context preservation (the AI remembers earlier messages)
- How product recommendations adapt based on refinement
- The visual quality of virtual try-on imagery
- The personalised greeting at the start (pre-built demo persona)
```

### Step 4: Retrieve External Context (Optional)

1. Follow the meeting context retrieval workflow in `specs/utils/meeting_context.md`
   - Pass project folder and artifact `demo_orchestration`
   - Surface any prior discussions about demo requirements, investor presentations,
     or client showcasing expectations
2. Follow the Atlassian search workflow in `specs/utils/atlassian_search.md`
   - Search for any demo scripts, presentation requirements, or stakeholder preferences

### Step 5: Run the Demo

**Run the shopping demo first** (shortest, clearest narrative):

```
Open: http://[demo-url]/?demo=shopping
```

Let the demo run completely without interruption. After the closing overlay appears, pause
and ask for initial reactions before continuing.

**If time allows, run the try-on or full demo:**

```
Open: http://[demo-url]/?demo=tryon
```

**If the demo stalls or fails mid-run**, restart:
- Reload the page
- Click play again
- Narrate: "Let me restart — the AI response took longer than expected this time"

### Step 6: Feature-by-Feature Discussion

After the demo, walk through each feature briefly:

```
### Feature Review Checklist

**Semantic Search (if shown)**
- [ ] Natural language queries returned relevant products
- [ ] Relevance explanations were clear
- [ ] Performance felt acceptable

**Conversational Assistant**
- [ ] Multi-turn conversation felt natural
- [ ] AI understood the initial query correctly
- [ ] Refinement narrowed results appropriately
- [ ] Shortcut pills are relevant to this catalog

**Virtual Try-On (if shown)**
- [ ] Image quality is sufficient for the demo
- [ ] Loading experience was acceptable
- [ ] Graceful fallback shown if try-on timed out

**Personalisation**
- [ ] Personalised greeting used the demo persona's name
- [ ] Demo felt cohesive as a personalised journey

**Overall Demo Narrative**
- [ ] The demo clearly communicates "AI-powered commerce"
- [ ] The automated flow felt natural, not mechanical
- [ ] The closing overlay message is compelling
- [ ] Timing felt appropriate (not too rushed, not too slow)
```

### Step 7: Gather Feedback

```
Please provide your feedback on the overall demo experience:

1. **Reviewer name and role:**

2. **Decision:**
   - [ ] Approved — demo is ready for client presentation / investor showcase
   - [ ] Approved with minor notes — demo ready, minor timing tweaks needed
   - [ ] Changes requested — see below (re-review needed before client presentation)
   - [ ] Needs discussion — major rework required

3. **Demo impact rating (1-5):**
   (1 = doesn't impress, 5 = genuinely wow)

4. **Timing rating (1-5):**
   (1 = too fast/too slow, 5 = perfect pacing)

5. **Narrative clarity rating (1-5):**
   (1 = unclear what we're watching, 5 = crystal clear story)

6. **Specific feedback:**
   - What worked best in the demo?
   - What felt unclear or underwhelming?
   - Any timing changes needed (which phases should be longer/shorter)?
   - Any queries to change (initial or refinement)?
   - Any closing overlay wording changes?
   - Should any features be included or removed from the demo?

7. **Presentation context:**
   - Who is this demo primarily for? (Client / Investors / Conference / Internal)
   - Any specific features to emphasise for that audience?
   - Any features to de-emphasise or remove?
```

### Step 8: Record Outcome

**If approved:**
```yaml
demo_orchestration:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  demo_impact_rating: [1-5]
  timing_rating: [1-5]
  narrative_rating: [1-5]
  review_notes: "[notes]"
```

**If changes requested:**
```yaml
demo_orchestration:
  review: changes_requested
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  review_notes: "Changes: [list]"
```

### Step 9: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` — artifact: `demo_orchestration`, action: `review`.

### Step 10: Suggest Next Steps

**If approved:**
```
## Demo Orchestration Review: Approved ✓

## Agentic Commerce Release: Complete

All features have been generated, validated, and reviewed:
- Storefront
- Semantic Search
- Conversational Assistant
- Virtual Try-On (if built)
- Visual Similarity (if built)
- LLM Tools (if built)
- Personalisation
- UCP Server (if built)
- Demo Orchestration

### Recommended Next Steps

1. **Production deployment**:
   - Swap Stripe test keys for live keys (STRIPE_SECRET_KEY = sk_live_...)
   - Configure a production Supabase project
   - Deploy all edge functions to production

2. **Enablement**:
   - Record a walkthrough of the demo for async sharing
   - Document how to run each demo mode for sales/marketing teams
   - Share the ?demo=full URL with client stakeholders

3. **Ongoing maintenance**:
   - Sync new Shopify products to the search index periodically
   - Monitor edge function logs for errors
   - Review personalisation data periodically for quality
```

**If changes requested:**
```
## Demo Orchestration Review: Changes Requested

Changes needed:
[list from reviewer feedback]

**Common timing fixes in src/lib/demoConstants.ts:**
- Slow down: increase DEMO_TIMINGS.resultsWait from 3000 to 5000
- Speed up: decrease DEMO_TIMINGS.greetingWait from 1500 to 800
- Change queries: update DEMO_QUERIES.shopping.initial

**Common narrative fixes:**
- Closing overlay wording: update in Index.tsx closing overlay JSX
- Demo mode selection: adjust which modes are active

After changes: re-validate and re-review.
```

## Output

- Updated `.wire/<project_id>/status.md` with review outcome
- Optional Jira ticket status update

---

*When this review is approved, the Agentic Commerce release is complete.*

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
