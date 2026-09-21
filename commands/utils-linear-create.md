---
description: Create Linear Project and issues for a project
argument-hint: <project-folder>
---

# Create Linear Project and issues for a project

## User Input

```text
$ARGUMENTS
```

## Path Configuration

- **Projects**: `.wire` (project data and status files)

When following the workflow specification below, resolve paths as follows:
- `.wire/` in specs refers to the `.wire/` directory in the current repository
- `TEMPLATES/` references refer to the templates section embedded at the end of this command
- `specs/<path>.md` references are shared workflow docs shipped with this plugin — read them from `${CLAUDE_PLUGIN_ROOT}/specs/<path>.md`. If the path matches a Wire command (e.g. `specs/requirements/generate.md`), it means that command (`/wire:requirements-generate`) and its spec is already embedded in the command file.

## Tracing (opt-in, off by default)

---
description: Internal utility — opt-in step-level execution tracing to .wire/releases/<release>/trace.jsonl when WIRE_TRACE=true
---

# Tracing — Detailed, Opt-In, Step-Level Execution Trace

## Purpose

`execution_log.md` records one terse row per whole command (timestamp, command, result, a detail string capped at 120 characters). That's enough for a normal audit trail, but it can't answer "what actually happened inside that command, step by step" — which specific files it read, what it inferred, what it proposed, what a consultant decided, why. Tracing exists for engagements that want that depth: a complete, structured, append-only record of every step of every command, scoped to the release and release type it ran under.

**Off by default.** Tracing never runs unless `WIRE_TRACE=true` is set in the shell environment. If it isn't, skip this entire section — do nothing, check nothing further, proceed straight to the Workflow Specification exactly as if this section didn't exist. This is the common case and must add zero overhead.

## Where it writes

`.wire/releases/<release_folder>/trace.jsonl` — one JSON object per line (JSON Lines), append-only, alongside that release's `status.md` and `execution_log.md`.

For commands not scoped to a specific release (cross-cutting utilities with `release_types: []` in their own front-matter, or any command whose argument isn't a release folder), write to `.wire/trace.jsonl` at the engagement level instead, with `release` and `release_type` fields set to `null`.

This file is **local only** — nothing in it is ever sent anywhere, unlike the anonymous Segment telemetry event described elsewhere. It stays on the consultant's machine, inside the engagement's own repo, exactly like `execution_log.md`.

## What to log, and when

If `WIRE_TRACE=true`:

1. **Resolve context once, before anything else**: the release folder (from this command's own argument, if it has one) and `release_type` (read `.wire/releases/<release_folder>/status.md`'s `project_type` or `release_type` field). If this command has no release-folder argument, both are `null`.
2. **Emit a `command_start` event** before beginning the Workflow Specification below.
3. **As you work through the Workflow Specification's own numbered steps, emit a `step` event after completing each one** — and where a step itself has meaningfully distinct numbered sub-parts (e.g. "check location A, then location B, then infer a match, then propose it"), treat each of those as its own step event too rather than collapsing them into one. The `detail` field has no length limit and is not a summary — write what actually happened: values found, files read, decisions made and why, what was proposed and what the consultant chose. If this step involved the data model registry or any other external/optional resource, log it explicitly: whether it was reached, what was searched, what matched (or didn't, and why not), and whether/how the result was used downstream.
4. **Emit a `command_end` event** when the workflow finishes, with the same `result` value this command would write to `execution_log.md` (`complete`, `pass`, `fail`, `approved`, etc.).

## How to emit an event

Use this pattern for every event (adjust the heredoc body and the Python literals per call — this is a template, not a fixed script):

```bash
[ "${WIRE_TRACE:-false}" = "true" ] && {
  mkdir -p ".wire/releases/<release_folder>" 2>/dev/null
  cat > "/tmp/wire_trace_detail_$$.txt" << 'WIRE_TRACE_DETAIL_EOF'
<the full, untruncated detail text for this event — safe to include quotes,
newlines, code snippets, anything; this heredoc is not shell-interpreted>
WIRE_TRACE_DETAIL_EOF
  python3 -c "
import json, datetime
detail = open('/tmp/wire_trace_detail_$$.txt').read().rstrip('\n')
event = {
    'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    'release': '<release_folder_or_null>',
    'release_type': '<release_type_or_null>',
    'command': 'utils-linear-create',
    'event': '<command_start|step|command_end>',
    'step': '<step_number_or_null>',
    'step_name': '<step_heading_or_null>',
    'result': '<result_value_or_null>',
    'detail': detail,
}
with open('.wire/releases/<release_folder>/trace.jsonl', 'a') as f:
    f.write(json.dumps(event) + chr(10))
"
  rm -f "/tmp/wire_trace_detail_$$.txt"
}
```

- `<release_folder_or_null>` / `<release_type_or_null>`: from Step 1 above; write the literal JSON `null` (no quotes) if either doesn't apply, or a quoted string if it does.
- `event`: `command_start`, `step`, or `command_end`.
- `step` / `step_name`: `null` for `command_start`/`command_end`; the step's own number (e.g. `"1.5"`) and heading (e.g. `"Check for a Canonical Vertical Match"`) for a `step` event.
- `result`: `null` except on `command_end`.
- Adjust the file path in the final `open(...)` call to `.wire/trace.jsonl` for engagement-level (non-release-scoped) commands.

## Rules

1. **Never block or fail the workflow.** If a trace write fails for any reason (disk full, permissions), continue the workflow regardless — trace failures are never surfaced to the user and never stop anything.
2. **Append only** — never rewrite or delete existing lines in `trace.jsonl`.
3. **This is additive to `execution_log.md` and Telemetry, not a replacement for either.** All three continue exactly as documented elsewhere; tracing is a separate, optional, much finer-grained record for engagements that opt in.
4. **Don't summarize into brevity.** The entire point of this mechanism over `execution_log.md` is that it isn't limited to a 120-character line — write the real detail.

## Example

```json
{"ts":"2026-07-05T14:20:03Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_start","step":null,"step_name":null,"result":null,"detail":"Invoked for release 20260705_acme (full_platform)"}
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found — not the Wire source repo). Checked ~/.wire/data-model-registry/ (found — cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce — entity shape (subscriber, subscription, subscription_event, monthly_retention, subscription_revenue) proposed as a structural analogue for Acme's MRR/NRR model."}
{"ts":"2026-07-05T14:20:34Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.3","step_name":"Check cross-vertical patterns","result":null,"detail":"crm_identity_resolution flagged as relevant — requirements FR-12 describes reconciling Salesforce and HubSpot contact records, a 12% mismatch rate noted in discovery. Proposed alongside the subscription-commerce adjacent match."}
{"ts":"2026-07-05T14:21:02Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.4","step_name":"Propose and record decision","result":null,"detail":"Presented both proposals. Consultant chose 'adapt' on subscription-commerce (kept subscriber/subscription/subscription_revenue, dropped monthly_retention as out of scope for this phase, renamed subscription_event to billing_event to match client terminology) and 'yes' on crm_identity_resolution as-is. Recorded data_model_registry.vertical: subscription-commerce and cross_vertical_schemas: [crm_identity_resolution] in .wire/engagement/context.md."}
{"ts":"2026-07-05T14:34:47Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"5","step_name":"Carry reference pointers forward","result":null,"detail":"account_dim mapped to subscription-commerce's subscriber entity — generation_constraints and reference_implementation pointer carried into data_model_specification.md. subscription_fct mapped to subscription entity, same treatment. contact_identity_map (new, from crm_identity_resolution) added as its own integration model with that pattern's reference_implementation pointer."}
{"ts":"2026-07-05T14:41:15Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"command_end","step":null,"step_name":null,"result":"complete","detail":"Generated data_model_specification.md — 14 models (5 staging, 4 integration, 5 warehouse), including 2 informed by the accepted registry proposals above."}
```

## Workflow Specification

---
wire_schema: "1.0"
command: utility
artifact: utils
domain: utils
release_types: []
action_type: utility
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Create or link Linear issues for a data platform project
argument-hint: <project-folder>

---

# Linear Issue Creation and Linking Utility

## Purpose

Set up Linear tracking for a data platform project. Supports two modes:

- **Create mode**: Create a new Linear issue hierarchy (Project → Issues → Sub-issues) from scratch
- **Link mode**: Search an existing Linear team for issues that match framework artifacts and link to them

Can be used in three ways:
- **During project creation**: Called automatically from `/wire:new` (Step 9.5) when the user opts in to Linear tracking
- **Mid-project enablement**: Run standalone on an existing project to retroactively add Linear tracking
- **Linking to existing boards**: When a Linear team already has issues, search and link to the most appropriate existing ones

## Usage

```bash
/wire:utils-linear-create YYYYMMDD_project_name
```

When invoked standalone (not from `/wire:new`), prompt the user for the Linear team key and the desired mode (create or link).

## Prerequisites

- Linear MCP server must be configured (`https://mcp.linear.app/sse`)
- Linear team identifier must be provided (e.g., `ENG`, `DATA`, `ACME`)
- Project must exist with a valid `status.md`

## Linear Data Model

Wire Framework maps to Linear as follows:

| Wire concept | Linear equivalent |
|---|---|
| Engagement / project | Linear **Project** (within a Team) |
| Artifact (e.g. requirements) | Linear **Issue** (child of Project) |
| Lifecycle step (generate/validate/review) | Linear **Sub-issue** (child of artifact Issue) |
| Sprint | Linear **Cycle** |

Linear uses parent–child relationships rather than Epic/Task/Sub-task issue types.

## Workflow

### Step 1: Read Project Context

**Process**:
1. Read the project's `status.md`
2. Extract from YAML frontmatter:
   - `project_name`
   - `client_name`
   - `project_type`
   - `artifacts` section (to determine in-scope artifacts)
3. Accept `linear_team_id` from the calling context (provided by user during `/wire:new`), or if running standalone, ask the user:
   ```
   What is the Linear team identifier? (e.g., ENG, DATA, ACME)
   ```

### Step 1.5: Determine Workflow Mode

Three modes are supported:

| `linear_mode` | Meaning |
|---|---|
| `"create"` | Create a new Linear project, then create all issues and sub-issues inside it |
| `"create_in_existing"` | Use an existing Linear project (provided by URL/ID), but create fresh issues and sub-issues inside it |
| `"link"` | Use an existing Linear project and link to pre-existing issues within it |

**If invoked from `/wire:new` with `linear_mode: "link"`**:
- Proceed to **Step 2A** (Search for Existing Issues)

**If invoked from `/wire:new` with `linear_mode: "create_in_existing"`**:
- Proceed to **Step 2** (Resolve Linear Project) — the `create_in_existing` path verifies the supplied `linear_project_id` and sets `resolved_project_id`.

**If invoked from `/wire:new` with `linear_mode: "create"` (or no mode specified)**:
- Proceed to **Step 2** (Create Linear Project)

**If invoked standalone** (not from `/wire:new`):
Ask the user:
```
How would you like to set up Linear tracking?
1. Create new project + new issues — Create a new project, issues, and sub-issues from scratch
2. Use existing project + create new issues — Paste an existing project URL or ID; Wire will create fresh issues inside it
3. Link to existing project + existing issues — Search for and link to issues that already exist in this Linear team
```

---

## Workflow Path A: Create New Issues

### Step 2: Resolve Linear Project

The goal of this step is to populate `resolved_project_id` and `resolved_project_url` — the canonical project reference used by all subsequent steps.

**When `linear_mode` is `"create"`**:

Optionally offer to customise the name:
```
Project name (press Enter to accept default: "[client_name] — [project_name]"):
```

Create the project:
```
save_project:
  name: "[confirmed_project_name]"
  addTeams: ["[linear_team_id]"]
  description: |
    Data platform project for [client_name].
    Project type: [project_type]
    Created: [date]
    Local tracking: .wire/releases/[folder_name]/status.md
  state: "started"
```

Store the returned `id` as `resolved_project_id` and the project URL as `resolved_project_url`.

**When `linear_mode` is `"create_in_existing"` or `"link"`**:

The user has already provided a `linear_project_id` (URL or raw ID). Verify it:
```
list_projects:
  team: "[linear_team_id]"
  query: "[linear_project_id]"
```

If the project is found: store the matching project's `id` as `resolved_project_id` and its URL as `resolved_project_url`.

If not found or inaccessible:
```
Error: Linear project "[linear_project_id]" could not be found or is not accessible.
Please check the project ID/URL and your permissions, then re-run:
/wire:utils-linear-create [folder]
```
Exit — do not proceed without a valid project.

### Step 3: Create Issues for Each In-Scope Artifact

For each artifact where the state is NOT `not_applicable`, create a top-level Issue under the project. Use `resolved_project_id` from Step 2 for all issue creation calls.

**Artifact display names:**

| Artifact | Issue Title | Description |
|---|---|---|
| requirements | Requirements Specification | Extract and validate requirements from SOW |
| workshops | Workshops | Discovery and clarification workshops |
| conceptual_model | Conceptual Model | Entity model and business object relationships |
| pipeline_design | Pipeline Design | Data pipeline architecture and data flow |
| data_model | Data Model Design | dbt model structure (staging/integration/warehouse) |
| mockups | Dashboard Mockups | Dashboard wireframes and UX mockups |
| pipeline | Data Pipeline | Pipeline implementation code |
| dbt | dbt Models | dbt model SQL and configuration |
| semantic_layer | Semantic Layer | LookML views, explores, and measures |
| dashboards | Dashboards | Dashboard implementation |
| data_quality | Data Quality Tests | Data quality validation and testing |
| uat | User Acceptance Testing | UAT plan and execution |
| deployment | Deployment | Production deployment artifacts |
| training | Training Materials | Training sessions and materials |
| documentation | Documentation | Technical and user documentation |

For each in-scope artifact:

```
save_issue:
  team: "[linear_team_id]"
  project: "[resolved_project_id]"
  title: "[Artifact Display Name]: [project_name]"
  description: "[Description from table above]"
```

Record each returned `id` as the artifact's `issue_id` and `identifier` as `issue_identifier` (e.g., `ENG-42`).

### Step 4: Create Sub-issues for Lifecycle Steps

For each artifact Issue, create Sub-issues for the applicable lifecycle steps.

**Lifecycle steps per artifact** (same as Jira — see `jira_create.md` for the full table):
- Most artifacts have: generate, validate, review
- `workshops`, `mockups`, `uat` have: generate, review (no validate)

For each applicable step:

**IMPORTANT: Sub-issues must only have `parentId` — never `project`, never `team`. Passing `project` causes Linear to surface the issue as a standalone project issue rather than a sub-issue. The parent relationship is established solely through `parentId`; team and project are inherited automatically.**

```
save_issue:
  parentId: "[artifact_issue_id]"
  title: "[Step]: [Artifact Display Name]"
  description: "[Step] the [artifact] for [project_name]"
```

Where `[Step]` is `Generate`, `Validate`, or `Review`.

Record each returned `id` as `[step]_id` and `identifier` as `[step]_identifier`.

### Step 4.5: Assign to Cycle (optional)

If the Linear team uses Cycles (equivalent to sprints):

```
linear_getCycles:
  teamId: "[linear_team_id]"
```

If an active Cycle exists, assign all artifact Issues to it:

```
save_issue:
  id: "[artifact_issue_id]"
  cycle: "[active_cycle_id]"
```

If no active Cycle exists, note this to the user — issues will appear in the backlog.

---

## Workflow Path B: Link to Existing Issues

### Step 2A: Search for Existing Issues

Search the Linear team for issues that could map to framework artifacts:

```
list_issues:
  team: "[linear_team_id]"
  filter:
    state: { type: { nin: ["completed", "cancelled"] } }
```

Also search for existing Projects:

```
list_projects:
  team: "[linear_team_id]"
```

### Step 2B: Match Issues to Framework Artifacts

For each in-scope artifact, score existing issues using the same algorithm as `jira_create.md` (keyword matching, display name matching, project/client name matching). Minimum threshold: 5 points.

**Artifact keyword mapping** (same as Jira):

| Artifact | Display Name | Match Keywords |
|---|---|---|
| requirements | Requirements Specification | "requirements", "scope", "SOW" |
| workshops | Workshops | "workshop", "discovery", "kickoff" |
| conceptual_model | Conceptual Model | "entities", "conceptual", "ERD" |
| pipeline_design | Pipeline Design | "pipeline", "architecture", "data flow" |
| data_model | Data Model Design | "dbt", "staging", "warehouse", "data model" |
| mockups | Dashboard Mockups | "mockup", "wireframe", "dashboard design" |
| pipeline | Data Pipeline | "pipeline", "extraction", "ingestion" |
| dbt | dbt Models | "dbt", "models", "transformations" |
| semantic_layer | Semantic Layer | "LookML", "semantic", "metrics", "measures" |
| dashboards | Dashboards | "dashboard", "report", "visualization" |
| data_quality | Data Quality Tests | "data quality", "testing", "dbt test" |
| uat | User Acceptance Testing | "UAT", "user acceptance", "sign-off" |
| deployment | Deployment | "deployment", "go-live", "production" |
| training | Training Materials | "training", "enablement", "onboarding" |
| documentation | Documentation | "documentation", "runbook", "handover" |

**Project matching**: If a Linear Project's name contains the client name or project name, match it as the engagement Project. Present multiple candidates to the user if ambiguous.

**Sub-issue matching**: For each matched Issue, retrieve its children:

```
list_issues:
  filter:
    parent: { id: { eq: "[issue_id]" } }
```

Match Sub-issues to lifecycle steps by keyword in the title:
- **generate**: "Generate", "Create", "Build", "Develop", "Write"
- **validate**: "Validate", "Test", "Check", "Verify", "QA"
- **review**: "Review", "Approve", "Sign-off", "Accept"

### Step 2C: Present Matches for User Confirmation

Display the proposed mapping, then ask:
```
1. Accept all matches — Link matched issues, create new for anything unmatched
2. Accept matches only — Link matched, skip unmatched (no new issues)
3. Let me adjust — Walk through each artifact manually
4. Cancel
```

### Step 2D: Execute Linking

Same logic as `jira_create.md` Step 2D: create new issues for unmatched artifacts, link matched, handle partial matches.

### Step 2E: Add Linking Comments

For each linked Issue, add a comment:

```
save_comment:
  issueId: "[issue_id]"
  body: |
    Linked to Wire Framework project: [project_name]
    Client: [client_name] | Type: [project_type]
    Local tracking: .wire/releases/[folder_name]/status.md

    This issue is now tracked by the Wire Framework.
    Status updates will be synced automatically.
```

---

## Common Steps (Both Paths)

### Step 5: Update status.md with Linear Keys

Update the project's `status.md` YAML frontmatter with all created/linked issue identifiers:

```yaml
linear:
  team_id: "ENG"
  project_id: "[resolved_project_id]"
  project_url: "[resolved_project_url]"
  artifacts:
    requirements:
      issue_id: "ISSUE_UUID"
      issue_identifier: "ENG-42"
      generate_id: "SUBISSUE_UUID"
      generate_identifier: "ENG-43"
      validate_id: "SUBISSUE_UUID"
      validate_identifier: "ENG-44"
      review_id: "SUBISSUE_UUID"
      review_identifier: "ENG-45"
    data_model:
      issue_id: "ISSUE_UUID"
      issue_identifier: "ENG-50"
      # ...
```

For out-of-scope artifacts, omit them from the `linear.artifacts` section entirely.

### Step 5.5: Sync Existing Progress (Mid-Project Only)

If this utility is running on a project that already has progress, call `specs/utils/linear_status_sync.md` to transition all Sub-issues to match the current local artifact states.

### Step 6: Report Results

```markdown
## Linear Issues Created

**Project**: [client_name] — [project_name]
**URL**: [project_url]
**Issues**: [count] artifact issues
**Sub-issues**: [count] lifecycle step sub-issues

### Issue Hierarchy

| Artifact | Issue | Generate | Validate | Review |
|---|---|---|---|---|
| Requirements | ENG-42 | ENG-43 | ENG-44 | ENG-45 |
| Data Model | ENG-50 | ENG-51 | ENG-52 | ENG-53 |
| ... | ... | ... | ... | ... |

All issue identifiers have been recorded in status.md.
```

### Step 7: Handle Edge Cases

**Linear MCP not available:**
```
Note: Could not connect to Linear (Linear MCP server not configured).
Skipping Linear issue creation. You can create issues later by running:
/wire:utils-linear-create [folder]
```

**Linear already configured:**
If `status.md` already has a `linear.project_id`:
```
Linear tracking is already configured for this project.

Project: [project_name] ([project_url])

Do you want to:
1. Keep existing Linear tracking (no changes)
2. Replace with new Linear issues (create from scratch)
3. Re-link to different existing issues (search again)
```

In all cases, project creation continues — Linear tracking is optional and additive.

## Output

This utility:
- **Create mode**: Creates a Linear Project + Issues + Sub-issues for the engagement
- **Link mode**: Searches existing Linear issues, matches to framework artifacts, links to them (creating only what's missing)
- Updates `status.md` with all issue identifiers (same structure regardless of mode)
- If run mid-project, syncs existing artifact progress to linked/created issues
- Fails gracefully if Linear is unavailable

Execute the complete workflow as specified above.

## Execution Logging

After completing the workflow, append a log entry to the project's execution_log.md:

---
description: Internal utility — appends a log entry to the project's execution log after any generate/validate/review workflow or skill activation
---

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

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
```

Then append one row per execution:

```markdown
| YYYY-MM-DD HH:MM | /wire:<command> | <result> | <detail> | <by> | <session> | <duration> | n/a | n/a |
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
  - `override` — `specs/utils/precondition_gate.md` recorded a consultant overriding an unmet precondition, or an advisory gate satisfied by a director's ruling
  - `mode` — the director handed control over or took it back ("you drive" / "I'll drive"), per `specs/utils/director_operating_model.md`
- **Detail**: A concise one-line summary of what happened. Include:
  - For generate: number of files created or key output filename
  - For validate: number of checks passed/failed
  - For review: reviewer name and brief feedback if changes requested
  - For new: project type and client name
  - For archive/remove: project name
  - For skill activations: brief description of what triggered the skill
  - For override: the unmet precondition, who overrode it, and their reason
  - For a ruling-satisfied advisory gate: the precondition and the ruling id
- **By**: the git user (`git config user.name`), or `unknown` if git has no
  user configured. Who the run is attributable to, regardless of what typed it.
- **Session**: what invoked the run. One of:
  - `typed` — a person typed the command
  - `orchestrator` — the orchestrating session dispatched it, followed by its
    session id in brackets where one is available: `orchestrator [a1b2c3]`
  - a lane label — the lane that ran it, e.g. `dbt-developer [staging 1/2]`
  - `autopilot` — `/wire:autopilot` ran it

  This is the same value the `invoked_by` telemetry property carries
  (`specs/utils/telemetry.md`), read from `WIRE_INVOKED_BY` and defaulting to
  `typed`. The log records it per row so the record on disk answers the same
  question telemetry answers in aggregate.
- **Duration**: Wall-clock time the workflow took. As the first action of the
  workflow, run `date +%s` and note the value as the start time. When
  appending the log row, run `date +%s` again and format the difference as
  `42s`, `4m 12s`, or `1h 03m`. If the start time was not captured, write
  `n/a`. Skill activation entries write `n/a`.
- **Tokens**: Total model tokens the run consumed (input + output, including
  cache reads and writes). Write the literal `n/a` — a model cannot measure
  its own token usage, and an estimated figure must never be written. On
  Claude Code, the Wire plugin's metrics hook backfills this cell with the
  measured value from the session transcript after the turn ends (see
  Metrics Backfill below). On runtimes without the hook (e.g. Gemini CLI)
  the cell stays `n/a`.
- **Cost (USD)**: Estimated cost of the measured tokens, e.g. `$0.42`. Same
  rule as Tokens: write `n/a`; the metrics hook backfills it where token
  usage can be measured. Never compute or guess this yourself.

## Skill Activation Entries

When a skill activates, it appends a row in the same format as commands, using `skill` in the Command column and the skill identifier in the Result column, with `n/a` in all three metric columns:

```markdown
| YYYY-MM-DD HH:MM | skill | <skill-identifier> | activated | <brief trigger description> | <by> | <session> | n/a | n/a | n/a |
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

## Stale Status Check

Immediately after appending a **command** row (this does not apply to skill activation entries), perform a quick freshness check against the project's `status.md`. This is additive to the logging behavior above — it never blocks the calling command and never modifies `status.md`.

**Process**:
1. Derive `artifact_id` from the command just logged: strip the `/wire:` prefix and the trailing `-generate`, `-validate`, or `-review` suffix (e.g. `/wire:migration-inventory-generate` → `migration_inventory`). If the command doesn't map to a recognizable artifact (e.g. `/wire:new`, `/wire:status`, `/wire:archive`), skip this check entirely.
2. Read the artifact's own block in `status.md`: `artifacts.<artifact_id>`.
3. Check whether that artifact has already passed its review/approval gate — its `review` field (or equivalent approval field) shows `pass`, `approved`, or `complete`.
4. If the gate has passed, scan every field in the `artifacts.<artifact_id>` block for a value that is still the literal string `TBD`, or an empty list (`[]`) / `null` where the artifact's own template expects a populated value (i.e. the field is not legitimately optional).
5. For each stale field found, emit a one-line warning in the command's output:
   ```
   ⚠ status.md still shows `<field>: TBD` for `<artifact_id>` despite review: pass — status may be stale
   ```
   Emit one warning per stale field — do not suppress after the first.
6. After the last warning (only when at least one was emitted), add one closing line offering the repair path:
   ```
   Run /wire:status-sync <release-folder> to reconcile the record (see specs/utils/status_sync.md).
   ```
   The offer is informational only — never block the calling command and never run the sync automatically.
7. If no stale fields are found, the review/approval gate has not yet passed, or `artifact_id` could not be derived: no output, proceed silently.

This check is self-contained within this utility, so every caller gets it automatically without any caller-side changes.

## Rules

1. **Append only** — never modify or delete existing log entries, and never
   re-order them. A row is appended at the bottom, always. Rewriting the file
   to insert a row in timestamp order is a modification, not an append. One
   exception: the metrics hook (see Metrics Backfill below) may rewrite the
   Duration, Tokens, and Cost cells of the most recent row, and nothing else.
2. **One row per command execution** — even if a command is re-run, add a new row (this creates the revision history)
3. **Always log after status.md is updated** — the log entry should reflect the final state
4. **Pipe characters in detail** — if the detail text contains `|`, replace with `—` to preserve table formatting
5. **Keep detail under 120 characters** — be concise
6. **Timestamps must not go backwards.** Because rows are appended in the order
   things happened, each row's timestamp is greater than or equal to the row
   above it. A row whose timestamp precedes its predecessor's means either the
   clock moved or a row was inserted out of order; both are record defects.
   `/wire:status-sync` flags them, naming both rows. This does not block any
   command — the log is written either way, and the flag is a repair prompt.
7. **Single writer in orchestrated mode.** When
   `specs/utils/director_operating_model.md`'s operating model is in force,
   only the orchestrating session appends to this file. Lanes write their own
   state files and the orchestrator writes the log rows from them (rule 6 of
   the operating model). Outside orchestrated mode, every command writes its
   own row as it always has.
8. **Never fabricate metrics.** Tokens and Cost are written as `n/a` and only
   ever filled by tooling that measured them. A best guess is worse than
   `n/a` in a client-facing audit trail.

## Metrics Backfill (Claude Code)

The Wire Claude Code plugin registers a `Stop` hook (`hooks/wire-metrics.sh`)
that runs after each turn ends. It reads the session transcript, sums the
measured token usage from the most recent `/wire:*` command invocation to the
end of the turn, estimates its cost from a built-in price table, and rewrites
the Duration (only if still `n/a`), Tokens, and Cost cells of the log's most
recent row — only when that row's Command matches the command found in the
transcript and the row already has the metric columns. It never touches any
other cell or row. Commands that span several turns (e.g. a review waiting on
feedback) are re-summed on each turn's hook run, so the final backfill covers
the whole command. If the cost table does not recognise the model, Tokens is
still filled and Cost stays `n/a`. On runtimes without this hook, the metric
cells keep the values the workflow wrote.

## Legacy five-column rows

Logs written before the `By` and `Session` columns existed have four data
columns, and logs written before the `Duration`, `Tokens`, and `Cost (USD)`
columns existed have four or six. They stay valid and are never rewritten:

- A reader parses columns positionally and treats a missing `By`, `Session`,
  or metric column as unknown. It does not treat a shorter row as malformed
  and does not backfill it.
- Missing columns are added on the next write. A file whose header still has
  the older shape gets the new header written once, at the point the first
  nine-column row is appended; existing rows are left as they are, so a log
  can legitimately hold several shapes.
- Nothing derives meaning from the absence of the columns. An old row is not
  "typed"; it is unknown. A row without metric cells is unmeasured, not free
  or instant — and the metrics hook skips rows that lack the metric columns.

## Example

```markdown
# Execution Log

| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a | n/a |
| 2026-02-22 14:35 | /wire:new | created | Project created (type: full_platform, client: Acme Corp) | Jane Smith | typed | 3m 40s | 84210 | $0.61 |
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements specification (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
| 2026-02-23 09:15 | /wire:conceptual_model-generate | complete | Generated entity model with 8 entities | Jane Smith | data-designer | 11m 48s | n/a | n/a |
| 2026-02-23 10:30 | /wire:conceptual_model-validate | fail | 2 issues: missing relationship, orphaned entity | Jane Smith | data-designer | 5m 02s | n/a | n/a |
| 2026-02-23 11:00 | /wire:conceptual_model-generate | complete | Regenerated entity model (fixed 2 issues, 8 entities) | Jane Smith | data-designer | 9m 31s | n/a | n/a |
| 2026-02-23 11:15 | /wire:conceptual_model-validate | pass | 12 checks passed, 0 failed | Jane Smith | data-designer | 4m 47s | n/a | n/a |
| 2026-02-23 14:00 | /wire:conceptual_model-review | changes_requested | Reviewed by John Doe — add Customer entity | Jane Smith | typed | 31m 20s | 122504 | $0.95 |
| 2026-02-23 15:30 | /wire:conceptual_model-generate | complete | Regenerated entity model (9 entities, added Customer) | Jane Smith | data-designer | 8m 56s | n/a | n/a |
| 2026-02-23 15:45 | /wire:conceptual_model-validate | pass | 14 checks passed, 0 failed | Jane Smith | data-designer | 4m 12s | n/a | n/a |
| 2026-02-23 16:00 | /wire:conceptual_model-review | approved | Reviewed by John Doe | Jane Smith | typed | 12m 33s | 74902 | $0.58 |
| 2026-02-24 09:05 | /wire:migration-strategy-generate | override | migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday | Jane Smith | typed | 2m 08s | 41207 | $0.33 |
| 2026-02-24 10:20 | /wire:conceptual_model-generate | override | business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff | Jane Smith | orchestrator [a1b2c3] | 7m 14s | 188341 | $1.44 |
```
