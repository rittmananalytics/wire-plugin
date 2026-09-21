---
name: Fathom Sync
description: Automatically pulls new Fathom call transcripts for the engagement's client into .wire/engagement/calls/ once per session, when fathom_sync is enabled for the engagement.
triggers:
  - The start of a conversation in a repository containing a .wire/ directory, immediately after the Engagement Context skill has loaded context, when .wire/engagement/context.md has fathom_sync.enabled set to true
---

# Fathom Sync Skill

## On Activation

Append a one-line entry to `.wire/execution_log.md` (or the active release's log, matching Engagement Context's own convention):

```
| YYYY-MM-DD HH:MM | skill | fathom-sync | activated | Checked for new Fathom calls |
```

## When This Skill Activates

Fires once per new conversation, immediately after the Engagement Context skill has loaded (so engagement state is already known) — never mid-conversation, never more than once per session.

Do **not** fire if any of these are true:
- `.wire/engagement/context.md` doesn't exist, or `fathom_sync.enabled` is not `true`
- This skill has already activated once in the current conversation
- The Fathom MCP server isn't configured or isn't reachable — check quietly, don't ask the user about it

All of the above are silent skips: no message, no note, nothing different about how the conversation proceeds. This is the expected outcome for most sessions and for any engagement that hasn't opted in.

## Procedure

1. Follow `specs/utils/fathom_sync.md` in **automatic mode** — no flags, defaults for `--after` (from `fathom_sync.last_synced`), `--before` (today), `--limit` (50). Findings extraction runs (not skipped) unless a prior session left `--no-findings`-equivalent state, which automatic mode never does.
2. That spec's own Step 8 (Report) already defines automatic-mode output: nothing if zero new calls, one brief line if any were found. Don't add anything beyond what that step specifies.
3. Continue to whatever the user actually asked for in their message — this skill never blocks or delays the response beyond the sync itself completing.

## Relationship to Engagement Context

This skill is deliberately separate from the Engagement Context skill rather than folded into it, even though they share the same "once per session" trigger: Engagement Context is meant to be fast (read a couple of files, summarize) and Fathom Sync can be genuinely slow (MCP calls, writing multiple files, a real analytical findings pass per new call). Keeping them separate means a heavy Fathom sync never makes the fast context-load feel sluggish, and either can be reasoned about independently.

## Relationship to Meeting Context (`specs/utils/meeting_context.md`)

Different job. Meeting Context does a live, ad-hoc Fathom search at *review* time, scoped to one artifact, and doesn't persist anything. Fathom Sync persists every new call as a durable, committed file once, unscoped to any particular artifact — so the whole team has it later without re-querying Fathom, and Meeting Context's own searches can find it locally instead of hitting the API again.
