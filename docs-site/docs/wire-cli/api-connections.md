---
sidebar_position: 3
title: API connections
---

# API connections

:::caution Experimental
4.6.1. The routes to Claude through the `codex` harness are the newest part of the CLI.
:::

The CLI needs a way to reach a model. This page covers where keys go, the four ways to connect, and how the CLI picks the harness and model for a run.

## Where keys go

Keys go in a file you write yourself, `~/.wire/secrets.env`. They never pass through a prompt, a log, or a chat with the agent. Run this in your own terminal. Each `read -rs` waits, without showing what you type, for you to paste a key and press Enter:

```
mkdir -p ~/.wire && chmod 700 ~/.wire
read -rs KEY && printf 'ANTHROPIC_API_KEY=%s\n' "$KEY" >> ~/.wire/secrets.env; unset KEY
read -rs KEY && printf 'OPENAI_API_KEY=%s\n' "$KEY" >> ~/.wire/secrets.env; unset KEY
chmod 600 ~/.wire/secrets.env
```

| Rule | Detail |
|---|---|
| Per-repository keys | `.wire/local/secrets.env` in a repository overrides the personal file |
| File permissions | A secrets file other users can read is skipped, with a note |
| Where keys are used | Loaded into the environment of a harness run only |
| Checking | `wire doctor` shows each key as set or not set |

You only need the keys for the routes you use. When nothing names a harness or model and `ANTHROPIC_API_KEY` is set, the CLI runs Claude Opus 5.5 (on Claude Code when it is installed, otherwise through the standalone agent). Without that key it runs OpenAI's default model, GPT-6.1 Sol.

## The four routes

| Route | Harness and provider | Key | Billing |
|---|---|---|---|
| OpenAI models | `codex` | `OPENAI_API_KEY` | OpenAI API, per token |
| Claude through the standalone agent | `codex`, `--provider anthropic` | `ANTHROPIC_API_KEY` | Anthropic API, per token |
| Claude through Claude Code | `claude` | `ANTHROPIC_API_KEY` | Anthropic API, per token |
| A local model | `codex`, `--provider lmstudio` | None | Free; runs on your machine |

### OpenAI models

The default. With `OPENAI_API_KEY` set, nothing else is needed:

```
wire dbt-validate 02-data-foundation
```

The standalone agent uses the API key only. "Sign in with ChatGPT" is kept to OpenAI's own Codex until OpenAI confirms a modified client may use it. To use a ChatGPT plan instead of a key, install Codex with npm, run `codex login`, and point the CLI at it:

```
export WIRE_CODEX_BIN=$(which codex)
```

The CLI never reads or changes Codex's stored login.

### Claude through the standalone agent

The standalone agent (`wire-agent`) talks to Anthropic's Messages API directly, with tools and prompt caching. No proxy is needed:

```
wire dbt-validate 02-data-foundation --provider anthropic --model claude-sonnet-5-5
```

OpenAI's own Codex cannot do this, and the CLI refuses `--provider anthropic` on it. If you only have OpenAI's Codex, the bridge (`wire bridge start`) runs a local proxy that does the translation. See the [full reference](../advanced/wire-cli#claude-without-claude-code).

### Claude through Claude Code

```
wire dbt-validate 02-data-foundation --harness claude --model claude-sonnet-5-5
```

Anthropic's terms keep Claude subscriptions (Max, Enterprise) inside Claude Code, so runs from the CLI are billed per token to the API key. In the concept run, a data model lane cost about $2 and a dbt lane about $4.

### A local model

Load a model with a large context in LM Studio and start its server:

```
lms load qwen/qwen3.6-35b-a3b --context-length 98304
lms server start --port 1234
```

Then:

```
wire dbt-validate 02-data-foundation --provider lmstudio --model qwen/qwen3.6-35b-a3b
```

Always pass `--model` with a local provider. The default 32k context is too small for a Wire spec plus the files a lane reads. Ollama works the same way with `--provider ollama`. On an M5 Max with a 35B model, a data model lane took 3 to 4 minutes and a dbt lane 11 minutes.

## How the CLI picks the harness and model

The first setting found wins:

1. Flags on the command: `--harness codex|claude`, `--model`, `--provider`
2. Environment: `WIRE_HARNESS`, `WIRE_MODEL`, `WIRE_MODEL_PROVIDER`
3. The release's `budget.harness` block in `status.md`
4. The engagement's `harness:` block in `.wire/engagement/context.md`
5. Nothing set: Claude Opus 5.5 when `ANTHROPIC_API_KEY` is set (the `claude` harness when Claude Code is installed, otherwise `codex` with the Anthropic provider); otherwise the `codex` harness with its own default model (GPT-6.1 Sol)

An engagement default looks like this:

```yaml
harness:
  default: codex
  codex:
    model_provider: lmstudio
    model: qwen/qwen3.6-35b-a3b
  claude:
    model: claude-sonnet-5-5
```

In the session, `harness`, `model` and `provider` change the setting for that session only.

## Checking a model before you rely on it

Wire's specifications were written and tuned against Claude. `wire eval` runs a five-case suite on any harness and model and grades the results without a model:

```
wire eval --harness codex --provider lmstudio --model qwen/qwen3.6-35b-a3b
```

A model is added to Wire's model routing only after it passes. Results so far are in `wire/cli/EVALS.md`.
