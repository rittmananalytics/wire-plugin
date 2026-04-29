---
description: Autonomous end-to-end engagement execution from SOW — discovery sprint then all delivery releases
argument-hint: [path-to-sow]
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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.10\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"autopilot\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.10\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Autonomous end-to-end engagement execution from SOW — discovery sprint + all delivery releases
argument-hint: <path-to-sow>
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
(e.g., "Acme Corporation", "Power Digital")
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

The discovery sprint runs the full Shape Up planning cycle autonomously. All four artifacts are generated, validated, and self-approved without human intervention. Autopilot makes all planning decisions from the SOW and supporting material.

## Step 3.1: Problem Definition

**Inputs**: `.wire/engagement/sow.md`, `.wire/engagement/context.md`, supporting docs
**Output**: `.wire/releases/01-discovery/planning/problem_definition.md`

**Autonomous generation process**:

1. Read all engagement context (SOW, context.md, supporting docs, additional_context)
2. Extract answers to the seven problem-framing questions directly from the source material:
   - **Who has the problem**: Identify the primary stakeholder role(s) from the SOW
   - **What they're trying to do**: Extract the job-to-be-done (not the solution)
   - **What's in the way**: Extract the friction, gap, or current-state pain points
   - **Current workarounds**: Infer from SOW's "as-is" description or context
   - **What "solved" looks like**: Extract desired outcomes and success criteria
   - **Constraints**: Extract budget ceiling, timeline, technology constraints, compliance
   - **Previously ruled out**: Extract any exclusions, assumptions, or "out of scope" clauses
3. Generate the full 10-section problem_definition document following the structure in `specs/discovery/problem_definition/generate.md`
4. Where information is genuinely absent from source material, write "[To confirm with client]" — do not fabricate

**Validate**:
- [ ] All 10 sections populated (sections with no source data marked "[To confirm]")
- [ ] Constraints section has budget/timeline/technology entries
- [ ] "What solved looks like" is outcome-oriented (not solution-prescribing)
- [ ] Impact table completed with current vs desired state

**Self-approve** if all validate checks pass. Update status.md:
```yaml
problem_definition:
  generate: "complete"
  validate: "pass"
  review: "approved"
  reviewed_by: "Wire Autopilot (self-review)"
  reviewed_date: [today]
  file: "planning/problem_definition.md"
```

**Self-review criteria**:
1. Problem is framed without prescribing a solution
2. Stakeholders are specific (not "the business" or "users")
3. SOW deliverables trace to the problem statement
4. Constraints are concrete, not abstract

**Document store sync**: If `docstore_provider` is set, follow `specs/utils/docstore_sync.md` to publish `planning/problem_definition.md` to the configured store. Fail gracefully — do not block if the sync fails.

Report:
```
--- Discovery: Problem Definition ---
Status: approved (self-reviewed)
File: .wire/releases/01-discovery/planning/problem_definition.md
---
```

## Step 3.2: Pitch

**Input**: `planning/problem_definition.md`
**Output**: `planning/pitch.md`

**Autonomous generation process**:

Generate the 10-section Shape Up pitch. Make all shaping decisions autonomously from the source material:

1. **Appetite**: Infer from SOW timeline —
   - 6+ weeks stated duration → Big batch (6 weeks)
   - 2–3 weeks → Small batch (1–2 weeks)
   - Ambiguous → Default to Big batch
2. **Problem statement**: Condense from problem_definition Section 3
3. **Appetite statement**: State the time budget and what that means for scope
4. **Solution**: Shape the core solution element — the one thing that, if done, solves the problem. Base on SOW deliverables. Use fat-marker description (rough but solved). Document trade-offs and autonomous decisions.
5. **Rabbit holes**: Identify 3–5 specific things to avoid based on SOW scope boundaries and constraints
6. **No-gos**: Extract explicitly out-of-scope items from SOW
7. **Open questions**: List 3–5 questions that need client confirmation before delivery starts
8. **Downstream releases**: Based on SOW deliverables and appetite, propose delivery release types:
   - Map each SOW deliverable category to the appropriate release type
   - Order releases logically (data-first before dashboards, etc.)
   - Assign a name and type to each (e.g., `02-data-foundation: pipeline_only`, `03-reporting: dashboard_extension`)
9. **Betting table case**: 2–3 bullet points making the case for proceeding
10. **Metrics for success**: Extract from SOW acceptance criteria or success criteria

Generate the pitch document following the full structure in `specs/discovery/pitch/generate.md`.

**Validate**:
- [ ] All 10 pitch sections populated
- [ ] Appetite defined (small/big batch)
- [ ] At least one downstream release identified in Section 8
- [ ] Rabbit holes list has at least 3 items
- [ ] No-gos list populated from SOW out-of-scope

**Self-approve** if validate passes. Update status.md:
```yaml
pitch:
  generate: "complete"
  validate: "pass"
  review: "approved"
  reviewed_by: "Wire Autopilot (self-review)"
  reviewed_date: [today]
  file: "planning/pitch.md"
```

**Self-review criteria**:
1. Solution is shaped — rough but solved, not open-ended
2. Appetite is fixed — not adjusted to fit the solution
3. Downstream releases are typed and named
4. Rabbit holes are concrete things (not abstract risks)

**Document store sync**: If `docstore_provider` is set, follow `specs/utils/docstore_sync.md` to publish `planning/pitch.md` to the configured store. Fail gracefully — do not block if the sync fails.

Report:
```
--- Discovery: Pitch ---
Status: approved (self-reviewed)
Downstream releases identified: [list]
File: .wire/releases/01-discovery/planning/pitch.md
---
```

## Step 3.3: Release Brief

**Input**: `planning/pitch.md`, `engagement/context.md`, `engagement/sow.md`
**Output**: `planning/release_brief.md`

**Autonomous generation process**:

Generate the formal 12-section release brief following the structure in `specs/discovery/release_brief/generate.md`. Make all content decisions from the pitch and SOW:

1. Extract deliverables from pitch Sections 3 (solution) and 8 (downstream releases)
2. Define acceptance criteria from SOW success criteria and pitch metrics
3. Extract budget from SOW contract terms
4. Populate downstream releases table from pitch Section 8 — this is the authoritative list of delivery releases to spawn
5. Mark sign-off block as "[Signature required before sprint plan]"

**Validate**:
- [ ] Deliverables table has at least one row with acceptance criteria
- [ ] Downstream releases table populated from pitch Section 8
- [ ] Timeline section populated (even if "TBD — to confirm with client")
- [ ] Out-of-scope section matches pitch no-gos

**Self-approve** if validate passes. Update status.md:
```yaml
release_brief:
  generate: "complete"
  validate: "pass"
  review: "approved"
  reviewed_by: "Wire Autopilot (self-review)"
  reviewed_date: [today]
  file: "planning/release_brief.md"
```

**Document store sync**: If `docstore_provider` is set, follow `specs/utils/docstore_sync.md` to publish `planning/release_brief.md` to the configured store. Fail gracefully — do not block if the sync fails.

Report:
```
--- Discovery: Release Brief ---
Status: approved (self-reviewed)
Delivery releases planned: [list from Section 4]
File: .wire/releases/01-discovery/planning/release_brief.md
---
```

## Step 3.4: Sprint Plan

**Input**: `planning/release_brief.md`, `planning/pitch.md`
**Output**: `planning/sprint_plan.md`

**Autonomous generation process**:

Generate the sprint plan following `specs/discovery/sprint_plan/generate.md`. Make all planning decisions autonomously:

1. Determine sprint length from appetite (small batch → 1 sprint, big batch → 3–5 sprints of ~1 week)
2. For each deliverable in the release brief, generate epics
3. For each epic, generate stories with Fibonacci point estimates (1/2/3/5/8 — no 13-point stories)
4. Assign each story to a sprint
5. Include a "Downstream Releases" table at the end — this is the canonical list of delivery releases that Phase 4 will execute:

   | Release Name | Type | Scope Summary | Priority |
   |---|---|---|---|
   | [e.g. 02-data-foundation] | [e.g. pipeline_only] | [1-line scope] | 1 |

**Velocity assumption**: 5 points per consultant day. Include buffer of 20%.

**Validate**:
- [ ] All release_brief deliverables have epics
- [ ] No story exceeds 8 points
- [ ] Point totals add up correctly
- [ ] Downstream Releases table has at least one row with name and type
- [ ] Every release type in the table is a valid Wire release type: full_platform, pipeline_only, dbt_development, dashboard_extension, dashboard_first, enablement

**Self-approve** if validate passes. Update status.md:
```yaml
sprint_plan:
  generate: "complete"
  validate: "pass"
  review: "approved"
  reviewed_by: "Wire Autopilot (self-review)"
  reviewed_date: [today]
  file: "planning/sprint_plan.md"
```

**Document store sync**: If `docstore_provider` is set, follow `specs/utils/docstore_sync.md` to publish `planning/sprint_plan.md` to the configured store. Fail gracefully — do not block if the sync fails.

Report:
```
--- Discovery: Sprint Plan ---
Status: approved (self-reviewed)
Total: [X] points across [N] sprints
Downstream releases to execute:
  [list with name and type]
File: .wire/releases/01-discovery/planning/sprint_plan.md
---
```

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
      {"label": "Stop here", "description": "End Autopilot — I will run delivery releases manually using /wire:session:start"}
    ],
    "multiSelect": false
  }]
}
```

- **Yes, execute all**: Proceed to Step 4.1
- **Review first**: Output paths to all discovery artifacts and wait for user to say "continue"
- **Stop here**: Jump to Phase 5 (commit + push) and Phase 6 (final summary)

## Step 4.1: For Each Delivery Release

Repeat steps 4.2–4.6 for each release in `planned_releases`.

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

Set artifact scope based on `current_type` (see Artifact Scope Reference at the end of this spec).

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
Artifact sequence: [ordered list for this type]
---
```

### Step 4.3: Run the Artifact Execution Loop

Execute the artifact sequence for `current_type`. All artifact paths use `.wire/releases/{current_release}/` as the release root. In the Per-Artifact Execution Blocks below, `{folder_name}` means `releases/{current_release}`.

**Artifact sequences by release type**:

**full_platform**: requirements → workshops → conceptual_model → pipeline_design → data_model → mockups → pipeline → dbt → semantic_layer → dashboards → data_quality → uat → deployment → training → documentation

**pipeline_only**: requirements → pipeline_design → pipeline → data_quality → deployment

**dbt_development**: requirements → data_model → dbt → semantic_layer → data_quality → deployment

**dashboard_extension**: requirements → mockups → dashboards → training

**dashboard_first**: requirements → mockups → viz_catalog → data_model → seed_data → dbt → semantic_layer → dashboards → data_refactor → data_quality → uat → deployment → training → documentation

**enablement**: training → documentation

For each artifact in the sequence, execute the Execution Loop (see Execution Loop section):

1. **Check status**: Read `.wire/releases/{current_release}/status.md`. If this artifact's generate state is already `complete` and review state is `approved`, skip it.

2. **Safety gate check**: If this artifact is in the safety-gated list (`pipeline`, `data_refactor`, `data_quality`, `deployment`), execute the Safety Gate protocol before proceeding.

3. **Generate**: Execute the generate logic for this artifact (see Per-Artifact Blocks below).
   - Update status.md: set `generate: complete`, `generated_date: [today]`
   - Log to `.wire/releases/{current_release}/execution_log.md`
   - **Jira sync**: If Jira is configured, sync — artifact=[artifact_name], action=generate, status=complete
   - **Linear sync**: If Linear is configured, sync — same artifact and action
   - **Document store sync**: If `docstore_provider` is set, follow `specs/utils/docstore_sync.md` to publish the generated artifact file. Fail gracefully — do not block.

4. **Validate**: Execute validation checks.
   - Pass → Update status.md: `validate: pass`
   - Fail → Re-generate (max 3 cycles); if still failing after 3 cycles, set `validate: fail`, log as blocked
   - Log to execution_log.md
   - **Jira sync**: sync validate result
   - **Linear sync**: If Linear is configured, sync validate result

5. **Self-Review**: Execute self-review criteria.
   - Approved → Update status.md: `review: approved`, `reviewed_by: "Wire Autopilot (self-review)"`
   - Issues found → Re-generate and re-validate (max 2 review cycles)
   - Still failing → set `review: changes_requested`, log as blocked
   - **Jira sync**: sync review result
   - **Linear sync**: If Linear is configured, sync review result
   - **Document store sync**: If approved and `docstore_provider` is set, re-sync the artifact to the store to reflect any revisions made during review cycles. Fail gracefully.

6. **Update checkpoint**: Move artifact to "Completed Phases" in autopilot_checkpoint.md with brief summary and any key context discovered.

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
   if [ "${WIRE_TELEMETRY:-true}" != "false" ]; then WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ARTIFACT_NAME-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.0\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"true\",\"autopilot_release\":\"{current_release}\",\"autopilot_artifact\":\"ARTIFACT_NAME\"}}" > /dev/null 2>&1 & fi
   ```
   Replace `ARTIFACT_NAME` with the actual artifact name. Do not wait for the result.

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
   /wire:session:start releases/[release_name]
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

# Per-Artifact Execution Blocks

Each block describes the generate, validate, and self-review logic for one artifact type.

In all path references below, `{folder_name}` means `releases/{current_release}` — the currently executing delivery release folder.

---

## ARTIFACT: requirements

### Generate

**Input**: SOW/documents in `.wire/{folder_name}/artifacts/`, `engagement/sow.md`, `engagement/context.md`
**Output**: `.wire/{folder_name}/requirements/requirements_specification.md`

**Process**:
1. Read all documents in `engagement/` and the release's `artifacts/` folder
2. Read the approved discovery artifacts: `releases/01-discovery/planning/release_brief.md`, `releases/01-discovery/planning/sprint_plan.md`
3. Extract and structure into a requirements specification with these sections:
   - **Executive Summary**: 2–3 paragraph overview
   - **Business Context**: Client background, problem statement, strategic goals, success criteria (from problem_definition)
   - **Stakeholders**: Table with name, role, department, involvement level
   - **Functional Requirements**: Numbered list (FR-001, FR-002, etc.) with description and acceptance criteria
   - **Non-Functional Requirements**: Performance, security, availability, scalability
   - **Data Requirements**: Source systems table (name, type, owner, volume, refresh frequency)
   - **Technical Requirements**: Platform, tools, environments, constraints
   - **Deliverables**: Table mapping SOW deliverables to Wire artifacts with acceptance criteria
   - **Timeline**: Milestones with dates (from sprint plan where available)
   - **Assumptions and Dependencies**
   - **Risks and Mitigations**: Table with risk, impact, likelihood, mitigation
   - **Scope Management**: In-scope, out-of-scope, change process (from discovery no-gos)
4. Write to `.wire/{folder_name}/requirements/requirements_specification.md`

### Validate

**Checks** (all must pass):
- [ ] Executive summary present and non-empty
- [ ] At least 3 functional requirements with acceptance criteria
- [ ] Non-functional requirements defined
- [ ] All data sources identified with owners
- [ ] All SOW deliverables documented
- [ ] Each deliverable has clear acceptance criteria
- [ ] Timeline with milestones
- [ ] Stakeholder roles defined
- [ ] Out-of-scope items documented
- [ ] Dependencies and assumptions documented

### Self-Review

**Criteria**:
1. **SOW Traceability**: Every deliverable in the SOW maps to at least one requirement
2. **Discovery Alignment**: Requirements are consistent with the problem_definition and pitch
3. **No Fabrication**: All requirements are traceable to the SOW or discovery artifacts — nothing invented
4. **Clarity**: Each functional requirement has testable acceptance criteria
5. **Consistency**: Requirements do not contradict each other

---

## ARTIFACT: workshops

### Generate

**Input**: `.wire/{folder_name}/requirements/requirements_specification.md`
**Output**: `.wire/{folder_name}/design/workshop_agenda.md`, `.wire/{folder_name}/design/workshop_decision_matrix.md`

**Process**:
1. Parse requirements for `[NEEDS CLARIFICATION]` markers, TBD items, ambiguities
2. Categorize by topic: requirements, data, technical, timeline, scope
3. Generate workshop agenda with parts: requirements clarification (45 min), data source details (30 min), technical approach (30 min), wrap-up (15 min)
4. Create decision matrix template: topic, options, decision, rationale, owner

### Validate

No specific validation checks.

### Self-Review

**Criteria**:
1. All ambiguities from requirements are addressed in workshop topics
2. Workshop agenda covers all TBD items
3. Decision matrix includes all open questions
4. **Autopilot Decision**: Since no actual workshop is conducted, auto-approve the workshop materials as reference documentation. Mark as `review: approved` with note: "Workshop materials generated as reference — no workshop conducted in Autopilot mode"

---

## ARTIFACT: conceptual_model

### Generate

**Input**: `.wire/{folder_name}/requirements/requirements_specification.md`, engagement artifacts for source schemas
**Output**: `.wire/{folder_name}/design/conceptual_model.md`

**Process**:
1. Extract business entities from requirements: nouns, deliverables, reporting subjects
2. For each entity: name (PascalCase), description, key attributes (3–6), approximate volume
3. Define relationships with verb phrases and cardinality
4. Generate Mermaid erDiagram (entity-only, no column definitions)
5. Include relationship narratives explaining business meaning
6. Section for entities out of scope
7. Section for open questions

### Validate

**Checks**:
- [ ] Every business noun in Functional Requirements is represented or explicitly out-of-scope
- [ ] Every relationship has valid cardinality markers at both ends
- [ ] Every relationship has a quoted label
- [ ] No `{}` column definitions in erDiagram (entity-only format)
- [ ] Mermaid syntax valid
- [ ] All entity names are singular PascalCase
- [ ] Each entity has description and at least 2 key business attributes
- [ ] At least one sentence per relationship narrative

### Self-Review

**Criteria**:
1. **Requirements Coverage**: All business entities from functional requirements are present
2. **Relationship Accuracy**: Cardinalities reflect real business rules
3. **No Orphans**: Every entity participates in at least one relationship
4. **SOW Alignment**: Model scope matches SOW scope
5. **Domain Language**: Entity names use client terminology from the SOW

---

## ARTIFACT: pipeline_design

### Generate

**Input**: `.wire/{folder_name}/requirements/requirements_specification.md`, `design/conceptual_model.md`, engagement artifacts for schemas
**Output**: `.wire/{folder_name}/design/pipeline_architecture.md`

**Process**:
1. Analyze each source system: technology, schema, volume, availability, sensitivity
2. Cross-reference against conceptual model entities — flag data gaps
3. Define replication strategy per source (full refresh, incremental, CDC, API, batch)
4. Specify pipeline architecture: landing/raw naming, staging layer (`stg_<source>__<entity>`), warehouse layer, error handling, scheduling
5. Generate Mermaid Data Flow Diagram: sources → ingestion → staging → warehouse → BI
6. Document design decisions with rationale
7. Include technology stack table and security/governance section
8. **Autonomous Decision**: Choose the most practical replication strategy based on SOW constraints and document the rationale

### Validate

**Checks**:
- [ ] Every source system from requirements appears in source analysis
- [ ] Every source has a replication method specified
- [ ] All staging models follow `stg_<source>__<entity>` naming
- [ ] All warehouse models follow `<entity>_fct` or `<entity>_dim` naming
- [ ] Error handling specified
- [ ] Scheduling defined with refresh cadences
- [ ] Technology stack complete
- [ ] DFD present with valid Mermaid syntax
- [ ] Every source system appears in DFD
- [ ] DFD uses subgraph blocks for layers
- [ ] PII handling addressed

### Self-Review

**Criteria**:
1. **Source Coverage**: All data sources from requirements are addressed
2. **Architecture Coherence**: Pipeline flows logically from source to warehouse
3. **Design Decisions Justified**: Each choice has a documented rationale
4. **DFD Completeness**: Diagram matches the written architecture
5. **Feasibility**: Chosen technologies and strategies are compatible with SOW constraints

---

## ARTIFACT: data_model

### Generate

**Input**:
- Default: `requirements/requirements_specification.md`, `design/conceptual_model.md`, `design/pipeline_architecture.md`
- dashboard_first: `requirements/requirements_specification.md`, `design/visualization_catalog.md`
**Output**: `.wire/{folder_name}/design/data_model_specification.md`, (dashboard_first also: `design/source_tables_ddl.sql`, `design/target_warehouse_ddl.sql`)

**Process**:
1. Define source definitions with freshness thresholds
2. Design staging models: `stg_<source>__<entity>`, view materialization, surrogate key composition, column renames, derived columns, tests
3. Design integration models: `int__<subject>__<description>`, ephemeral/view, for cross-system joins
4. Design warehouse models:
   - Fact tables: `<entity>_fct`, grain, surrogate key, foreign keys, measures
   - Dimension tables: `<entity>_dim`, SCD Type 1 or 2
   - Aggregates: `<subject>_<grain>`, pre-aggregated measures
5. Specify seed files for configurable business logic
6. Generate physical ERD as Mermaid erDiagram with all warehouse models, columns, PKs, FKs
7. Document cross-system join keys
8. Define dbt test coverage plan
9. **For dashboard_first**: Additionally generate `source_tables_ddl.sql` and `target_warehouse_ddl.sql`

### Validate

**Checks**:
- [ ] Staging follows `stg_<source>__<entity>` with double underscore
- [ ] Warehouse facts use `<entity>_fct`, dimensions use `<entity>_dim`
- [ ] Surrogate keys follow `<entity>_pk`, foreign keys follow `<entity>_fk`
- [ ] All columns in snake_case
- [ ] Every conceptual entity appears as a warehouse model
- [ ] Every model has a grain statement
- [ ] Every model has a surrogate key
- [ ] Every FK references a defined PK in another model
- [ ] Minimum tests: `not_null(pk)` and `unique(pk)` on all models
- [ ] FK columns have `relationships` tests
- [ ] ERD present with valid Mermaid erDiagram syntax
- [ ] PKs marked `PK`, FKs marked `FK` in ERD

### Self-Review

**Criteria**:
1. **Entity Coverage**: All conceptual model entities are represented
2. **Grain Correctness**: Each fact table has a clearly defined, appropriate grain
3. **FK/PK Consistency**: All foreign key references resolve to valid primary keys
4. **Naming Conventions**: Consistent naming throughout
5. **Test Coverage**: Adequate tests defined for data integrity
6. **ERD Accuracy**: ERD matches the written specifications

---

## ARTIFACT: mockups

### Generate

**Input**: `.wire/{folder_name}/requirements/requirements_specification.md`
**Output**: `.wire/{folder_name}/design/mockups/` directory + `design/mockups/mockups_index.md`

**Process** (Wireframe Mode — used in Autopilot):
1. Identify dashboards/screens from requirements
2. For each dashboard, generate an ASCII wireframe mockup showing layout, chart placeholders, filter bar, data labels
3. Create `mockup_[dashboard_name].md` for each with: title, purpose, audience, wireframe, data requirements table, filters, interactions
4. Create `mockups_index.md` linking all mockups

### Validate

No specific validation checks.

### Self-Review

**Criteria**:
1. **Requirements Coverage**: Every functional requirement that implies a visualization is addressed
2. **Data Traceability**: Each chart references specific measures and dimensions
3. **Layout Clarity**: Wireframes are readable and show logical organization
4. **Audience Appropriateness**: Executive dashboards differ from operational dashboards

---

## ARTIFACT: viz_catalog (dashboard_first only)

### Generate

**Input**: `design/dashboard_visualization_catalog.csv`, `design/dashboard_spec.md`, `requirements/requirements_specification.md`
**Output**: `.wire/{folder_name}/design/visualization_catalog.md`

**Process**:
1. Parse CSV: map dashboard page → visualization → chart type → measures/dimensions
2. Parse dashboard_spec.md: extract purposes, layout, filters, interactions
3. Cross-reference with requirements for coverage analysis
4. Generate structured catalog with summary, per-dashboard breakdown, measures/dimensions indices, requirements coverage, gaps

### Validate

No specific validate step.

### Self-Review

**Criteria**:
1. **CSV Fidelity**: All rows from the CSV are represented
2. **Requirements Coverage**: >80% of relevant requirements addressed
3. **Measure/Dimension Consistency**: Names consistent across visualizations
4. **Gaps Identified**: Uncovered requirements called out

---

## ARTIFACT: seed_data (dashboard_first only)

### Generate

**Input**: `design/source_tables_ddl.sql`, `design/target_warehouse_ddl.sql`, `design/visualization_catalog.md`
**Output**: `.wire/{folder_name}/dev/seed_data/*.csv` files + `dev/seed_data/README.md`

**Process**:
1. Parse both DDL files: extract table names, columns, types, PKs, FKs
2. Read visualization catalog to identify which measures need non-zero values
3. Build dependency graph: dimensions before facts
4. For each source table in dependency order, generate CSV with realistic domain-appropriate data
5. Create README.md with overview, files table, dependency order, FK relationships, dbt seed config snippet

### Validate

**Checks**:
- [ ] Every CSV parses without errors
- [ ] Header rows match expected columns from DDL
- [ ] No empty files (at least 1 data row)
- [ ] No duplicate values in PK columns
- [ ] No NULL values in PK columns
- [ ] Every FK value exists in referenced parent table PK
- [ ] Date columns contain valid dates (YYYY-MM-DD)
- [ ] Numeric columns contain valid numbers
- [ ] Fact tables have variation in measure columns

### Self-Review

**Criteria**:
1. **Referential Integrity**: All FK→PK relationships hold
2. **Realistic Data**: Values are domain-appropriate and varied
3. **Sufficient Volume**: Enough rows for meaningful dashboard visualizations
4. **DDL Alignment**: Column names and types match the DDL specifications

---

## ARTIFACT: pipeline

### Generate

**Input**: `requirements/requirements_specification.md`, `design/pipeline_architecture.md`
**Output**: Pipeline code and configuration in `.wire/{folder_name}/dev/pipeline/`

**Process**:
1. Read pipeline architecture for source definitions and replication strategy
2. Generate pipeline configuration for the specified technology (Fivetran, Airbyte, custom Python)
3. Generate orchestration config (Airflow DAGs, Cloud Composer, cron)
4. Generate error handling and monitoring setup
5. Create pipeline documentation

### Validate

**Checks**:
- [ ] Pipeline configuration files are syntactically valid
- [ ] All source systems from pipeline_design are addressed
- [ ] Scheduling cadences match pipeline_design specifications
- [ ] Error handling is configured

### Self-Review

**Criteria**:
1. **Architecture Alignment**: Pipeline code matches the pipeline design
2. **Source Coverage**: All sources from the design are implemented
3. **Error Handling**: Failure scenarios are covered
4. **Documentation**: Pipeline is documented for operations

---

## ARTIFACT: dbt

### Generate

**Input**: `.wire/{folder_name}/design/data_model_specification.md`, dbt conventions (if found)
**Output**: dbt models in the repository's `dbt/` directory (NOT inside `.wire/`). The only dbt-related output inside the release folder is `.wire/{folder_name}/dev/dbt_models_summary.md`.

**Process**:
1. Check for project-specific dbt conventions file
2. Determine dbt project location: check if `dbt/` exists in the repository root. If yes, use it. If not, create it.
3. Generate staging models in `dbt/models/staging/<source_system>/`:
   - `stg_<source>__<entity>.sql` — source() calls, surrogate keys, renames, filters
   - `_sources.yml` per source system with freshness
   - `stg_<source_system>.yml` — model docs and tests
   - Materialized as view
4. Generate integration models in `dbt/models/integration/`:
   - `int__<entity>.sql` — one per entity, consolidating staging inputs
   - `int__<entity>__<description>.sql` — optional intermediate models
   - **Always create integration models**, even if simple pass-throughs
5. Generate warehouse models in `dbt/models/warehouse/core/`:
   - `<entity>_dim.sql` — dimensions with SCD handling
   - `<entity>_fct.sql` — facts with measures, FKs
   - `<entity>_agg.sql` — pre-aggregated tables if needed
   - Table materialization
6. Generate schema.yml files with model descriptions, column descriptions, and tests
7. Generate `dbt/dbt_project.yml` if new project
8. **For dashboard_first with seed data**: Generate seed-based source definitions using `ref('seed_name')` instead of `source()` in staging models
9. Create `.wire/{folder_name}/dev/dbt_models_summary.md` with model counts, test coverage, and directory listing

**SQL Standards**:
- 4-space indentation, max 80 char lines
- All CTEs from refs/sources prefixed with `s_`
- Final CTE always named `final`, ending with `select * from final`
- Lowercase field names and functions
- Explicit join types (inner join, left join)
- Field ordering: keys, dates, attributes, metrics, metadata

### Validate

**Checks — Naming**:
- [ ] Staging: `stg_<source>__<entity>.sql`
- [ ] Integration: `int__<object>.sql` or `int__<object>__<action>.sql`
- [ ] Dimensions: `<object>_dim.sql`
- [ ] Facts: `<object>_fct.sql`
- [ ] PKs: `<object>_pk`, FKs: `<referenced_object>_fk`
- [ ] Timestamps: `<event>_ts`, Booleans: `is_`/`has_`
- [ ] All snake_case, singular names

**Checks — SQL Structure**:
- [ ] All ref/source in top CTEs with `s_` prefix
- [ ] Final CTE present with `select * from final`
- [ ] 4-space indentation
- [ ] Explicit join types (not bare `join`)
- [ ] `as` keyword used for all aliases

**Checks — Testing**:
- [ ] Every model appears in schema.yml
- [ ] Every PK has `unique` and `not_null` tests
- [ ] FK columns have `relationships` tests
- [ ] Enum/status fields have `accepted_values` tests

**Checks — Documentation**:
- [ ] All staging models and columns documented
- [ ] All warehouse models and columns documented
- [ ] Column descriptions use business terminology

**Checks — Architecture Completeness**:
- [ ] Integration layer exists: at least one `int__*.sql` file is present
- [ ] Every warehouse model references an integration model via `ref('int__...')`
- [ ] Every staging entity that feeds a warehouse model has a corresponding integration model

**Checks — Directory Structure**:
- [ ] All staging models in `dbt/models/staging/<source_system>/`
- [ ] All integration models in `dbt/models/integration/`
- [ ] All warehouse models in `dbt/models/warehouse/core/`
- [ ] No `.sql` model files inside `.wire/` (documentation only goes there)
- [ ] `dbt/dbt_project.yml` exists

### Self-Review

**Criteria**:
1. **Model Coverage**: Every model in the data_model specification has a corresponding SQL file
2. **SQL Quality**: Code follows conventions, CTEs are well-structured
3. **Test Coverage**: All PKs, FKs, and critical fields have tests
4. **Documentation**: All models and columns have business-friendly descriptions
5. **Seed/Source Correctness**: Source definitions match the data sources
6. **Architecture**: All three layers present (staging → integration → warehouse)

---

## ARTIFACT: semantic_layer

### Generate

**Input**: `requirements/requirements_specification.md`, `design/data_model_specification.md`, dbt schema.yml files
**Output**: LookML view files, model file updates, validation summary

**Process**:
1. Read requirements to understand business goals and measures
2. Examine existing LookML project structure (if any) for conventions
3. Map data types: STRING→string, INT64→number, DATE→time, TIMESTAMP→time, BOOLEAN→yesno
4. For each warehouse model, create a LookML view:
   - Primary key (hidden: yes)
   - Dimensions: string, time (dimension_group), numeric, yesno, derived
   - Measures: count, sum, average, count_distinct with value_format_name
   - Drill fields and groups/labels
5. Define explores with joins: relationship, join type, sql_on
6. Validate syntax: balanced braces, `;;` after SQL, type on all dimensions
7. Update model file with new explores
8. Create LookML summary document

### Validate

**Checks**:
- [ ] Balanced braces in all files
- [ ] SQL blocks end with `;;`
- [ ] Every dimension has `type:` specified
- [ ] All use `${TABLE}.column` syntax
- [ ] Primary keys defined with `primary_key: yes`
- [ ] Labels are business-friendly
- [ ] Explores have `relationship:` defined
- [ ] Numeric measures have `value_format_name`
- [ ] Dates use `dimension_group` with timeframes

### Self-Review

**Criteria**:
1. **Model Coverage**: All warehouse models are represented as LookML views
2. **Measure Completeness**: All measures from requirements/data model are exposed
3. **Business Language**: Labels and descriptions use business terminology
4. **Explore Design**: Joins correctly reflect the data model relationships
5. **Syntax Validity**: All files would parse without errors

---

## ARTIFACT: dashboards

### Generate

**Input**: `requirements/requirements_specification.md`, `design/mockups/` or `design/visualization_catalog.md`, semantic layer definitions
**Output**: Dashboard specification files in `.wire/{folder_name}/dev/dashboards/`

**Process**:
1. Read mockups/visualization catalog to identify all dashboards and their visualizations
2. Map each visualization to semantic layer fields (explores, dimensions, measures)
3. Generate LookML dashboard files (or Looker dashboard specs) for each dashboard
4. Generate dashboard documentation: purpose, audience, key metrics, navigation guide
5. Create dashboard summary with tile counts and field references

### Validate

**Checks**:
- [ ] Every mockup/catalog visualization has a corresponding dashboard element
- [ ] All field references exist in the semantic layer
- [ ] Dashboard filters reference valid dimensions
- [ ] Layout is complete

### Self-Review

**Criteria**:
1. **Visualization Coverage**: All mockup/catalog visualizations are implemented
2. **Field Accuracy**: All field references resolve to semantic layer definitions
3. **Requirements Alignment**: Dashboards address the functional requirements
4. **Usability**: Logical dashboard organization with appropriate filters

---

## ARTIFACT: data_refactor (dashboard_first only)

### Generate

**Input**: `design/source_tables_ddl.sql` (seed version), real data access or revised DDL
**Output**: `.wire/{folder_name}/design/data_refactor_plan.md`, updated dbt files

**Process**:
1. **Autonomous Decision**: Generate the refactoring plan based on seed DDL and document what changes are needed when real data is available
2. Compare seed-based DDL against expected real source schemas (from SOW/requirements)
3. Generate refactoring plan: schema comparison, table-by-table analysis, dbt configuration changes, staging model updates
4. If real data access is available, execute the refactoring immediately

### Validate

**Checks** (if plan only):
- [ ] Refactoring plan covers all seed-to-source mappings
- [ ] Column mapping differences are documented
- [ ] Impact assessment is complete

### Self-Review

**Criteria**:
1. **Mapping Completeness**: Every seed table has a corresponding real source mapping
2. **Plan Clarity**: Steps are clear enough for manual execution if needed
3. **No Regressions**: Warehouse models and tests would continue to work after refactoring
4. **Seed Preservation**: Seed files are explicitly preserved as reference

---

## ARTIFACT: data_quality

### Generate

**Input**: `requirements/requirements_specification.md`, dbt models, data model specification
**Output**: Data quality test files and monitoring configuration in `.wire/{folder_name}/test/`

**Process**:
1. Read requirements for data quality expectations
2. Analyze dbt models for testable assertions
3. Generate data quality tests: freshness, row count, business rule, cross-table consistency, anomaly detection
4. Generate monitoring configuration
5. Create data quality documentation

### Validate

**Checks**:
- [ ] Tests cover all critical data quality dimensions: freshness, completeness, consistency, accuracy
- [ ] All source systems have freshness tests
- [ ] Business rules from requirements are codified as tests
- [ ] Test documentation is complete

### Self-Review

**Criteria**:
1. **Requirements Coverage**: Data quality requirements from the SOW are addressed
2. **Test Adequacy**: Critical business rules have corresponding tests
3. **Monitoring**: Alert thresholds are reasonable
4. **Documentation**: Test purposes are clearly documented

---

## ARTIFACT: uat

### Generate

**Input**: `requirements/requirements_specification.md`, dashboard specs, dbt models
**Output**: `.wire/{folder_name}/test/uat_plan.md`

**Process**:
1. Read requirements and deliverables with acceptance criteria
2. For each deliverable, generate test scenarios with: test case ID, description, prerequisites, test steps, expected results, pass/fail criteria
3. Create UAT plan with overview, test environment setup, test cases by deliverable, sign-off template, issue tracking process

### Validate

No specific validate checks.

### Self-Review

**Criteria**:
1. **Deliverable Coverage**: Every SOW deliverable has at least one test case
2. **Testability**: Each test case has clear, measurable pass/fail criteria
3. **Completeness**: UAT covers functional, non-functional, and integration aspects

---

## ARTIFACT: deployment

### Generate

**Input**: All completed development artifacts, requirements
**Output**: `.wire/{folder_name}/deploy/deployment_runbook.md`, deployment scripts

**Process**:
1. Identify all components to deploy: dbt models, pipelines, dashboards, semantic layer
2. Generate deployment runbook:
   - Pre-deployment checklist
   - Deployment steps in order (with commands)
   - Post-deployment verification
   - Rollback procedure
   - Communication plan
   - **dbt deployment section** (if dbt generated): reference actual file paths in `dbt/models/` and include commands:
     ```
     cd dbt && dbt deps
     dbt run --select staging
     dbt run --select integration
     dbt run --select warehouse
     dbt test
     ```
3. Generate deployment scripts if applicable
4. Create production configuration files

### Validate

**Checks**:
- [ ] All project components are covered
- [ ] Rollback procedure is defined
- [ ] Pre/post-deployment verification steps are clear
- [ ] Deployment order handles dependencies
- [ ] If dbt models exist: runbook references actual file paths in `dbt/models/`
- [ ] If dbt models exist: runbook includes `dbt run` and `dbt test` with correct working directory

### Self-Review

**Criteria**:
1. **Component Coverage**: All deliverables are included in the deployment plan
2. **Rollback Safety**: Rollback procedure would restore previous state
3. **Verification**: Post-deployment checks would confirm successful deployment
4. **Clarity**: Steps are specific enough for someone unfamiliar to execute

---

## ARTIFACT: training

### Generate

**Input**: `requirements/requirements_specification.md`, dbt models, dashboards, semantic layer
**Output**: Training materials in `.wire/{folder_name}/enablement/`:
- `training_[type]_session_plan.md`
- `training_[type]_slides.md` (Marp format)
- `training_[type]_exercises.md`
- `training_[type]_quick_reference.md`
- `training_delivery_checklist.md`

**Process**:
1. Determine training types from SOW deliverables (data team, BI developer, end user, admin)
2. For each type, generate session plan, slides, exercises, and quick reference
3. Create delivery checklist: pre-session, during session, post-session tasks

### Validate

**Checks**:
- [ ] All deliverable-related training types are covered
- [ ] Session plans have learning objectives and exercises
- [ ] Exercises reference actual project artifacts (real model names, dashboard names)
- [ ] Quick reference covers common tasks

### Self-Review

**Criteria**:
1. **Audience Appropriateness**: Content level matches the target audience
2. **Coverage**: All delivered features are covered in training
3. **Practical Exercises**: Exercises use real project artifacts and scenarios
4. **Completeness**: All required training types from SOW are included

---

## ARTIFACT: documentation

### Generate

**Input**: All project artifacts (requirements, design, development, deployment)
**Output**: Documentation in `.wire/{folder_name}/enablement/documentation/`:
- `architecture_guide.md`
- `operations_guide.md`
- `user_guide.md`
- `glossary.md`

**Process**:
1. Read all completed project artifacts
2. Generate documentation suite:
   - **Architecture Guide**: System overview, data flow, component descriptions, technology stack, design decisions
   - **Operations Guide**: Monitoring, troubleshooting, common issues, runbooks, SLA management
   - **User Guide**: Dashboard navigation, report interpretation, FAQ, getting help
   - **Glossary**: Business terms, technical terms, metrics definitions
3. Cross-reference against requirements to ensure completeness

### Validate

**Checks**:
- [ ] Architecture guide covers all system components
- [ ] Operations guide includes troubleshooting for common scenarios
- [ ] User guide covers all delivered dashboards/reports
- [ ] Glossary includes all business and technical terms used in the project

### Self-Review

**Criteria**:
1. **Completeness**: All aspects of the delivered solution are documented
2. **Accuracy**: Documentation reflects the actual implementation
3. **Accessibility**: Written for the target audience
4. **Cross-References**: Documents link to each other appropriately

---

# Artifact Scope Reference

## full_platform
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
workshops: {generate: not_started, review: not_started}
conceptual_model: {generate: not_started, validate: not_started, review: not_started}
pipeline_design: {generate: not_started, validate: not_started, review: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
pipeline: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
uat: {generate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
```

## pipeline_only
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
pipeline_design: {generate: not_started, validate: not_started, review: not_started}
pipeline: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

## dbt_development
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

## dashboard_extension
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
```

## dashboard_first
```yaml
requirements: {generate: not_started, validate: not_started, review: not_started}
mockups: {generate: not_started, review: not_started}
viz_catalog: {generate: not_started}
data_model: {generate: not_started, validate: not_started, review: not_started}
seed_data: {generate: not_started, validate: not_started, review: not_started}
dbt: {generate: not_started, validate: not_started, review: not_started}
semantic_layer: {generate: not_started, validate: not_started, review: not_started}
dashboards: {generate: not_started, validate: not_started, review: not_started}
data_refactor: {generate: not_started, validate: not_started, review: not_started}
data_quality: {generate: not_started, validate: not_started, review: not_started}
uat: {generate: not_started, review: not_started}
deployment: {generate: not_started, validate: not_started, review: not_started}
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
# workshops, conceptual_model, pipeline_design, pipeline: not_applicable
```

## enablement
```yaml
training: {generate: not_started, validate: not_started, review: not_started}
documentation: {generate: not_started, validate: not_started, review: not_started}
# All others: not_applicable
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
