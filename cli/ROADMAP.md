# Wire CLI roadmap: from the 5.0 alpha to parity with the Wire plugin, on a forked Codex

Written 4 November 2026 after the concept run (`CONCEPT_RUN.md`). This is the
plan for the route the fork decision left open: a deep fork of Codex that
takes the benefits a fork can give, MCP servers in the CLI, a conversational
session, and the rest of the gaps against the Wire plugin for Claude Code.
Estimates are in continuous agent time with the pacing items named; a phase
with a registry change waits on a pull request to the process registry.

## Progress (5 November 2026; phase 2 streaming added for 4.6.1)

All eight phases have been worked on `feature/wire-cli-5.0` and the fork
branch `wire/brand-0.166.0`, with tests in `wire/tests/cli/` and
`wire/tests/codex/` and the live checks named below. What is left needs a
person.

| Phase | Done | Live check | Left for a person |
|---|---|---|---|
| 0 | Fork on upstream tag `rust-v0.166.0`; version stamped; licence, NOTICE and change statement in every archive; third-party notices; API-key sign-in rule (`CODEX_API_KEY`); release workflow; installer provides PyYAML | Clean-home install; `wire-agent --version` | v5.0.0-alpha.2 published by hand (CLI, both Mac agents, Homebrew formula with an agent per Mac chip); the release workflow could not run (GitHub Actions billing). Left: Linux agents, a workflow run once billing is fixed, Developer ID signing and notarisation |
| 1 | `wire mcp`; selection in `.wire/engagement/mcp_servers.yml`; servers passed per run on both harnesses; warehouse rule on MCP calls; the agent ships `codex-code-mode-host` | Context7 through `wire exec` | Sign in to Fathom, Atlassian and the warehouse and run a review, a Jira sync and an audit |
| 2 | Conversation threads; typed commands and lane questions answered in the session; `/approve`, `/park`, `/rule`; replies streamed on Codex's app-server protocol with questions answered inside the turn (`request_user_input`), activity lines, Claude's stream-json deltas | A resumed thread kept its context; on wire-agent (5 November 2026) an OpenAI and a Claude turn streamed, asked a question with options and used the answer in the same turn | Lanes stay on `codex exec`; one app-server process per turn, not one per session |
| 3 | Native Anthropic provider in the fork; the agent's own home with Wire's hooks trusted by hash; Wire's tools as an MCP server; the framework compiled into the binary (`wire-agent framework path`, 1.9 MB compressed) and registered as the agent's `wire` plugin, so `wire codex-install` copies no plugin (4.6.1) | Task A on Claude Sonnet 5.5, no proxy: 12 of 12, about $2.05 against $2.05; `wire_status` called; rule 6 refused under the new home; a repository installed without the copy ran the `wire` skill from the carried framework (375 commands) | The CLI itself still ships as Python beside the agent, so an install is two parts, not one file |
| 4 | Status line, release context, next action, `/handoff`, telemetry, the `Ran:` check; a live panel on the terminal's bottom two rows (status line, work in progress, lanes with the 30-minute stall flag, next action), 4.6.1 | Unit-tested against the mod's own strings; the panel driven in a pseudo-terminal (scroll region set and released, rows redrawn per activity) | The drift watch; no panel inside the agent's own full-screen interface |
| 5 | OS sandbox profile per lane; `owns:` read from the release type; spend ledger and cap; build slot; record committed | A write outside a lane's paths refused by the OS | `owns:` per artifact: schema, resolver and check in Wire (4.6.2); the registry content is wire-process-registry#75, merged and synced in 4.6.2 |
| 6 | `wire eval` and the core suite; routing for Claude through codex; ticket and migration releases; Run in Wire CLI from Studio; the tiers suite (seven cases across the four workload tiers) and routing from it: Claude `mechanical` and `lane_economy` to Haiku 5.5, `tiers_codex.mechanical` to GPT-6-Luna (4.6.1) | Core: OpenAI 5/5, Claude 5/5, Qwen 4/5. Tiers: GPT-6-Astra, GPT-6.1-Sol, Sonnet 5.5 and Haiku 5.5 7/7; GPT-6-Luna 6/7 (judgment); Qwen 5/7 (EVALS.md) | Approved names versus the convention: wire-process-registry#76, merged and synced in 4.6.2 (test: validate_approved_name_precedence.py); thirteen tiers cases from 4.6.2, three or four per tier, and the `claude` harness run live (EVALS.md) |
| 7 | `wire update`, `wire uninstall`; the agent in the Homebrew formula; the docs-site page | Unit-tested | Apple notarisation; a Linux run; Windows (not supported) |

## What stays fixed

- The CLI owns the release loop in code (runnable set, claim, lanes in
  worktrees, consolidation, the record). The agent runs steps.
- The Wire plugin for Claude Code stays the reference until the CLI reaches
  parity on the items in section 9, then both are supported and measured.
- Every phase ships with tests under `wire/tests/cli/` or `wire/tests/codex/`
  and a live run on the concept-run copy before it is called done.
- Specs live in the process registry; a phase that needs a spec change says
  so and raises the registry pull request first.

## The phases

| Phase | Goal | Agent time | Pacing item |
|---|---|---|---|
| 0 | Close the alpha: licences, versions, notices, release pipeline | 1 day | a public release step by a person |
| 1 | MCP servers through the CLI | 1 to 2 days | sign-in to each remote server by a person |
| 2 | A conversational session: talk to the agent, answer lanes mid-run, rulings inline | 2 to 3 days | none |
| 3 | The deep fork: `wire-agent` with Wire inside it | 4 to 6 days | Rust builds on three platforms; code signing by a person |
| 4 | Parity with the Wire mod in the session | 2 to 3 days | none |
| 5 | Enforcement and budget: OS-level tree ownership, spend ledger and caps | 2 days | a registry change (owns per release type) |
| 6 | Evals, model routing, the conflicts the run exposed | 2 to 3 days | a registry change (spec versus convention precedence) |
| 7 | Distribution: signed builds, Linux and Windows, update, docs | 2 days | Apple notarisation account; Windows signing |

Phases 1, 2 and 4 do not depend on the fork and can start now on unmodified
Codex; phase 3 then moves them inside the binary. Total: three to four weeks
of continuous agent time, with the public and signing steps as the gates.

## Phase 0: close the alpha (1 day)

- Ship `LICENSE`, `NOTICE` and `WIRE-CHANGES.txt` in the agent tarball
  (done locally; replace the release asset), add Codex and LiteLLM to
  `wire/third_party/manifest.yaml` and `THIRD_PARTY_NOTICES.md`.
- Stamp the fork's version (`5.0.0-alpha.1+codex-0.166.0`) so `wire-agent
  --version` says what it is; `wire version` reads the shipped version (done).
- A release workflow in GitHub Actions: build the agent on macOS arm64 and
  x86_64 and Linux x86_64 from the fork at a pinned tag, package, publish the
  pre-release and the formula. A person approves the workflow run.
- Decide and document the sign-in rule for the forked binary: API key by
  default; "Sign in with ChatGPT" only on unmodified Codex until OpenAI's
  position on open-source clients is confirmed in writing.
- Acceptance: `curl ... | sh` and `brew install wire` with no `WIRE_VERSION`,
  on a clean machine, run `wire doctor` and a typed command.

## Phase 1: MCP servers through the CLI (1 to 2 days)

What the plugin has: Atlassian, Fathom, Context7, Notion, Amplitude, Linear
and the warehouse servers in `.mcp.json`, used by review, sync, docstore
and migration commands.

- `wire codex-install` writes the plugin's server list into the install
  set's `.codex/config.toml` as `[mcp_servers.<name>]` entries (HTTP servers
  with OAuth, stdio servers with their commands), read from the same
  `.mcp.json` the plugin is built from, so the list has one source.
- `wire mcp list | login <server> | check` wraps Codex's own MCP commands and
  reports what a release's commands need against what is signed in, as
  `/wire:mcp` does in the plugin.
- Tool names: the specs name Claude Code's form (`mcp__fathom__search_meetings`);
  the dispatcher skill and the lane prompt carry the mapping to Codex's form,
  and the catalogue records which commands need which server.
- The hook applies the warehouse rules to MCP calls: `warehouse_spend: none`
  refuses BigQuery `execute_sql` and Snowflake `sql_exec` from a lane, as
  the Wire mod does; bytes billed from tool results feed phase 5's ledger.
- Acceptance: a review command through the CLI finds Fathom context; a
  generate command syncs a Jira or Linear issue; a migration audit reads the
  warehouse; each on a live server, recorded in `CONCEPT_RUN.md`.

## Phase 2: the conversational session (2 to 3 days)

Today the session is direction: text in, a plan, go, the commands run
headless. The gap against the plugin is that nothing can talk to you
mid-run. Codex already has the pieces: the `app-server` JSON-RPC protocol
(stateful, streaming, over stdio), and a `request_user_input` tool a model
can call.

- Replace `codex exec` for interactive work with a session held open on the
  app-server protocol. The session shows the agent's messages as they
  stream and lets you type back; a Wire command typed in the session runs
  in that same conversation, so follow-up questions have the context.
- Lanes keep running headless, but a lane that calls `request_user_input`
  (or reports `needs_ruling`) no longer parks by default: the question is
  shown in the session, your answer is relayed to the lane, and the lane
  continues. Unattended runs (`--yes --no-interaction`) keep the parking
  behaviour; the record shows which happened.
- Rulings inline: `/approve <artifact> [--final]`, `/park <artifact>
  <question>`, `/rule <id> <ruling>` in the session write `review_events`,
  parked decisions and `decisions.md` exactly as the plugin's instant
  commands do, through the CLI's record writer.
- The review flow: a review command in the session is a conversation with
  you, not a headless run; its stakeholder dialogue works as in the plugin.
  `wire run` still never dispatches a review.
- Acceptance: the orchestration lane that asked "Dagster, dbt Cloud or
  Airflow?" in the concept run gets its answer typed in the session and
  completes; a review is approved in the session and the record matches the
  plugin's.

## Phase 3: the deep fork, `wire-agent` (4 to 6 days)

The fork stops being branding and becomes the product's agent, with the
benefits a fork can give and nothing else changed:

- **A native Anthropic provider** in Rust, inside the binary: the Messages
  API with prompt caching, tool use and streaming, selected with
  `model_provider = "anthropic"`. The bridge and LiteLLM go away. Gemini
  through the upstream GCP provider, so one binary serves the three model
  families.
- **Wire inside the agent process**: `wire_status`, `wire_gate`,
  `wire_record`, `wire_lint` and `dbt` as native tools with compact output,
  the pattern dbt's Wizard measured (a build report of 150 tokens against
  1,300 of raw output). The lane rules move from a shell hook to the tool
  layer, where `cp`, `mv`, `sed -i` and `cd` are no longer blind spots.
- **Bundled framework**: the spec corpus, the catalogue, the authoring
  skills and the lane agents compiled into the binary (`include_dir`), so an
  install is one file and a repository needs no `.wire/codex-plugin/` copy.
- **Its own identity**: binary `wire-agent`, home `~/.wire/agent` (so it
  never collides with a person's own Codex), version stamped, the Wire mark
  on its welcome screen, "Wire" in its titles.
- **Tracking upstream**: rebase on upstream tags, one per Wire minor release,
  with the fork's tests (the snapshot tests that name "OpenAI Codex"
  re-recorded once) in CI.
- Acceptance: the concept run's three model families through one binary
  with no proxy; the Claude leg's cost within 10 percent of Claude Code's
  for the same lane (caching works); the install is one download.

## Phase 4: parity with the Wire mod in the session (2 to 3 days)

Everything the mod gives Claude Code, in the session:

- A status line: active release, claim, next action, context use, with a
  note at 85 percent as the mod's toast.
- The release context once per session in the agent's system prompt:
  parked decisions, last rulings, business-rules summary, iterations, claim,
  next action, within a line budget.
- The next command as a suggestion when the prompt is empty.
- The hard gate before destructive and warehouse-touching commands, with
  `--override-gate "<reason>"` recorded as the mod records it (typed runs
  have it; lanes get it at dispatch).
- The `Ran:` check on every orchestrator reply, with the miss recorded.
- Metrics in every log row from measured usage (done) and telemetry: the
  same `wire_command` event the plugin sends, with `invoked_by` and a new
  `harness` property, opt-out with `WIRE_TELEMETRY=false`.
- The compaction handoff: the handoff template as the session's compaction
  instructions and `/handoff` to write it.
- Acceptance: `wire/tests/schema/validate_mod_contract.py` extended to the
  CLI, so the two implementations are held to one contract.

## Phase 5: enforcement and budget (2 days)

- **Tree ownership at the operating-system level**: a lane's sandbox allows
  writes only under its `Owns:` trees (Codex's sandbox with per-lane
  writable roots on macOS and Linux), so the hook becomes a second line and
  `cp`, `mv` and `cd` stop mattering.
- **Owns declared per release type** in the registry (`owns:` on each
  artifact), replacing the CLI's fixed rule; a registry pull request.
- **Budget at dispatch**: `warehouse_spend: none | estimate_required |
  cap:<amount>`, the spend ledger at `lanes/_spend.jsonl` from bytes billed
  in warehouse tool results, a cap raising a parked decision, one build per
  warehouse project at a time. The same rules as the mod, in the CLI.
- **The record committed**: `wire run` commits `status.md` and the log with
  each consolidation, so a lane's merge and its record travel together.
- Acceptance: the fixtures in `wire/tests/core/` for lanes and budget run
  against the CLI unchanged.

## Phase 6: evals, routing and the conflicts the run exposed (2 to 3 days)

- **An eval suite per model**: five representative commands on a fixture
  release, output checked by the deterministic validators, run on each
  harness and model before it is allowed on a client-facing deliverable; the
  results table lives beside `CONCEPT_RUN.md` and gates `model-routing.yaml`.
- **Model routing per harness** filled in (`tiers_codex`, `tiers_anthropic`,
  economy models), so a planning command gets a stronger model and a
  mechanical one a cheaper one on every harness.
- **Spec versus convention precedence**: the run showed three models
  handling the approved-names-versus-naming-convention conflict three ways.
  The specs should say which wins and when a ruling is needed; a registry
  pull request, then a fixture that checks the three harnesses agree.
- **Releases built from tickets and the migration profiles** exercised
  through `wire run` and `wire work`, with the ticket-delivery fixtures.
- **Studio**: "Run in Wire CLI" beside "Run in Claude Code", and the session
  launching Studio.

## Phase 7: distribution and operations (2 days)

- Signed and notarised macOS binaries, Linux x86_64 and arm64, Windows
  x86_64, from the release workflow; the Homebrew formula carrying the
  agent; a Scoop or winget manifest.
- `wire update`, `wire uninstall`.
- A docs-site section built from `WIRE_CLI.md`; the Gemini CLI noted as
  not supported by the CLI (its users keep the extension).

## What each known gap maps to

| Gap against the Wire plugin (from `WIRE_CLI.md`) | Phase |
|---|---|
| No Wire mod: band, context section, next command, instant commands, hard gate, metrics, telemetry | 4 |
| Headless steps cannot ask you mid-run; reviews and setup are conversations | 2 |
| No MCP servers unless the harness has them | 1 |
| Claude billed by API key | none: Anthropic's terms; the eval and routing work (6) keeps the cost visible |
| Lane rules by hooks on Codex only; `cp`, `mv`, `sed -i`, `cd` unseen | 3 (tools) and 5 (sandbox) |
| Budget rules partial | 5 |
| Owns from a fixed rule | 5 (registry) |
| No telemetry, no Gemini CLI, no Studio launch | 4, 7, 6 |
| Other models vary | 6 |
| Ticket releases and migration profiles not exercised | 6 |
| Standalone agent macOS arm64 only, unstamped version, welcome screen unverified | 0 and 7 |
| Record left uncommitted | 5 |
| The bridge is the newest, least-tested part | 3 removes it |
| The fork buys only branding | 3 |

## Order and risks

Start with 0, 1 and 2 on unmodified Codex (they are harness features, not
fork features) while the fork's provider work (3) begins in parallel; 4
lands on whichever binary is current; 5 and 6 need their registry changes
agreed first; 7 closes. The risks: OpenAI's position on modified clients
and ChatGPT sign-in (phase 0 decides: API key by default); upstream Codex
moving under the fork (rebase per tag, not per commit); and the specs'
tuning to Claude (phase 6 measures it rather than assuming it). Nothing in
the plan removes the Claude Code plugin; parity is measured against it.
