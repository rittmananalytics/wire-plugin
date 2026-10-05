---
sidebar_position: 7
title: Telemetry and metrics (the Wire mod)
---

# Telemetry and metrics: the Wire mod

From 4.1.0 the Wire plugin for Claude Code includes a mod: a small module of function hooks that Claude Code runs alongside your session. In 4.1.0 it records which Wire commands ran, fills in the Duration, Tokens and Cost cells of each command's row in the execution log, and adds two instant commands: `/wire-usage` and `/wire-studio`. It refuses nothing and changes no tool call. This page covers what it records, the two commands, and how to turn telemetry or metrics off.

The mod replaces two settings hooks from 4.0: a telemetry script that scraped each prompt for a `/wire:` token, and a metrics script that re-read the session transcript after every turn. Those disagreed with each other by about two to one, and could not see commands an agent ran. The mod sees the event that started each command, so it counts typed, orchestrated, lane and Autopilot runs correctly.

## What it records for each Wire command

| Started by | How the mod knows | `invoked_by` |
|---|---|---|
| You typed it | A `/wire:` command ran | `typed` |
| You typed it in a session Wire Studio opened | The same, in a terminal Studio tagged with `WIRE_INVOKED_BY=studio` | `studio` |
| The orchestrating session | A Wire command through the Skill tool on the main loop | `orchestrator` |
| Autopilot | The same, after `/wire:autopilot` ran in the session | `autopilot` |
| A lane | A Wire command through the Skill tool inside a subagent | `lane` |

Each event carries the command, the release it named, `invoked_by`, the session and agent ids, the Wire version, the operating system, the git remote and branch, and your operating-system user name and machine hostname. It never carries prompt text, the command's other arguments, file contents or data. Because it includes your user name, hostname and git remote, the event identifies you and can identify the client; it is not anonymous.

## Execution-log metrics

1. When a Wire command starts, the mod opens a run for it.
2. Every model request adds the usage the API reports to the run open in its own loop: the main session, or one lane.
3. When that loop's turn ends, the mod fills the command's row in the release's `execution_log.md`: Duration (only if the command left it `n/a`), Tokens and Cost (USD). It fills only the newest row for that command that is still unfilled and dated no earlier than the day before the run started, and never touches another cell or row.
4. A lane's row, which the orchestrating session writes after the lane reports, is filled when that write happens.

Cost comes from a price table in the mod. A model it does not recognise leaves Cost at `n/a`, with Tokens still filled. Nothing is estimated.

## /wire-usage

`/wire-usage` prints the Wire commands this session has run, with who started each, its duration, tokens, cost and whether its log row has been filled. It answers at once, with no model turn.

## /wire-studio

`/wire-studio` starts [Wire Studio](./wire-studio) for the repository the session is in, without a model turn:

| Command | What it does |
|---|---|
| `/wire-studio` or `/wire-studio start` | Starts Studio in the background on the first free port from 4800 to 4820 and opens it in your browser. If Studio is already running for this repository, it gives you the address instead. |
| `/wire-studio start --port <n>` | The same, on a port you choose |
| `/wire-studio restart` | Stops this repository's Studio and starts it again, for example after updating the plugin |
| `/wire-studio stop` | Stops this repository's Studio |
| `/wire-studio status` | Says whether Studio is running for this repository, and where |

Studio keeps running after the session ends, until you stop it. Each repository gets its own Studio and port; its record and log are in `~/.wire/studio/`. If Studio exits as it starts (most often because PyYAML is missing), `/wire-studio` shows the reason from the log.

## Turning it off

| Job | Plugin option (`/config`) | Environment variable |
|---|---|---|
| Telemetry | Usage telemetry | `WIRE_TELEMETRY=false` |
| Execution-log metrics | Execution-log metrics | `WIRE_METRICS=false` |

`disableAllHooks` or `--safe-mode` in Claude Code stop the mod entirely. Gemini CLI has no mod: it keeps the in-command telemetry and leaves the metric cells as the command wrote them.

## What comes next

The mod is the base for later 4.x releases planned in [wire#270](https://github.com/rittmananalytics/wire/issues/270): enforcing the release director's lane rules before a breach happens, adding release context to every session, and fast review commands that Wire Studio can use to record decisions.
