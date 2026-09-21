---
description: Autonomous end-to-end engagement execution from SOW — discovery sprint then all delivery releases
argument-hint: [path-to-sow]
model: claude-fable-5
---

# Autonomous end-to-end engagement execution from SOW — discovery sprint then all delivery releases

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
    'command': 'autopilot',
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
command: lifecycle
artifact: autopilot
domain: autopilot
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder"
description: Autonomous end-to-end engagement execution from SOW — discovery sprint + all delivery releases
argument-hint: <path-to-sow>

delegates_to:
  - utils/runnable_set
workload: planning
---

# Wire Autopilot — Autonomous Engagement Execution

## Purpose

Wire Autopilot takes a Statement of Work (SOW) and any supporting materials, asks a small set of clarifying questions, then autonomously executes the entire engagement lifecycle — starting with a discovery sprint (problem definition → pitch → release brief → sprint plan) and then executing each downstream delivery release in sequence.

For each release the autopilot generates, validates, and self-reviews every artifact without further human involvement. It produces a complete, demonstrable set of deliverables across all planned releases.

**Safety gates** automatically pause execution before any phase that could affect external systems — activating data connectors, running SQL against databases, or deploying to live environments. At each safety gate, Autopilot presents what it has done so far and asks for explicit confirmation before proceeding.

Autopilot shares the same state files (`status.md`, `autopilot_checkpoint.md`) as the individual commands. A user can switch between Autopilot and manual commands at any point.

## Inputs

**Required**:
- SOW or proposal document path (provided as argument or asked in Phase 1)

**Optional**:
- Additional supporting documents (org charts, call transcripts, architecture diagrams) gathered in Phase 1

---

# Phase 1: Clarifying Questions

Before going autonomous, Autopilot gathers all necessary context upfront. Ask each question in sequence, waiting for the user's response before proceeding.

## Step 1.1: SOW File Path

If a file path was provided as the command argument, verify the file exists using Glob. If found, proceed to Step 1.2.

If no argument was provided or the file was not found, ask directly in chat:

```
Please provide the path to your Statement of Work (SOW) or proposal document.
(e.g., "path/to/SOW.pdf" or "path/to/proposal.docx")
```

Wait for user response. Verify the file exists. If not found, inform the user and ask again.

Once the SOW is located, read it immediately to extract context for subsequent questions.

## Step 1.2: Engagement Details

Ask directly in chat (one question at a time):

```
What is the client name for this engagement?
(e.g., "Acme Corporation", "Client M")
```

Wait for response. Then:

```
What is the engagement name? (used for folder names)
(e.g., "acme_data_platform", "power_digital_analytics")
```

Wait for response. Then:

```
What is your name (engagement lead)?
```

Wait for response. Derive:
- `client_name`: Display name as provided
- `engagement_name`: Lowercase, underscores for spaces, no special chars
- `engagement_lead`: As provided
- `engagement_id`: Today's date as YYYYMMDD

## Step 1.3: Repo Mode

Ask directly in chat:

```
Is this repo the client's code repo, or a dedicated delivery repo?

Option A — Combined: The .wire/ folder lives directly in the client's code repo.
           Simple setup. Default for most engagements.

Option B — Dedicated delivery repo: This repo is exclusively for Wire delivery
           artifacts. The client's code repo is separate.

Which applies? (A/B)
```

Wait for response. If Option B, ask:

```
Please provide the client code repo details:
1. GitHub URL
2. Local path on your machine
3. Default branch (default: main)
```

Store `client_repo_url`, `client_repo_local_path`, `client_repo_branch`.

## Step 1.4: Issue Tracker Integration

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to track this engagement in an issue tracker?",
    "header": "Issue Tracker",
    "options": [
      {"label": "Jira", "description": "Create or link Jira Epic, Tasks, and Sub-tasks"},
      {"label": "Linear", "description": "Create or link a Linear Project, Issues, and Sub-issues"},
      {"label": "Both Jira and Linear", "description": "Track in both Jira and Linear simultaneously"},
      {"label": "No, skip issue tracking", "description": "Track progress in status.md only"}
    ],
    "multiSelect": false
  }]
}
```

**If Jira or Both selected**, ask:

```
What is the Jira project key? (e.g., DP, ACME, PROJ)
And how would you like to set it up? (create new issues / link to existing)
```

Store `jira_project_key` and `jira_mode` ("create" or "link").

**If Linear or Both selected**, ask (as two separate questions):

First:
```
What is the Linear team identifier? (e.g., ENG, DATA, ACME)
```

Then:
```
How would you like to set up Linear?
  1. Create a new Linear project and new issues — Wire will create a project, issues, and sub-issues from scratch
  2. Use an existing Linear project and create new issues in it — Wire will create fresh issues inside an existing project
  3. Link to existing issues in an existing project — Wire will search the team for matching issues and link them
```

If option 2 or 3 is chosen, ask:
```
Paste the Linear project URL or ID (e.g. https://linear.app/acme/project/my-project-abc123):
```

Store `linear_team_id`, `linear_project_id` (if option 2 or 3 — extract from URL or use as-is), and `linear_mode` ("create", "create_in_existing", or "link").

## Step 1.4.5: Document Store Integration

**Question 1** — Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Would you like to replicate generated documents to a client-accessible document store for review and annotation?",
    "header": "Document Store",
    "options": [
      {"label": "Confluence", "description": "Publish documents to a Confluence space — reviewers can comment and annotate inline"},
      {"label": "Notion", "description": "Publish documents to a Notion workspace — reviewers can comment and edit pages"},
      {"label": "Both Confluence and Notion", "description": "Publish to both simultaneously"},
      {"label": "No, skip document store", "description": "Documents stay in GitHub only"}
    ],
    "multiSelect": false
  }]
}
```

**Question 2** — If "Confluence" or "Both Confluence and Notion" was selected, ask directly in chat:
```
What is the Confluence space key where Wire documents should be published?
(e.g. PROJ, ACME, DATA — found in the space URL: /wiki/spaces/PROJ/...)
```

**Question 3** — If "Notion" or "Both Confluence and Notion" was selected, ask directly in chat:
```
What is the Notion parent page for Wire documents?
Paste the page URL or ID (e.g. https://www.notion.so/My-Projects-abc123 or just the ID).
This page must already exist and be accessible via the Notion MCP.
```

Store `docstore_provider` ("confluence", "notion", "both", or null), `confluence_space_key` (if Confluence selected), and `notion_parent_page_id` (if Notion selected — extract ID from URL if a full URL was given).

## Step 1.5: Additional Context

Ask directly in chat:

```
Do you have any other supporting documents I should read? (org charts, call
transcripts, architecture diagrams, existing data model docs)

Provide file paths, or type "no" to skip.
```

Store paths as `supporting_docs`. Read each file that exists.

Also ask:

```
Is there anything else I should know about this engagement? For example:
- Specific technologies or platforms (BigQuery, Snowflake, Looker)
- Naming conventions or standards
- Stakeholder preferences
- Existing codebase or infrastructure

Type "no" to skip.
```

Store as `additional_context`.

## Step 1.6: Confirm, Launch, and Request Permissions

After gathering all inputs, enter plan mode to present the execution plan and pre-authorize shell operations.

1. Call `EnterPlanMode`
2. Write a plan file with the following content:

```markdown
# Wire Autopilot Execution Plan

## Configuration
- **Client**: [client_name]
- **Engagement**: [engagement_name]
- **Lead**: [engagement_lead]
- **SOW**: [sow_path]
- **Supporting docs**: [list or "none"]
- **Jira**: [project_key or "None"]
- **Linear**: [team_id or "None"]
- **Document store**: [provider or "None"]
- **Additional context**: [summary or "none"]

## Execution Sequence

### Phase 2: Engagement Setup
- Create two-tier .wire/ folder structure
- Set up engagement context and copy SOW
- Create 01-discovery release

### Phase 3: Discovery Sprint (autonomous)
1. Problem Definition — generate → validate → self-approve
2. Pitch — generate → validate → self-approve
3. Release Brief — generate → validate → self-approve
4. Sprint Plan — generate → validate → self-approve

### Phase 4: Delivery Releases
(Determined by sprint plan output — typically 2–4 releases)
Each release: create folder → execute full artifact sequence for its type

## What Autopilot Does For Each Artifact
1. **Generate** the artifact from upstream outputs
2. **Validate** against quality criteria (up to 3 retry cycles)
3. **Self-review** for completeness (up to 2 review cycles)
4. Update status tracking

## Safety Gates
These phases will **pause for explicit confirmation** before proceeding:
- **pipeline** — Activates data connectors
- **data_refactor** — Runs dbt against real databases
- **data_quality** — Executes SQL tests against databases
- **deployment** — Deploys to live environments

## Shell Operations Required
- Git (branch creation, commits, push)
- Directory and file management (mkdir, cp)
- dbt commands (compile, run, test, seed, deps)
- File listing and existence checks
- GitHub CLI (create pull request)
```

3. Call `ExitPlanMode` with `allowedPrompts`:

```json
{
  "allowedPrompts": [
    {"tool": "Bash", "prompt": "git operations (checkout, branch, status, add, commit, push, rev-parse, diff)"},
    {"tool": "Bash", "prompt": "create engagement and release directories and copy files (mkdir, cp, mv)"},
    {"tool": "Bash", "prompt": "run dbt commands (compile, run, test, seed, deps, debug, ls)"},
    {"tool": "Bash", "prompt": "run data quality checks and validation scripts"},
    {"tool": "Bash", "prompt": "list files and check file existence (ls, find, wc, cat, head, tail)"},
    {"tool": "Bash", "prompt": "GitHub CLI operations (gh pr create, gh pr view)"}
  ]
}
```

4. If the user approves the plan, proceed to Phase 2.
5. If the user rejects or requests changes, return to Step 1.2 to reconfigure.

**Runtime note**: In Gemini CLI, skip this step and proceed directly to Phase 2. Use appropriate permission flags (e.g., `--yolo`) for autonomous execution.

---

# Phase 2: Engagement Setup

## Step 2.1: Git Branch

1. Run `git rev-parse --abbrev-ref HEAD` to check the current branch
2. If on `main` or `master`, create and switch to `feature/{engagement_name}`:
   ```bash
   git checkout -b feature/{engagement_name}
   ```
3. If branch already exists, switch to it
4. Store `branch_name` for the final summary

## Step 2.2: Create Two-Tier Folder Structure

```bash
mkdir -p .wire/engagement/calls
mkdir -p .wire/engagement/org
mkdir -p .wire/research/sessions
mkdir -p .wire/releases/01-discovery/planning
mkdir -p .wire/releases/01-discovery/artifacts
touch .wire/engagement/calls/.gitkeep
touch .wire/engagement/org/.gitkeep
touch .wire/research/sessions/.gitkeep
touch .wire/releases/01-discovery/artifacts/.gitkeep
```

## Step 2.3: Copy SOW and Supporting Docs

```bash
cp {sow_path} .wire/engagement/sow.md   # or sow.pdf if PDF
```

If `supporting_docs` were provided, copy each to `engagement/`:
```bash
cp {doc_path} .wire/engagement/
```

## Step 2.4: Create Engagement Context File

Read `TEMPLATES/engagement-context-template.md` and populate:
- `{{ENGAGEMENT_NAME}}` → engagement_name
- `{{CLIENT_NAME}}` → client_name
- `{{CREATED_DATE}}` → today's date (YYYY-MM-DD)
- `{{ENGAGEMENT_LEAD}}` → engagement_lead
- `{{REPO_MODE}}` → `combined` or `dedicated_delivery`

If dedicated_delivery, populate the client_repo section. Write to `.wire/engagement/context.md`.

## Step 2.5: Create Discovery Release Status File

Read `TEMPLATES/discovery-status-template.md` and populate:
- `{{RELEASE_ID}}` → engagement_id (YYYYMMDD)
- `{{RELEASE_NAME}}` → `01-discovery`
- `{{CLIENT_NAME}}` → client_name
- `{{ENGAGEMENT_NAME}}` → engagement_name
- `{{CREATED_DATE}}` → today's date

Write to `.wire/releases/01-discovery/status.md`.

## Step 2.6: Issue Tracker Setup (if opted in)

**If Jira or Both selected**: Follow the workflow in `specs/utils/jira_create.md`. Pass `release_type: discovery` and artifact scope (problem_definition, pitch, release_brief, sprint_plan). If Jira fails, note the failure and continue.

**If Linear or Both selected**: Follow the workflow in `specs/utils/linear_create.md`. Pass `release_type: discovery` and the same artifact scope. If Linear fails, note the failure and continue.

When Both is selected, run both workflows independently — one failure does not block the other.

## Step 2.6.5: Document Store Setup (if opted in)

If `docstore_provider` is set, follow the workflow in `specs/utils/docstore_setup.md`. Pass the engagement name, `releases/01-discovery` as the release folder, and `docstore_provider`. If setup fails, note the failure and continue — document store is optional and additive.

## Step 2.7: Initialize Autopilot Checkpoint

Create `.wire/autopilot_checkpoint.md`:

```markdown
# Autopilot Checkpoint

## Configuration
- Engagement: [engagement_name]
- Client: [client_name]
- Lead: [engagement_lead]
- SOW: [sow_filename]
- Jira: [project_key or "None"]
- Linear: [team_id or "None"]
- Document store: [provider or "None"]
- Branch: [branch_name]

## SOW Summary
[Condensed 500-word summary covering: business context, deliverables, data sources, key stakeholders, timeline, and technology preferences]

## Engagement Structure
- Discovery release: .wire/releases/01-discovery/
- Delivery releases: (to be determined by sprint plan)

## Completed Phases
(none yet)

## Current Phase
engagement_setup: complete

## Key Context
- Data sources: [list from SOW]
- Key entities: [list from SOW]
- Deliverables: [list from SOW]
- Technologies: [from SOW + additional_context]
- SOW timeline: [duration from SOW]

## Decisions Made
(none yet)

## Blocked Artifacts
(none)
```

Output:
```
--- Engagement Setup Complete ---
Client: {client_name}
Engagement: {engagement_name}
Branch: {branch_name}
Discovery release: .wire/releases/01-discovery/
Beginning discovery sprint...
---
```

---

# Phase 3: Discovery Sprint (Autonomous)

The discovery sprint runs the full Shape Up planning cycle autonomously: `problem_definition` → `pitch` → `release_brief` → `sprint_plan`, per `wire/release-types/discovery_shape_up.yaml` (a single, unambiguous release type — no order-resolution ambiguity here, unlike Phase 4's shared-domain types).

Run this exactly like Phase 4's Step 4.3 procedure: resolve the order from `discovery_shape_up.yaml` (in practice, always the fixed sequence above — the release type has no branching), then for each artifact run the real `/wire:{command}-generate`, `/wire:{command}-validate`, and self-reviewed `/wire:{command}-review` against `.wire/releases/01-discovery/`, exactly as Step 4.3b describes. The same Self-Review Mode applies for review steps.

Generate steps here occasionally have a "wait for the user" checkpoint written for a human filling the document in interactively (see e.g. `discovery/pitch/generate.md`) — apply the same self-answer principle Self-Review Mode uses: don't wait, make the call yourself from the SOW and supporting material, autonomously. This is where Autopilot's planning judgment matters most — e.g. for `pitch`, infer appetite from the SOW's stated timeline (6+ weeks → big batch; 2-3 weeks → small batch; ambiguous → default big batch) rather than asking; for `sprint_plan`, use a 5-points-per-consultant-day velocity assumption with 20% buffer. Apply this kind of inference wherever a generate spec would otherwise pause for input, sourced from what the spec actually asks for — not a separately maintained copy of its logic.

`sprint_plan`'s output includes the "Downstream Releases" table (name, type, scope, priority) that Step 3.5 below reads — confirm during self-review that every release type listed there is one Wire actually supports (has a `wire/release-types/*.yaml`): `discovery_shape_up`, `sop_discovery`, `full_platform`, `dbt_development`, `dashboard_first`, `platform_migration`, `droughty`, `agentic_data_stack`, `pipeline_only`, `dashboard_extension`, `enablement`.

After all four discovery artifacts are `review: approved`, proceed to Step 3.5.

---

## Step 3.5: Parse Downstream Releases

Read the "Downstream Releases" table from `.wire/releases/01-discovery/planning/sprint_plan.md`.

For each row, extract:
- `release_name`: the folder name (e.g., `02-data-foundation`)
- `release_type`: the Wire release type (e.g., `pipeline_only`)
- `scope_summary`: the one-line scope description

Store as an ordered list: `planned_releases = [{"name": ..., "type": ..., "scope": ...}, ...]`

Update autopilot_checkpoint.md:
```markdown
## Delivery Releases to Execute
| Release | Type | Scope |
|---------|------|-------|
| [name] | [type] | [scope] |
```

---

# Phase 4: Delivery Release Execution

For each release in `planned_releases`, in order:

## Step 4.0: Confirm Release Plan with User

Before spawning and executing releases, present the plan and confirm:

Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "Discovery sprint complete. Ready to execute [N] delivery releases:\n[list each release with name and type]\n\nProceed with autonomous execution?",
    "header": "Discovery Complete — Proceed to Delivery?",
    "options": [
      {"label": "Yes, execute all releases", "description": "Proceed autonomously through all planned delivery releases"},
      {"label": "Review discovery artifacts first", "description": "Pause here — I'll review the discovery output before proceeding"},
      {"label": "Stop here", "description": "End Autopilot — I will run delivery releases manually using /wire:session-start"}
    ],
    "multiSelect": false
  }]
}
```

- **Yes, execute all**: Proceed to Step 4.1
- **Review first**: Output paths to all discovery artifacts and wait for user to say "continue"
- **Stop here**: Jump to Phase 5 (commit + push) and Phase 6 (final summary)

## Step 4.1: For Each Delivery Release

Repeat steps 4.2–4.5 for each release in `planned_releases`.

Set `current_release` = the current release name (e.g., `02-data-foundation`).
Set `current_type` = the current release type (e.g., `pipeline_only`).

### Step 4.2: Create Release Folder (Spawn)

```bash
mkdir -p .wire/releases/{current_release}/{artifacts,requirements,design,dev,test,deploy,enablement}
touch .wire/releases/{current_release}/requirements/.gitkeep
touch .wire/releases/{current_release}/design/.gitkeep
touch .wire/releases/{current_release}/dev/.gitkeep
touch .wire/releases/{current_release}/test/.gitkeep
touch .wire/releases/{current_release}/deploy/.gitkeep
touch .wire/releases/{current_release}/enablement/.gitkeep
```

Create the status file by reading `TEMPLATES/status-template.md` and populating:
- `{{PROJECT_ID}}` → engagement_id
- `{{PROJECT_NAME}}` → engagement_name
- `{{PROJECT_TYPE}}` → current_type
- `{{CLIENT_NAME}}` → client_name
- `{{CREATED_DATE}}` → today's date

The written status.md's `project_type` (or `release_type` — templates aren't
consistent about the field name; check both) drives everything that
follows — Step 4.3 reads it back to resolve the artifact sequence. No
scope/sequence needs to be set here by hand.

Write to `.wire/releases/{current_release}/status.md`.

Initialize release checkpoint block in autopilot_checkpoint.md:
```markdown
## Release: {current_release} ({current_type})
Status: in_progress
Started: [timestamp]
```

Output:
```
--- Starting Release: {current_release} ({current_type}) ---
Artifact sequence: [resolved from wire/release-types/{current_type}.yaml — see Step 4.3]
---
```

### Step 4.2.5: Data Model Registry — Automatic Setup Attempt (Conditional, Silent)

Same gap this closes as `specs/new.md`'s equivalent step: `data_model-generate`'s canonical-vertical matching only ever checks for a local registry copy, never fetches one, so an RA consultant running Autopilot on a machine that never had `/wire:utils-data-model-registry-setup` run manually would get the feature silently and permanently skipped despite having real GitHub access. The gate should be repo access, not "did anyone remember to run the setup command first."

1. **Check relevance.** Read `wire/release-types/{current_type}.yaml`. If no `phases[].artifacts[]` entry has `id: data_model`, skip this step silently — this release will never call `data_model-generate`.
2. **Check the attempted marker.** `ls ~/.wire/data_model_registry_setup_attempted 2>/dev/null`. If present, skip silently — already handled, on this machine, possibly by an earlier release in this same run or an earlier engagement entirely.
3. **Attempt it.** Follow `specs/utils/data_model_registry_setup.md` as an automated caller (its Step 1.5). It writes the marker itself.
4. **Report minimally**, exactly as `specs/new.md`'s equivalent step does — one unobtrusive line on success, nothing at all on failure. Do not treat a failure here as a blocker or log it as an error; continue straight to Step 4.3.

This runs at most once per Autopilot invocation, on whichever release first needs it (typically the first `full_platform`/`dbt_development`/`dashboard_first` release in the plan) — not once per release.

### Step 4.3: Resolve Order and Run the Artifact Execution Loop

Autopilot never hardcodes which artifacts a release type has or what order
they run in — that lives in exactly one place,
`wire/release-types/{current_type}.yaml`, and drifts if duplicated. Resolve
it fresh for every release; do not cache across releases of different types.

#### Step 4.3a: Resolve the artifact order

Run `specs/utils/runnable_set.md` for `{current_release}`. It reads the
release-type YAML (resolved from `project_type`, else `release_type`, in
`status.md`), applies the active profile, and returns every artifact's state
plus a topological order.

Autopilot uses the order and the `not applicable` classification. It does not
use the `parked: needs ruling` classification the way the orchestrating session
does — Autopilot's whole premise is that it answers review gates itself
(see "Self-Review Mode"), so an artifact `runnable_set` marks as parked at a
review edge is one Autopilot proceeds through under self-review. Everything
else is identical: same YAML, same profile resolution, same tie-break on
`sequence` between artifacts with no dependency between them.

Autopilot's behaviour is unchanged by this. The topological read it used to
perform inline is the same read; it now lives in one place so that
`/wire:start`, `/wire:delegate`, the orchestrating session and Autopilot cannot
disagree about what comes next. Keeping four copies of it is how the
`full_platform` sequence lost the `orchestration` artifact.

If `runnable_set` stops because the release type resolves to no YAML file, stop
with its message — that is a real gap, and guessing at a sequence hides it.

#### Step 4.3b: For each artifact in the resolved order

1. **Check status**: Read `.wire/releases/{current_release}/status.md`. If
   this artifact's generate state is already `complete` and review state is
   `approved`, skip it.

2. **Safety gate check**: If this artifact is in the safety-gated list
   (`pipeline`, `data_refactor`, `data_quality`, `deployment`; and for
   `platform_migration` releases: `target_setup`, `ingestion_migration`,
   `orchestration_migration`, `cutover`), execute the Safety Gate protocol
   before proceeding. This list is Autopilot policy (which steps are risky
   enough to pause for) — it's independent of the YAML and stays as-is.

3. **Generate — run the real command**: Execute
   `/wire:{command}-generate {current_release}` exactly as if the user had
   typed it — not a paraphrase of its logic, the actual command. Its own
   Auto-Delegation (including `precondition_gate` if the spec declares
   `preconditions`) and Post-Execution Hooks (execution_log, Jira/Linear
   sync, document store sync, commit) run unchanged and need no duplication
   here. See "Handling a precondition-gate block" below for what happens if
   the gate stops it.

4. **Validate — run the real command, if it exists**: Not every artifact
   has a validate step (`mockups`, `uat`, `workshops` don't). If
   `/wire:{command}-validate` exists for this artifact, run it the same
   way. On fail, the real spec's own retry guidance applies; if still
   failing after 3 cycles, treat as blocked and log it — do not loop
   forever.

5. **Review — self-review mode**: See "Self-Review Mode" below. Run through
   the real `review.md` spec's actual content, but answer its own
   questions autonomously instead of waiting for a human. Up to 2
   regenerate-and-re-review cycles if self-review finds issues; still
   failing after that, set `review: changes_requested` and log as blocked.

6. **Update checkpoint**: Move artifact to "Completed Phases" in
   `autopilot_checkpoint.md` with a brief summary and any key context
   discovered.

7. **Report progress**:
   ```
   --- Artifact Complete: [artifact_name] ([current_release]) ---
   Status: [approved/blocked]
   Files: [list]
   Progress: [N/total] artifacts in this release, [R/total_releases] releases done
   ---
   ```

8. **Telemetry**: Fire-and-forget:
   ```bash
   if [ "${WIRE_TELEMETRY:-true}" != "false" ]; then WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ARTIFACT_NAME-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"4.0.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"invoked_by\":\"autopilot\",\"autopilot_release\":\"{current_release}\",\"autopilot_artifact\":\"ARTIFACT_NAME\"}}" > /dev/null 2>&1 & fi
   ```
   Replace `ARTIFACT_NAME` with the actual artifact name. Do not wait for the result.

#### Self-Review Mode

The real `*-review.md` spec for an artifact is written for a live human —
it calls `AskUserQuestion` or otherwise asks the reviewer directly, and
expects to wait for their answer. Autopilot cannot wait for a human here
(that would defeat the point of running autonomously), but it also
shouldn't hand-maintain its own separate copy of what "good" looks like for
each artifact — that's exactly the kind of duplication that caused
`autopilot.md` to silently drift from the real specs before this rewrite.

Instead, self-review means running the real spec but substituting yourself
for the human at the one or two points it asks a question:

1. Read the real `wire/specs/<domain>/<artifact>/review.md` in full.
2. Follow every step that isn't an interactive question exactly as written
   — e.g. "Load meeting context," "Present [artifact] for review" (produce
   the summary, just don't display-and-wait), any structural/completeness
   checks the spec describes.
3. Where the spec would call `AskUserQuestion` or say "ask the reviewer" /
   "who approved this," don't wait for input. Instead, evaluate the spec's
   own stated review criteria against the artifact yourself, right there,
   and decide `approved` or `changes_requested` on that basis.
4. Write status.md exactly as the spec's own "Update status" / "Record
   review" step describes — same fields a human approval would produce —
   except `reviewed_by: "Wire Autopilot (self-review)"` instead of a
   person's name.
5. If you decide `changes_requested`, treat your own findings as the
   feedback: regenerate the artifact addressing them, then re-run this
   procedure. Up to 2 cycles (matching the existing retry budget); if still
   not passing after that, stop and log it as blocked rather than looping
   indefinitely.

This means a review's actual criteria — whatever they currently say in the
real spec — govern self-review too. If a review.md's criteria change later
(via a `wire-process-registry` PR), autopilot's self-review reflects that
automatically; nothing in `autopilot.md` itself needs to change.

#### Handling a precondition-gate block

If Step 4.3a resolved the order correctly, every artifact's `precondition_gate`
(triggered inside the real generate/validate/review command's own
Auto-Delegation, per `wire/specs/utils/precondition_gate.md`) should pass
silently by the time Autopilot reaches it — that's what a correct
topological order guarantees. If it blocks anyway, that signals a real
structural problem (a bug in the resolved order, a manually-edited status.md
that regressed something, a genuinely missing dependency), not routine
friction to route around.

Do **not** self-override. `precondition_gate.md`'s override contract
requires a real person's name and reason — Autopilot cannot supply that on
someone else's behalf, and silently answering its own override prompt would
undermine the entire point of the gate. Instead, pause with the same
`AskUserQuestion` pattern as a Safety Gate:

```json
{
  "questions": [{
    "question": "[artifact]/[command] is blocked: [unmet precondition from the gate's own message]. This wasn't expected given the resolved execution order — how would you like to proceed?",
    "header": "Precondition Gate — [artifact_name] in [current_release]",
    "options": [
      {"label": "I'll override it now", "description": "Prompts for your name and reason, per the gate's normal override flow, then continues"},
      {"label": "Let me investigate first", "description": "Pause here — I'll check status.md and the release-type YAML before deciding"},
      {"label": "Stop here", "description": "End Autopilot at this point — I will continue manually"}
    ],
    "multiSelect": false
  }]
}
```

Log the block and its resolution in `autopilot_checkpoint.md` under a new
"Precondition Gate Blocks" note — this is useful signal that the YAML's
`depends_on` graph and Autopilot's derived order disagree somewhere, worth
fixing at the source rather than overriding repeatedly on future runs.

### Step 4.4: Release Resumption Protocol

If Autopilot is invoked and a release in progress already has artifacts completed:

1. Read `.wire/releases/{current_release}/status.md` to identify completed phases
2. Identify the first incomplete artifact in the sequence
3. Resume from that point — do NOT re-generate already-approved artifacts

### Step 4.5: Commit After Each Release

After all artifacts in a release are processed:

```bash
git add .wire/releases/{current_release}/ dbt/ 2>/dev/null; git add -u; true
```

Check for staged changes. If changes exist:

```bash
git commit -m "Wire Autopilot: {engagement_name} — {current_release} ({current_type}) complete

Client: {client_name}
Release: {current_release}
Type: {current_type}
Artifacts: {comma-separated list of completed artifacts}"
```

Update autopilot_checkpoint.md:
```markdown
## Release: {current_release} ({current_type})
Status: complete
Committed: [commit hash]
```

Output:
```
--- Release Complete: {current_release} ---
Type: {current_type}
Committed: [hash]
[R/total_releases] releases done. Moving to next release...
---
```

---

## Safety Gates

Certain artifacts can touch external systems. Before processing any of these, Autopilot **must pause** and request explicit user confirmation.

**Safety-gated artifacts:**

| Artifact | Risk | Warning |
|----------|------|---------|
| `pipeline` | Activates real data connectors (Fivetran, Airbyte) that begin replicating from production sources | "This phase will generate pipeline configuration. When activated, this could start replicating data from your production source systems. Please confirm the target environment and connector credentials are correct before proceeding." |
| `data_refactor` | Modifies dbt source definitions to point to real client data | "This phase will switch dbt models from seed data to real client data sources. The validate step will run `dbt compile` and potentially `dbt run` against your database. Please confirm the database connection is pointing to the correct (non-production) environment." |
| `data_quality` | Runs SQL-based tests against the database | "This phase will run data quality tests that execute SQL queries against your database. Please confirm the target database connection is correct." |
| `deployment` | Creates and potentially executes deployment scripts against live environments | "This phase will generate deployment runbooks and scripts. Executing these would deploy changes to a live environment. Please confirm you are ready to proceed with deployment planning." |

**Safety gate behavior** — when the execution loop reaches a safety-gated artifact, it MUST:

1. Pause execution
2. Present a summary of all completed work so far (from the checkpoint)
3. Display the risk-specific warning message
4. Use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "[Warning message for this artifact]. How would you like to proceed?",
    "header": "Safety Gate — [artifact_name] in [current_release]",
    "options": [
      {"label": "Proceed", "description": "Continue — I have verified the target environment"},
      {"label": "Review first", "description": "Show me all generated artifacts so far, then I'll decide"},
      {"label": "Stop here", "description": "End Autopilot — I will continue manually from this point"}
    ],
    "multiSelect": false
  }]
}
```

- **Proceed**: Continue with the artifact's generate/validate/review cycle
- **Review first**: Output a summary of all files generated so far with their paths, then wait for the user to say "continue"
- **Stop here**: Commit progress, output final summary (Phase 6), and exit

---

# Phase 5: Final Commit, Push, and Pull Request

After all releases are processed (or when Autopilot stops):

## Step 5.1: Final Commit

Stage any uncommitted changes:
```bash
git add .wire/ dbt/ 2>/dev/null; git add -u; true
```

Check for staged changes. If any:
```bash
git commit -m "Wire Autopilot: {engagement_name} — engagement complete

Client: {client_name}
Releases: {comma-separated list of release names}
Branch: {branch_name}"
```

## Step 5.2: Git Push

```bash
git push -u origin {branch_name}
```

If push fails (no remote configured), log: "Note: Could not push to remote. Commits are saved locally." and skip PR creation.

## Step 5.3: Create Pull Request

Check `gh` CLI is available:
```bash
which gh
```

If not available, log: "Note: GitHub CLI (gh) not found. Please create a PR manually for branch {branch_name}." and skip to Phase 6.

Create the PR:
```bash
gh pr create \
  --title "Wire: {client_name} — {engagement_name}" \
  --body "## Summary

Wire Autopilot generated artifacts for the **{engagement_name}** engagement.

**Client**: {client_name}
**Engagement Lead**: {engagement_lead}

## Releases

| Release | Type | Artifacts | Status |
|---------|------|-----------|--------|
| 01-discovery | discovery | problem_definition, pitch, release_brief, sprint_plan | complete |
[for each delivery release: name, type, artifact count, complete/partial]

---
Generated by Wire Autopilot v3.4.0"
```

Capture the PR URL as `pr_url`.

---

# Phase 6: Final Summary

Output a comprehensive summary:

```
## Wire Autopilot — Engagement Complete

**Client**: [client_name]
**Engagement**: [engagement_name]
**Lead**: [engagement_lead]
**Branch**: [branch_name]
**Pull Request**: [pr_url or "Not created — see notes above"]

### Discovery Sprint
| Artifact | Generate | Validate | Review |
|----------|----------|----------|--------|
| problem_definition | complete | pass | approved |
| pitch | complete | pass | approved |
| release_brief | complete | pass | approved |
| sprint_plan | complete | pass | approved |

### Delivery Releases

[For each delivery release:]
#### [release_name] ([release_type])
| Artifact | Generate | Validate | Review | Files |
|----------|----------|----------|--------|-------|
| [artifact] | [complete] | [pass/N/A] | [approved/N/A] | [count] |

### Overall Statistics
- Total releases: [discovery + delivery count]
- Total artifacts: [count across all releases]
- Files generated: [count]
- dbt models: [count] (if applicable)
- LookML views: [count] (if applicable)
- Dashboard specs: [count] (if applicable)
- Training sessions: [count] (if applicable)
- Documentation guides: [count] (if applicable)

### Blocked Phases (if any)
[List with reasons and manual resolution steps]

### What's Ready for Demo
[List of concrete deliverables with file paths]

### Next Steps
1. Review the pull request: [pr_url]
2. Share discovery artifacts with the client for sign-off:
   - Problem definition: .wire/releases/01-discovery/planning/problem_definition.md
   - Pitch: .wire/releases/01-discovery/planning/pitch.md
   - Release brief: .wire/releases/01-discovery/planning/release_brief.md
3. [If blocked phases] Address them manually, then resume:
   /wire:session-start releases/[release_name]
4. [If dbt generated] Run against real data:
   cd dbt && dbt deps && dbt run
5. [If applicable] Schedule stakeholder demos using generated training materials
```

Log final entry to `.wire/autopilot_checkpoint.md`:
```markdown
## Autopilot Complete
Finished: [timestamp]
Releases: [count] ([list])
PR: [pr_url]
```

---

# Engagement-Level Resumption Protocol

If Autopilot is invoked on an engagement that already has work in progress:

1. Check whether `.wire/engagement/context.md` exists — if not, treat as a fresh engagement
2. Check `.wire/autopilot_checkpoint.md` for compressed context from prior phases
3. Check `.wire/releases/01-discovery/status.md` — if all four discovery artifacts are approved, skip Phase 3
4. Check `planned_releases` from the checkpoint — identify which releases are complete and which are in progress
5. Resume execution from the first incomplete artifact in the first incomplete release
6. Do NOT re-generate already-completed and approved artifacts

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
