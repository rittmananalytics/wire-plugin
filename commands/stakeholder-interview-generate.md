---
description: Generate a stakeholder interview write-up with the mandatory four-tag template
argument-hint: <release-folder>
---

# Generate a stakeholder interview write-up with the mandatory four-tag template

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.5\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"stakeholder-interview-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.5\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate a stakeholder interview write-up with the mandatory four-tag template
argument-hint: "[release-folder] --stakeholder <slug>"
---

# Stakeholder Interview — Generate

Follow `specs/utils/discovery_analyst_delegate.md` before executing the workflow below.

## Purpose

Creates **one** stakeholder interview write-up for a specific stakeholder from the stakeholder map. This command is **repeatable per stakeholder** — call it once per interview, ideally within 24 hours of the call, while the conversation is fresh.

The write-up is the source-of-truth for what a stakeholder said and is the input to the consolidation step. Every theme bullet on the write-up carries the **mandatory four-tag set**: a domain tag, a type tag, a Hierarchy of Needs tier, and a PPT axis. Validation (`/wire:stakeholder-interview-validate`) enforces those four tags mechanically — they cannot be retrofitted from the consolidated matrix without losing diagnostic signal.

Models Phase 2 of the Canonical Discovery Playbook.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/stakeholder_map.md` (reviewed and approved)
- `--stakeholder <slug>` — the slug from the stakeholder map; uniquely identifies the row

**Helpful**:
- Fathom recording URL for this stakeholder's interview (highly recommended — generate fills from the transcript)
- Any documents the stakeholder shared (named dashboards, spreadsheets, decision trees)

## Workflow

### Step 1: Locate the release and stakeholder

1. Resolve `.wire/releases/$ARGUMENTS/`. Confirm `release_type: sop_discovery`.
2. Parse `--stakeholder <slug>` from arguments. If missing: ask the consultant for the slug, listing all P0/P1 slugs from the stakeholder map.
3. Read the stakeholder's row from `planning/stakeholder_map.md`. If the slug is not found in the map, stop — "Add this stakeholder to the map first via `/wire:stakeholder-map-generate`, or pick an existing slug from: [list]."
4. Compute the target write-up path: `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`. If it already exists, ask the consultant whether to **re-generate** (overwrite) or **append** new content.

### Step 2: Source the interview content

Ask:
```
Provide the Fathom recording URL for this interview (or paste the transcript directly, or type "no recording" to scaffold a blank template):
```

If a Fathom URL is provided, use the Fathom MCP server to pull the transcript and meeting summary. Extract:
- A verbatim quote that best captures what this person needs the sponsor to remember
- The role, day-to-day, painful things, decisions/workflows, KPIs lived by, existing assets, risks raised, scope notes

If a transcript is pasted, do the same extraction on the pasted content.

If "no recording", scaffold the template with empty sections — the consultant fills them in by hand.

### Step 3: Draft the write-up

**Output**: `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`

```markdown
---
slug: <slug>
stakeholder_name: "<Firstname Lastname>"
title: "<Title>"
department: "<Department>"
priority: <P0|P1|P2>
interview_date: <YYYY-MM-DD>
interviewer: "<RA name>"
fathom_url: <URL or null>
related_documents: []
---

# {{stakeholder_name}} — {{department}} Discovery

## Stakeholder quote (their words)

> "The single sentence or short paragraph that best captures what this person needs the sponsor to remember. Verbatim. Use the quote that would change a sponsor's mind if they read nothing else."

## Meeting summary

- Their role and how data fits into it
- The single most painful thing about today's analytics for them
- The decision or workflow they want to do better
- The KPIs or measures they live by
- Existing assets they rely on (named dashboards, sheets, sources)
- Risks or concerns they raised
- What they would flag as out-of-scope or low priority

## Themes

Every theme bullet below carries all four tags:

1. `#<domain>` — one of the in-scope domains (e.g. `#retail`, `#fulfillment`, `#finance`)
2. `#<type>` — one of: `#pain` | `#requirement` | `#kpi` | `#risk` | `#existing-asset`
3. `#<hierarchy>` — one of: `#collect` | `#clean` | `#define-track` | `#analyse` | `#optimise-predict`
4. `#<ppt>` — one of: `#people` | `#process` | `#technology`

Classification rules:
- Hierarchy tier: **the lowest tier whose absence is blocking it**. A predictive-modelling ask blocked by unreliable customer data is a `#clean` requirement until the foundations are fixed.
- PPT axis: **the axis whose absence is causing it**. Pick the binding constraint — refusing to choose is refusing to diagnose.

Examples:
- `#retail #pain #clean #process` — Store managers cannot trust footfall numbers because the SAP/EPOS reconciliation runs weekly and breaks silently
- `#retail #kpi #define-track #people` — UPT, ATV, Conversion definitions vary by region; no agreed business owner
- `#retail #existing-asset #analyse #technology` — Looker dashboard 520, currently the most-used dashboard for store conversion

### Theme list

- [theme bullet text] `#<domain> #<type> #<hierarchy> #<ppt>`
- [theme bullet text] `#<domain> #<type> #<hierarchy> #<ppt>`

## Follow-ups required

- [ ] Outstanding question, owner, due date

## Documentation referenced

- List of attached or linked source documents the stakeholder shared
```

When generating from a Fathom transcript, **propose** the four tags for each theme but explicitly mark uncertain classifications with a `?` suffix (e.g. `#process?`) so the consultant can confirm. Do not leave any tag missing.

### Step 4: Update status

In `status.md`, append (or update) the entry in `interviews:` for this slug:

```yaml
interviews:
  - slug: <slug>
    stakeholder_name: "<Firstname Lastname>"
    title: "<Title>"
    priority: <P0|P1|P2>
    interviewer: "<RA name>"
    interview_date: <YYYY-MM-DD>
    file: "planning/interviews/<slug>.md"
    fathom_url: <URL or null>
    generate: complete
    validate: not_started
    review: not_started
    themes_tagged: 0
```

Also update the aggregate `stakeholder_interview` artifact state to `generate: in_progress` if it was `not_started`. It becomes `complete` only when every P0 and P1 stakeholder from the map has a write-up.

### Step 5: Sync to document store

Follow `specs/utils/docstore_sync.md` — this creates the per-stakeholder Confluence/Notion page.

### Step 6: Output summary

Show: the file path, the count of theme bullets, the count of themes with uncertain tags (`?` suffix), and the next command:

```
/wire:stakeholder-interview-validate $ARGUMENTS --stakeholder <slug>
```

## Output Files

- `.wire/releases/$ARGUMENTS/planning/interviews/<slug>.md`
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
