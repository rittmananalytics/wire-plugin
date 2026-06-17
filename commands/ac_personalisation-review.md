---
description: Demo and stakeholder approval for personalisation
argument-hint: <release-folder>
---

# Demo and stakeholder approval for personalisation

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
description: Review personalisation engine with stakeholders — profiles, greetings, shortcuts, and privacy
argument-hint: <project-folder>
---

# Agentic Commerce — Personalisation Review Command

## Purpose

Demo the personalisation engine to stakeholders, showing the self-segmentation modal, personalised greetings, dynamic shortcut pills, and the privacy-by-design approach (no PII in events). Capture approval or change requests before the UCP Server and Demo Orchestration features.

## Usage

```bash
/wire:ac_personalisation-review YYYYMMDD_project_name
```

## Prerequisites

- `personalisation.validate: pass` in status.md

## Workflow

### Step 1: Verify Prerequisites

1. Read `.wire/<project_id>/status.md`
2. Check `personalisation.validate == pass`

If not:
```
Warning: Personalisation has not passed validation.
Run `/wire:ac_personalisation-validate <project>` first.
Proceed anyway? (y/n)
```

### Step 2: Prepare for Demo

Before the session:
1. Read the validation report at `.wire/<project_id>/personalisation/validation_report.md`
2. Confirm privacy checks all passed — if any failed, do not proceed with the demo
3. Clear localStorage in the demo browser (so the modal appears naturally)
4. Optionally: pre-seed some event data using the demo visitor ID to demonstrate
   history-based shortcuts (search for 2-3 products before the session)

### Step 3: Present for Review

```
## Personalisation Review Session

**Project:** [PROJECT_NAME]
**Feature:** Personalisation Engine
**Validation Report:** .wire/[project_id]/personalisation/validation_report.md

### Privacy Confirmation

Before reviewing the feature, note:
- All event tracking uses anonymous visitor IDs (UUIDs), never email addresses
- The self-segmentation profile captures email for discount code delivery only
- The events table has been verified to contain no PII (confirmed in validation)

### What to Review

**Self-Segmentation Modal**
- [ ] The modal appears at an appropriate time (not immediately on load)
- [ ] The form steps feel natural and not intrusive
- [ ] The discount code incentive is compelling
- [ ] "No thanks" dismissal works cleanly
- [ ] Form fields collect the right information for your business

**Personalised Greetings**
- [ ] Greetings feel warm and personalised, not robotic
- [ ] When a recent search exists, the greeting references it naturally
- [ ] Without a profile, the default greeting is still welcoming

**Dynamic Shortcut Pills**
- [ ] Shortcuts are relevant to the user's history and preferences
- [ ] Seasonal shortcuts feel timely and appropriate
- [ ] The "Best sellers" fallback shortcut is always present
- [ ] Pills are limited to 4 — not overwhelming

**Event Tracking (Non-Visible)**
- [ ] Analytics don't noticeably slow down any user interactions
- [ ] The data collected would be genuinely useful for future personalisation
- [ ] Privacy approach (anonymous visitor IDs) is acceptable
```

### Step 4: Retrieve External Context (Optional)

1. Follow the meeting context retrieval workflow in `specs/utils/meeting_context.md`
   - Pass project folder and artifact `personalisation`
   - Surface any discussions about data collection, privacy requirements, or GDPR
2. Follow the Atlassian search workflow in `specs/utils/atlassian_search.md`
   - Search for any data privacy policies or customer experience requirements
   - Search for any prior discussions about personalisation goals

### Step 5: Demo Script

**Demo Scenario: First-Time Visitor → Returning Personalised Visitor**

1. **Show the cold-start experience**
   - Open the site in a fresh browser (no profile, no history)
   - Open the shopping assistant — show the default greeting and generic shortcuts
   - Narrate: "This is a new visitor — generic but still friendly"

2. **Self-segmentation modal**
   - Wait (or trigger manually) for the segmentation modal to appear
   - Complete the form with a demo persona:
     Name: "Sam", Email: "sam@demo.com"
     Style preferences: Performance, Technical
     Size: M, Waist: 32
   - Submit — show the discount code
   - Close the modal

3. **Immediately personalised**
   - Open the shopping assistant again
   - Show the personalised greeting: "Hey Sam, what are you in the mood for today?"
   - Show the style-based shortcuts (Performance gear, Technical kit)
   - Narrate: "Same session — already personalised from explicit preferences"

4. **Build up behavioural history**
   - Perform 2-3 searches in the semantic search bar (e.g. "summer jerseys")
   - View 2-3 product detail pages
   - Add 1 item to cart

5. **Return visit experience (simulate)**
   - Refresh the page
   - Open the shopping assistant again
   - Show the history-aware greeting: "Welcome back, Sam! Still looking for summer jerseys?"
   - Show the dynamic shortcut: `More like "summer jerseys"`
   - Narrate: "The system remembered Sam's behaviour and personalised the experience"

6. **Privacy demonstration (optional — for technically informed stakeholders)**
   - Open Supabase dashboard → Table editor → events table
   - Show that rows contain visitor_id (UUID), event_type, and payload
   - Confirm no email addresses or names visible in any row
   - Narrate: "No PII is stored in the events table — full GDPR compliance"

### Step 6: Gather Feedback

```
Please provide your feedback:

1. **Reviewer name and role:**

2. **Decision:**
   - [ ] Approved — proceed to next feature
   - [ ] Approved with minor notes — proceed, address notes during enablement
   - [ ] Changes requested — list below before proceeding
   - [ ] Needs discussion — data collection scope needs review

3. **Segmentation modal rating (1-5):**
   (1 = too intrusive, 5 = natural and compelling)

4. **Personalisation quality rating (1-5):**
   (1 = doesn't feel personal, 5 = feels genuinely relevant)

5. **Privacy approach rating (1-5):**
   (1 = insufficient, 5 = appropriate and well-designed)

6. **Specific feedback:**
   (Note any form field concerns, greeting wording issues, shortcut relevance,
   timing of modal appearance, or GDPR/privacy concerns)

7. **Data collection scope (if any concerns):**
   (Are we collecting too much? Too little? Any fields to add or remove?)
```

### Step 7: Record Outcome

**If approved:**
```yaml
personalisation:
  generate: complete
  validate: pass
  review: approved
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  modal_rating: [1-5]
  personalisation_rating: [1-5]
  privacy_rating: [1-5]
  review_notes: "[notes]"
```

**If changes requested:**
```yaml
personalisation:
  review: changes_requested
  reviewed_by: "Name, Role"
  review_date: YYYY-MM-DD
  review_notes: "Changes: [list]"
```

### Step 8: Sync to Jira (Optional)

Follow `specs/utils/jira_sync.md` — artifact: `personalisation`, action: `review`.

### Step 9: Suggest Next Steps

**If approved:**
```
## Personalisation Review: Approved ✓

### Suggested Next Features

- **UCP Server** (external agent API — final infrastructure feature):
  `/wire:ac_ucp_server-generate <project>`

- **Demo Orchestration** (showcase personalisation in automated demo):
  `/wire:ac_demo_orchestration-generate <project>`
```

**If changes requested:**
```
## Personalisation Review: Changes Requested

Changes needed:
[list from reviewer feedback]

**Common fixes:**
- Modal timing: adjust the 30-second delay in SelfSegmentationModal
- Greeting wording: update generateGreeting() in src/lib/personalisation.ts
- Shortcut relevance: update generateShortcuts() with more catalog-specific queries
- Form fields: add/remove fields in SelfSegmentationModal form

After changes: re-validate and re-review.
```

## Output

- Updated `.wire/<project_id>/status.md` with review outcome
- Optional Jira ticket status update

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

# Execution Log — Command and Skill Logging

## Purpose

After completing any generate, validate, or review workflow (or a project management command that changes state), append a single log entry to the project's execution log file. Skills also append an entry on activation, making the log a unified trace of all agent activity — both explicit commands and auto-activated skills.

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
- **Command**: Either the `/wire:*` command invoked, or `skill` for a skill activation entry
- **Result / Skill name**: For commands, the outcome; for skills, the skill identifier. Use one of:
  - `complete` — generate command finished successfully
  - `pass` — validate command passed all checks
  - `fail` — validate command found failures
  - `approved` — review command: stakeholder approved
  - `changes_requested` — review command: stakeholder requested changes
  - `created` — `/wire:new` created a new project
  - `archived` — `/wire:archive` archived a project
  - `removed` — `/wire:remove` deleted a project
  - `activated` — a skill was auto-activated (used with `skill` in the Command column)
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> |
```

Skill identifiers:

| Skill | Identifier |
|-------|-----------|
| Engagement Context | `engagement-context` |
| Research Persistence | `research-persistence` |
| dbt Development | `dbt-development` |
| LookML Content Authoring | `lookml-authoring` |
| dbt Analytics QA | `dbt-analytics-qa` |
| dbt Migration | `dbt-migration` |
| dbt Troubleshooting | `dbt-troubleshooting` |
| dbt Semantic Layer | `dbt-semantic-layer` |
| dbt Unit Testing | `dbt-unit-testing` |
| dbt DAG | `dbt-dag` |
| Dagster | `dagster` |
| Fivetran | `fivetran` |
| Project Review | `project-review` |
| Looker Dashboard Mockup | `looker-dashboard-mockup` |

This makes skill activations visible in the same log that captures command invocations, enabling full activity tracing across both explicit commands and automatic skill triggers.

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
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation |
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
