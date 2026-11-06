---
sidebar_position: 20
title: Wire CLI (experimental)
---

:::caution Experimental
The Wire CLI is experimental (wire#408). It is for trying out, not for client delivery; the Wire plugin for Claude Code remains the product. This page is generated from the CLI's guide (`wire/cli/README.md`) by `wire/scripts/sync_cli_docs.py`.
:::

# Wire CLI

Experimental, 4.6.1 (wire#408). Not for client use yet. The Wire
plugin for Claude Code remains the reference way to run Wire; the CLI is a
second way that does not depend on Claude Code, measured on one real release
so far (see "Limitations" and "How it was built").

Contents: what it is; prerequisites; install; keys and sign-in; set up an
engagement repository; everyday use; MCP servers; evals and model routing;
choosing the harness and model;
Claude without Claude Code; local models; what it writes where;
limitations against the Wire plugin; troubleshooting; uninstall; how it was
built and what it relies on; for developers.

## What it is

`wire` is a command-line program that runs Wire's workflow specifications
through an agent harness of your choice. It owns the release loop itself:
it reads a release's `status.md`, works out what can run next, dispatches each
step as a lane in its own git worktree, checks what the lane changed, merges
clean work, and writes the record (`status.md`, `execution_log.md`). The agent
harness only ever runs one step and reports.

Harnesses:

| Harness | Runs the step through | Models | Sign-in |
|---|---|---|---|
| `codex` | The standalone `wire-agent` the installer ships (Codex with the Wire mark and a native Anthropic provider), or OpenAI's Codex CLI | OpenAI models; Claude (`--provider anthropic` on `wire-agent`, or the bridge on OpenAI's codex); a local model through LM Studio or Ollama | OpenAI or Anthropic API key; `codex login` with a ChatGPT plan only on OpenAI's codex |
| `claude` | Claude Code (`claude -p`) | Claude models | Anthropic API key |

Typing `wire` alone opens a session with the Wire banner, where plain text
is direction and bare command names run Wire commands.

## Prerequisites

| Need | Why | Check |
|---|---|---|
| macOS or Linux, a terminal, `git` | the CLI works in git repositories and makes worktrees for lanes | `git --version` |
| Python 3.9 or later | the CLI is Python | `python3 --version` |
| PyYAML | the runnable-set resolver reads YAML | `python3 -c "import yaml"`; else `python3 -m pip install --user pyyaml` (the Homebrew install brings its own) |
| One harness | runs the steps | `codex --version` or `claude --version`; the standalone `wire-agent` comes with the installer and the Homebrew formula on macOS (Apple silicon and Intel) |
| An engagement repository with `.wire/` | what Wire works on | made by `/wire:new` or `/wire:adopt` in Claude Code, or an existing engagement |
| Optional: LM Studio or Ollama | a local open-weight model | only if you want one |

Codex, if you want it beside the standalone agent: `npm install -g @openai/codex`.
Claude Code: https://claude.com/claude-code.

## Install

**curl** (installs to `~/.wire`, writes `~/.local/bin/wire`, fetches the
standalone agent for your machine when the release ships one):

```
curl -fsSL https://github.com/rittmananalytics/wire-plugin/releases/download/v4.6.1/install-wire.sh | sh
```

To pin a version, or if the installer cannot look one up, prefix the `sh`
with `WIRE_VERSION=4.6.1`. Make sure `~/.local/bin` is on your PATH.

**Homebrew** (the tap is the public `wire-plugin` repository):

```
brew tap rittmananalytics/wire https://github.com/rittmananalytics/wire-plugin
brew install wire
```

Homebrew installs its own Python and PyYAML, and on a Mac the standalone
agent. Elsewhere the `codex` harness uses `codex` from your PATH.

Then:

```
wire doctor
```

It reports `codex`, `claude`, PyYAML, which keys are set (by name only),
whether LM Studio answers, and whether the current repository has the
Codex install set. Updating: run the installer again with the new version
(older versions stay under `~/.wire/versions/`), or `brew upgrade wire`.

## Keys and sign-in

Keys live in a file you write yourself. They never pass through a prompt,
a log, or a chat with the agent. In your own terminal:

```
mkdir -p ~/.wire && chmod 700 ~/.wire
read -rs KEY && printf 'ANTHROPIC_API_KEY=%s\n' "$KEY" >> ~/.wire/secrets.env; unset KEY
read -rs KEY && printf 'OPENAI_API_KEY=%s\n' "$KEY" >> ~/.wire/secrets.env; unset KEY
chmod 600 ~/.wire/secrets.env
```

Each `read -rs` waits silently for a paste and Enter. A per-repository file,
`<repo>/.wire/local/secrets.env`, overrides the personal one. A secrets
file readable by other users is skipped with a note.

- **Anthropic.** An API key from the Claude Console. Anthropic's terms keep
  Claude subscriptions (Max, Enterprise) inside Claude Code, so the `claude`
  harness and the bridge bill the key per token.
- **OpenAI.** An API key from the OpenAI platform. The standalone agent
  (`wire-agent`) uses the key only: the CLI passes it as `CODEX_API_KEY` and
  refuses the run when there is none. "Sign in with ChatGPT" is for OpenAI's
  own Codex until OpenAI confirms that a modified client may use it; to use a
  ChatGPT plan, install Codex with npm, run `codex login`, and point the CLI
  at it with `WIRE_CODEX_BIN=$(which codex)`. The CLI never reads or changes
  Codex's stored login.
- **Local model.** No key. See "Local models".

`wire doctor` shows each key as set or not set. The CLI loads the file into
the environment of a harness run and nowhere else.

## Set up an engagement repository

Once per repository, in its root:

```
wire codex-install
```

This writes the files Codex reads from the repository: `.codex/hooks.json`
and `.codex/hooks/wire_hooks.py` (the lane rules and the lint-on-write),
`.codex/agents/*.toml` (the 13 lane agents), `.codex/config.toml` (lanes run
flat) and `AGENTS.md`. It refuses to overwrite a file that differs unless you
pass `--force`.

The standalone `wire-agent` (4.6.1 and later) carries the Wire framework
itself: the specifications, the command catalogue, the authoring skills, the
lane agents and Studio. The first run unpacks them under
`~/.wire/agent/framework/<version>/` and registers them as the agent's `wire`
plugin, so the repository holds no copy of the plugin. With OpenAI's own
`codex`, or with `--copy`, `wire codex-install` copies the plugin into
`.wire/codex-plugin/` and adds a marketplace entry, as before. A copy left by
an earlier install is not used by `wire-agent`; the installer names it, and it
can be removed with `git rm -r`.

Then trust the hooks once. Codex runs no untrusted hook:

```
codex
/hooks
```

Approve the two Wire entries and quit. A changed hook script keeps its
trust; a changed `hooks.json` needs `/hooks` again (the installer says so
when it replaces one). Add `.wire/local/` to `.gitignore` if it is not there:
the CLI keeps worktrees, lane logs, briefs and secrets under it.

The `claude` harness needs none of this: the CLI's own checks apply to every
harness, and Claude Code's edits in a lane are limited to the lane's paths.

A `claude` step runs on the repository's settings only
(`--setting-sources project,local`) and only the MCP servers Wire passes
(`--strict-mcp-config`). Your own Claude Code settings, plugins and claude.ai
connectors are left out: on a test machine they added 40 MCP servers and
cost about five times as much on a one-line question. The Wire plugin's hooks
load in a step only when the repository enables the plugin in
`.claude/settings.json`. `WIRE_CLAUDE_USER_SETTINGS=true` keeps your own
settings for a run.

## Everyday use

```
wire                                   the session
wire status <release>                  states, runnable set, claim, next action
wire run <release> [--yes] [--once]    orchestrate: lanes, merge, record
wire <command> <release> [args]        one Wire command, as /wire:<command> would run
wire gate <release> <command>          would the precondition gate allow it
wire exec "<prompt>"                   one prompt through the harness, headless
wire mcp list | add | login | check   MCP servers for this engagement
wire eval [suite] [--harness ...]      the eval suite on a harness and model (EVALS.md)
wire doctor | wire bridge | wire codex-install | wire version | wire update | wire uninstall
```

**The session.** `wire` shows the banner, the engagement and its releases,
and a prompt naming the active release:

```
wire 02-data-foundation> status
wire 02-data-foundation> dbt-validate
wire 02-data-foundation> plan
wire 02-data-foundation> run --yes --once
wire 02-data-foundation> get the semantic layer validated and tell me what blocks dashboards
```

The last line is direction. The harness gets the release as data (states,
runnable set, parked decisions, the last log rows, the commands the release
knows) and the rule that it runs nothing; it replies in plain English with
the commands that carry the intent out. The session shows the run plan and
waits for `go`, `adjust <what>` or `cancel`, runs them one at a time, and
ends with `Ran: ...`. A question gets an answer and no plan. `use <release>`
changes the active release; `harness`, `model`, `provider` set the session;
`exec <text>` is a raw prompt; `help`, `quit`.

The session is a conversation. Direction continues the same agent thread from
turn to turn, so a follow-up ("and what about the dashboards?") has the
earlier turns; `new` starts a fresh one, as does `use <release>`. A Wire
command typed in the session talks to you as it does in Claude Code: when it
ends a message with a question (a review's sign-off, a setup choice), the
session shows it, you answer at `you>`, and the same thread continues. During
`run`, a lane that stops on a question is answered the same way: the answer
is recorded as a ruling (`R-n` in `decisions.md`) and the lane resumes in its
own worktree and conversation. A blank answer parks it as before.

Replies appear as they are written. On the `codex` harness the session holds
each turn open on Codex's app-server protocol: the reply streams in, each
command, file edit and tool call shows as a dimmed line as it starts, and when
the agent needs a choice from you it asks inside the turn (numbered options;
type a number or your own answer) and carries on with your answer. On the
`claude` harness the reply streams the same way, but Claude Code in `-p` mode
cannot ask mid-turn, so a question still ends the turn and your answer starts
the next. `wire <command>` and `wire exec` stream too when run in a terminal.
Lanes in `wire run` stay headless on `codex exec`. `WIRE_STREAM=false` turns
streaming off; a Codex without the app-server falls back to `codex exec` with
a note. Ctrl-C during a streamed turn stops the turn; a second Ctrl-C leaves.

What the Wire mod gives Claude Code, the session gives here: a live panel on
the bottom two rows of the terminal. The first row is the status line
(`[Wire v4.6.1] 02-data-foundation (full_platform) · 5 approved · 1
parked · claim: you · ctx:42%`). The second shows the next action when
nothing runs; while something runs, it shows the command and how long it has
run, the last command or edit the agent started, and during `wire run` each
lane with its time, a lane quiet for 30 minutes flagged as the mod's stall
timer does. The rest of the session scrolls above it. `WIRE_PANEL=false`, a
pipe or a terminal under 10 rows prints the status line when it changes
instead. The session also gives one note when the
conversation reaches 85 percent of its context, the release context (next
action, claim, parked decisions, last rulings, business rules by domain,
iterations in flight) in the agent's prompt each turn, the next action on an
empty line (`next` runs it), and `/handoff`, which writes
`lanes/handoff-<session>.md` from the handoff template. A typed run whose
reply does not end with `Ran:` gets a note, as the mod's rule-7 check does.
Usage telemetry is the plugin's `wire_command` event with `runtime: wire-cli`
and the harness; `WIRE_TELEMETRY=false` turns it off, and it carries no
arguments or prompt text.

The director's record, written at once by the session:

```
/approve dbt --final [--as client] [--evidence <url>]    review_events; --final sets review: approved
/park semantic_layer "Which explores ship first?" [--awaiting client]
/rule PD-2 Dagster -- the client already runs it          R-n in decisions.md; PD-2 cleared
/rule conceptual_model.depends_on.business_rules skip -- agreed at kickoff
```

These write the same entries as the Wire mod's `/wire-approve` and
`/wire-park` in Claude Code and the rulings format in the director operating
model, so Studio and the plugin read them unchanged.

**`wire run`.** One pass: checks the status file; resolves the claim (another
person's claim silent for over 30 minutes needs `--take-over`; a live one
stops you); computes the runnable set; prints the run plan and waits for
`go` unless `--yes`; dispatches one lane per runnable artifact, each in a
worktree under `.wire/local/worktrees/` on the harness; then consolidates:
a lane that wrote `status.md` or `execution_log.md`, or wrote outside the
trees it owns, is parked and never merged; a clean lane is merged with a
merge commit; the artifact's outcome and one log row per lane are written
by the CLI. A lane that stops on a question is parked as a decision
(`PD-n`) in `status.md`. It stops at a review (a review is your ruling,
never dispatched), a block, a parked lane, or after one pass with `--once`.
Exit codes: 0 done, 1 status-file problem, 3 plan not approved, 4 claim
held by someone else, 5 gate refused, 6 a lane was parked.

**A typed command.** `wire dbt-validate 02-data-foundation` runs the spec in
the repository with `WIRE_INVOKED_BY=typed`; the spec writes the record and
the CLI fills in the tokens and duration afterwards. The gate runs first;
`--override-gate "<reason>"` goes past a refusal and records the override.

## MCP servers

The servers an engagement uses are listed once, in
`.wire/engagement/mcp_servers.yml`, committed with the repository. Sign-in is
per person and stays in Codex's own store; the file holds URLs only.

```
wire mcp list                        the catalogue, what this engagement selected, sign-in state
wire mcp add atlassian               a server from Wire's catalogue
wire mcp add fathom https://...      a server with your organisation's URL
wire mcp login atlassian             sign in once (a browser opens)
wire mcp check 02-data-foundation    what this release's commands need
wire mcp remove notion
```

Every run (`wire run`, a typed command, `wire exec`) gets the selected
servers: on the codex harness as `-c mcp_servers.<server>.url=...` (Codex reads
a repository's `.codex/config.toml` only in a folder you have trusted, so the
CLI does not rely on it), on the claude harness as `--mcp-config`, with the
servers' tools allowed. A server Codex reports as not signed in is still
passed, with a note: some serve anonymous calls (Context7), and one that needs
a sign-in fails at start-up with one error line while the run goes on.

**Wire's own tools.** Every run (lanes, typed commands, `wire exec`) also
gets a `wire` MCP server the CLI starts, `wire tools-server`, with four
tools: `wire_status` and `wire_gate` (a release's state and the gate's answer
in a few lines), `wire_lint` (the conventions check on files) and `dbt` (dbt
with a short result: counts by status and each failure, not dbt's log; under
`warehouse_spend: none` it refuses commands that query the warehouse). They
work on both harnesses. `WIRE_TOOLS=false` leaves the server out.

Tool names match: Codex calls an MCP tool `mcp__<server>__<tool>`, as Claude
Code does, so a specification's tool names work when the server key is the
same. In a lane under `warehouse_spend: none`, the hook refuses BigQuery
`execute_sql` and Snowflake `sql_exec`, as the Wire mod does in Claude Code.

## Evals and model routing

`wire eval` runs the core suite (five cases: asking Wire for the runnable set,
the gate's answer, respecting a ruling, not guessing a parked decision, a
typed validate that records its run) on any harness and model, graded without
a model. Results are in `EVALS.md`. A model is routed to a tier in
`wire/model-routing.yaml` only after it passes. A run on Claude through the
codex harness (`--provider anthropic` or the bridge) takes Claude's tiers; a
named provider such as LM Studio has its own block.

From Wire Studio, "Run in Wire CLI" (shown when `wire` is on the PATH) opens a
session with the directive as its first line (`wire --first "<directive>"`);
`studio` in the session starts Studio for the repository.

## Choosing the harness and model

Highest first: flags (`--harness codex|claude`, `--model`, `--provider`,
`--sandbox`); environment (`WIRE_HARNESS`, `WIRE_MODEL`, `WIRE_MODEL_PROVIDER`);
the release's `budget.harness` block in `status.md`; the engagement's block
in `.wire/engagement/context.md`:

```yaml
harness:
  default: codex
  codex:
    model_provider: lmstudio
    model: qwen/qwen3.6-35b-a3b
  claude:
    model: claude-sonnet-5-5
```

With nothing set: `codex` with its own default model. A lane's model follows
`specs/delegate.md`: the command's workload tier, then the economy model
when `budget.model_tier: economy`, else the configured model. The routing
file's tiers are Claude model ids and apply to the `claude` harness; another
harness uses the configured model until the file carries its own ids.

## Claude without Claude Code

**The standalone agent (`wire-agent`) speaks the Anthropic Messages API
itself.** It translates Codex's requests to Anthropic's format and the
replies back, with tools and prompt caching, and needs no proxy:

```
wire dbt-validate 02-data-foundation --harness codex --provider anthropic --model claude-sonnet-5-5
```

Needs `ANTHROPIC_API_KEY` in `~/.wire/secrets.env` (sent as Anthropic's
`x-api-key` header). OpenAI's own `codex` cannot do this; the CLI refuses
`--provider anthropic` on it and says so.

**With OpenAI's `codex`, the bridge.** Codex speaks only the Responses API,
and Anthropic's OpenAI-compatible endpoint is Chat Completions and not for
production. `wire bridge start`
runs a LiteLLM proxy (Responses API to the Anthropic Messages API, prompt
caching on) behind a small shim that removes what the translation cannot
carry. Then any `codex` run can use Claude:

```
wire bridge start
wire dbt-validate 02-data-foundation --harness codex --provider wirebridge --model claude-sonnet-5-5
wire bridge stop
```

Setup once: `python3 -m venv ~/.wire/bridge-venv && ~/.wire/bridge-venv/bin/pip install 'litellm[proxy]'`.
Needs `ANTHROPIC_API_KEY`. Models: claude-sonnet-5-5, claude-opus-5-5,
claude-haiku-5-5, claude-fable-5-1. Measured: a full data model lane through
the bridge completed on Claude Sonnet; the shim went through four live
fixes to get there, so treat it as the newest part.

## Local models

LM Studio: load a model with a large context (`lms load &lt;model>
--context-length 98304`; the default 32k is too small for a Wire spec plus
the files a lane reads) and start the server on port 1234 (`lms server
start --port 1234`). Then `--provider lmstudio --model &lt;model id>`. Always
pass `--model`: Codex's `--oss` without one downloads a model of its own.
Measured on an M5 Max with a 35B mixture-of-experts model: a data model
lane in 3 to 4 minutes, a dbt lane in 11.

## What it writes where

| Path | What |
|---|---|
| `.wire/releases/<release>/status.md`, `execution_log.md` | the record, written by the CLI (lanes are refused) |
| `.wire/releases/<release>/lanes/<lane>.md` | each lane's state file |
| `.wire/local/worktrees/<lane>/` | a lane's worktree while it runs; kept when parked |
| `.wire/local/lane-logs/` | per-run transcripts (`<lane>-<stamp>.codex.jsonl`), stderr, hook logs |
| `.wire/local/briefs/`, `.wire/local/cli_session` | lane briefs; this clone's session id |
| `~/.wire/versions/<v>`, `~/.wire/current` | the installed CLI and framework; `bin/wire-agent` |
| `~/.wire/secrets.env`, `~/.wire/bridge/` | keys; the bridge's config and logs |
| `~/.wire/cli_history` | the session's line history |
| `~/.wire/agent/` | `wire-agent`'s own home (its `CODEX_HOME`): sessions, MCP sign-ins, and a `config.toml` in which the CLI trusts each engagement repository and Wire's two hooks while `.codex/hooks.json` is the one Wire ships. Your own `~/.codex` is never used by a Wire run. `WIRE_AGENT_HOME` moves it; a `CODEX_HOME` you set is left alone. |

The merge commits carry each lane's work. After each pass the CLI commits
`status.md`, `execution_log.md` and `decisions.md` on their own ("wire: record
for &lt;release>"), so a lane's merge and its record travel together;
`--no-commit-record` (or `WIRE_COMMIT_RECORD=false`) leaves them for you.

## Limitations against the Wire plugin in Claude Code

These are the significant ones. The plugin is the complete product; the CLI
is an alpha measured on one release.

1. **The panel is a terminal's bottom two rows.** It shows the status line,
   the work in progress and the lanes with the 30-minute stall flag, as the
   Wire mod's band does, but it is plain text: no clickable parts, and the
   drift watch is not in the session. Inside the agent's own full-screen
   interface (running `wire-agent` directly) there is no panel.
2. **Lanes are headless.** Replies in the session stream, and on the
   `codex` harness the agent can ask you inside a turn. A lane in `wire run`
   runs on `codex exec`: its question ends its turn, and the session relays
   your answer into a new turn of the lane's thread. An unattended
   `wire run --yes --no-interaction` still parks questions, and on the
   `claude` harness the agent cannot ask mid-turn. `/wire:new` and
   `/wire:adopt`, which set up a repository over many questions, are still
   easier in Claude Code. `wire run` never dispatches a review.
3. **MCP servers need choosing and signing in.** The plugin configures
   Atlassian, Context7, Amplitude, Airbyte and Coupler.io for every user. The
   CLI passes the servers an engagement selects (`wire mcp add`, see "MCP
   servers") and each person signs in once. Warehouse servers (BigQuery,
   Snowflake) and Fivetran are added by URL. Fathom, Jira and the warehouse
   have not yet been run live through the CLI; Context7 has.
4. **Claude is billed by API key.** Subscriptions do not apply outside
   Claude Code (Anthropic's terms). A data model lane on Claude Code cost
   about $2 and a dbt lane about $4 in the concept run.
5. **Lane rules are enforced twice on Codex, once on Claude Code.** On the
   codex harness each lane runs in an operating-system sandbox profile in
   which only its owned trees, its state file, `decisions.md` and dbt's
   scratch folders are writable (seatbelt on macOS; Linux not yet run), and
   the hooks refuse what they can see; on the `claude` harness its edits are
   scoped to the same paths and its shell is limited to reading commands.
   `WIRE_OS_SANDBOX=false` falls back to Codex's workspace-write mode.
6. **Budget rules match the mod.** `warehouse_spend: none`
   refuses BigQuery and Snowflake MCP calls and Wire's dbt tool; under
   `cap:<amount>` the spend ledger (`lanes/_spend.jsonl`) is written by the
   lane hook and the dbt tool, a call past the cap is refused, and the CLI
   parks one budget decision; one dbt build per project runs at a time. A
   lane's `dbt build` in its own shell is refused under `none` and, under a
   cap, sent to Wire's dbt tool, which measures it. Warehouse spend from
   other tools (a Python script, the `bq` CLI) is not measured.
7. **The trees a lane owns come from a fixed rule** unless the release type
   lists `owns:` for the artifact, which the CLI now reads; the process
   registry does not list them yet. An unusual repository layout can refuse
   a write the lane needed; the parked lane's worktree is kept so you can see.
8. **No Gemini CLI.** Its users keep the Gemini extension.
9. **Other models vary.** Wire's specs were written and tuned against Claude.
   In the concept run all three model families completed the same steps,
   and they differed in judgement where the spec and the conventions
   disagreed (one kept the approved names, one asked, one renamed). Review
   what a lane produced before you trust it.
10. **Releases built from tickets are worked one ticket at a time.**
    `wire status` lists each ticket's state (the rules Studio uses) and `wire
    run` names the next ticket instead of dispatching lanes, since on a ticket
    branch only the ticket's iteration file is written. Work a ticket with
    `wire work <release> <ticket>`. Migration releases resolve their profile
    as Studio does; a full migration has not been run through the CLI.
11. **The standalone agent is published for macOS only** so far (Apple
    silicon and Intel). The release workflow builds Linux (glibc) too, once a
    person runs it; Linux has not been tested by hand. Builds are not signed or
    notarised (an Apple developer account is needed), so a copy downloaded
    with a browser rather than the installer meets Gatekeeper. Windows is not
    supported: the launcher, the build-slot lock and the sandbox profile are
    POSIX. The agent reports `codex-cli 4.6.1+codex.0.166.0`: the
    Wire version, then the upstream Codex release. Its welcome screen has not
    been checked by eye.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `PyYAML is missing` | `python3 -m pip install --user pyyaml`, or use the Homebrew install |
| `could not read the latest release` | the pre-release is not GitHub's "latest": prefix `WIRE_VERSION=4.6.1` |
| A lane writes nothing and the hooks log is empty | the hooks are not trusted in this repository: `codex`, `/hooks` |
| `Command blocked by PreToolUse hook` for a write that was in scope | the parked lane's worktree and `.wire/local/lane-logs/*.hooks.jsonl` show the reason; report it, it is a Wire bug |
| `LM Studio is not responding` | `lms server start --port 1234`; always pass `--model` |
| The bridge returns 400 | `~/.wire/bridge/shim.log` names the dropped tool types and the last input items; `~/.wire/bridge/litellm.log` has the upstream error |
| `release is claimed by <name>` | another person's session holds the release; `--take-over` after 30 minutes of silence, never while they work |
| The session shows no colour or the mark is black on dark | `WIRE_THEME=dark` (or `light`); the terminal did not answer the background query |

## Uninstall

`wire update` installs the newest release (`--check` only reports);
`wire uninstall` shows what it would remove and `wire uninstall --yes` removes
the launcher, the installed versions, `~/.wire/current` and the private Python
environment, keeping your keys and the agent's home (`--all` removes those
too). Homebrew: `brew upgrade wire`, or
`brew uninstall wire && brew untap rittmananalytics/wire`. In a repository:
remove `.codex/hooks.json`, `.codex/hooks/`, `.codex/agents/`,
`.codex/config.toml`, `.agents/plugins/marketplace.json`, `AGENTS.md`
and `.wire/codex-plugin/` if you no longer want the Codex integration.

## How it was built and what it relies on

- **The Wire CLI itself** (`wire/cli/`) is Python, standard library plus
  PyYAML, written for this alpha. It reuses Wire's existing deterministic
  code unchanged: Studio's resolver (`wire/studio/wire_studio/runnable.py`,
  the executable form of `specs/utils/runnable_set.md`), `wire_gate.py`,
  `status_file.py`, `lint_conventions.py`, and the same `COMMANDS` catalogue
  the plugins are built from. The Codex plugin target
  (`wire/packaging/codex-plugin/`) packages the spec corpus, a dispatcher
  skill, the authoring skills, the lane agents converted to Codex's TOML, and
  the hooks.
- **OpenAI Codex CLI** (Apache 2.0, Rust) is the default harness, run as
  `codex exec --json`. Nothing in Codex was changed for that.
- **The standalone agent is a fork of Codex**: `rittmananalytics/codex`,
  branch `wire/brand`, two files changed (the welcome renderer draws the
  Wire mark; the title reads "Wire (Codex v...)"), built with Rust 1.95 in
  about 11 minutes. Everything else is upstream. It is rebuilt from an
  upstream tag when a Wire release needs a newer Codex; it is not a
  continuously rebased fork. `WIRE.md` on that branch says the same.
- **Claude Code** (Anthropic) is the `claude` harness, run as `claude -p`
  with a restricted tool allow-list, on the repository's settings only. Not
  changed. First run live in 4.6.2: core suite 5/5, tiers suite on Sonnet 5.5
  (EVALS.md).
- **LiteLLM** (MIT, Python) is the bridge's proxy, installed into
  `~/.wire/bridge-venv`; the shim in front of it is about 200 lines of Wire
  code. Not forked.
- **LM Studio** (proprietary, free) or **Ollama** (MIT) serve local models;
  Codex's built-in providers talk to them. Optional.
- **Homebrew** carries the formula; **GitHub releases** on the public
  `wire-plugin` repository carry the assets. The installer is a POSIX shell
  script.
- Licence of the Wire parts: FSL-1.1-ALv2, as the plugin.

The design, the live findings and the measurements are in
`wire/cli/CONCEPT_RUN.md` and `wire/cli/FORK_DECISION.md`; the tracking
issue is wire#408.

## For developers

`python3 wire/cli/wire.py` runs the checkout's CLI. Tests:
`wire/tests/cli/validate_wire_cli.py` (the record writer, the claim, settings,
adapters, `wire run` on a git copy of the Studio fixture with a fake harness,
the session, the bridge shim), `wire/tests/cli/validate_installer.py`,
`wire/tests/codex/validate_codex_packaging.py` (the hook's decisions, the
agent conversion, the built package, the installer). `wire/scripts/package-cli.sh`
packages, `build-agent.sh` builds the agent from the fork,
`publish-cli-release.sh` publishes (a person runs it: a public release).
`wire/cli/tools/concept_leg.sh` and `concept_measure.py` run and measure a
concept-run leg.
