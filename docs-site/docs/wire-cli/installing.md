---
sidebar_position: 2
title: Installing the CLI
---

# Installing the CLI

:::caution Experimental
4.6.0. Releases are pre-releases on the public `rittmananalytics/wire-plugin` repository.
:::

## Prerequisites

| Need | Why | Check |
|---|---|---|
| macOS or Linux, a terminal, `git` | The CLI works in git repositories and makes a worktree for each lane | `git --version` |
| Python 3.9 or later | The CLI is written in Python | `python3 --version` |
| PyYAML | Reads Wire's release-type files | `python3 -c "import yaml"`. The installers provide it if it is missing. |
| A harness | Runs each step | The standalone `wire-agent` comes with the install on a Mac. Otherwise install OpenAI's Codex (`npm install -g @openai/codex`) or Claude Code. |
| An engagement repository with a `.wire/` folder | What Wire works on | Made by `/wire:new` or `/wire:adopt` in Claude Code, or an existing engagement |

## Install

### curl

```
curl -fsSL https://github.com/rittmananalytics/wire-plugin/releases/download/v4.6.0/install-wire.sh | sh
```

This installs the CLI to `~/.wire/versions/4.6.0`, writes the launcher `~/.local/bin/wire`, and fetches the standalone agent for your machine when the release has one. Make sure `~/.local/bin` is on your `PATH`.

Pre-releases are not GitHub's "latest" release. If the installer cannot find a version, put `WIRE_VERSION=4.6.0` in front of `sh`.

### Homebrew

```
brew tap rittmananalytics/wire https://github.com/rittmananalytics/wire-plugin
brew install wire
```

Homebrew installs its own Python and PyYAML, and on a Mac the standalone agent (Apple silicon and Intel).

## Check the install

```
wire version
wire doctor
```

`wire doctor` lists what the CLI can find. Keys are shown as set or not set, never their values:

```
  codex                                 codex-cli 0.166.0 (/opt/homebrew/bin/codex)
  claude                                2.1.318 (Claude Code)
  pyyaml                                present
  ANTHROPIC_API_KEY                     set
  OPENAI_API_KEY                        set
  ~/.wire/secrets.env                   loaded
  MCP servers (this engagement)         none selected (.wire/engagement/mcp_servers.yml; wire mcp list, wire mcp add <server>)
  LM Studio (localhost:1234)            qwen/qwen3.6-35b-a3b, openai/gpt-oss-20b
  .codex/hooks (this repo)              installed; trust once with /hooks in Codex
  .wire/ (this repo)                    present
```

## Set up an engagement repository

Once per repository, in its root folder:

```
wire codex-install
```

This copies the Codex form of the Wire plugin into `.wire/codex-plugin/` and writes the files Codex reads from a repository:

| File | What it is |
|---|---|
| `.codex/hooks.json`, `.codex/hooks/wire_hooks.py` | The lane rules (what a lane may write) and the conventions check after each write |
| `.codex/agents/*.toml` | Wire's 13 lane agents |
| `.codex/config.toml` | Lanes run one level deep |
| `AGENTS.md`, a marketplace entry | Instructions and the plugin entry Codex reads |

It will not overwrite a file you have changed unless you pass `--force`.

Then approve the hooks once. Codex does not run a hook until you trust it:

```
codex
/hooks
```

Approve the two Wire entries and quit. After an update that changes `.codex/hooks.json`, the installer tells you to do this again.

Add `.wire/local/` to `.gitignore` if it is not there already. The CLI keeps lane worktrees, logs, briefs and per-repository secrets under it.

The `claude` harness needs none of this. Claude Code applies its own hooks, and the CLI's own checks apply on every harness.

## Update and uninstall

| Task | Command |
|---|---|
| Check for a newer release | `wire update --check` |
| Install the newest release | `wire update`, or `brew upgrade wire` |
| See what uninstalling would remove | `wire uninstall` |
| Uninstall, keeping keys and the agent's home | `wire uninstall --yes` |
| Uninstall everything | `wire uninstall --yes --all` |
| Homebrew | `brew uninstall wire && brew untap rittmananalytics/wire` |

Older versions stay under `~/.wire/versions/` until you uninstall.
