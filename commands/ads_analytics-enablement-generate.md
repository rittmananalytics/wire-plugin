---
description: Generate user training and maintenance documentation
argument-hint: <release-folder>
---

# Generate user training and maintenance documentation

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.1\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ads_analytics-enablement-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.1\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Generate user training materials and handover documentation for the agentic data stack
argument-hint: <release-folder>
---

# Agentic Data Stack — Enablement Generate

## Purpose

Produce the user-facing documentation and data team handover materials for the agentic data stack. Users need to know what to ask, what the agent's limitations are, and how to interpret the provenance footer. The data team needs to know how to maintain the skill files as models evolve.

## Usage

```bash
/wire:ads_analytics-enablement-generate YYYYMMDD_client_agentic_data_stack
```

## Prerequisites

- `launch_gate.review: approved`

## Workflow

### Step 1: Generate User Guide

Write `.wire/<release-folder>/artifacts/agentic_data_stack_user_guide.md`:

```markdown
# [Client] Agentic Data Stack — User Guide

## What It Does

The agentic data stack answers business questions about your data platform in plain English. 
Ask it like you'd ask a data analyst.

## How to Ask Good Questions

**Be specific about time periods:**
- ✅ "Revenue last month" / "Revenue in Q1 2025"
- ❌ "Recent revenue" (ambiguous)

**Name the metric you want:**
- ✅ "Total revenue" / "Order count" / "Active customers"
- ❌ "How are we doing?" (too broad)

**Specify dimensions if you want a breakdown:**
- ✅ "Revenue by channel last quarter"
- ❌ "Revenue" (returns aggregate only)

## Understanding the Source Footer

Every answer includes:
```
Source tier: Semantic | Curated | Raw
Dataset: [table or metric name]
Freshness: [last updated timestamp]
Domain owner: [contact email]
```

**Semantic**: The answer comes from a defined business metric. Highest confidence.  
**Curated**: The answer comes from a governed dbt model. High confidence.  
**Raw**: The answer required ad-hoc SQL. Use with care — verify against a dashboard 
before including in external reports.

## What the Agent Can and Cannot Do

**Can do:**
- Answer questions about [list cleared domains]
- Break down metrics by standard dimensions (date, channel, region, category)
- Identify top-N or bottom-N rankings

**Cannot do (yet):**
- [List blocked domains] — launching in [second wave date]
- Multi-step attribution modelling
- Real-time data (data freshness is [X hours] behind live)
- Write to or modify any data

## When to Double-Check

Always verify against your canonical dashboard or with the domain owner before:
- Including a number in an external report or client presentation
- Making a significant budget or staffing decision
- The answer surprises you significantly
```

### Step 2: Generate Data Team Maintenance Guide

Write `.wire/<release-folder>/artifacts/agentic_data_stack_maintenance_guide.md`:

```markdown
# Agentic Data Stack — Maintenance Guide

## How the Agent Works

The agentic data stack uses three sources:
1. **Semantic layer** (dbt SL / LookML) — defined metrics
2. **DOMAIN_REFERENCE.md files** — per-domain knowledge, collocated with dbt models
3. **Canonical dbt models** — direct SQL fallback

## How to Keep It Accurate

### When you change a dbt model

If you modify a canonical mart model, update the collocated DOMAIN_REFERENCE.md:
- Check the "Key fields" table is still accurate
- Check the "Common Questions" examples still return correct results
- Check the "Known Limitations" section still applies

The CI check will warn if a model SQL changes without the reference file changing.

### When you add a new metric

After adding a metric to the semantic layer:
1. Add it to the relevant DOMAIN_REFERENCE.md "Semantic Layer Metrics" table
2. Add 1–2 example questions covering the new metric to the eval suite
3. Run `./eval/run_evals.sh <domain>` to confirm accuracy is maintained

### Monthly accuracy check

Run the full eval suite monthly:
```bash
cd <dbt_project_path> && ./.claude/eval/run_evals.sh all
```

If any domain drops below its target, investigate immediately — don't wait for users 
to report wrong answers.

## Key Contacts

| Domain | Owner | Contact |
|---|---|---|
| orders | Data Platform | data-platform@company.com |
| customers | Analytics Engineering | analytics@company.com |
```

### Step 3: Update Status

```yaml
enablement:
  generate: complete
  generated_date: YYYY-MM-DD
  user_guide: complete
  maintenance_guide: complete
```

## Output

- `.wire/<release-folder>/artifacts/agentic_data_stack_user_guide.md`
- `.wire/<release-folder>/artifacts/agentic_data_stack_maintenance_guide.md`
- Updated `status.md`

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
