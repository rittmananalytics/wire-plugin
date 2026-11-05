---
sidebar_position: 5
title: Platforms and limitations
---

# Platforms and limitations

:::caution Experimental
4.6.0. The CLI has been measured on one real release so far. The Claude Code plugin is the complete product.
:::

## Platforms

| Platform | CLI | Standalone agent (`wire-agent`) | Notes |
|---|---|---|---|
| macOS, Apple silicon | Yes | Yes | The platform the CLI was built and tested on |
| macOS, Intel | Yes | Yes | The agent is built for Intel; checked under Rosetta, not yet on an Intel Mac |
| Linux (glibc), x86_64 and arm64 | Yes | Not in alpha.2 | The release workflow builds Linux agents; none published yet. Use OpenAI's Codex or Claude Code as the harness. Not yet tested by hand. |
| Windows | No | No | The launcher, the build lock and the lane sandbox are POSIX-only. WSL has not been tried. |

**Signing.** The Mac agents are not signed or notarised by Apple yet. Installs through curl or Homebrew run without a warning. A copy downloaded through a web browser is blocked by macOS the first time it runs. Install with curl or Homebrew instead, or allow it once in System Settings, Privacy & Security.

**Gemini CLI.** Not a harness. Gemini CLI users keep the Wire extension for Gemini.

## Limitations against the Claude Code plugin

| # | Area | In the CLI | In the plugin |
|---|---|---|---|
| 1 | Status display | A status line printed when it changes; the next action on an empty line | A live band above the prompt; lane stall timer; drift watch |
| 2 | Conversation | Turn by turn: each reply appears when the turn ends, not word by word | Streamed |
| 3 | Setting up an engagement | `/wire:new` and `/wire:adopt` work, but their many questions are easier to answer in Claude Code | Designed for it |
| 4 | Reviews | `wire run` never dispatches a review; a review is your ruling, recorded with `/approve` | The same rule, through `/wire-approve` |
| 5 | MCP servers | Chosen per engagement and signed in per person; Fathom, Jira and warehouse servers not yet run live | A fixed set configured for every user |
| 6 | Billing for Claude | Per token on an API key | A Claude subscription can apply |
| 7 | Lane rules | On `codex`, an operating-system sandbox (macOS only so far) plus the hooks; on `claude`, edits scoped to the lane's folders and read-only shell | The Wire mod's refusals |
| 8 | Warehouse spend | Measured from Wire's dbt tool and the warehouse MCP servers; spend from other tools (a Python script, the `bq` command) is not measured | The same |
| 9 | Releases built from tickets | Worked one ticket at a time with `wire work <release> <ticket>`; `wire run` names the next ticket instead of dispatching lanes | The same model |
| 10 | Folder ownership | Comes from a fixed rule unless the release type lists `owns:`; an unusual repository layout can refuse a write a lane needed | The same rule |
| 11 | Other models | Wire's specs were tuned against Claude. In the concept run, three model families completed the same steps but made different choices where the spec and the conventions disagreed | Claude |

**What to do about 11.** Review what a lane produced before you approve it, whatever the model. Run `wire eval` on a model before you rely on it.

## When a lane is parked

A lane is parked, not merged, when it:
- writes `status.md` or `execution_log.md` (only the CLI writes the record);
- writes outside the folders it owns;
- stops on a question you did not answer.

Its worktree is kept under `.wire/local/worktrees/` so you can see what it did. The reason is in `status.md` as a parked decision (`PD-n`) and in `.wire/local/lane-logs/`. If the hooks refused a write that should have been allowed, report it: that is a Wire bug.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `PyYAML is missing` | `python3 -m pip install --user pyyaml`, or use the Homebrew install |
| `could not read the latest release` | Put `WIRE_VERSION=4.6.0` in front of the installer's `sh` |
| A lane writes nothing and the hooks log is empty | The hooks are not trusted in this repository: run `codex`, then `/hooks` |
| `LM Studio is not responding` | `lms server start --port 1234`, and always pass `--model` |
| `release is claimed by <name>` | Another person is running the release. `--take-over` only after 30 minutes of silence, never while they work. |
| No colour, or the Wire mark is dark on a dark background | Set `WIRE_THEME=dark` or `WIRE_THEME=light` |
