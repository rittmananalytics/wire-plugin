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
   if [ "${WIRE_TELEMETRY:-true}" != "false" ]; then WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"ARTIFACT_NAME-generate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"4.6.9\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"invoked_by\":\"autopilot\",\"autopilot_release\":\"{current_release}\",\"autopilot_artifact\":\"ARTIFACT_NAME\"}}" > /dev/null 2>&1 & fi
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
