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
