---
description: Validate engagement brief completeness
argument-hint: <release-folder>
---

# Validate engagement brief completeness

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.7.5\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"engagement-brief-validate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.7.5\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Validate the engagement brief for completeness before kick-off
---

# Engagement Brief — Validate

## Purpose

Checks that the engagement brief is complete enough to walk into the discovery kick-off with. The brief is internal-RA, so validation is structural and specificity-focused rather than stakeholder-facing.

## Inputs

**Required**:
- `.wire/releases/$ARGUMENTS/planning/engagement_brief.md`

## Workflow

### Step 1: Locate the brief

Resolve release folder from `$ARGUMENTS`. Read `planning/engagement_brief.md`. If not found: "Engagement brief not found. Run `/wire:engagement-brief-generate $ARGUMENTS` first."

### Step 2: Run checks

Collect PASS / WARNING / FAIL for each.

#### Field completeness
- [ ] Client field populated (full legal name)
- [ ] SoW reference present
- [ ] Sponsor name and email present (not "TBD")
- [ ] Lead Consultant named
- [ ] Problem statement is exactly one sentence and uses the client's framing (not RA boilerplate)
- [ ] Desired outcome is exactly one sentence and is business-outcome framed (not deliverable framed)
- [ ] In-scope domains: at least one bullet
- [ ] Out-of-scope: at least one bullet (this is the most-skipped row; flag if empty)
- [ ] Success metrics: at least one measurable metric (a number, a count, or a named KPI)
- [ ] Known constraints: at least one specific constraint
- [ ] Known risks: at least one risk named
- [ ] Target dates: at least kick-off and playback dates set; Release 1 start can be `TBD`

#### Quality checks
- [ ] **Problem vs deliverable**: the problem statement does not describe a tool or deliverable (e.g. "we need Looker") — it describes a business problem
- [ ] **Outcome specificity**: the desired outcome contains either a measurable change ("reduce X by Y") or a named user behaviour change ("store managers can answer X without calling head office")
- [ ] **Out-of-scope is real**: the out-of-scope items are things that genuinely look in-scope. "World peace" doesn't count.
- [ ] **Sponsor has a personal success line**: the Sponsor field includes what success looks like for them personally, not just their title

#### Pre-discovery checklist
- [ ] SoW marked as read
- [ ] HubSpot deal record marked as reviewed (or a note explaining why not)
- [ ] Stakeholder map noted as drafted (link or status `not_started` flag)

### Step 3: Produce report

**Output**: `.wire/releases/$ARGUMENTS/planning/engagement_brief_validation.md`

```markdown
# Engagement Brief Validation Report

**Release**: $ARGUMENTS
**Date**: {{TODAY}}
**File**: planning/engagement_brief.md

## Result: PASS / FAIL / PASS WITH WARNINGS

## Checks

| Check | Result | Note |
|---|---|---|
| Client | ✅ | |
| Sponsor present + personal success | ⚠️ | No personal success line — ask sponsor at kick-off |
| Problem statement is 1 sentence in client's words | ✅ | |
| Desired outcome is business-outcome framed | ❌ | "Build a Looker dashboard" — rewrite as a behaviour change |
| Out-of-scope present | ❌ | Empty — fill before kick-off; this is the most common cause of scope creep |
| Success metrics measurable | ⚠️ | |
| Constraints specific | ✅ | |
| Risks named | ✅ | |
| Target dates set | ✅ | |
| Pre-discovery checklist progress | ⚠️ | HubSpot deal record not yet reviewed |

## Issues to Resolve

### FAIL: Out-of-scope empty
The out-of-scope section is empty. The playbook's failure-mode table specifically calls this out as the most common cause of overrun. List at least three items that look in-scope but are not — sponsor will confirm at kick-off.

### FAIL: Desired outcome describes a deliverable
"Build a Looker dashboard" is a deliverable, not an outcome. Rewrite as a behaviour change or measurable improvement (e.g. "Store managers answer the same five conversion questions without calling head office").

## Next Steps

[If PASS or PASS WITH WARNINGS]:
1. Resolve any warnings before kick-off
2. Internal RA review (Head of Delivery sign-off): /wire:engagement-brief-review $ARGUMENTS
3. Then draft the stakeholder map: /wire:stakeholder-map-generate $ARGUMENTS

[If FAIL]:
1. Fix the issues listed
2. Re-run validation: /wire:engagement-brief-validate $ARGUMENTS
```

### Step 4: Update status

```yaml
artifacts:
  engagement_brief:
    validate: complete   # or "failed" if FAIL
```

### Step 5: Output summary

Show the result and the top issue (if any).

## Output Files

- `.wire/releases/$ARGUMENTS/planning/engagement_brief_validation.md`
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
