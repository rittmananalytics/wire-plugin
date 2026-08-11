---
description: Auto-delegation protocol for deployment, documentation, and enablement generate commands — dispatch to Delivery Lead subagent when available
---

# Delivery Lead Auto-Delegation

Before executing any deployment, documentation, and enablement generate command inline, check whether the `wire:delivery-lead` agent definition is available.

## Protocol

### Step 1: Check for agent definition

Look for `agents/delivery-lead/AGENT.md` in the Wire plugin directory. The typical paths to check:
- `.claude/plugins/wire/agents/delivery-lead/AGENT.md`
- `agents/delivery-lead/AGENT.md`

### Step 2: Check execution context

Skip delegation if any of the following are true:
- The agent definition file is not found
- This instance is already running as a `wire:delivery-lead` subagent (check the system prompt or context for this indicator — if in doubt, proceed inline to avoid infinite loops)
- The `--inline` flag was passed as part of the command arguments

### Step 3: Dispatch to specialist agent

If the agent definition exists and the above skip conditions are not met, spawn a `wire:delivery-lead` subagent using the Agent tool with:
- `subagent_type`: `wire:delivery-lead:AGENT`
- Prompt: include the release folder argument (`$ARGUMENTS`), the specific command being run, and the key input file paths from this spec's **Inputs** section
- Do not execute the workflow steps below — the subagent handles them

Then return immediately. The subagent will complete the work and update `status.md`.

### Step 4: Inline fallback

If delegation was skipped (agent not found or already in a subagent context), proceed with the workflow steps below as normal.
