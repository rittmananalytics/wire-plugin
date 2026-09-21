---
description: Create Jira Epic and issues for a project
argument-hint: <project-folder>
---

# Create Jira Epic and issues for a project

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
    'command': 'utils-jira-create',
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
description: Create or link Jira issues for a data platform project
argument-hint: <project-folder>

---

# Jira Issue Creation and Linking Utility

## Purpose

Set up Jira tracking for a data platform project. Supports two modes:

- **Create mode**: Create a new Jira issue hierarchy (Epic → Tasks → Sub-tasks) from scratch
- **Link mode**: Search an existing Jira project for issues that match framework artifacts and link to them instead of creating duplicates

Can be used in three ways:
- **During project creation**: Called automatically from `/wire:new` (Step 9.5) when the user opts in to Jira tracking
- **Mid-project enablement**: Run standalone on an existing project to retroactively add Jira tracking at any point
- **Linking to existing boards**: When a Jira project already has issues (e.g. in a running sprint), search and link to the most appropriate existing issues

## Usage

```bash
/wire:utils-jira-create YYYYMMDD_project_name
```

When invoked standalone (not from `/wire:new`), prompt the user for the Jira project key and the desired mode (create or link).

## Prerequisites

- Atlassian MCP server must be configured
- Jira project key must be provided
- Project must exist with a valid `status.md`

## Workflow

### Step 1: Read Project Context

**Process**:
1. Read the project's `status.md`
2. Extract from YAML frontmatter:
   - `project_name`
   - `client_name`
   - `project_type`
   - `artifacts` section (to determine in-scope artifacts)
3. Accept `jira_project_key` from the calling context (provided by user during `/wire:new`), or if running standalone, ask the user directly:
   ```
   What is the Jira project key? (e.g., DP, ACME, PROJ)
   ```

### Step 1.5: Determine Workflow Mode and Structure

The setup is parameterised by two dimensions:

- **`jira_mode`**: `create` (build the issue hierarchy from scratch) or `link` (find and link to existing issues already in a Jira project).
- **`jira_structure`**: `subtasks` (default — one Task per artifact + three Sub-tasks per artifact for generate / validate / review) or `single_issue` (one Task per artifact, no Sub-tasks; the Task moves through workflow states as commands run).

**If invoked from `/wire:new` with `jira_mode: "link"`**:
- Proceed to **Step 2A** (Search for Existing Issues). The `link` mode currently assumes `subtasks` structure (linking to issues that have their own Sub-tasks).

**If invoked from `/wire:new` with `jira_mode: "create"` and `jira_structure: "single_issue"`**:
- Proceed to **Step 2** (Create Epic), then take the **Single-issue branch** in Step 3 (one Task per artifact, no Sub-tasks).

**If invoked from `/wire:new` with `jira_mode: "create"` and `jira_structure: "subtasks"` (or no structure specified — backwards compatible default)**:
- Proceed to **Step 2** (Create Epic), then take the **Sub-tasks branch** in Step 3 (existing behaviour: one Task per artifact + three Sub-tasks).

**If invoked standalone** (not from `/wire:new`):
- After getting the Jira project key in Step 1, use `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "How would you like to set up Jira tracking?",
    "header": "Jira Mode",
    "options": [
      {"label": "Create — sub-tasks per command", "description": "Epic → Task per artifact → 3 Sub-tasks (generate / validate / review). Default."},
      {"label": "Create — single issue per artifact", "description": "Epic → Task per artifact. The Task moves through To Do → In Progress (generate) → In Review (validate) → Done (review approved). Requires workflow support for those four states."},
      {"label": "Link to existing issues", "description": "Search for and link to existing issues in this Jira project (sub-tasks structure assumed)"}
    ],
    "multiSelect": false
  }]
}
```

Store `jira_mode` and `jira_structure` accordingly:
- "Create — sub-tasks per command" → `mode: create`, `structure: subtasks`
- "Create — single issue per artifact" → `mode: create`, `structure: single_issue`
- "Link to existing issues" → `mode: link`, `structure: subtasks`

### Step 1.6: Pre-flight workflow check (single_issue structure only)

If `jira_structure: single_issue` is selected, verify the Jira project's workflow supports the four required states: **To Do**, **In Progress**, **In Review**, **Done**. Use the Atlassian MCP to inspect available transitions on any existing issue in the project; if all four states are reachable, proceed. If any state is missing, output:

```
The Jira project [PROJECT_KEY] does not appear to support the workflow states required for single_issue structure: To Do, In Progress, In Review, Done.

Options:
1. Add the missing states / transitions to the Jira workflow and re-run.
2. Re-run /wire:new and choose "Create — sub-tasks per command" instead.
3. If your workflow uses different state names (e.g. "In QA" instead of "In Review"), tell me the names and I'll map them.
```

Wait for user input before proceeding.

---

## Workflow Path A: Create New Issues (Existing)

### Step 2: Create Epic

Create the top-level Epic for the project:

```
createJiraIssue:
  projectKey: "[jira_project_key]"
  issueType: "Epic"
  summary: "[client_name] - [project_name] Data Platform"
  description: |
    Data Platform project for [client_name].

    **Project Type**: [project_type]
    **Created**: [date]

    ## Artifacts in Scope
    [List of in-scope artifacts]

    ## Tracking
    Local status: .wire/[folder_name]/status.md
```

Record the returned Epic key (e.g., `PROJ-123`).

### Step 3: Create Tasks for Each In-Scope Artifact

For each artifact where the state is NOT `not_applicable`, create a Task under the Epic.

**Artifact display names and descriptions**:

| Artifact | Task Summary | Description |
|----------|-------------|-------------|
| requirements | Requirements Specification | Extract and validate requirements from SOW |
| workshops | Workshops | Discovery and clarification workshops |
| conceptual_model | Conceptual Model | Entity model and business object relationships |
| pipeline_design | Pipeline Design | Data pipeline architecture and data flow diagram |
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
createJiraIssue:
  projectKey: "[jira_project_key]"
  issueType: "Task"
  summary: "[Artifact Display Name]: [project_name]"
  description: "[Description from table above]"
  parentKey: "[epic_key]"
```

Record each returned Task key.

### Step 4: Sub-tasks or single issue — branch on `jira_structure`

#### Step 4a — `jira_structure: single_issue` (one Task per artifact)

Skip Sub-task creation. Instead, store only the Task key in status.md and ensure each Task starts in the **To Do** workflow state.

For each Task created in Step 3:

1. Verify the Task is in **To Do** state. If newly created it should be (Jira's default starting state). If not, transition it back to To Do.
2. Record only `task_key` in status.md under `jira.artifacts.[artifact]` — leave `generate_key`, `validate_key`, `review_key` as `null` (the Sub-tasks don't exist in this structure).
3. Also record `structure: single_issue` at the top of the `jira` section.

Skip to Step 5 (Update status.md).

The single Task will move through workflow states as commands run, per the state-transition matrix in `wire/specs/utils/jira_sync.md`:

| Command result | Transitions Task to |
|---|---|
| `<artifact>-generate` completes | **In Progress** |
| `<artifact>-validate` passes | **In Review** |
| `<artifact>-validate` fails | **In Progress** (kept, with comment) |
| `<artifact>-review` approved | **Done** |
| `<artifact>-review` changes_requested | **In Progress** |

The Jira project's workflow must support those four states. The pre-flight check in Step 1.6 verified this.

#### Step 4b — `jira_structure: subtasks` (default — one Task + three Sub-tasks per artifact)

For each Task, create Sub-tasks for the applicable lifecycle steps. Not all artifacts have all three steps (e.g., workshops and mockups have no validate step).

**Lifecycle steps per artifact**:

| Artifact | Generate | Validate | Review |
|----------|----------|----------|--------|
| requirements | yes | yes | yes |
| workshops | yes | no | yes |
| conceptual_model | yes | yes | yes |
| pipeline_design | yes | yes | yes |
| data_model | yes | yes | yes |
| mockups | yes | no | yes |
| pipeline | yes | yes | yes |
| dbt | yes | yes | yes |
| semantic_layer | yes | yes | yes |
| dashboards | yes | yes | yes |
| data_quality | yes | yes | yes |
| uat | yes | no | yes |
| deployment | yes | yes | yes |
| training | yes | yes | yes |
| documentation | yes | yes | yes |

For each applicable step:

```
createJiraIssue:
  projectKey: "[jira_project_key]"
  issueType: "Sub-task"
  summary: "[Step]: [Artifact Display Name]"
  description: "[Step] the [artifact] for [project_name]"
  parentKey: "[task_key]"
```

Example Sub-tasks for Requirements:
- `Generate: Requirements Specification`
- `Validate: Requirements Specification`
- `Review: Requirements Specification`

Record each returned Sub-task key.

---

## Workflow Path B: Link to Existing Issues

### Step 2A: Search for Existing Issues

Search the Jira project for issues that could map to framework artifacts. Use `searchJiraIssuesUsingJql` with a tiered strategy:

**Query 1 — Epics in the project:**
```
searchJiraIssuesUsingJql:
  jql: "project = [jira_project_key] AND issuetype = Epic ORDER BY created DESC"
  maxResults: 20
```

**Query 2 — Tasks/Stories in active sprint:**
```
searchJiraIssuesUsingJql:
  jql: "project = [jira_project_key] AND issuetype in (Task, Story) AND sprint in openSprints() ORDER BY created DESC"
  maxResults: 50
```

**Query 3 — Fallback: all open Tasks/Stories (if Query 2 returns no results or project doesn't use sprints):**
```
searchJiraIssuesUsingJql:
  jql: "project = [jira_project_key] AND issuetype in (Task, Story) AND status != Done ORDER BY created DESC"
  maxResults: 50
```

If Query 2 returns results, use those (sprint-scoped). If not, use Query 3 (all open issues). This handles Scrum, Kanban, and no-sprint projects.

Note to user if falling back:
```
No active sprint found in [KEY]. Searching all open issues.
```

### Step 2B: Match Issues to Framework Artifacts

For each in-scope artifact, find the best matching Jira issue from the search results using a scored matching algorithm.

**Scoring rules:**

| Signal | Score | Description |
|--------|-------|-------------|
| Summary contains artifact display name | +10 | e.g., "Requirements Specification" in issue summary |
| Summary contains artifact keyword | +5 | e.g., "requirements", "dbt", "pipeline" |
| Summary contains project name or client name | +3 | Indicates project relevance |
| Description contains artifact keywords | +2 | Weaker signal from description text |
| Issue type matches expected (Task for artifacts) | +2 | Type alignment |
| Issue is in active sprint | +1 | Recency/relevance bonus |

**Minimum threshold**: 5 points. Issues scoring below 5 are not considered matches.

**Assignment**: Process artifacts in descending order of their best match score. Each Jira issue can only be matched to one artifact (no double-matching). If two artifacts would match the same issue, the higher-scoring match wins and the lower-scoring artifact tries its next-best candidate.

**Artifact keyword mapping:**

| Artifact | Display Name | Match Keywords |
|----------|-------------|----------------|
| requirements | Requirements Specification | "requirements", "scope", "SOW", "deliverables" |
| workshops | Workshops | "workshop", "discovery", "kickoff" |
| conceptual_model | Conceptual Model | "entities", "conceptual", "ERD" |
| pipeline_design | Pipeline Design | "pipeline", "architecture", "data flow" |
| data_model | Data Model Design | "dbt", "staging", "warehouse", "data model" |
| mockups | Dashboard Mockups | "mockup", "wireframe", "dashboard design" |
| pipeline | Data Pipeline | "pipeline", "extraction", "data pipeline" |
| dbt | dbt Models | "dbt", "models", "transformations" |
| semantic_layer | Semantic Layer | "LookML", "semantic", "metrics", "measures" |
| dashboards | Dashboards | "dashboard", "report", "visualization" |
| data_quality | Data Quality Tests | "data quality", "testing", "dbt test" |
| uat | User Acceptance Testing | "UAT", "user acceptance", "sign-off" |
| deployment | Deployment | "deployment", "go-live", "production" |
| training | Training Materials | "training", "enablement", "onboarding" |
| documentation | Documentation | "documentation", "runbook", "handover" |

**Epic matching:**
- If an Epic's summary contains the client name or project name, match it as the project Epic
- If multiple Epics match, present them to the user for selection
- If no Epic matches, mark as "no Epic match" — `epic_key` will be null in status.md

**Sub-task matching** — For each matched Task, retrieve its Sub-tasks:
```
searchJiraIssuesUsingJql:
  jql: "parent = [task_key] AND issuetype = Sub-task ORDER BY created ASC"
  maxResults: 20
```

Match Sub-tasks to lifecycle steps using keyword detection in the Sub-task summary:
- **generate_key**: Summary contains "Generate", "Create", "Build", "Develop", or "Write"
- **validate_key**: Summary contains "Validate", "Test", "Check", "Verify", or "QA"
- **review_key**: Summary contains "Review", "Approve", "Sign-off", or "Accept"

If Sub-task names don't contain recognisable keywords, present them to the user:
```
Sub-tasks found under [PROJ-45] "[Task summary]":
1. [PROJ-46] "Write initial draft" — Map to: Generate? Validate? Review? Skip?
2. [PROJ-47] "QA check" — Map to: Generate? Validate? Review? Skip?
```

**Classify each artifact:**
- **Matched**: Task found (score >= 5) and at least one Sub-task mapped
- **Partial match**: Task found but no or incomplete Sub-task matches
- **No match**: No candidate Task scored above the threshold

### Step 2C: Present Matches for User Confirmation

Display the proposed mapping to the user:

```markdown
## Proposed Jira Issue Mapping

**Epic**: [PROJ-123] "[Epic summary]" → Project Epic
  (or: "No matching Epic found — epic_key will be left empty")

### Artifact Mapping

| Artifact | Jira Issue | Score | Sub-tasks Found | Status |
|----------|-----------|-------|-----------------|--------|
| Requirements | PROJ-45 "Requirements Doc" | 15 | Gen: PROJ-46, Val: PROJ-47, Rev: PROJ-48 | Matched |
| dbt Models | PROJ-50 "dbt Development" | 12 | Gen: PROJ-51, Val: PROJ-52 | Partial (missing Review) |
| Dashboards | PROJ-55 "Build Dashboards" | 8 | — | Partial (no sub-tasks) |
| Data Quality | — | — | — | No match |

### Summary
- **Matched**: [count] artifacts fully matched
- **Partial**: [count] artifacts partially matched
- **Unmatched**: [count] artifacts with no match
```

Then ask the user for confirmation using `AskUserQuestion`:

```json
{
  "questions": [{
    "question": "How would you like to proceed with this mapping?",
    "header": "Confirm Linking",
    "options": [
      {"label": "Accept all matches", "description": "Link matched issues and create new issues for anything unmatched or missing"},
      {"label": "Accept matches only", "description": "Link matched issues, skip unmatched artifacts (no new issues created)"},
      {"label": "Let me adjust", "description": "Walk through each artifact and specify which issue to link"},
      {"label": "Cancel", "description": "Don't set up Jira tracking"}
    ],
    "multiSelect": false
  }]
}
```

### Step 2D: Execute Linking

Based on the user's response:

**"Accept all matches":**
1. Record all matched issue keys (Epic, Tasks, Sub-tasks) for status.md
2. For **unmatched artifacts**: create new Tasks and Sub-tasks under the matched Epic (using the same creation logic from Steps 3 and 4). If no Epic was matched, create a new Epic first (using Step 2).
3. For **partial matches** (Task matched but some Sub-tasks missing): create only the missing Sub-tasks under the matched Task

**"Accept matches only":**
1. Record all matched issue keys for status.md
2. Leave unmatched artifacts with null keys in status.md (they can be linked or created later by re-running this utility)
3. For partial matches, record what was found and leave missing Sub-task keys as null

**"Let me adjust":**
For each in-scope artifact, ask the user directly in chat:
```
For [Artifact Display Name]:
- Suggested match: [PROJ-45] "[Summary]" (score: 15)
- Type a different issue key (e.g., PROJ-99) to link to that issue instead
- Type "skip" to leave unlinked
- Type "create" to create a new issue
```
For any manually specified issue key, fetch it with `getJiraIssue` to verify it exists and retrieve its Sub-tasks. Then apply Sub-task matching as in Step 2B.

**"Cancel":**
- Skip Jira integration entirely
- Continue to Step 10 of `/wire:new` (or exit if standalone)

### Step 2E: Add Linking Comments

For each **linked** issue (not newly created ones — those are handled by the creation path), add a comment to provide an audit trail in Jira:

**Comment on linked Epic:**
```
addCommentToJiraIssue:
  issueKey: "[epic_key]"
  body: |
    Linked to Wire Framework project: [project_name]
    Client: [client_name] | Type: [project_type]
    Local tracking: .wire/[folder_name]/status.md

    This Epic is now being tracked by the Wire Framework.
    Status updates will be synced automatically.
```

**Comment on each linked Task:**
```
addCommentToJiraIssue:
  issueKey: "[task_key]"
  body: |
    Linked to Wire Framework artifact: [Artifact Display Name]
    Project: [project_name]

    This task is now tracked by the Wire Framework.
    Sub-task transitions will be synced automatically.
```

Skip comments on newly created issues (they already have descriptions from the creation step).

### Step 2F: Proceed to Common Steps

After the linking workflow completes, proceed to:
- **Step 5** (Update status.md with Jira Keys) — same YAML structure as creation mode
- **Step 5.5** (Sync Existing Progress) — transitions linked issues to match current artifact states
- **Step 6** (Report Results) — uses the linking report format (see below)

**Linking report format** (used instead of the creation report when issues were linked):

```markdown
## Jira Issues Linked

**Epic**: [PROJ-123] "[Epic summary]"
**Linked**: [count] artifact tasks (from existing issues)
**Created**: [count] artifact tasks (new issues for unmatched artifacts)
**Sub-tasks linked**: [count]
**Sub-tasks created**: [count]

### Issue Hierarchy

| Artifact | Task | Source | Generate | Validate | Review |
|----------|------|--------|----------|----------|--------|
| Requirements | PROJ-45 | Linked | PROJ-46 (L) | PROJ-47 (L) | PROJ-48 (L) |
| dbt Models | PROJ-50 | Linked | PROJ-51 (L) | PROJ-52 (L) | PROJ-60 (C) |
| Data Quality | PROJ-61 | Created | PROJ-62 (C) | PROJ-63 (C) | PROJ-64 (C) |

**(L) = Linked to existing issue, (C) = Created new issue**

All issue keys have been recorded in status.md.
```

---

## Step 4.5: Sprint Assignment (Both Paths)

After creating or linking all Tasks and Sub-tasks, assign them to a sprint on the project's board.

### 4.5.1: Find the Board

Use the Atlassian MCP to find the board for this Jira project:

```
fetch:
  method: GET
  url: "/rest/agile/1.0/board?projectKeyOrId=[jira_project_key]"
```

Extract the first `boardId` from the response. If no board is found, log `"Note: No Jira board found for project [jira_project_key]. Skipping sprint assignment."` and proceed to Step 5.

### 4.5.2: Check for Existing Sprints

Query for active and future sprints on the board:

```
fetch:
  method: GET
  url: "/rest/agile/1.0/board/{boardId}/sprint?state=active,future"
```

### 4.5.3: Determine Sprint

- If an **active sprint** exists: use it (store `sprintId` and `sprint_name`)
- If no active sprint but a **future sprint** exists: use the future sprint (will be started in Step 4.5.5)
- If **no sprints** exist: create a new sprint:

```
jiraWrite:
  method: POST
  url: "/rest/agile/1.0/sprint"
  body:
    name: "[client_name] — [project_name]"
    boardId: [boardId]
    startDate: "[today ISO format]"
    endDate: "[today + 14 days ISO format]"
```

Store the returned `sprintId` and `sprint_name`.

### 4.5.4: Move Issues into Sprint

Move all Task-level issue keys into the sprint (Sub-tasks inherit from their parent):

```
jiraWrite:
  method: POST
  url: "/rest/agile/1.0/sprint/{sprintId}/issue"
  body:
    issues:
      - "[task_key_1]"
      - "[task_key_2]"
      - ...
```

### 4.5.5: Start Sprint (if not active)

If the sprint used in Step 4.5.3 is not already active (i.e., it was a future or newly created sprint), start it:

```
jiraWrite:
  method: POST
  url: "/rest/agile/1.0/sprint/{sprintId}"
  body:
    state: "active"
    startDate: "[today ISO format]"
    endDate: "[today + 14 days ISO format]"
```

### 4.5.6: Handle Edge Cases

- **Kanban board** (no sprints concept): Skip sprint assignment silently — issues will appear on the Kanban board automatically
- **Sprint API fails**: Log `"Note: Could not assign issues to sprint. Issues are created in backlog."` and continue — do not block the workflow
- **Board has multiple active sprints**: Use the most recently created active sprint

Store `sprint_name` for inclusion in the Step 6 report.

---

## Common Steps (Both Paths)

### Step 5: Update status.md with Jira Keys

Update the project's `status.md` YAML frontmatter with all created issue keys:

```yaml
jira:
  project_key: "PROJ"
  epic_key: "PROJ-123"
  artifacts:
    requirements:
      task_key: "PROJ-124"
      generate_key: "PROJ-125"
      validate_key: "PROJ-126"
      review_key: "PROJ-127"
    data_model:
      task_key: "PROJ-128"
      generate_key: "PROJ-129"
      validate_key: "PROJ-130"
      review_key: "PROJ-131"
    # ... (all in-scope artifacts)
```

For out-of-scope artifacts, omit them from the jira.artifacts section entirely.

### Step 5.5: Sync Existing Progress (Mid-Project Only)

If this utility is running on a project that already has progress (i.e., some artifacts have `generate: complete`, `validate: pass`, or `review: approved`):

1. After writing Jira keys to status.md, call the full reconciliation workflow in `specs/utils/jira_status_sync.md`
2. This transitions all Sub-tasks to match the existing local artifact states
3. For example, if requirements are already generated and validated, the `Generate: Requirements` and `Validate: Requirements` Sub-tasks will be transitioned to "Done"

This ensures the Jira board immediately reflects the project's actual state rather than showing all Sub-tasks as "To Do".

### Step 6: Report Results

**Output**:

```markdown
## Jira Issues Created

**Epic**: [PROJ-123] [client_name] - [project_name] Data Platform
**Tasks**: [count] artifact tasks
**Sub-tasks**: [count] lifecycle step sub-tasks
**Sprint**: [sprint_name] ([active/started])

### Issue Hierarchy

| Artifact | Task | Generate | Validate | Review |
|----------|------|----------|----------|--------|
| Requirements | PROJ-124 | PROJ-125 | PROJ-126 | PROJ-127 |
| Data Model | PROJ-128 | PROJ-129 | PROJ-130 | PROJ-131 |
| ... | ... | ... | ... | ... |

All issue keys have been recorded in status.md.
```

### Step 7: Handle Edge Cases

**Atlassian MCP not available:**
```
Note: Could not connect to Jira (Atlassian MCP server not configured).
Skipping Jira issue creation. You can create issues later by running:
/wire:utils-jira-create [folder]
```

**Epic creation fails:**
```
Error: Failed to create Jira Epic. Check that:
- Project key "[key]" exists in Jira
- You have permission to create issues
- The Epic issue type is available in this project

Skipping Jira issue creation. Project created without Jira tracking.
```

**Partial creation failure:**
If some Tasks or Sub-tasks fail to create:
1. Record successfully created issue keys in status.md
2. Report which issues failed
3. Suggest manual creation or retry

**Jira already configured:**
If `status.md` already has a `jira.epic_key`:
```
Jira tracking is already configured for this project.

Epic: [PROJ-123] - [project_name]

Do you want to:
1. Keep existing Jira tracking (no changes)
2. Replace with new Jira issues (create from scratch)
3. Re-link to different existing issues (search again)
```

**Linking-specific edge cases:**

**No issues found in project:**
```
No existing issues found in Jira project [KEY].

Would you like to create new issues instead?
```
If yes, switch to the creation workflow (Step 2 onwards).

**No active sprint:**
- Fall back to searching all non-Done issues (Query 3)
- Note: "No active sprint found. Searching all open issues."

**Ambiguous matches (multiple issues score equally for one artifact):**
Present the top 2-3 candidates to the user:
```
Multiple possible matches for [Artifact]:
1. [PROJ-45] "Requirements Document" (score: 12)
2. [PROJ-50] "Project Requirements" (score: 12)
3. None of these — create new

Which one?
```

**Issues already in "Done" state:**
- Matched issues in "Done" status are still linkable
- Show the current Jira status in the confirmation table so the user can decide
- The `jira_status_sync.md` workflow handles state mapping correctly regardless of current issue state

**Jira uses "Story" instead of "Task":**
- The JQL queries search both: `issuetype in (Task, Story)`
- Stories are treated as Task equivalents for matching purposes

In all cases, project creation continues — Jira tracking is optional and additive.

## Output

This utility:
- **Create mode**: Creates Jira Epic + Tasks + Sub-tasks for the project
- **Link mode**: Searches existing Jira issues, matches them to framework artifacts, and links to them (creating only what's missing)
- Updates `status.md` with all issue keys (same format regardless of mode)
- If run mid-project, syncs existing artifact progress to linked/created issues
- Reports the issue hierarchy with linked vs created indicators
- Fails gracefully if Jira is unavailable
- Can be run at any point in the project lifecycle

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
