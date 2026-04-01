---
description: Agent-based autonomous engagement execution — spawns worker agents per artifact for isolation, recovery, and parallelism
argument-hint: [path-to-sow]
---

# Agent-based autonomous engagement execution — spawns worker agents per artifact for isolation, recovery, and parallelism

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.4.6\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"autopilot-orchestrated\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.4.6\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Agent-based autonomous engagement execution — orchestrator that spawns worker agents per artifact
argument-hint: <path-to-sow>
---

# Wire Autopilot (Orchestrated) — Agent-Based Engagement Execution

## Purpose

This is the agent-based evolution of Wire Autopilot. Instead of running the entire engagement as one monolithic conversation, this orchestrator spawns **worker agents** for each artifact's generate→validate→self-review cycle.

**Benefits over monolithic autopilot:**
- **Context isolation**: Each worker agent starts fresh with only the context it needs
- **Recovery**: If a worker fails, the orchestrator can re-spawn it without replaying the whole conversation
- **Parallelism**: Independent artifacts can be executed by concurrent agents
- **Checkpointing**: The orchestrator tracks progress in `autopilot_checkpoint.md` and can resume from any point

**Shared state**: This orchestrator uses the same `status.md` and `autopilot_checkpoint.md` files as the monolithic autopilot (`autopilot.md`). A user can switch between orchestrated and monolithic mode at any point.

## When to Use

- **Use this spec** (`autopilot_orchestrated`) for engagements with multiple delivery releases or complex release types (`full_platform`, `dashboard_first`)
- **Use `autopilot.md`** for single-release engagements or when the user prefers monolithic execution
- Both specs can resume from the other's checkpoint — they are interchangeable at any pause point

---

# Phase 1: Clarifying Questions (Interactive)

Phase 1 is identical to `autopilot.md` Phase 1. The orchestrator runs this directly — no agents needed.

Follow `autopilot.md` Steps 1.1 through 1.6 exactly:
1. SOW file path
2. Engagement details (client name, engagement name, lead)
3. Repo mode (combined vs dedicated)
4. Issue tracker integration (Jira / Linear / Both / None)
5. Document store integration (Confluence / Notion / Both / None)
6. Additional context
7. Confirm, launch, and request permissions

**One addition to Step 1.6**: When presenting the execution plan, add this note:

```
## Execution Mode: Agent-Based (Orchestrated)

Each artifact will be generated by an independent worker agent.
- Artifacts with no dependencies on each other will run in parallel
- Safety gates still require your explicit confirmation
- Progress is checkpointed after every artifact
- You can stop and resume at any time
```

---

# Phase 2: Engagement Setup (Direct)

Phase 2 is identical to `autopilot.md` Phase 2. The orchestrator runs this directly.

Follow `autopilot.md` Steps 2.1 through 2.7 exactly:
1. Git branch
2. Create two-tier folder structure
3. Copy SOW and supporting docs
4. Create engagement context file
5. Create discovery release status file
6. Issue tracker setup
7. Initialize autopilot checkpoint

**One addition to Step 2.7**: Add a `## Context Digest` section to `autopilot_checkpoint.md` (empty, to be populated by workers):

```markdown
## Context Digest

(populated as artifacts are completed)
```

---

# Phase 3: Discovery Sprint (Agent-Based)

The discovery sprint executes four artifacts sequentially. Each is spawned as a worker agent. Discovery artifacts are sequential because each depends on the prior one.

## Step 3.0: Read Templates

Before spawning any workers, read:
1. `wire/specs/utils/agent_worker.md` — the worker prompt template
2. `wire/specs/utils/dependency_graph.md` — for reference
3. `wire/specs/utils/context_digest.md` — for digest rules

Store the template in memory for the remainder of the orchestration.

## Step 3.1: Problem Definition Agent

**Build the worker prompt** by substituting into the agent_worker.md template:

| Variable | Value |
|----------|-------|
| `{artifact_name}` | `problem_definition` |
| `{release_folder}` | `01-discovery` |
| `{release_type}` | `discovery` |
| `{spec_path}` | `discovery/problem_definition/generate.md` |
| `{condensed_context}` | Engagement context only (SOW summary, client, technology, data sources from `## Key Context` in checkpoint) |
| `{output_file_path}` | `planning/problem_definition.md` |

**Additional instructions to append to the prompt**:
```
## Discovery-Specific Instructions

This is a discovery artifact. The input is the SOW and engagement context,
not prior Wire artifacts.

Read these files as your primary inputs:
- .wire/engagement/sow.md (or .pdf)
- .wire/engagement/context.md
- Any files in .wire/engagement/ (supporting docs)

Follow the generation process in specs/discovery/problem_definition/generate.md.
Write output to: .wire/releases/01-discovery/planning/problem_definition.md
```

**Spawn the agent** using the Agent tool:
```
Agent(
  description: "Generate problem definition",
  prompt: [assembled prompt],
  subagent_type: "general-purpose"
)
```

**After the agent returns**:
1. Parse the `## Worker Result` block from the agent's response
2. If `status: approved`:
   - Build a context digest entry following `context_digest.md` rules for `problem_definition`
   - Read the first 50 lines of `.wire/releases/01-discovery/planning/problem_definition.md` to extract key details
   - Append the digest entry to `## Context Digest` in `autopilot_checkpoint.md`
   - Update `## Completed Phases` in checkpoint
   - Report progress to the user
3. If `status: validate_failed` or `status: review_failed`:
   - Log the blocked reason in checkpoint
   - Report the failure to the user
   - Ask whether to retry, skip, or stop

## Step 3.2: Pitch Agent

**Build the worker prompt** — same process as 3.1 with:

| Variable | Value |
|----------|-------|
| `{artifact_name}` | `pitch` |
| `{spec_path}` | `discovery/pitch/generate.md` |
| `{condensed_context}` | Engagement key context + problem_definition digest entry |
| `{output_file_path}` | `planning/pitch.md` |

**Additional instructions**:
```
## Discovery-Specific Instructions

Read the problem definition as your primary upstream input:
- .wire/releases/01-discovery/planning/problem_definition.md
- .wire/engagement/sow.md (for SOW details not in the problem definition)

Follow specs/discovery/pitch/generate.md.
Write output to: .wire/releases/01-discovery/planning/pitch.md
```

**Spawn, process result, update digest** — same pattern as 3.1.

## Step 3.3: Release Brief Agent

| Variable | Value |
|----------|-------|
| `{artifact_name}` | `release_brief` |
| `{spec_path}` | `discovery/release_brief/generate.md` |
| `{condensed_context}` | Engagement key context + problem_definition digest (first line) + pitch digest (full) |
| `{output_file_path}` | `planning/release_brief.md` |

**Additional instructions**:
```
## Discovery-Specific Instructions

Read the pitch as your primary upstream input:
- .wire/releases/01-discovery/planning/pitch.md
- .wire/engagement/sow.md
- .wire/engagement/context.md

Follow specs/discovery/release_brief/generate.md.
Write output to: .wire/releases/01-discovery/planning/release_brief.md
```

## Step 3.4: Sprint Plan Agent

| Variable | Value |
|----------|-------|
| `{artifact_name}` | `sprint_plan` |
| `{spec_path}` | `discovery/sprint_plan/generate.md` |
| `{condensed_context}` | Engagement key context + pitch digest (first line) + release_brief digest (full) |
| `{output_file_path}` | `planning/sprint_plan.md` |

**Additional instructions**:
```
## Discovery-Specific Instructions

Read the release brief as your primary upstream input:
- .wire/releases/01-discovery/planning/release_brief.md
- .wire/releases/01-discovery/planning/pitch.md (for appetite and scope details)

Follow specs/discovery/sprint_plan/generate.md.
Write output to: .wire/releases/01-discovery/planning/sprint_plan.md

IMPORTANT: The sprint plan MUST include a "Downstream Releases" table at the end.
This table is parsed by the orchestrator to determine which delivery releases to create.
```

## Step 3.5: Parse Downstream Releases

After the sprint plan agent returns successfully:

1. Read `.wire/releases/01-discovery/planning/sprint_plan.md`
2. Parse the "Downstream Releases" table to extract: `release_name`, `release_type`, `scope_summary`
3. Store as `planned_releases` list
4. Update `autopilot_checkpoint.md`:
   ```markdown
   ## Delivery Releases to Execute
   | Release | Type | Scope |
   |---------|------|-------|
   | [name] | [type] | [scope] |
   ```

## Step 3.6: Discovery Commit

```bash
git add .wire/releases/01-discovery/ .wire/engagement/ .wire/autopilot_checkpoint.md
git commit -m "Wire Autopilot (orchestrated): discovery sprint complete

Client: {client_name}
Engagement: {engagement_name}
Artifacts: problem_definition, pitch, release_brief, sprint_plan
Mode: agent-based orchestration"
```

Report:
```
--- Discovery Sprint Complete ---
Artifacts: 4/4 approved
Downstream releases planned: [list]
Committed: [hash]
---
```

---

# Phase 4: Delivery Release Execution (Agent-Based)

## Step 4.0: Confirm Release Plan

Same as `autopilot.md` Step 4.0 — present the planned releases and ask whether to proceed, review, or stop.

## Step 4.1: For Each Delivery Release

For each release in `planned_releases`, execute Steps 4.2 through 4.6.

### Step 4.2: Create Release Folder

Same as `autopilot.md` Step 4.2 — create folder structure, status.md, and checkpoint entry. The orchestrator runs this directly (no agent needed — it's just mkdir and file writes).

### Step 4.3: Execute Artifact Graph

This is the core orchestration loop. Instead of running artifacts in a fixed sequence, the orchestrator uses the dependency graph.

**Algorithm**:

```
current_release = the release being executed
release_type = the release type (from status.md)

LOOP:
  1. Read .wire/releases/{current_release}/status.md
  2. Read wire/specs/utils/dependency_graph.md to get the graph for release_type
  3. Find all artifacts where:
     - All upstream dependencies have review: approved
     - This artifact's generate is NOT complete (or is failed and retryable)
  4. If no artifacts are ready:
     - If all artifacts are approved → release is complete, exit loop
     - If some artifacts are blocked → release is partially complete, report and exit loop
  5. Separate ready artifacts into:
     - safety_gated: those in the safety gate list
     - parallel_group: those that can run concurrently (same dependency level)
  6. For each safety_gated artifact:
     - Present safety gate (same as autopilot.md Safety Gates section)
     - If user says "Stop here" → commit and exit
     - If user says "Review first" → show all files, wait for "continue"
     - If user says "Proceed" → add to parallel_group
  7. Spawn worker agents for all artifacts in parallel_group:
     - Build each worker prompt using agent_worker.md template
     - Select condensed_context using context_digest.md rules
     - Spawn all agents concurrently using the Agent tool
  8. Wait for all spawned agents to return
  9. For each returned agent:
     - Parse Worker Result
     - Build context digest entry (if approved)
     - Update autopilot_checkpoint.md
     - Report progress
  10. GOTO LOOP
```

**Building the worker prompt for delivery artifacts**:

For each artifact, substitute into the agent_worker.md template:

| Variable | Source |
|----------|--------|
| `{artifact_name}` | The artifact being generated |
| `{release_folder}` | Current release folder name |
| `{release_type}` | From status.md |
| `{spec_path}` | Mapped from artifact name (see Spec Path Mapping below) |
| `{condensed_context}` | Built per context_digest.md — only upstream dependency digests |
| `{client_name}` | From engagement context |
| `{engagement_name}` | From engagement context |
| `{target_platform}` | From engagement context |
| `{output_file_path}` | From the spec's Output section |
| `{jira_sync_instructions}` | Jira block from agent_worker.md if configured, else "skip" block |
| `{linear_sync_instructions}` | Linear block if configured, else "skip" block |
| `{docstore_sync_instructions}` | Docstore block if configured, else "skip" block |

**Spec Path Mapping**:

| Artifact | Spec Path |
|----------|-----------|
| `requirements` | `requirements/generate.md` |
| `workshops` | `design/workshops_generate.md` |
| `conceptual_model` | `design/conceptual_model/generate.md` |
| `pipeline_design` | `design/pipeline_design/generate.md` |
| `data_model` | `design/data_model/generate.md` |
| `mockups` | `design/mockups/generate.md` |
| `viz_catalog` | `design/viz_catalog/generate.md` |
| `seed_data` | `development/seed_data/generate.md` |
| `pipeline` | `development/pipeline/generate.md` |
| `dbt` | `development/dbt_generate.md` |
| `semantic_layer` | `development/semantic_layer/generate.md` |
| `dashboards` | `development/dashboards/generate.md` |
| `data_refactor` | `development/data_refactor/generate.md` |
| `data_quality` | `testing/data_quality/generate.md` |
| `uat` | `testing/uat/generate.md` |
| `deployment` | `deployment/generate.md` |
| `training` | `enablement/training_generate.md` |
| `documentation` | `enablement/documentation/generate.md` |

**Spawning parallel agents**:

When multiple artifacts are ready simultaneously, spawn them all in a single message using multiple Agent tool calls:

```
# Example: conceptual_model, pipeline_design, and mockups all ready

Agent(
  description: "Generate conceptual model",
  prompt: [conceptual_model prompt],
  subagent_type: "general-purpose"
)
Agent(
  description: "Generate pipeline design",
  prompt: [pipeline_design prompt],
  subagent_type: "general-purpose"
)
Agent(
  description: "Generate mockups",
  prompt: [mockups prompt],
  subagent_type: "general-purpose"
)
```

All three agents execute concurrently. The orchestrator waits for all to return before re-evaluating the dependency graph.

### Step 4.4: Release Resumption

If the orchestrator is invoked and a release has partially completed artifacts:

1. Read `status.md` — identify which artifacts are already approved
2. The dependency graph algorithm (Step 4.3) naturally handles this: it finds the next ready artifacts by checking what's approved and what's not
3. No special resumption logic needed — the graph-driven loop is inherently resumable

### Step 4.5: Commit After Each Release

After the artifact graph loop exits (all artifacts approved or blocked):

```bash
git add .wire/releases/{current_release}/ dbt/ 2>/dev/null; git add -u; true
```

If changes exist:
```bash
git commit -m "Wire Autopilot (orchestrated): {engagement_name} — {current_release} ({current_type}) complete

Client: {client_name}
Release: {current_release}
Type: {current_type}
Artifacts: {comma-separated list of completed artifacts}
Mode: agent-based orchestration"
```

Update checkpoint and report progress.

### Step 4.6: Move to Next Release

After committing, advance to the next release in `planned_releases` and repeat from Step 4.2.

---

# Phase 5: Final Commit, Push, and Pull Request

Identical to `autopilot.md` Phase 5, with one PR body change:

Add to the PR body:
```
**Execution mode**: Agent-based orchestration
```

---

# Phase 6: Final Summary

Identical to `autopilot.md` Phase 6, with one addition:

After the overall statistics, add:

```
### Agent Execution Summary
- Total worker agents spawned: [count]
- Parallel batches: [count of times multiple agents ran concurrently]
- Average validation cycles per artifact: [mean]
- Blocked artifacts: [count]
```

---

# Resumption Protocol

The orchestrator can resume from any point by reading the checkpoint:

1. Read `.wire/autopilot_checkpoint.md`
2. Check `## Current Phase`:
   - If `engagement_setup: complete` but no discovery artifacts → start Phase 3
   - If discovery partially done → resume Phase 3 from the first incomplete artifact
   - If discovery complete → check `## Delivery Releases to Execute`
3. For delivery releases:
   - Read each release's `status.md`
   - Find the first release with incomplete artifacts
   - Enter the artifact graph loop (Step 4.3) for that release
4. The orchestrator re-reads the context digest from the checkpoint to rebuild `condensed_context` for workers

**Cross-mode resumption**: Because this orchestrator uses the same checkpoint and status files as `autopilot.md`, a user who started with the monolithic autopilot can resume with the orchestrated version (and vice versa) at any pause point.

---

# Error Handling

## Worker Agent Failure

If a worker agent fails entirely (crashes, times out, returns no parseable result):

1. Check `status.md` to see if the worker updated status before failing
2. If status was updated to `validate: fail` or `review: changes_requested` → treat as a normal blocked artifact
3. If status was NOT updated (worker died mid-execution):
   - Reset the artifact in status.md to its pre-execution state
   - Log the failure in checkpoint: `### {artifact_name} (AGENT FAILED) — [error details]`
   - Ask the user: retry with a new agent, skip this artifact, or stop

## Partial File Writes

If a worker agent wrote some but not all expected files:

1. Check which files exist at the expected output paths
2. If the primary output file exists and status.md shows `generate: complete`:
   - Proceed with validation (the worker may have failed during validate/review)
   - Spawn a new worker with instructions to "validate and review only" (skip generate)
3. If the primary output file doesn't exist:
   - Reset and retry from scratch

## Blocked Artifact Cascade

When an artifact is blocked, all downstream artifacts in the dependency graph become unreachable. The orchestrator:

1. Identifies all transitively blocked artifacts
2. Reports the full impact to the user
3. Offers options: retry the blocked artifact, skip it (mark downstream as skipped), or stop

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
