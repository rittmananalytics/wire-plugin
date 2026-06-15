---
description: Auto-delegation protocol for migration generate commands — dispatch to migration-specialist subagent when available
argument-hint: (internal — called by migration generate commands)
---

# Auto-delegation protocol for migration generate commands — dispatch to migration-specialist subagent when available

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
mkdir -p ~/.wire && WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]') && echo "$WIRE_UID" > ~/.wire/telemetry_id && curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"3.9.6\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1 &
```

### If the file exists:

The identity is already established. Proceed to Step 2.

## Step 2: Send Track Event

Run this single Bash command. Execute it exactly as written — do not split it, do not wait for output, and proceed immediately to the Workflow Specification:

```bash
WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo "unknown") && curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"utils-migration-agent-delegate\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"3.9.6\",\"os\":\"$(uname -s)\",\"runtime\":\"claude\",\"autopilot\":\"false\"}}" > /dev/null 2>&1 &
```

## Rules

1. **Never block** — the curl runs in background (`&`) with all output suppressed
2. **Never fail the workflow** — if any part of telemetry fails (no network, no curl, no python3), silently continue to the Workflow Specification
3. **Execute as a single Bash command** — do not split into multiple Bash calls
4. **Do not inspect the result** — fire and forget
5. **Proceed immediately** — after running the Bash command, continue to the Workflow Specification without waiting

## Workflow Specification

---
description: Auto-delegation protocol for migration generate commands — dispatch to migration-specialist subagents when available
---

# Migration Agent Auto-Delegation

Before executing any migration generate command inline, check whether the `wire:migration-specialist` agent definition is available.

## Protocol

### Step 1: Check for agent definition

Look for `agents/migration-specialist/AGENT.md` in the Wire plugin directory. The typical paths to check:
- `.claude/plugins/wire/agents/migration-specialist/AGENT.md`
- `agents/migration-specialist/AGENT.md`

### Step 2: Check execution context

Skip delegation if any of the following are true:
- The agent definition file is not found
- This instance is already running as a `wire:migration-specialist` subagent (check the system prompt or context for this indicator — if in doubt, proceed inline to avoid infinite loops)
- The `--inline` flag was passed as part of the command arguments

### Step 3: Dispatch to specialist agent(s)

If the agent definition exists and the above skip conditions are not met, determine how many agents to spawn:

#### For `dbt-migration-generate` (parallel dispatch within and across batches)

**Model group size**: 5 models per agent (adjust down to 3 for Complex-rated models; up to 8 for Simple-only groups).

1. Read `dbt_audit.csv` to identify all distinct `batch_number` values and the models in each batch.

2. If `--model <name>` or `--models <list>` was passed: spawn a **single** `wire:migration-specialist` agent for that exact set.

3. If `--batch N` was passed: load all models with `batch_number = N`. Split them into groups of the model group size (above). Spawn **one `wire:migration-specialist` agent per group**, all in parallel, each receiving `--batch N --models <group_list>`. Wait for all group agents to complete, then write the combined `batch_{N}_summary.md`.

4. If no flag was passed: identify all pending batches (not in `dbt_migration.batches_complete`). For each pending batch, split models into groups as in step 3. Spawn **all group agents across all pending batches simultaneously** — one agent per model group, all batches at once. Each agent receives `--batch N --models <group_list>`. Wait for all agents to complete, then write per-batch summaries and update top-level status.

   Each agent operates on a distinct set of models and writes to separate output paths — there are no write conflicts.

   Example: 3 pending batches of 20 models each, group size 5 → 12 agents spawned simultaneously.

#### For all other migration generate commands

Spawn a **single** `wire:migration-specialist` subagent with:
- `subagent_type`: `wire:migration-specialist:AGENT`
- Prompt: release folder argument (`$ARGUMENTS`), the specific command being run, and the key input file paths from this spec's **Inputs** section

Do not execute the workflow steps below — the subagent handles them.

Then return immediately. The subagent will complete the work and update `status.md`.

### Step 4: Inline fallback

If delegation was skipped (agent not found or already in a subagent context), proceed with the workflow steps below as normal.

Execute the complete workflow as specified above.
