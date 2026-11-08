---
sidebar_position: 1
title: What the Wire CLI is
---

# What the Wire CLI is

:::caution Experimental
The Wire CLI is experimental (first released in 4.6.0, wire#408). Use it to try Wire outside Claude Code, not for client delivery yet. The Wire plugin for Claude Code remains the reference way to run Wire.
:::

The Wire CLI is a program called `wire` that you run in a terminal. It runs the same Wire workflow specifications as the Claude Code plugin, but it does not need Claude Code. You can run Wire's steps on OpenAI models, on Claude through an API key, or on a model running on your own machine.

## How it differs from the plugin

In the Claude Code plugin, the Claude Code session runs the release: it reads the release record, decides what to run, starts lane agents and writes the record. In the CLI, the `wire` program does that work itself, in code:

| Job | Claude Code plugin | Wire CLI |
|---|---|---|
| Read `status.md` and work out what can run next | The orchestrating session, following the specs | `wire`, using the same resolver Wire Studio uses |
| Hold the release claim | The orchestrating session | `wire` |
| Run one step (a generate, validate or review) | A lane agent in Claude Code | A lane on the harness you choose, in its own git worktree |
| Check what a lane changed and merge it | The orchestrating session | `wire`, from the worktree's diff |
| Write `status.md` and `execution_log.md` | The orchestrating session | `wire` |

The model only ever runs one step and reports. The CLI keeps the record, so the record on disk is the same shape as a plugin run, and Wire Studio and the plugin read it unchanged.

## Harnesses

A harness is the agent program that runs a step. The CLI supports two:

| Harness | What runs the step | Models |
|---|---|---|
| `codex` | `wire-agent`, the standalone agent the installer ships (OpenAI's open-source Codex with Wire's changes), or OpenAI's own Codex CLI | OpenAI models; Claude through an Anthropic API key; a local model through LM Studio or Ollama |
| `claude` | Claude Code, run headless (`claude -p`) | Claude models |

With no harness or model configured, the CLI runs Claude Opus 5.5 when `ANTHROPIC_API_KEY` is set (on `claude` when Claude Code is installed, otherwise on `codex`), and `codex` with GPT-6.1 Sol when it is not.

See [API connections](./api-connections) for how to set each one up.

## Three ways to use it

1. **The session.** Type `wire` in an engagement repository. You get a prompt for the active release, where you type Wire command names or plain English. Plain English is treated as direction: Wire proposes the commands that carry it out, waits for `go`, then runs them. See [A CLI session](./a-cli-session).
2. **`wire run <release>`.** One pass of the release loop: it shows the run plan, dispatches one lane per runnable artifact, merges clean work and writes the record.
3. **A typed command.** `wire dbt-validate 02-data-foundation` runs one Wire command, as `/wire:dbt-validate` would in Claude Code.

## When to use it

- You want to run Wire without Claude Code, or on a model other than Claude.
- You want to compare how different models handle the same Wire step (`wire eval`).
- You want the release loop to run from a script.

For client delivery, and for setting up a new engagement (`/wire:new`, `/wire:adopt`), use the Claude Code plugin. See [Platforms and limitations](./platforms-and-limitations).

## The rest of this section

| Page | What it covers |
|---|---|
| [Installing](./installing) | Prerequisites, curl and Homebrew installs, `wire doctor`, setting up an engagement repository |
| [API connections](./api-connections) | Keys, OpenAI, Claude, local models, choosing the harness and model |
| [MCP servers](./mcp-servers) | Choosing servers for an engagement, signing in, Wire's own tools |
| [Platforms and limitations](./platforms-and-limitations) | What runs where, and what the CLI does not do yet |
| [A CLI session](./a-cli-session) | A typical session, step by step |
| [Wire CLI reference](../advanced/wire-cli) | The full guide, generated from `wire/cli/README.md` |
