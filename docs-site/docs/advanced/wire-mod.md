---
sidebar_position: 7
title: The Wire mod
---

# The Wire mod

The Wire plugin for Claude Code includes a mod: a module of function hooks that Claude Code runs alongside your session. It records which Wire commands ran and what they cost, carries the active release's context into every session, checks conventions on every write, enforces the release director's lane rules before a breach happens, and adds six instant commands that run with no model turn. This page covers what it does, what it refuses and when, and how to turn each part off.

The mod does nothing on Gemini CLI, which has no hook mechanism. There, telemetry stays inside each command and the rules below remain conventions.

## What it does, by part

| Part | What happens | Since |
|---|---|---|
| Telemetry | One `wire_command` event per Wire command, with `invoked_by` taken from the event that ran it (`typed`, `orchestrator`, `lane`, `autopilot`, `studio`). Never prompt text or arguments. | 4.1.0 |
| Execution-log metrics | The Duration, Tokens and Cost (USD) cells of each command's row in `execution_log.md`, filled from measured usage when the command's turn ends. | 4.1.0 |
| Status line | `[Wire v4.5.0] 02-data-foundation (full_platform) · 5 approved · 1 parked · claim: Jane Smith · ctx:42%`, for the active release resolved by `/wire:start`'s order. Two releases active with no branch match shows "say which", never a guess. | 4.5.0 |
| Release context | One session-scoped section in the system prompt: the session line, the release's parked decisions and their questions, the last ten rulings, the business-rules register by domain, iterations in flight, the claim and the next command. Rebuilt only when `status.md`, `decisions.md` or the register changes. | 4.5.0 |
| Next command | The next runnable command, as it would be typed, suggested in the empty prompt box at session start. | 4.5.0 |
| Lint on write | `lint_conventions.py` runs on every write to a dbt model, LookML view, Cube model, dbt Charts board or Airflow DAG. Findings come back as a toast and a note the model reads in the same turn. A clean write shows nothing. | 4.5.0 |
| Commands band | A row above the prompt listing the Wire commands this session ran, in full, with result, tokens and cost; steps a gate stopped as `Not run:` rows. `/wire-ran` prints the same as text. | 4.5.0 |
| Rule 7 check | A reply that ran Wire commands and ended without a `Ran:` line naming each in full gets a toast, and the miss is sent as a `wire_ran_line_missing` event. | 4.5.0 |
| Enforcement | The lane rules below, as refusals. | 4.5.0 |
| Review commands | `/wire-approve` and `/wire-park` write to `status.md` with no model turn. | 4.5.0 |
| Hard gates | A destructive or warehouse-touching command on an unmet blocking precondition is refused, naming the override. | 4.5.0 |
| Stall timer | A lane with no state-file write for 30 minutes gets one toast and one note telling the orchestrator to re-dispatch its remaining items. | 4.5.0 |
| Handoff | Compaction uses Wire's handoff template; `/wire-handoff` writes the same summary to the release's `lanes/` folder. | 4.5.0 |
| Drift watch | Off by default. Every eight turns once the context passes 50 percent, one forked question asks which recent instructions contradict a ruling. | 4.5.0 |

## What it refuses, and when

Every refusal applies only when all three hold:

1. The `enforce` option is on (the default).
2. The engagement is in orchestrated mode (`orchestration.mode` in `.wire/engagement/context.md`; the default on Claude Code).
3. The release named in the lane brief carries a claim (`agents.coordinator_session` in `status.md`) held by this session, or by this user, who may resume in a new session.

In manual mode, on an unclaimed release, or on a release another person holds, the mod observes and refuses nothing. Each refusal names the rule and what to do instead.

| Rule | Refused | Message points to |
|---|---|---|
| Lane brief | An `agent.spawn` whose prompt is a Wire lane brief lacking `Owns:`, `State file:` or `Resume:` | The missing line |
| `lanes_max` | A lane brief when as many lanes are live as the budget allows (default 4) | The lanes it is queued behind |
| 1, flat lanes | A lane's Agent tool call | Report that the work is bigger than one lane |
| 3, tree ownership | A lane's Write, Edit, MultiEdit or NotebookEdit whose real path is outside its `Owns:` trees, and is not its state file or the release's `decisions.md` | The owned directories |
| 6, single writer | A lane's write to `status.md` or `execution_log.md` under `.wire/releases/`, with the write tools or Bash (a redirect, `sed -i`, `tee`, `python3 -c`) | The lane's state file |
| `warehouse_spend: none` | A lane's BigQuery `execute_sql`, Snowflake `sql_exec`, or `dbt build`, `run`, `snapshot`, `seed` or `test`. `execute_sql_readonly` is allowed. | Change the budget or report as budget-blocked |
| 2, one build per project | A lane's `dbt build`, `run`, `snapshot` or `seed` while another lane holds the slot for the same project (`--project`, else the release) under 60 minutes | The holder |
| Spend cap | The next warehouse call from a lane once the release's recorded spend has passed `cap:<amount>` | The total, the cap, and the parked decision raised |
| Hard gate | A gated command (`deployment-*`, `cutover-*`, `dbt-migration-defer-build`, and every generate whose validate does real work) when a blocking precondition is unmet in `status.md` | Re-run with `--override-gate "<reason>"`, recorded against your name by the precondition gate |

A ruling in `decisions.md` never satisfies a blocking gate; that is the precondition gate's own rule. Advisory gates are never the mod's to refuse.

The spend ledger is `.wire/releases/<release>/lanes/_spend.jsonl`, one row per warehouse call from a lane: lane, tool, bytes billed, USD at the BigQuery on-demand rate, time. Snowflake rows carry `bytes_scanned` with no price.

**Collision guard.** A command typed on a release another person has written to in the last 30 minutes, or on work a live lane is doing, gets a toast naming the holder and runs anyway. A person typing a command is exercising control.

## The instant commands

| Command | What it does |
|---|---|
| `/wire-usage` | This session's Wire commands with duration, tokens and cost |
| `/wire-ran` | The same list as the band shows: each command in full, its result, tokens, cost, and any `Not run:` rows |
| `/wire-approve <artifact> [--as internal\|client] [--evidence <url>] [--final]` | Appends one review event to `review_events:` on the artifact in `status.md`, with your git name and the date. `--final` also sets `review: approved`, `reviewed_by` and `reviewed_date`, as `<artifact>-review` does. Nothing else changes. |
| `/wire-park <artifact> "<question>" [--awaiting <who>]` | Appends a `parked_decisions` entry with the next `PD-n` id |
| `/wire-handoff` | One forked model request over the session, written to `.wire/releases/<release>/lanes/handoff-<session>.md`, with the cost shown |
| `/wire-studio start\|restart\|stop\|status` | Runs [Wire Studio](./wire-studio) for the repository as a background process |

Both review commands take `--release <folder>` when more than one release is active. Mod command names cannot contain a colon, which is why these are `/wire-` and not `/wire:`.

## Automatic upgrade at session start

Most engagement repositories never have `/wire:upgrade` run on them. From 4.5.1 the mod applies the two upgrade steps that need no judgment itself, at every session start in a Wire repository:

- The 4.0 session-check hook (`UserPromptSubmit` running `wire-session-check.sh` in `.claude/settings.json`) is removed with its script. Every other hook and setting stays.
- An execution log whose header still has four or six columns gets the nine-column header and separator. Data rows are never touched.

Both are idempotent, so a repository that is current sees nothing. When something changed, one note says what and asks you to commit it with your next pull request. The same note names any release whose `wire_plugin_version` is older than the plugin, or absent, so you run `/wire:upgrade <release>` for it; that command changes `status.md` and asks first, which the mod does not do for it. A release another person holds with a live claim is left alone. Queuing `/wire:upgrade` automatically for a release that is behind is [wire#400](https://github.com/rittmananalytics/wire/issues/400).

## How `/wire:start` knows the mod is loaded

At session start the mod writes `.wire/local/mod.json` with its version, the session id, the resolved release and the mode. `/wire:start` reads it and reports "Wire mod not loaded" with the likely reason (Claude Code older than 2.1.316, which the mod's multi-file layout needs; hooks disabled; a managed-settings policy) when the record is absent or from another session.

## Turning parts off

| Part | Plugin option (`/config`) | Environment variable |
|---|---|---|
| Telemetry | Usage telemetry | `WIRE_TELEMETRY=false` |
| Execution-log metrics | Execution-log metrics | `WIRE_METRICS=false` |
| Enforcement and hard gates | Lane rule enforcement | `WIRE_ENFORCE=false` |
| Release context and the next-command suggestion | Release context in the system prompt | `WIRE_CONTEXT=false` |
| Lint on write | Convention lint on write | `WIRE_LINT=false` |
| Drift watch (on) | Drift watch | `WIRE_DRIFT_WATCH=true` |
| Context section length | Release context lines (default 60) | |

`disableAllHooks` or `--safe-mode` in Claude Code stop the mod entirely.

## What the mod hooks and calls

From `claude plugin validate` on the plugin:

```
hooks: session.start, command.run{command=wire-usage}, command.run{command=wire-studio},
  command.run{command=wire-ran}, command.run{command=wire-approve}, command.run{command=wire-park},
  command.run{command=wire-handoff}, command.run, tool.call{tool=Skill}, tool.call{tool=Agent},
  tool.call{tool=Write|Edit|MultiEdit|NotebookEdit}, tool.call{tool=Bash}, tool.call, agent.spawn,
  turn.step, turn.complete, prompt.compose, session.measure, session.compact,
  ui.render{component=AbovePrompt}
gating hooks: command.run, tool.call (each form above), agent.spawn, session.compact
calls: $.clock.after, $.clock.every, $.clock.now, $.clock.sleep, $.command.register, $.env.get,
  $.fs.exists, $.fs.list, $.fs.read, $.fs.stat, $.fs.write, $.http.fetch (Segment only),
  $.model.fork (/wire-handoff and the drift watch), $.process.run (git, hostname, uname, python3
  for the Wire scripts, Studio), $.prompt.suggest, $.session.append, $.session.cwd, $.session.id,
  $.state.get, $.state.set, $.ui.resolve, $.ui.status, $.ui.toast
env reads: HOME, USER, USERNAME, WIRE_CONTEXT, WIRE_DRIFT_WATCH, WIRE_ENFORCE, WIRE_INVOKED_BY,
  WIRE_LINT, WIRE_METRICS, WIRE_PERSONA, WIRE_TELEMETRY
env writes: nothing
```

The mod never approves or allows a call it did not refuse, rewrites nothing except the compaction instructions, and makes one kind of network call (telemetry, off with one setting).

## Replaced from 4.0

| Before | Now |
|---|---|
| `hooks/wire-telemetry.sh` on `UserPromptExpansion` | The `command.run` and `tool.call` hooks |
| `hooks/wire-metrics.sh` and `wire_metrics.py` on `Stop` | The `turn.step` and `turn.complete` hooks |
| `TEMPLATES/wire-session-check.sh` on `UserPromptSubmit` (an hourly marker file) | The `prompt.compose` section, once per session. `/wire:new` no longer installs the hook; the mod removes it at session start (4.5.1), and `/wire:upgrade` offers to where the mod is off. |
| `TEMPLATES/wire-statusline.sh` (most recently modified folder) | `$.ui.status`, by `/wire:start`'s resolution order |
| The build-slot file lock in `dbt-migration-defer-build` | The slot in the mod's state on Claude Code; the file lock remains for Gemini CLI |
