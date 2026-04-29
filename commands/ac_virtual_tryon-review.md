---
description: Demo and stakeholder approval for virtual try-on
argument-hint: <release-folder>
---

# Demo and stakeholder approval for virtual try-on

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
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ac_virtual_tryon-review\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.13\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Review AI virtual try-on feature with stakeholders for approval
argument-hint: <project-folder>
---

# Agentic Commerce — Virtual Try-On Review Command

## Purpose

Demo the virtual try-on feature to stakeholders, evaluate image generation quality and the graceful fallback experience, and capture approval or change requests before proceeding to the next feature.

## Usage

```bash
/wire:ac_virtual_tryon-review YYYYMMDD_project_name
```

## Prerequisites

- `virtual_tryon.validate: pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Check `virtual_tryon.validate == pass`

If not:
```
Warning: Virtual try-on has not passed validation.
Run `/wire:ac_virtual_tryon-validate <project>` first.
Proceed anyway? (y/n)
```

### Step 2: Prepare for Demo

Before the review session:
1. Read the validation report at `.wire/<project_id>/virtual_tryon/validation_report.md`
2. Identify which image model was used and its generation quality notes
3. Pre-upload a demo photo to `localStorage("user_photo_url")` so the demo starts smoothly
4. Select 2-3 products with clean, high-contrast product images (jackets, jerseys) that
   tend to produce better try-on results

### Step 3: Present for Review

```
## Virtual Try-On Review Session

**Project:** [PROJECT_NAME]
**Feature:** AI Virtual Try-On
**Image Model:** [from validation report]
**Validation Report:** .wire/[project_id]/virtual_tryon/validation_report.md

### What to Review

**Generation Quality**
- [ ] The generated try-on image is realistic and shows the product on the person
- [ ] The person's face and body pose are preserved
- [ ] Clothing overlay looks natural (not pasted, no obvious artefacts)
- [ ] Quality is sufficient to increase purchase confidence

**UX and Loading Experience**
- [ ] "Try this on" button is clearly visible on the product page
- [ ] Loading animation is engaging rather than a blank wait
- [ ] Loading text cycling feels appropriate for the 10-30s wait
- [ ] The 45-second timeout fallback is handled gracefully

**Photo Upload Flow**
- [ ] Photo upload prompt is clear and non-intrusive
- [ ] Users can change their photo easily
- [ ] Privacy messaging is adequate (if required by client)

**Fallback and Error Experience**
- [ ] When try-on fails, the "Add to Cart" button is still clearly available
- [ ] The error message is reassuring, not alarming
- [ ] The failure does not feel like a dead end
```

### Step 4: Retrieve External Context (Optional)

1. Follow the meeting context retrieval workflow in `specs/utils/meeting_context.md`
   - Pass project folder and artifact `virtual_tryon`
   - Surface any discussions about AI image quality expectations or privacy concerns
2. Follow the Atlassian search workflow in `specs/utils/atlassian_search.md`
   - Search for any brand guidelines around AI-generated imagery
   - Search for any data privacy or photo retention requirements

### Step 5: Demo Script

**Demo Scenario: Product Try-On on the Product Detail Page**

1. **Navigate to a product detail page**
   - Choose a product with a clear, well-lit product image
   - Point out where the "Try this on" button sits

2. **First-time photo upload**
   - Click "Upload a photo to try this on"
   - Upload the pre-prepared demo photo
   - Show the thumbnail preview and "Change photo" option

3. **Trigger try-on**
   - Click "Try this on"
   - Show the loading animation cycling through the three loading messages
   - Narrate: "The AI is compositing the product image onto the person's photo —
     this takes 10-30 seconds with a 45-second timeout"

4. **Show result**
   - When the try-on image appears, compare it side-by-side with the product image
   - Point out how the person's pose and face are preserved
   - Click "Add to Cart" from the try-on view

5. **Show graceful fallback (optional)**
   - Demonstrate what happens when try-on fails or times out
   - Show that "Add to Cart" remains available

6. **Second product**
   - Navigate to another product with the photo already stored
   - Show that the photo is remembered — no re-upload needed

### Step 6: Gather Feedback

```
Please provide your feedback:

1. **Reviewer name and role:**

2. **Decision:**
   - [ ] Approved — proceed to next feature
   - [ ] Approved with minor notes — proceed, address notes during enablement
   - [ ] Changes requested — list below before proceeding
   - [ ] Needs discussion — image quality may need a different model

3. **Image generation quality rating (1-5):**
   (1 = unusable, 3 = acceptable for demo, 5 = production-ready)

4. **Loading experience rating (1-5):**

5. **Fallback experience rating (1-5):**

6. **Specific feedback:**
   (Note any artefacts, quality issues, UX rough edges, or privacy concerns)

7. **Model recommendation:**
   - [ ] Current model is acceptable
   - [ ] Recommend switching to: [model name]
   - [ ] Recommend removing this feature from the demo

8. **Privacy or legal concerns (if any):**
```

### Step 7: Record Outcome

**If approved:**
```yaml
virtual_tryon:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  image_quality_rating: [1-5]
  loading_ux_rating: [1-5]
  fallback_rating: [1-5]
  review_notes: "[notes]"
```

**If changes requested:**
```yaml
virtual_tryon:
  review: changes_requested
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  review_notes: "Changes: [list]"
```

### Step 8: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` — artifact: `virtual_tryon`, action: `review`.

### Step 9: Suggest Next Steps

**If approved:**
```
## Virtual Try-On Review: Approved ✓

### Suggested Next Features

- **Visual Similarity** (catalog discovery via image matching):
  `/wire:ac_visual_similarity-generate <project>`

- **Demo Orchestration** (showcase try-on in automated demo flow):
  `/wire:ac_demo_orchestration-generate <project>`
```

**If changes requested:**
```
## Virtual Try-On Review: Changes Requested

Changes needed:
[list from reviewer feedback]

**Common fixes:**
- Switch image model: update GEMINI_API_KEY → OPENAI_API_KEY and update
  the model call in supabase/functions/virtual-tryon/index.ts
- Improve prompt: add more detail about preserving face and adjusting lighting
- Adjust timeout: change TRYON_TIMEOUT constant if generation regularly exceeds limit

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
