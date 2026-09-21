---
description: Auto-delegation protocol for semantic layer and dashboard generate commands — dispatch to Semantic Layer Developer subagent when available
---

# Semantic Layer Developer Auto-Delegation

Before executing any semantic layer and dashboard generate command inline, check whether the `wire:semantic-layer-developer` agent definition is available.

## Protocol

### Step 1: Check for agent definition

Look for `agents/semantic-layer-developer/AGENT.md` in the Wire plugin directory. The typical paths to check:
- `.claude/plugins/wire/agents/semantic-layer-developer/AGENT.md`
- `agents/semantic-layer-developer/AGENT.md`

### Step 2: Check execution context

Skip delegation if any of the following are true:
- The agent definition file is not found
- This instance is already running as a `wire:semantic-layer-developer` subagent (check the system prompt or context for this indicator — if in doubt, proceed inline to avoid infinite loops)
- The `--inline` flag was passed as part of the command arguments

### Step 3: Dispatch to specialist agent

If the agent definition exists and the above skip conditions are not met, spawn a `wire:semantic-layer-developer` subagent using the Agent tool with:
- `subagent_type`: `wire:semantic-layer-developer:AGENT`
- Prompt: include the release folder argument (`$ARGUMENTS`), the specific command being run, and the key input file paths from this spec's **Inputs** section
- Do not execute the workflow steps below — the subagent handles them

Then return immediately. The subagent will complete the work and update `status.md`.

### Step 3b: `bi_migration` batches

`omni-model-generate` and `omni-content-generate` on a `bi_migration` release follow this protocol with one addition: when the command is run without `--batch` (or with `--all`) and the plan has more than one pending batch, spawn one `wire:semantic-layer-developer` subagent per pending batch, each receiving `--batch <id>`, all in parallel, each writing only under its own `migration/omni_model/<batch>/` or `migration/omni_content/<batch>/` tree. Under the release director model each subagent is a lane and follows the lane contract in `specs/utils/director_operating_model.md`; the orchestrating session writes `status.md` after reading each lane's state file.

### Step 4: Inline fallback

If delegation was skipped (agent not found or already in a subagent context), proceed with the workflow steps below as normal.
