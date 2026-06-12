---
description: Generate engagement brief from SoW and deal context
argument-hint: <release-folder>
---

# Generate engagement brief from SoW and deal context

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.8.4\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"engagement-brief-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.8.4\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate the engagement brief for a SOP discovery release
---

# Engagement Brief — Generate

## Purpose

Drafts the internal RA Engagement Brief at the start of a SOP discovery release. The brief is a two-page internal document that captures the commercial and scope context the consultant must walk into the kick-off already knowing. It is not a sponsor deliverable — it exists so that pre-discovery work is grounded in what the deal record and SoW already say, before any of the sponsor's time is spent.

Models Phase 0 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- Release folder: `.wire/releases/$ARGUMENTS/` with `release_type: sop_discovery` in `status.md`

**Helpful (read if present)**:
- `engagement/context.md` — engagement overview created by `/wire:new`
- `engagement/sow.md` (or `sow.pdf`, or any file under `engagement/references/`)
- `engagement/calls/` — Fathom transcripts from the sales process (preceding kick-off)
- HubSpot deal record — if the Atlassian/HubSpot MCP is available, fetch the deal owner's notes

## Workflow

### Step 1: Locate the release

1. Resolve `.wire/releases/$ARGUMENTS/`. Confirm `status.md` has `release_type: sop_discovery`. If not, stop — "This command only applies to SOP discovery releases."
2. If the brief already exists at `planning/engagement_brief.md`, ask whether to **re-generate** (overwrite) or **update** (preserve existing fields and only fill gaps).

### Step 2: Gather source material

Read in order, summarising what each contributes to the brief:

1. `engagement/sow.md` — in-scope domains, contractual deliverables, named success metrics, named stakeholders, target go-live, explicit out-of-scope statements
2. `engagement/context.md` — anything captured by `/wire:new`
3. `engagement/calls/` — meeting notes and Fathom transcripts from the sales process. Look for: stated problems, expressed desired outcomes, named stakeholders, sensitivities
4. HubSpot deal record (if MCP available) — `mcp__claude_ai_HubSpot__get_crm_objects` for the deal; pull meeting notes and engagement objectives
5. Any files in `engagement/references/` (annual reports, investor decks, careers page snapshots)

If sources are thin, ask the engagement lead the missing questions directly — one at a time.

### Step 3: Draft the engagement brief

**Output location**: `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`

Template:

```markdown
# Engagement Brief: {{ENGAGEMENT_NAME}}

**Status**: Draft (internal RA)
**Release**: {{RELEASE_ID}}_{{RELEASE_NAME}}
**Date**: {{TODAY}}

| Field | Content |
|---|---|
| **Client** | Full legal name (and trading name if different) |
| **Engagement** | SoW reference, signature date, contract value, payment terms |
| **Sponsor** | Name, title, email, what success looks like for them personally |
| **Lead Consultant** | RA owner |
| **RA Team** | Named consultants and % allocation |
| **Problem statement (1 sentence)** | What is broken today that the client is paying us to fix — in their words |
| **Desired outcome (1 sentence)** | What "done" looks like in business terms, not deliverable terms |
| **In-scope domains** | Bullet list. Be precise. |
| **Out-of-scope (explicit)** | Bullet list of things that look in-scope but are not |
| **Success metrics** | KPI definitions, dashboard count, model count, user count, target adoption rate |
| **Known constraints** | Tech stack lock-in, regulatory, regional, security, existing contracts, budget caps |
| **Known risks** | Sponsor turnover, internal politics, data access blockers, parallel programmes |
| **Commercial structure** | Direct / PSF-funded / mixed. Invoicing schedule. |
| **Target dates** | Kick-off, playback, Release 1 start, Release 1 go-live |

## Pre-discovery checklist progress

- [ ] SoW read in full
- [ ] HubSpot deal record reviewed (sales-process meeting notes and Fathom recordings)
- [ ] Slack `#sales` and any client channel scanned
- [ ] Client public materials reviewed (annual report, careers page, conference talks)
- [ ] Confluence space (or Discovery folder) set up
- [ ] Google Drive folder set up following the standard structure
- [ ] Findings Playback deck template copied to engagement Drive
- [ ] Stakeholder Map drafted with gaps identified (see `/wire:stakeholder-map-generate`)
- [ ] Sponsor confirmation requested: discovery scope, stakeholders, time commitment, target playback date

## Notes
[Anything that didn't fit a row above — historical context, surprises from the sales record, etc.]
```

### Step 4: Update status

```yaml
artifacts:
  engagement_brief:
    generate: complete
    file: planning/engagement_brief.md
    generated_date: {{TODAY}}
```

### Step 5: Sync to document store (if configured)

Follow `specs/utils/docstore_sync.md` to mirror the brief to Confluence or Notion.

### Step 6: Output summary

Print: artifact location, top three gaps the consultant needs to chase (typically: target playback date, sponsor confirmation of stakeholders, budget/timeline specificity), and the next command:

```
/wire:engagement-brief-validate $ARGUMENTS
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`
- Updated `.wire/releases/$ARGUMENTS/status.md`

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
