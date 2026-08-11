---
description: Auto-delegation protocol for mockups-generate on dashboard_first projects — dispatch to dashboard-mock-developer subagent when available
---

# Dashboard Mock Developer Auto-Delegation

Before executing the mockups generate workflow inline, check whether the `wire:dashboard-mock-developer` agent definition is available.

## Protocol

### Step 1: Check for agent definition

Look for `agents/dashboard-mock-developer/AGENT.md` in the Wire plugin directory. The typical paths to check:
- `.claude/plugins/wire/agents/dashboard-mock-developer/AGENT.md`
- `agents/dashboard-mock-developer/AGENT.md`

### Step 2: Check execution context

Skip delegation if any of the following are true:
- The agent definition file is not found
- This instance is already running as a `wire:dashboard-mock-developer` subagent (check the system prompt or context for this indicator — if in doubt, proceed inline to avoid infinite loops)
- The `--inline` flag was passed as part of the command arguments
- The project type is not `dashboard_first` (standard-mode mockups run inline)

### Step 3: Dispatch to specialist agent

If the agent definition exists and the above skip conditions are not met, spawn a `wire:dashboard-mock-developer` subagent using the Agent tool with:
- `subagent_type`: `wire:dashboard-mock-developer:AGENT`
- Prompt: include the release folder argument (`$ARGUMENTS`), the command being run (`mockups-generate`), and the key input paths — status.md, requirements specification, and any SOW or source materials in the artifacts folder
- Do not execute the workflow steps below — the subagent handles them

Then return immediately. The subagent will complete the mockups, write the viz catalog CSV and dashboard specification, and update `status.md`.

### Step 4: Inline fallback

If delegation was skipped (agent not found, already in a subagent context, or non-dashboard_first project), proceed with the workflow steps below as normal.
