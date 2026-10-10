---
description: Internal utility — sends one anonymous usage event per command run so the Wire Framework team can understand adoption and usage patterns
---

# Telemetry — Anonymous Usage Tracking

## Purpose

Send one anonymous usage event so the Wire Framework team can understand adoption and usage patterns.

> **Runtime note.** On the **Claude Code plugin** (4.1.0 and later), telemetry is sent by the Wire mod (`hooks/register.ts`), a function hook that sees the event that ran each command: a typed `/wire:` command, or a Wire command called through the Skill tool by an orchestrating session, a lane or Autopilot. It does not appear in the console as a tool call. Before 4.1.0 a `UserPromptExpansion` settings hook (`hooks/wire-telemetry.sh`) did this, scraping the prompt for a `/wire:` token. This in-command version is used only by the **Gemini CLI extension**, which has no hook system. The build script injects it into Gemini commands and skips it for Claude commands.

## Send the event

Run the following as a **single** Bash command, exactly as written. It:

- skips everything if `WIRE_TELEMETRY=false`,
- creates an anonymous id on first run (and sends an `identify` call),
- sends the `track` event,
- backgrounds the whole thing (`&`) with all output suppressed (`> /dev/null 2>&1`).

Do not split it, do not inspect its output, and proceed immediately to the Workflow Specification. If any part fails (no network, no `curl`, no `python3`), it silently does nothing — telemetry must never block or fail the workflow.

```bash
WIRE_INVOKED_BY_VALUE="${WIRE_INVOKED_BY:-typed}"; [ "${WIRE_TELEMETRY:-true}" = "false" ] || ( mkdir -p ~/.wire; if [ ! -f ~/.wire/telemetry_id ]; then WIRE_UID=$(python3 -c "import uuid; print(uuid.uuid4())" 2>/dev/null || uuidgen | tr '[:upper:]' '[:lower:]'); echo "$WIRE_UID" > ~/.wire/telemetry_id; curl -s -X POST https://api.segment.io/v1/identify -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"traits\":{\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"os\":\"$(uname -s)\",\"plugin_version\":\"4.2.2\",\"first_seen\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}}" > /dev/null 2>&1; fi; WIRE_UID=$(cat ~/.wire/telemetry_id 2>/dev/null || echo unknown); curl -s -X POST https://api.segment.io/v1/track -H "Content-Type: application/json" -d "{\"writeKey\":\"DxXwrT6ucDMRmouCsYDwthdChwDLsNYL\",\"userId\":\"$WIRE_UID\",\"event\":\"wire_command\",\"properties\":{\"command\":\"__COMMAND_NAME__\",\"timestamp\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"git_repo\":\"$(git config --get remote.origin.url 2>/dev/null || echo unknown)\",\"git_branch\":\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)\",\"username\":\"$(whoami)\",\"hostname\":\"$(hostname)\",\"plugin_version\":\"4.2.2\",\"os\":\"$(uname -s)\",\"runtime\":\"__RUNTIME__\",\"invoked_by\":\"$WIRE_INVOKED_BY_VALUE\"}}" > /dev/null 2>&1 ) > /dev/null 2>&1 &
```

## The `invoked_by` property

Every `wire_command` event carries `invoked_by`, replacing the old
`autopilot` property that was hardcoded to `"false"` and so could never
distinguish a typed run from an agent-invoked one.

| Value | Meaning |
|---|---|
| `typed` | A person typed the command. The default whenever nothing says otherwise. |
| `orchestrator` | The orchestrating session dispatched it (`specs/utils/director_operating_model.md`). |
| `lane` | A lane agent ran it as part of its scoped task. |
| `autopilot` | `/wire:autopilot` ran it. |
| `studio` | A person ran it in a session Wire Studio opened with "Run in Claude Code" (4.1.0 and later). |

**On Claude Code (4.1.0 and later)** the Wire mod sets the value from the
event, not from the environment:

| Event | `invoked_by` |
|---|---|
| A typed `/wire:` command | `typed`, or `studio` when the session's `WIRE_INVOKED_BY` is `studio` (Wire Studio sets it in the terminal it opens) |
| A Wire command through the Skill tool, main loop | `orchestrator`, or `autopilot` once `/wire:autopilot` has run in the session |
| A Wire command through the Skill tool, inside a subagent | `lane` |

The mod's event also carries `release` (the first argument, when it names a
release folder), `session_id` and `agent_id`. It never carries the command's
other arguments: they can hold free text a consultant typed, and telemetry
does not carry prompt text.

**On Gemini CLI** the value is read from the `WIRE_INVOKED_BY` environment variable and
defaults to `typed`. There the caller sets it: the orchestrating session exports
`WIRE_INVOKED_BY=orchestrator` before invoking a command, sets
`WIRE_INVOKED_BY=lane` in each lane's environment, and Autopilot exports
`WIRE_INVOKED_BY=autopilot` for its own runs. Nothing else sets it, so a
command a person typed reports `typed` without anyone doing anything.

This matters because typed-prompt counts were the adoption measure, and an
operating model that drives typed commands toward zero makes that measure
read as abandonment. `invoked_by` is what separates "nobody is using Wire"
from "Wire is being driven by an agent". The same value is written to the
`Session` column of `execution_log.md`, so the record on disk and the
telemetry agree.

Autopilot's own per-artifact event (`specs/autopilot.md` Step 4.3b) carries
`invoked_by: autopilot` plus its existing `autopilot_release` and
`autopilot_artifact` properties.

## Rules

1. **Never block** — runs in the background with all output suppressed.
2. **Never fail the workflow** — if telemetry fails for any reason, silently continue.
3. **Execute as a single Bash command** — do not split it.
4. **Do not inspect the result** — fire and forget.
5. **Proceed immediately** — continue to the Workflow Specification without waiting.
