---
name: Engagement Context
description: Automatically loads Wire engagement and release context at the start of a conversation. Fires when a .wire/ directory is present and context has not yet been established in the current session.
triggers:
  - Any message in a repository containing a .wire/ directory where engagement context has not yet been loaded
  - User begins discussing an engagement, release, or artifact without prior context in the conversation
  - User asks what to work on next, what the current status is, or what release is active
---

# Engagement Context Skill

## On Activation

Before proceeding with any work, append a one-line entry to `.wire/execution_log.md` (at engagement root, or within the active release if no engagement-root log exists):

```
| YYYY-MM-DD HH:MM | skill | engagement-context | activated | Context loaded for new conversation |
```

If `.wire/execution_log.md` does not exist, create it with the standard header first.

## When This Skill Activates

This skill fires automatically at the **start of a conversation** in any repository that contains a `.wire/` directory, when the agent has not yet established engagement context. It is the replacement for the deprecated `/wire:session:start` command — context loading is now implicit, not explicit.

Do NOT fire this skill if:
- You have already read and summarised the engagement context earlier in this conversation
- The user's message is clearly not Wire-related (e.g. they are asking about something unrelated to the engagement)

## Context Loading Procedure

### Step 1: Locate the Active Release

Check `.wire/releases/*/status.md` (two-tier layout) or `.wire/*/status.md` (legacy layout). Sort by last modified; use the most recently modified.

If multiple releases exist, note them all. Use the most recently modified as the active release for the context summary.

### Step 2: Read Engagement Context

Read `.wire/engagement/context.md` if present. Extract:
- Client name and engagement overview
- Business objectives
- Key stakeholders
- Current engagement state (which releases exist, which are active/completed)

### Step 3: Read Release State

Read the active release `status.md`. Extract:
- Release name, type, and current phase
- Artifact completion state (what is done, in progress, blocked)
- Last 3 rows of session history (what was done recently and what the suggested next focus is)
- Any blockers

### Step 4: Surface Context Summary

Output a brief, scannable context block before responding to the user's request:

```
## Wire Engagement Context

**Client**: [client_name] | **Release**: [release_name] ([release_type])
**Phase**: [current_phase] | **Last worked**: [date of last session history row, or "no prior sessions"]

**Status**: [X artifacts complete, Y in progress] — [brief 1-line state of play]
**Suggested next**: [next focus from last session, if any]
```

Keep this to 4–6 lines. Do not dump the entire status file. If there is no prior session history, say so in one line.

### Step 5: Proceed With the User's Request

After outputting the context summary, immediately proceed with what the user asked for. Do not ask for permission to continue or offer a menu of options unless the user's request is ambiguous.

If the user asked a specific question or gave a specific instruction, answer it — do not replace their intent with a session plan. Reserve structured planning for `/wire:plan`.

## Edge Cases

### No .wire/ directory
Do not activate. Proceed normally without Wire context.

### First session (no prior history)
Output the context summary with "No prior sessions" for the last-worked field and suggest the first incomplete artifact as the natural next step.

### Multiple active releases
List all releases in one line: "3 releases: 01-discovery (complete), 02-data-foundation (active), 03-dashboards (planned)." Focus the state detail on the most recently modified.

### engagement/context.md missing
Load release state only. Note "No engagement context file found" in one line — non-blocking.

## What This Skill Does Not Do

- It does not enter Plan Mode or propose a session plan (use `/wire:plan` for that)
- It does not block the user's request while loading context
- It does not ask the user questions before proceeding
- It does not replace the content of what the user asked — it prepends context to it
