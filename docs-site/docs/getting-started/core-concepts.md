---
sidebar_position: 4
title: Core Concepts
---

# Core Concepts

Whichever release type you run, and however you drive Wire, the same small set of ideas turns up in every session: a command that carries its own specification, an artifact that passes through three gates, a gate that stops a step running before the one it depends on and a record of what happened, kept in a status file and a log. This page describes the concepts that hold across every release, whichever way you drive Wire. Since 4.0.0 there are two ways. On Claude Code you can direct Wire in plain English: say what you want done and Wire works out which command that is from the release-type definition, runs it, tells you what it did and stops where a decision is yours. Or you can type the commands yourself, on Claude Code or Gemini CLI, exactly as in 3.x. Part 1 of this guide shows the first way through four worked releases and a ticket worked inside one of them; this page and the rest of the Technical Reference describe the machinery both ways share, and the commands are named throughout because that is what runs in either case.

> **Command notation:** Commands in this guide are shown in Claude Code format (`/wire:*`). If you are using Gemini CLI, drop the `/wire:` prefix and replace colons with spaces, so that, for example, `/wire:requirements-generate my_project` becomes `/dp requirements generate my_project`.

## Self-contained command architecture

What actually happens when you run a command? Every `/wire:*` command is a single, self-contained file, and the command file *is* the complete workflow specification, so there is no separation between a discovery layer and a logic layer. In Claude Code, these are `.md` files distributed as a plugin; in Gemini CLI, they are `.toml` files distributed as an extension.

```mermaid
sequenceDiagram
    participant U as You
    participant CC as Claude Code
    participant CMD as Plugin Command
    participant P as Project Data<br/>.wire/project/

    U->>CC: /wire:dbt-generate 20260216_live_pastoral
    CC->>CMD: Load command file (complete workflow spec)
    CMD->>CC: Prerequisites, templates, conventions, steps
    CC->>P: Read status.md (check prerequisites)
    CC->>P: Read design/data_model_specification.md (input artifact)
    CC->>CC: Generate code using templates + project context
    CC->>P: Write models/*.sql, models/*.yml
    CC->>P: Update status.md
    CC->>U: Confirm output + suggest next step
```

Each command file contains the full workflow inline, from 100 lines for a simple review command to over 1,500 lines for dbt generation. The same file runs whether you typed the command, the orchestrating session ran it in response to a plain-English directive or a lane agent ran it as its assigned task, and only the `Session` column of the execution log records which.

## The artifact lifecycle

How does an artifact get from nothing to something the client has signed off? Every artifact produced by the framework follows three gates:

- **Generate**: AI produces the artifact from upstream inputs and templates
- **Validate**: Automated checks run (naming, test coverage, completeness, etc.)
- **Review**: You or the client approves the artifact

```mermaid
stateDiagram-v2
    [*] --> not_started
    not_started --> generate_complete : generate
    generate_complete --> validate_pass : validate PASS
    generate_complete --> validate_fail : validate FAIL
    validate_fail --> generate_complete : fix and regenerate
    validate_pass --> review_approved : review Approved
    validate_pass --> review_changes : review Changes Requested
    review_changes --> generate_complete : revise and regenerate
    review_approved --> READY : downstream unblocked
    READY --> [*]
```

An artifact should not progress until all three gates are passed, and downstream artifacts check upstream readiness before they generate. When you direct Wire rather than type, generate and validate run for you, and the review gate is where Wire stops and asks: approve now, request changes or park for client sign-off.

## Directing rather than typing

**Since v4.0.0, on Claude Code.** You do not have to know which of 338 commands comes next. Say what you want done ("run what's next", "approve it and carry on", "start a new engagement from this SOW") and Wire computes the answer from the release-type definition, says in one plain sentence what it is about to do, sets the run out as a command-level plan and waits for your go when it is more than one command or touches a warehouse, runs it and stops where a decision is yours. Its report leads with the outcome in plain words and ends with a line naming the commands that ran, so you learn the command names as you go rather than up front.

Three tiers do the work:

| Tier | Who | Duties |
|---|---|---|
| **Release director** | One human per release | States intent, makes rulings, approves at gates, sets the budget |
| **Orchestrating session** | One session per release | Computes what is runnable, dispatches lanes, writes `status.md` and the execution log, runs the consolidation pass |
| **Lane agents** | 1 to 12, flat | One scoped task each, own tree, own state file, report once |

Everything else on this page applies unchanged. Every step runs the real Wire command, so the artifact lifecycle, the precondition gate, auto-validate, the status file and the execution log behave identically to typing it yourself. The three things that change are these:

- **What runs next** is computed from the release-type graph rather than remembered, by one shared procedure that `/wire:start`, `/wire:delegate`, Autopilot and the orchestrating session all read.
- **A review is never run without your decision.** At every review gate Wire asks for one of approve now, request changes or park for client sign-off. Parked decisions accumulate in `status.md` and are the first line of every session.
- **A release carries a claim**, so a second session working the same release offers to join as reviewer rather than dispatching into it.

Typing any `/wire:` command yourself always works, and the orchestrating session re-reads the record afterwards and carries on. Saying "you drive" hands control back to you for the rest of the session; "I'll drive" hands it forward again. To turn direction off for a whole engagement, set `orchestration.mode: manual` in `.wire/engagement/context.md`. Gemini CLI stays command-driven, since it has no skills or agents.

See [The Release Director Model](../advanced/release-director) for the full rules, the worked session and the lane contract, and [Agent Architecture](../advanced/wire-agent-architecture) for how the tiers, commands, skills and MCP servers fit together.

## The precondition gate

**Since v4.0.0.** What stops a step running before the artifact it depends on has been approved? Every `-generate`/`-validate`/`-review` command auto-delegates to a shared utility, [`precondition_gate.md`](https://github.com/rittmananalytics/wire/blob/main/wire/specs/utils/precondition_gate.md), before doing anything else. It reads the command's declared `preconditions` from its own front-matter, which is either a static list (for example "`data_model.review` must be `approved`") or the `dynamic` sentinel for the handful of artifacts (`mockups`, `pipeline_design`, `data_model`, `data_quality`, `dashboards`, `deployment`, `training`, `documentation`) whose correct precondition genuinely differs by release type. A `dynamic` precondition resolves at runtime from the current release's `wire/release-types/<type>.yaml`, which is the same file [Autopilot](../advanced/autopilot) reads to resolve execution order.

If the precondition is not met, the command **blocks by default**. You can override it, but only explicitly: the gate asks for your name and a reason, and records both in `status.md`'s `precondition_overrides` and in `execution_log.md` as an `override` result. As such, "I skipped a step on purpose" becomes a visible, attributable decision rather than something that just silently happened.

A precondition may instead be marked `enforcement: advisory`, where running without it is a real choice a consultant may legitimately make, and `business_rules` is the case that introduced it. An advisory gate warns, takes a one-line reason and records an `advisory_skip` rather than blocking. **Since v4.0.0** a director's ruling recorded in `decisions.md` satisfies a matching advisory gate without asking again, and the log row cites the ruling id. A **blocking** precondition, however, is never satisfied by a ruling: the recorded override below is the only way past one.

```mermaid
flowchart LR
    CMD["/wire:dbt-generate"] --> GATE{"precondition_gate\nmet?"}
    GATE -->|Yes| RUN["Run the workflow"]
    GATE -->|No| ASK["Block:\noverride, or stop?"]
    ASK -->|"Override\n(name + reason)"| LOG["Record in status.md +\nexecution_log.md"]
    LOG --> RUN
    ASK -->|Stop| END(("Command exits"))

    style GATE fill:#fce4ec,stroke:#c62828
    style LOG fill:#fff3e0,stroke:#e65100
```

## Automatic validation

**Since v4.0.0.** Validate used to be a separate step a consultant had to remember to run between generate and review. It no longer is: every `generate` command that has a matching `validate` command for the same artifact now runs that validate step automatically once it finishes writing the artifact, and folds the PASS/FAIL result straight into generate's own output, with no separate command and nothing to remember.

```mermaid
flowchart LR
    GEN["/wire:data_model-generate"] --> WRITE["Artifact written"]
    WRITE --> AUTO{"auto_validate\nfalse?"}
    AUTO -->|"No (default)"| RUN["Runs data_model-validate\nautomatically"]
    RUN --> RESULT["PASS/FAIL folded into\ngenerate's own output"]
    AUTO -->|Yes| SKIP["States plainly why, and that\nyou must run validate yourself"]

    style RUN fill:#e8f5e9,stroke:#2e7d32
    style SKIP fill:#fff3e0,stroke:#e65100
```

A handful of validate steps are expensive because they do real work beyond re-reading local files: `dbt-validate` runs an actual `dbt run`/`dbt test`, and some migration and semantic-layer validates query a live warehouse or BI tool directly. Those generate commands declare `auto_validate: false` in front-matter (see [command schema](https://github.com/rittmananalytics/wire/blob/main/wire/schemas/command-schema.md#auto_validate-generate-commands-only)) and skip the automatic run, stating plainly why and that you need to trigger `validate` yourself once you are ready to pay that cost, rather than paying it on every draft iteration of generate.

Either way, nothing changes about the gate that matters: `review` already requires `validate: PASS` for its own artifact as one of its declared preconditions (see above), enforced by the precondition gate regardless of whether validation happened automatically or manually. An `auto_validate: false` artifact can therefore never reach review unvalidated, since the opt-out only changes *when* validate runs, never *whether* it is required. A handful of artifacts have no separate validate step at all (`mockups`, `workshops`, `uat`, `viz_catalog`, `playbook`, Droughty's own umbrella `generate`) and this section does not apply to them either way.

## Git branching

Where should release work live in git? `/wire:new` enforces a mandatory branch check, and if you run it while on `main` or `master` the framework will stop and ask you to create a feature branch before any project files are created. It suggests `feature/{folder_name}`, but you can choose your own name.

This ensures that all release work lives on a branch that can be reviewed via pull request before merging.

## The status file

Each release has a `status.md` file at `.wire/releases/<release-folder>/status.md`, and this is the running instance of the delivery process, created by `/wire:new` when you select a release type and updated by every subsequent command. It has two roles:

1. **Human-readable**: release overview, notes, blockers and session history
2. **Machine-readable YAML frontmatter**: the instantiated process definition (which artifacts are in scope, which gates have been passed and what comes next)

The framework updates `status.md` automatically after each command.

**Since v4.0.0** it also carries three blocks for the director model: `budget` (concurrent lanes, warehouse spend, where to stop; absent means the defaults), `parked_decisions` (a list of decisions waiting on you, replacing the single `paused_at` value) and `agents.coordinator_session` (the release claim: who is driving, on which branch and when they last wrote). Where a release type declares profiles, the release also records which profile it is running.

## The execution log

Each project maintains an `execution_log.md` file that records a timestamped entry for every command that changes state:

```markdown
| Timestamp | Command | Result | Detail | By | Session | Duration | Tokens | Cost (USD) |
|-----------|---------|--------|--------|----|---------|----------|--------|------------|
| 2026-02-22 14:40 | /wire:requirements-generate | complete | Generated requirements spec (3 files) | Jane Smith | orchestrator [a1b2c3] | 18m 05s | 412876 | $3.18 |
| 2026-02-22 15:12 | /wire:requirements-validate | pass | 14 checks passed, 0 failed | Jane Smith | orchestrator [a1b2c3] | 6m 22s | 156430 | $1.02 |
| 2026-02-22 16:00 | /wire:requirements-review | approved | Reviewed by Jane Smith | Jane Smith | typed | 24m 10s | 98764 | $0.74 |
```

**Since v4.0.0** the log carries five more columns. `By` is the git user. `Session` says what invoked the run: `typed`, `orchestrator [id]`, a lane label such as `dbt-developer [staging 1/2]` or `autopilot`. `Duration`, `Tokens` and `Cost (USD)` record what the run took: the duration is measured by the command itself, while the token count and estimated cost are backfilled after the turn by the plugin's metrics hook on Claude Code, which reads the measured usage from the session transcript, so that the values are never estimated by the model, and on runtimes without the hook (Gemini CLI) they stay `n/a`. Rows written before 4.0.0 have four data columns; they stay valid and are never rewritten, and an old row is treated as unknown rather than assumed to be typed. Rows are append-only and never re-sorted, so `/wire:status-sync` reports a row whose timestamp precedes the one above it rather than repairing it, because re-ordering an append-only log destroys the evidence of what happened in what order.

### What each column holds

`Result` comes from a closed list, so the log can be counted rather than read line by line:

| Result | What it records |
|---|---|
| `complete` | a generate command finished |
| `pass` / `fail` | a validate outcome |
| `approved` / `changes_requested` | a review outcome |
| `override` | a precondition was overridden, or an advisory gate was satisfied by a ruling |
| `mode` | the director handed control over, or took it back |
| `created` / `archived` / `removed` | a release was created, archived or deleted |
| `activated` | a skill fired, rather than a command |

`Detail` is a one-line summary in most rows, but on an `override` row it follows a fixed shape, so the artifact, the step, the person and the reason can all be read out of it:

```
migration_inventory.review required approved, was not_started — overridden by Jane Smith: client demo tomorrow, inventory sign-off deferred to Monday
business_rules.review required approved, was not_started — ruling R-1 (Jane Smith): agree definitions at kickoff
```

The two forms are different events. The first is a consultant deciding to proceed past a block. The second is an advisory gate satisfied by a director's ruling, and it cites the ruling id.

### Skills appear in the log too

A skill that fires writes a row in the same table, with `skill` in the Command column and the skill's identifier in the Result column:

```markdown
| 2026-02-22 14:30 | skill | engagement-context | activated | Context loaded for new conversation | Jane Smith | typed | n/a | n/a |
```

One log therefore holds both halves of what the AI did on a release: the commands somebody asked for, and the skills that fired on their own.

### Reading the log back

The log is written so it can be used afterwards, not just kept. Two things read it:

- **[`/wire:status-sync`](../reference/management-commands#wirestatus-sync)** repairs the record when work done outside a command run has left it behind. It reports an out-of-order row rather than fixing it, because re-sorting an append-only log destroys the evidence.
- **The [`project-review` skill](../reference/skills#project-review)** reviews an engagement from the record. It reads the log, every `status.md` and the git history, and reports coverage against what the release type defines, where rework concentrated, every recorded override with its stated reason, how the work was invoked, measured effort and cost, and the work the git history shows happened with no command at all. It needs nothing outside the repository.

## The chain of derivation

Why does the order of artifacts matter so much? Each artifact constrains the next, so that by the time the AI generates LookML the dimension names, measure definitions and join paths are fully determined by upstream artifacts, and there is no room for improvisation.

```mermaid
graph LR
    SOW["SOW PDF<br/><i>Client scope</i>"]
    REQ["Requirements<br/><i>FR-1..FR-N, NFR-1..NFR-N</i>"]
    CM["Conceptual Model<br/><i>Business entities<br/>+ relationships</i>"]
    DM["Data Model<br/><i>Tables, columns,<br/>joins, seeds + ERD</i>"]
    DBT["dbt Code<br/><i>SQL models,<br/>YAML tests</i>"]
    LML["LookML<br/><i>Views, explores,<br/>measures</i>"]
    DASH["Dashboards<br/><i>Tiles, filters,<br/>layouts</i>"]

    SOW -->|"extract"| REQ
    REQ -->|"model"| CM
    CM -->|"informs"| DM
    DM -->|"generates"| DBT
    DBT -->|"generates"| LML
    LML -->|"generates"| DASH
```

## Specialist agents

Who actually does the work when a command runs? As of v3.9.4, Wire commands auto-delegate to one of thirteen specialist subagents: a `dbt-developer` agent that only knows dbt conventions, a `qa-agent` that is a pure critic with no generation responsibility, and so on. This happens transparently when you run individual commands, and to batch-delegate all pending work across an entire release you use `/wire:delegate <release-folder>`.

**Since v4.0.0** those same agents run as **lanes** under the director model. A lane writes its own artifact tree and its own state file, rewritten after each completed item so that a lost session costs at most the item in flight, and it does **not** write `status.md` or the execution log: the orchestrating session is the single writer of both, and its consolidation pass fails a lane that wrote the record itself. Outside orchestrated mode, delegation behaves exactly as it did in 3.x.

See [Wire Agents](../advanced/wire-agents) for the full agent roster and how delegation works, and [The Release Director Model](../advanced/release-director) for the lane contract.

## Research persistence

Technical research is easy to lose between sessions, so when the AI performs it during a session it automatically saves structured summaries to `.wire/research/sessions/YYYY-MM-DD-HHMM/summary.md`. The engagement-context skill checks these saved summaries when loading context, and if a relevant prior finding exists it is surfaced rather than re-running the same research.

This means:
- **Cross-release knowledge carries over**: research done during the discovery release is available when working on the delivery release
- **Re-starting a session does not lose context**: prior technical findings are always available
- **Less AI context consumed**: the AI reads a condensed summary instead of re-running the same web searches
