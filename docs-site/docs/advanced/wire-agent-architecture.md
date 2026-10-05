---
sidebar_position: 3
title: Agent Architecture
---

# Wire 4.0.0 Agent Architecture

When a release is running under Wire 4.0.0 there may be a person, a Claude Code session and several subagents all working in the same repository at once, and if you have to support, extend or simply trust that arrangement you need to know who does what, how the pieces talk to each other and where the record of the work lives. This note explains all three. It is based on the `release/v4.0.0` branch of the Wire source repo at commit `9a8672e0` (6 September 2026) and on the installed build of the same release, and it was written on a live Looker to Omni migration engagement, which is where its examples come from.

The short version is that Wire runs a release with three tiers. A person, the release director, decides what should happen. One Claude Code session, the orchestrating session, turns those decisions into Wire command runs. Underneath it, up to 12 lane agents each take one scoped piece of work and report back when it is done. Everything still goes through the same Wire commands it always did, so the record on disk (`status.md`, `execution_log.md`, `decisions.md` and the artifacts themselves) looks the same whether a person typed a command or an agent ran it. The rules for all of this live in `specs/utils/director_operating_model.md`, and the `release-director` skill is what applies them inside Claude Code. We will take the tiers from the top down, director first, then the orchestrating session, then the lanes. After that we will look at the commands, skills and MCP servers they all use before finishing with the runtime itself.

![The five layers of the Wire 4.0.0 agent architecture, and the record files each tier writes](/img/wire-agent-architecture/wire-agent-architecture-1-layers-simple.png)
*Diagram 1. The five layers of the architecture, and the record files each tier writes.*

## 1. The release director

The release director is one named person per release, and their job is to decide, not to do. In practice that means saying what they want ("run what's next", "carry on", "start a new engagement from this SOW"), making a ruling when the process needs one ("skip business rules, we'll agree the definitions at kickoff"), approving or parking work at review gates, setting the budget in plain words ("two lanes, nothing against a warehouse, stop at decisions") and handling the client conversations that sit around all of that. They can also hand the wheel over or take it back: saying "you drive" puts the session into manual mode for the rest of the conversation, and "I'll drive", or any new instruction, hands control back.

When a director opens a session in orchestrated mode, the first thing they see is the number of decisions waiting and what the questions are, which come from the `parked_decisions` list in `status.md`. The director either answers them or gives a new instruction, and the orchestrating session reads each message as one of five kinds of directive: start an engagement, run whatever can run, rule on a parked decision, answer a question or hand control back. It only asks for clarification when two readings of the message would lead to different work.

Before anything runs, the orchestrator says in a line what it is about to do, in plain words, and every report it makes ends with a line naming the commands that ran. When the directive would run more than one command, or anything that queries a warehouse, it goes one step further and sets the run out as a plan: one row per command, written in full, with what it may touch and the decision at which the run will stop, and then waits for go, adjust or cancel. That is deliberate, because a director who has never typed a Wire command still gets to learn what the thing they just approved is called, sees the shape of a run before it costs anything, and never has the command names become the headline.

Rulings are written down the moment they are given, not when they are used. They go into `.wire/releases/<release>/decisions.md` with an id, a timestamp, the director's name, the artifact and dependency they apply to, the decision itself and the reason. A ruling can satisfy an advisory gate, but it can never satisfy a blocking one; the only way past a blocking gate is the recorded override in the precondition gate, which needs a person's name and reason given at the time.

Reviews work the same way, in that none of them run without a ruling. When the work reaches a review gate, the orchestrator lays out a summary of the artifact, the validate result and whatever meeting notes or document-store comments the review spec gathers, then waits. The director can approve now, in which case the review command runs under their name. They can ask for changes, in which case the change list is recorded and generate runs again. Or they can park it for client sign-off, which adds a `parked_decisions` entry naming who needs to sign and writes no review row at all.

Orchestrated mode is the default on Claude Code. You can turn it off for a whole engagement by setting `orchestration.mode: manual` in `.wire/engagement/context.md`, or for one session by saying "you drive", and typing a `/wire:` command yourself always works, since the orchestrator re-reads the state afterwards and carries on from there. One person drives a release at a time. If someone else needs to work on the same release, they either join as a reviewer or become what the spec calls a "human lane": they own a named directory, work in manual mode inside it and hand their work back through a pull request.

![Six exchanges between the release director and the orchestrating session, with the file written at each step](/img/wire-agent-architecture/wire-agent-architecture-2-director-simple.png)
*Diagram 2. Six exchanges between the release director and the orchestrating session, with the file written at each step.*

## 2. The orchestrating session

So what is the thing the director is talking to? The orchestrating session is the ordinary Claude Code session you have open in the engagement repo. It runs on whatever model that session is using (the operating model asks for the most capable one available), and it comes to life through the `release-director` skill, once the `engagement-context` skill has loaded the engagement state, in any repo that has a `.wire/` directory, and only when your message is an instruction about the delivery work rather than a question about the code.

Every time you give it a directive it goes through the same sequence. It works out which mode it should be in (the runtime first, then anything said in the conversation, then the engagement setting, then the default). It works out which release you mean: one named in the message, failing that the one matching the current git branch or worktree, failing that the only release with a `status.md` write in the last seven days, and otherwise it asks rather than guessing. It re-reads the release's `status.md`, the release-type graph, `decisions.md` and the engagement `context.md`, because a plan formed three messages ago may already be out of date. It checks the release claim (more on that below), reports any parked decisions, works out what is runnable from the graph, applies the budget and tells you what it held back because of it, sets out the run plan and waits for your go where more than one command or a warehouse query is involved, then dispatches lanes and runs any foreground work. Finally it runs a consolidation pass, writes the record and reports once.

The record is the part the operating model is strictest about. In orchestrated mode the orchestrator is the only thing that writes `status.md` and `execution_log.md`, and lanes never touch either file.

| File | What the orchestrator keeps in it |
|---|---|
| `status.md` | The generate, validate and review state of every artifact; the `agents` block that holds the release claim; the `budget` block; the `parked_decisions` list |
| `execution_log.md` | One row per command run or skill activation, append only, with nine columns: timestamp, command, result, detail, who ran it, what invoked it (`typed`, `orchestrator [id]`, a lane label or `autopilot`), duration, tokens and cost |
| `decisions.md` | Rulings, written when given. Lanes can append their own modelling decisions here too |
| `lanes/<lane-label>.md` | One state file per lane. The orchestrator reads these and writes `status.md` and the log rows from them |
| `trace.jsonl` | An optional step-by-step trace, written only when `WIRE_TRACE=true`, and never sent anywhere |

The token and cost cells in the log deserve a note. The command writes them as `n/a`, and after the turn ends a hook in the plugin reads the measured usage from the Claude Code transcript and fills them in. The model never estimates them.

The release claim is how two sessions avoid working on the same release at once. Before dispatching anything, the orchestrator looks at the `agents.coordinator_session` block in `status.md`. If nobody holds the claim, it takes it. If the same person holds it from this or an older session, it carries on and refreshes the session id. If someone else holds it and wrote to `status.md` in the last 30 minutes, it does not dispatch, and offers to join as a reviewer or move to another release. If the other person has not written for more than 30 minutes, it offers to take over instead. The `last_write` timestamp is refreshed on every `status.md` write, and the same 30-minute figure is what counts as a stalled lane.

Before it tells you a lane's artifact is ready for a ruling, the orchestrator runs five checks. Do the files the lane says it wrote exist? Did validate run, and does its recorded result match what the lane claimed? Did the lane leave `status.md` alone? For anything that touched a warehouse, do the results check out against the warehouse itself rather than the lane's summary? And does a sample of the work stand up when read at full depth? These checks run whatever model the lanes were on.

One more thing on models. The session itself uses the session model, but four of the commands it is most likely to run are pinned to a specific one: `/wire:new`, `/wire:autopilot`, `/wire:adopt` and `/wire:sprint-plan-generate` carry `model: claude-fable-5` in their front-matter and run on that model regardless of the session default. Section 4 explains how that pinning works.

For a concrete example, the `status.md` for the Looker to Omni migration release this note was written on recorded orchestrated mode, a claim by the consultant's session on `main` taken at 21:56 on 6 September 2026 and one parked decision, PD-1, asking which Omni shared model the migration should write to. The release execution log had one row at that point: the activation of the `release-director` skill.

## 3. Lane agents

A lane is one specialist agent doing one scoped job, in its own directory, with its own state file. Lanes are "flat", meaning that a lane never starts agents of its own.

There are 13 specialists, each defined by an `AGENT.md` file under `agents/` in the plugin:

| Agent | What it covers |
|---|---|
| `discovery-analyst` | Requirements, workshops, discovery artifacts |
| `data-designer` | Conceptual model, data model, pipeline design, standard-mode mockups and viz catalog |
| `dashboard-mock-developer` | Interactive HTML mockups and viz catalog for dashboard-first releases |
| `mock-data-developer` | CSV seed data, and the later move from seeds to real data |
| `pipeline-engineer` | Fivetran, Airbyte and dlt connectors |
| `dbt-developer` | Staging, integration and warehouse dbt models |
| `semantic-layer-developer` | LookML views and explores, dashboards, Omni model and content batches |
| `orchestration-engineer` | DAGs, scheduling, orchestration migration |
| `data-quality-engineer` | Tests, Droughty QA, field docs, UAT |
| `migration-specialist` | Audits, inventory, strategy, plan, target setup, parity, cutover |
| `delivery-lead` | Deployment, kickoff, training, playbooks |
| `agentic-data-stack-developer` | Canonical models, knowledge skills, agent configs, eval suites |
| `qa-agent` | Validation only, across all release types. It never generates anything |

A definition has seven front-matter fields: the agent id, a description, the model, the Wire commands it is allowed to run (`specs`), the skill files loaded into its context (`skills`), the MCP servers it needs (`mcp_requirements`, for example `bigquery` and `github`) and an `output_contract` listing the status fields and directories it may write. The body of the file describes the role, what the agent always does, what counts as done, what it must not do and the lane contract.

All 13 definitions set `model: claude-opus-4-8`. A director who sets `model_tier: economy` in the budget gets lanes dispatched on a lower-tier model instead, although the spec does not name which one. The consolidation pass runs either way, so the choice of model changes how much that pass finds, not whether it happens.

To start a lane, the orchestrator uses Claude Code's Agent tool with `subagent_type` set to the agent id, for example `wire:dbt-developer:AGENT`. The agent definition becomes the subagent's system context, and the lane runs on the same Claude Code account and key as the main session. The prompt it receives is the "lane brief", which always has the same ten fields:

```
Lane:        <label, e.g. conceptual_model or dbt-developer [staging 1/2]>
Release:     <release folder>
Task:        <the Wire command(s) to run, in order>
Owns:        <the only directories this lane may write>
State file:  .wire/releases/<release>/lanes/<label>.md
Resume:      Read the state file first; skip completed items.
             Rewrite it after each completed item, not at the end.
Budget:      <this lane's share; the warehouse_spend setting>
Flat:        Do not spawn sub-agents. If bigger than one lane, say so and stop.
Status:      Do not write status.md or execution_log.md.
Report:      Report once: complete, stalled, or needs a ruling.
```

The orchestrator also sets `WIRE_INVOKED_BY=lane` in the lane's environment, so that both the telemetry event and the log row record what invoked the run.

Every definition and every brief restate the same five rules. Rewrite your state file after each completed item, so that losing the session costs at most the item in flight. If you are restarted with the same brief, read the state file first and skip what is already done. Write only inside the directories you own, and commit those files by name, never with `git add -A`. Leave `status.md` and `execution_log.md` alone (appending to `decisions.md` is fine). Stay flat and report once, when you finish, stall or hit a decision you cannot make. Progress lives in the state file, not in chat.

Where does the parallelism come from? It comes from the shape of the release graph rather than from counting items. If two artifacts are runnable and neither depends on the other, they become two lanes, up to the `lanes_max` budget setting, which defaults to four, and anything beyond that queues in dependency order. Some artifacts are "interactive", meaning their generate step needs input from the person as it goes; mockups on a dashboard-first release is the usual case, and those run in the foreground with the director, never as a lane. The orchestrator never polls a lane to ask how it is getting on. It reads the state files, and a lane that has not written its state file for 30 minutes is treated as stalled, at which point its remaining items can be handed to a fresh lane.

Three agents split big jobs into batches. The dbt developer does it when any layer has more than five models: batches of five, up to eight per layer, with staging finished before integration starts and integration before warehouse. The semantic-layer developer batches by explore, three at a time up to six batches. The migration specialist batches source tables, ten at a time up to eight batches. Each batch counts as a lane against `lanes_max`, and the orchestrator only marks the artifact complete once every batch in the wave has finished.

![The orchestrating session computing the runnable set, dispatching three lanes within the budget, and consolidating their reports](/img/wire-agent-architecture/wire-agent-architecture-3-lanes-simple.png)
*Diagram 3. The orchestrating session working out what is runnable, dispatching three lanes within the budget and consolidating their reports.*

Three rules keep lanes from treading on each other. A lane that needs its own branch works in a separate git worktree and never switches the main checkout. Build locks are held for a single build and released between builds. Only one build runs per warehouse project at a time.

Outside orchestrated mode the same agents are still used, just differently. A single generate or validate command checks whether its specialist's definition exists and, if so, hands the work to that subagent, and in that mode the subagent updates `status.md` itself, exactly as it did in 3.x.

![One dbt-developer lane running /wire:dbt-generate through the gate, the steps, validate and its state file, with the skills it loads, the tools it calls and what it writes](/img/wire-agent-architecture/wire-agent-architecture-4-lane-internals-simple.png)
*Diagram 4. One dbt-developer lane running `/wire:dbt-generate`: the gate, the steps, validate and the state file, plus the skills it loads, the tools it calls and what it writes.*

## 4. Wire commands

Everything the three tiers do ends up as a command run, so it helps to know what a command file contains. The installed 4.0.0 build has 334 command files under `commands/`: 93 generate, 88 validate, 82 review and 71 others covering engagement setup, sessions, status, migration tooling and utilities. Each is a Claude Code slash command, which is to say a markdown file that Claude Code loads when someone types or invokes `/wire:<name>`, with the release folder arriving in `$ARGUMENTS`.

Open one and you will find the same shape every time. The front-matter carries a description and an argument hint, plus a `model:` line on the seven commands that are pinned to a model. Then come the user input and path configuration (`.wire/` in the repo, `${CLAUDE_PLUGIN_ROOT}/specs/` for shared specs), a tracing section that only does anything when `WIRE_TRACE=true`, and, on 82 of the 92 generate commands, an automatic validation section: generate runs its own validate step and folds the result into its output, unless the spec sets `auto_validate: false` because validate would run real code or query a live system. After that is the workflow specification proper, with its own front-matter (`command`, `artifact`, `domain`, `release_types`, `action_type`, `logs_execution`, `inputs`, `preconditions` and `delegates_to`), a pointer to the auto-delegation utility for its specialist agent, the numbered steps, the embedded templates and the list of output files. The file ends with the execution logging section.

The precondition gate runs first in every generate, validate and review command. It takes the artifact's `depends_on` list, either from the command's own front-matter or, where that says `dynamic`, from the release-type graph under the active profile, and checks each entry against `status.md`. If something is unmet, it blocks. An unmet advisory entry with a matching ruling passes, and the log cites the ruling id. Any other override has to be recorded with a person's name and reason as an `override` row.

The graph itself is 12 YAML files under `release-types/`: `agentic_data_stack`, `bi_migration`, `dashboard_extension`, `dashboard_first`, `dbt_development`, `discovery_shape_up`, `droughty`, `enablement`, `full_platform`, `pipeline_only`, `platform_migration` and `sop_discovery`. Each lists its phases and artifacts, with an id, a command, whether it is required, a sequence number and `depends_on` entries marked blocking or advisory, plus optional profiles that switch phases on or off. The runnable-set procedure, the precondition gate, `/wire:start`, `/wire:delegate` and `/wire:autopilot` all read this one file, which is why they cannot disagree about what comes next.

As for what a command writes: the artifact files go under `.wire/releases/<release>/`, written by the command directly. The `status.md` entry and the execution log row are written by the command when it was typed or auto-delegated, and by the orchestrator when the command ran inside a lane. A lane writes its own state file after each item. Non-obvious choices go into `decisions.md`. If a tracker or document store is configured, the command updates the Jira or Linear issue and the Confluence or Notion page through the sync utilities. Tracing, when on, adds to `trace.jsonl`. Separately from all of that, the plugin's prompt-expansion hook sends one anonymous telemetry event per `/wire:` run carrying an `invoked_by` value, and its stop hook fills in the token and cost cells of the last log row after the turn ends.

A single command runs one step after another inside one session. The parallelism in Wire comes from the orchestrator dispatching independent artifacts to separate lanes at the same time, and from the fan-out batches described above. The budget bounds all of it: `lanes_max`, `warehouse_spend` (where `none` refuses any lane whose command would query a warehouse) and `stop_at`.

"Workload routing" is the mechanism behind the pinned models. A spec can carry `workload: <tier>`. When the plugin is built, the tier is looked up in `wire/model-routing.yaml` and the model id is stamped into the command's front-matter. There are four tiers: `mechanical` maps to Haiku 4.5 and `planning` maps to Fable 5, while `templated-generation` and `judgment` are left on the session model for now. Seven commands are stamped today: `new`, `autopilot`, `adopt` and `sprint-plan-generate` on `claude-fable-5`, and `migrate`, `utils-session-summary` and `help` on `claude-haiku-4-5`. Everything else runs on the session model. This is a separate mechanism from the lane economy setting in the budget.

Underneath, the Claude Code features in play are slash commands from `commands/*.md`, plugin packaging through `.claude-plugin/plugin.json`, the `model` front-matter field, a function-hook module named in `hooks/hooks.json` (the Wire mod, `hooks/register.ts`, for telemetry and the metrics backfill, from 4.1.0), the Agent tool for lanes, MCP tools, the Bash tool for git, `gh`, the Omni CLI, `bq`, dbt and Python, git worktrees and a forced output style.

## 5. Wire skills

If commands are what Wire does, skills are how it behaves while doing it. The build ships 69 skills under `skills/`, each a `SKILL.md` with a name, a description and a list of triggers. Claude Code loads a skill when the conversation matches its triggers or when someone invokes it by name. Skills do not write artifacts. They shape how the session and the lanes behave, and each activation adds a `skill | <id> | activated` row to the execution log.

They fall into four groups. The control skills run the show: `engagement-context` loads the engagement and release state at the start of a conversation; `release-director` is the orchestrating session's operating procedure, the thing that resolves mode, release and claim, reports parked decisions, works out the runnable set and dispatches; and `fathom-sync` pulls new client call transcripts once per session where a client domain has been set. The domain knowledge skills (`dbt-development`, `droughty`, `lookml-content-authoring`, `omni`, `dagster`, `fivetran`, `airbyte`, `metabase`, `snowflake-development` and the rest) carry naming conventions, validation rules and platform procedures, and they are loaded into a lane through the `skills` list in its agent definition, and into the main session whenever you work outside Wire commands. The `omni` skill wraps the nine upstream skills from `exploreomni/omni-agent-skills`, which are installed separately. The writing standards are the `technical-writing` skill and the `plain-language` output style, which is forced on for the plugin. Finally, `wire-release`, `wire-usage-analysis` and `research` look after the framework itself and save research findings under `.wire/research/sessions/`.

Skills only exist on Claude Code. Gemini CLI has neither skills nor agents, so Wire there always runs in manual mode with typed commands.

## 6. MCP server tools

How does any of this reach the systems outside the repository? MCP (Model Context Protocol) servers are how the session and the lanes reach warehouses, trackers, document stores and meeting transcripts, and alongside the Bash tool they are the only way a command touches anything external.

The plugin ships an `.mcp.json` with six servers: `atlassian`, `fathom`, `context7`, `coupler-io`, `airbyte` and `amplitude`. RudderStack is not bundled: its server runs through a local `mcp-remote` bridge that opens a browser sign-in every time it starts, so it is added per engagement in `.claude/settings.json` only where the client uses it (the `rudderstack` skill shows the block). Others, such as BigQuery, Looker, Omni Analytics, Notion, Linear and Slack, come from your own Claude Code configuration. All of them authenticate through Claude Code's OAuth flow, and only the URL and transport are stored, never a credential.

In practice the warehouse servers (BigQuery or Snowflake) are used by the dbt developer, the QA agent, the migration specialist, the semantic-layer developer and the validate commands for schema and query checks. Atlassian or Linear handle issue tracking from generate and review commands and from `/wire:status` reconciliation. Confluence or Notion act as the document store: generate commands publish to it and review commands fetch the comments back. Fathom supplies meeting transcripts to review commands, the discovery analyst and `fathom-sync`. Context7 is for library documentation during development, and Amplitude for the product analytics skills. The agent definitions say what each needs: 12 of the 13 want `github` and eight want `bigquery` or `snowflake`, while the discovery analyst alone wants `fathom`. A lane inherits whatever MCP connections the session has.

`/wire:mcp check <release>` tells you whether you are ready. It reads `status.md`, works out which servers that release needs and probes each with a five-second timeout, then reports connected, auth required, unavailable or not configured. On the engagement this note was written on, two of the configured servers failed to connect on the day (Linear returned a 404 and RudderStack timed out), which is exactly the situation the check exists to catch.

If the BigQuery server is unreachable, commands that read or write BigQuery fall back to the `bq` command-line tool automatically, call by call, with `--location` set explicitly from `status.md`. Some systems are reached by command-line tools rather than MCP in any case: the Omni CLI, the Looker SDK through `LOOKERSDK_*` environment variables, dbt, git and `gh`.

## 7. Claude Code and the operating system

Claude Code is the runtime for all three tiers. The orchestrating session is a Claude Code session open in the engagement repo, and lanes are Claude Code subagents started by the Agent tool inside it. Commands, skills, agents, hooks and the output style all arrive as plugin features, loaded from the plugin cache at `~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/`. The plugin comes from the `wire-plugin` marketplace as `wire`, currently `4.0.0`.

On the machine itself, the Bash tool runs git, `gh`, the Omni CLI, `bq`, dbt and `python3`. The Wire mod is a TypeScript module Claude Code runs itself, with no separate runtime; it reaches the network and files only through Claude Code. The `.wire/` tree in the repo is the system of record, with git as its history and its transport. Lanes that need a branch get a git worktree. Runtime settings travel as environment variables: `WIRE_INVOKED_BY`, `WIRE_TRACE`, `WIRE_TELEMETRY`, `WIRE_METRICS` and the Looker and Omni credentials. The anonymous telemetry id lives at `~/.wire/telemetry_id`.

Claude Code's permission mode decides what the session and its lanes are allowed to do. For unattended runs against live systems the recommended setting is `acceptEdits` plus an explicit allowlist in `.claude/settings.json`. The migration engagement this note was written on ships one with eight Bash patterns: git clone, git inside the LookML snapshot, git ls-remote, omni, python3, date, mkdir and ls. Anything outside the list fails visibly in the turn output, which is what you want. `--dangerously-skip-permissions` is not used against live systems.

You do not need a person at the keyboard. `claude -p "<text>"` runs a single turn and `claude -p -c "<text>"` continues the same conversation. On that engagement, a `harness/run_test.sh` script uses that to send turns 1 to 5 of the migration test script, with `--output-format stream-json` rendered readable by `harness/format_stream.py`, everything appended to `harness_run.log` and a gate pattern checked against each turn's final text before the next one is sent. Turn 6, the cutover, is deliberately not in the harness, because that is a ruling a person gives in an interactive session. The record does not care whether a run was headless or interactive; it looks the same either way.

Nothing assumes a long-running process. Lanes die with the session that started them, and because of the state files that costs at most the item that was in flight. A new session re-reads the state, resolves the claim and carries on. Work that has to run unattended belongs in a scheduled routine or a CI job, not in a lane.

There are two other runtimes to be aware of. Gemini CLI runs the same commands but has no skills, agents or per-command model field, so it is manual mode only. The VS Code extension (`wire-vscode`, version 3.10.19) is a sidebar over the `.wire/` files with a command picker; it does not take part in orchestration.

## Diagram sources

The diagrams were drawn with Claude Design using the Rittman Analytics design system: Google Sans with Inter as the fallback, IBM Plex Mono for file and command names, indigo `#4F60FF` as the primary colour, ink `#181B25` for the director tier, the mint and indigo tints for lane and command cards, 12 px card corners and 1 px `#E1E1E9` borders. The tokens come from the kickoff deck's `colors_and_type.css` in the Wire plugin.

There are two sets. The simple set is the one embedded above: one line per tier, fewer boxes and no titles, so that each diagram reads at a glance. The detailed set adds the file names, the record each tier writes and the steps inside a lane, and is the one to reach for when you need the mechanism rather than the shape:

- [Layers (detailed)](/img/wire-agent-architecture/wire-agent-architecture-1-layers.png)
- [Director and orchestrator (detailed)](/img/wire-agent-architecture/wire-agent-architecture-2-director.png)
- [Lane dispatch (detailed)](/img/wire-agent-architecture/wire-agent-architecture-3-lanes.png)
- [Lane internals (detailed)](/img/wire-agent-architecture/wire-agent-architecture-4-lane-internals.png)

All eight PNG exports are 2880 by 1800. The editable canvas and the artboard sources (`Main.dc.html`, `DirectorOrchestrator.dc.html`, `LaneDispatch.dc.html`, `LaneInternals.dc.html` and their simple variants, with `canvas.json`) are kept with the engagement that produced them. To change a diagram, edit its source and re-export the PNG, and keep the artboard names as they are between revisions.
