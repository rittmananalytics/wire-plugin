---
description: Demo and stakeholder approval for visual similarity
argument-hint: <release-folder>
---

# Demo and stakeholder approval for visual similarity

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_visual_similarity-review\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.13\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Review visual similarity feature with stakeholders for approval
argument-hint: <project-folder>
---

# Agentic Commerce — Visual Similarity Review Command

## Purpose

Demo the visual similarity discovery feature to stakeholders, evaluate result relevance and UI quality, and capture approval or change requests. The review should demonstrate that "Find Similar" returns genuinely visually related products and adds real discovery value to the shopping experience.

## Usage

```bash
/wire:ac_visual_similarity-review YYYYMMDD_project_name
```

## Prerequisites

- `visual_similarity.validate: pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Check `visual_similarity.validate == pass`

If not:
```
Warning: Visual similarity has not passed validation.
Run `/wire:ac_visual_similarity-validate <project>` first.
Proceed anyway? (y/n)
```

### Step 2: Prepare for Demo

Before the session:
1. Read the validation report at `.wire/<project_id>/visual_similarity/validation_report.md`
2. Note which product types produced the best similarity results during validation
3. Identify 3 products to use in the demo — choose products with distinctive visual features
   (e.g. a brightly coloured jersey, a patterned item, a plain black piece)
4. Pre-run "Find Similar" on those products to warm the cache

### Step 3: Present for Review

```
## Visual Similarity Review Session

**Project:** [PROJECT_NAME]
**Feature:** Visual Similarity Discovery
**Approach:** [Real-time / Pre-computed embeddings]
**AI Model:** [from validation report]
**Validation Report:** .wire/[project_id]/visual_similarity/validation_report.md

### What to Review

**Result Relevance**
- [ ] Similar products are visually related to the source (colour, silhouette, style)
- [ ] The top results feel intuitively correct to a shopper
- [ ] Results differ meaningfully between different source products
- [ ] Similarity scores feel calibrated (not all 95+, not all 55-)

**Explanation Quality**
- [ ] Similarity reasons reference real visual attributes (not generic)
- [ ] Reasons are concise and shopper-friendly
- [ ] The percentage badge feels meaningful

**Discovery Value**
- [ ] "Find Similar" surfaces products that might otherwise be missed
- [ ] The feature would plausibly increase time on site and basket size
- [ ] It works across different product types in the catalog

**UI Integration**
- [ ] "Find Similar" button is correctly positioned and easy to find
- [ ] Loading experience is acceptable for a 5-15 second wait
- [ ] Result grid looks on-brand
```

### Step 4: Retrieve External Context (Optional)

1. Follow the meeting context retrieval workflow in `specs/utils/meeting_context.md`
   - Pass project folder and artifact `visual_similarity`
   - Surface any discussions about product discovery strategy or catalog navigation
2. Follow the Atlassian search workflow in `specs/utils/atlassian_search.md`
   - Search for any UX research or customer journey maps related to product discovery

### Step 5: Demo Script

**Demo Scenario: Product Discovery via Visual Similarity**

1. **Start on the product grid**
   - Open a product and point out the "Find Similar" button

2. **First product — distinctive colour**
   - Choose a brightly coloured jersey (e.g. red and yellow)
   - Click "Find Similar"
   - Show the loading state and the ~5-15 second wait (narrate: "AI is analysing the image")
   - Show results: point out that the top matches share the colour palette
   - Read one `similarity_reason` aloud — e.g. "Shares the same bold red base colour
     and graphic panel placement"

3. **Second product — silhouette**
   - Choose a plain black bib shorts
   - Click "Find Similar"
   - Show that results are also shorts/bottoms, not jerseys or accessories
   - Point out: the AI is matching on shape, not just colour

4. **Third product — pattern**
   - If available, choose a product with a distinctive pattern (camo, stripes, dots)
   - Show that results share the pattern type

5. **Discovery value narrative**
   - "A shopper arrives looking at this jersey. They click Find Similar and discover
     this other product they wouldn't have found by browsing categories."
   - Click through to one similar product from the results

6. **Score comparison**
   - Show the range of scores across the 6 results
   - Point out how the score drops as visual similarity decreases

### Step 6: Gather Feedback

```
Please provide your feedback:

1. **Reviewer name and role:**

2. **Decision:**
   - [ ] Approved — proceed to next feature
   - [ ] Approved with minor notes — proceed, address notes during enablement
   - [ ] Changes requested — list below before proceeding
   - [ ] Needs discussion — relevance quality needs improvement

3. **Result relevance rating (1-5):**
   (1 = results feel random, 5 = results are spot-on)

4. **Explanation quality rating (1-5):**

5. **UX integration rating (1-5):**

6. **Specific feedback:**
   (Note any product types where results were poor, any wording issues,
   any layout preferences)

7. **Catalog coverage concerns (if any):**
   (Did Find Similar work well for all product types, or only some?)
```

### Step 7: Record Outcome

**If approved:**
```yaml
visual_similarity:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  relevance_rating: [1-5]
  explanation_rating: [1-5]
  ux_rating: [1-5]
  review_notes: "[notes]"
```

**If changes requested:**
```yaml
visual_similarity:
  review: changes_requested
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  review_notes: "Changes: [list]"
```

### Step 8: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` — artifact: `visual_similarity`, action: `review`.

### Step 9: Suggest Next Steps

**If approved:**
```
## Visual Similarity Review: Approved ✓

### Suggested Next Features

- **LLM Chat with Tools** (autonomous product search agent):
  `/wire:ac_llm_tools-generate <project>`

- **Personalisation Engine** (connect visual preferences to user profile):
  `/wire:ac_personalisation-generate <project>`
```

**If changes requested:**
```
## Visual Similarity Review: Changes Requested

Changes needed:
[list from reviewer feedback]

**Common fixes:**
- Improve relevance: adjust scoring prompt weights (colour/silhouette/style ratios)
- Improve reasons: add instruction "use specific product attribute names, not generic terms"
- Performance: switch from real-time to pre-computed embeddings if latency is an issue

After changes: re-validate and re-review.
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
