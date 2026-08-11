---
description: Auto-delegation protocol for seed_data-generate and data_refactor-generate — dispatch to mock-data-developer subagent when available
---

# Mock Data Developer Auto-Delegation

Before executing the seed_data or data_refactor generate workflow inline, check whether the `wire:mock-data-developer` agent definition is available.

## Protocol

### Step 1: Check for agent definition

Look for `agents/mock-data-developer/AGENT.md` in the Wire plugin directory. The typical paths to check:
- `.claude/plugins/wire/agents/mock-data-developer/AGENT.md`
- `agents/mock-data-developer/AGENT.md`

### Step 2: Check execution context

Skip delegation if any of the following are true:
- The agent definition file is not found
- This instance is already running as a `wire:mock-data-developer` subagent (check the system prompt or context for this indicator — if in doubt, proceed inline to avoid infinite loops)
- The `--inline` flag was passed as part of the command arguments

### Step 3: Dispatch to specialist agent

If the agent definition exists and the above skip conditions are not met, spawn a `wire:mock-data-developer` subagent using the Agent tool with:
- `subagent_type`: `wire:mock-data-developer:AGENT`
- Prompt: include the release folder argument (`$ARGUMENTS`), the specific command being run (`seed_data-generate` or `data_refactor-generate`), and the key input paths — status.md, viz catalog CSV, dashboard specification, and data model specification
- Do not execute the workflow steps below — the subagent handles them

Then return immediately. The subagent will complete the work and update `status.md`.

### Step 4: Inline fallback

If delegation was skipped (agent not found or already in a subagent context), proceed with the workflow steps below as normal.
