---
sidebar_position: 6
title: A CLI session
---

# A CLI session

:::caution Experimental
4.6.0. The engagement below is fictional, and long output is shortened with `...`. The screens show the CLI's real formats.
:::

This walks through a morning's work on a `dbt_development` release, `02-data-foundation`, from opening the session to handing over. It assumes the CLI is [installed](./installing), the repository is set up with `wire codex-install`, an [API connection](./api-connections) is in place, and the engagement's [MCP servers](./mcp-servers) are added and signed in.

## 1. Open the session

In the engagement repository:

```
cd ~/code/acme-analytics
git pull
wire
```

The CLI shows the Wire mark, the engagement and its releases, the active release and a status line:

```
  Wire CLI 4.6.0 (experimental)
  Engagement: acme_analytics.
  Releases: 02-data-foundation, 01-discovery.
  Active: 02-data-foundation.
  Type `help` for the commands, `quit` to leave.

[Wire v4.6.0] 02-data-foundation (dbt_development) · 1 approved · 0 parked · claim: none
wire 02-data-foundation>
```

The active release is the one whose `status.md` changed most recently. `use 01-discovery` changes it; `releases` lists them all.

## 2. See where the release stands

```
wire 02-data-foundation> status
Release 02-data-foundation (dbt_development, phase design)
  business_rules               not applicable
  requirements                 complete
  workshops                    not applicable
  data_model                   runnable: generate
  dbt                          blocked: data_model.review required approved, was not_started
  semantic_layer               not applicable
  data_quality                 blocked: dbt.review required approved, was not_started
  deployment                   blocked: data_quality.validate required PASS, was not_started
Runnable, in order: data_model
Parallel set (lanes_max 4): data_model
Claim: none
Next: /wire:data_model-generate 02-data-foundation (data_model is runnable)
next: /wire:data_model-generate 02-data-foundation   (type `next` to run it)
```

Each artifact shows its state. A blocked one names the step it is waiting on. This is the same answer Wire Studio gives.

## 3. Give direction in plain English

You do not need to know the command names. Type what you want:

```
wire 02-data-foundation> get the data model drafted and checked, and tell me what has to happen before dbt can start
```

The model gets the release as data (states, runnable set, parked decisions, the last log rows) and the rule that it runs nothing itself. It answers in plain English and proposes the commands:

```
The data model is the next step: requirements are complete and approved. I would
generate it, then validate it. dbt is blocked until the data model has been
reviewed and approved, which is your ruling, not something I can run.

Run plan (one at a time, in the repository, recorded by each command):
  1. /wire:data_model-generate 02-data-foundation
  2. /wire:data_model-validate 02-data-foundation
go / adjust / cancel?
```

You can answer:
- `go` to run the plan;
- `adjust <what>`, for example `adjust only generate for now`, to get a new plan;
- `cancel` to run nothing.

```
go
Running: /wire:data_model-generate 02-data-foundation, /wire:data_model-validate 02-data-foundation
...
Ran: /wire:data_model-generate 02-data-foundation, /wire:data_model-validate 02-data-foundation
```

Each command runs through the harness as it would in Claude Code: the precondition gate first, then the spec, which writes the artifact and the record. If a command stops with a question (a setup choice, for example), the session shows it, you answer at the prompt, and the same conversation continues.

The session keeps the conversation between turns, so a follow-up such as "and which entities did it leave out?" has the context. `new` starts a fresh conversation.

## 4. Review and approve

A review is your decision, so Wire never runs it for you. Read the data model in your editor or in Wire Studio (`studio` in the session starts it). When the client has signed it off, record the approval:

```
wire 02-data-foundation> /approve data_model --final --as client --evidence https://acme.atlassian.net/browse/DATA-41
Recorded: data_model approved (client) by Jane Smith; review: approved
```

`--final` sets the review to approved. Without it, the approval is recorded as a review event only. The entry is the same one `/wire-approve` writes in Claude Code, so the plugin and Studio read it unchanged.

## 5. Run the release loop

With the data model approved, dbt is now runnable. Use `run` to let Wire dispatch it as a lane:

```
wire 02-data-foundation> run --once
Run plan for 02-data-foundation (harness=codex model=default; lanes_max 4):
  1. /wire:dbt-generate 02-data-foundation
     lane dbt; owns dbt/models, .wire/releases/02-data-foundation/artifacts/dbt; model default (rule 3: session default)
  Stops after this pass at the first review, block or parked lane.
go / cancel? go
MCP servers for this run: atlassian, context7, wire
Dispatching 1 lane(s) on codex...
```

The lane works in its own git worktree under `.wire/local/worktrees/`. It may only write the folders listed after `owns`. If it needs a decision, it asks:

```
  dbt asks: The source has both order_date and order_created_at. Which is the order date for the fact table?
  Your answer (blank to park it): order_created_at, converted to the client's time zone
  Recorded as R-3; resuming dbt...
  dbt: complete; merged wire/lane/02-data-foundation/dbt
Record committed: status.md, execution_log.md, decisions.md.
```

Your answer is recorded as a ruling (`R-3` in `decisions.md`) and the lane resumes where it stopped. A blank answer parks the question as a decision (`PD-n`) in `status.md` instead.

When the lane finishes, the CLI checks the worktree's changes. Clean work is merged with a merge commit. A lane that wrote the record files, or wrote outside its folders, is parked and not merged. The CLI then writes the artifact's outcome and one log row for the lane, and commits the record.

## 6. Run a single command

A Wire command name runs that command on the active release:

```
wire 02-data-foundation> dbt-validate
...
Ran: /wire:dbt-validate 02-data-foundation
```

## 7. Park a question and record a ruling

To hold a question for someone else:

```
wire 02-data-foundation> /park dbt "Should cancelled orders count towards revenue?" --awaiting client
Parked as PD-2: Should cancelled orders count towards revenue?
```

When the answer comes back:

```
wire 02-data-foundation> /rule PD-2 Exclude them -- confirmed by the finance lead on 5 November
Ruling R-4 recorded in decisions.md; PD-2 cleared from status.md
```

## 8. Hand over and leave

`/handoff` writes `lanes/handoff-<session>.md` from Wire's handoff template, so the next person (or your next session) can pick up. Then push the work:

```
wire 02-data-foundation> /handoff
Handoff written to .wire/releases/02-data-foundation/lanes/handoff-....md.
wire 02-data-foundation> quit
git push
```

## Session commands

| Type | What it does |
|---|---|
| Plain English | Direction: Wire proposes commands, waits for `go` |
| A Wire command name, e.g. `dbt-validate` | Runs that command on the active release |
| `status`, `next` | The release's state; run the next action |
| `run [--once] [--yes]` | One pass of the release loop |
| `/approve`, `/park`, `/rule` | Record a review approval, a parked question, a ruling |
| `use <release>`, `releases` | Change or list releases |
| `harness`, `model`, `provider` | Change the setting for this session |
| `exec <text>` | Send a raw prompt to the harness |
| `new`, `/handoff`, `studio` | Fresh conversation; write a handoff; start Wire Studio |
| `help`, `quit` | Help; leave |

## Outside the session

The same work runs as single commands, which suits scripts:

```
wire status 02-data-foundation
wire data_model-generate 02-data-foundation
wire run 02-data-foundation --yes --once
```

`wire run` exit codes: 0 done, 1 a problem in the status file, 3 plan not approved, 4 release claimed by someone else, 5 gate refused, 6 a lane was parked.
