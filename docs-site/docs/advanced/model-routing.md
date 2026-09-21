---
sidebar_position: 13
title: Model routing
---

# Model routing

**As of v4.0.0.** Not every Wire command needs the same intelligence, and paying frontier-model prices to render help text is as wasteful as asking a small model to set up an engagement. Wire therefore runs different commands on different Claude models, through two mechanisms that are independent of each other:

1. **Workload routing**: a command tagged with a workload tier always runs on that tier's model, whatever the session default. It is set per command at build time, and it applies on Claude Code only.
2. **Lane economy mode**: `budget.model_tier: economy` in a release's `status.md` makes the orchestrator dispatch delegated lanes on a lower-tier model. It is set per release by the director. See [The release director](./release-director#budget).

This page covers the first. Neither mechanism changes the record: `status.md`, `execution_log.md`, the precondition gate and validation run identically on every model, and the [execution log's Duration, Tokens and Cost columns](../getting-started/core-concepts#the-execution-log) show what each run consumed.

## Why

Wire's 300 or more commands do not need the same intelligence. Rendering help text, summarising a log or moving files by fixed rules wastes money and headroom on a frontier model, while engagement setup, autonomous orchestration and sprint planning underperform on a small one. Routing puts each command's floor and ceiling where its work is.

## The tiers

The vocabulary is fixed, and the mapping lives in one file, `wire/model-routing.yaml`:

| Tier | Model (stage 1) | Meaning |
|---|---|---|
| `mechanical` | `claude-haiku-4-5` | Deterministic, low-judgment work: doc rendering, log summarisation, fixed-rule migrations |
| `templated-generation` | session default | Template-driven artifact generation |
| `judgment` | session default | Validates and reviews needing interpretation |
| `planning` | `claude-fable-5` | Engagement setup, orchestration, adoption assessment, sprint planning |

Stage 1 maps only the extremes. The middle tiers stay on the session model until per-command token data (the execution log's metric columns) shows where a split pays, and a floor applies throughout: nothing that produces a client-facing deliverable goes below the session default. As such, a tier demotion needs an eval comparison, not intuition.

## Commands routed today

| Command | Tier | Model |
|---|---|---|
| `/wire:new` | planning | `claude-fable-5` |
| `/wire:autopilot` | planning | `claude-fable-5` |
| `/wire:adopt` | planning | `claude-fable-5` |
| `/wire:sprint-plan-generate` | planning | `claude-fable-5` |
| `/wire:migrate` | mechanical | `claude-haiku-4-5` |
| `/wire:utils-session-summary` | mechanical | `claude-haiku-4-5` |
| `/wire:help` | mechanical | `claude-haiku-4-5` |

Every other command inherits the session model, exactly as before.

## How it works

So how does a command end up on a particular model? A spec opts in with one frontmatter line:

```yaml
workload: planning
```

At build time, `build-packages.sh` resolves the tag against `wire/model-routing.yaml` and stamps the model into the generated Claude Code command's frontmatter (`model: claude-fable-5`), and Claude Code then runs that command on that model. There is no runtime logic and no hook: the routing is data, applied once per build.

Specs live in the process registry, so a tag change is a registry PR, whereas the model a tier maps to is a wire-repo change to `wire/model-routing.yaml` alone, which gives you one place to bump when models move on.

## Limits and overrides

- **Claude Code only.** Gemini CLI has no per-command model field, so the extension's commands are unaffected and run on the session model.
- **Whole command, not steps.** A tagged command runs entirely on its tier's model. Commands that mix planning with grunt work stay untagged, and their delegable steps are the lane mechanism's job.
- **Account access.** A stamped model the account cannot use fails that command's turn with a clear model error; `/model` and the session default are unaffected. Remove the tag's value in `wire/model-routing.yaml` (set it to `""`) to fall back to the session model fleet-wide.
- **Model switches reset the prompt cache**, so tiers are deliberately coarse, since a session alternating models turn by turn re-pays its context each time.

## Guardrails

- Tier 0 lint (`wire/tests/lint_specs.py`) fails on an unknown `workload` value in any spec, on registry tiers that drift from the vocabulary, on a malformed model id and on a build script that stops stamping.
- `wire/tests/utils/validate_model_routing.py` verifies the full chain (registry, spec tags and the committed `wire/dist/` command files) against an expected list. Adding or re-tiering a tag fails the test until the expected file is updated deliberately.
- The execution log's Tokens and Cost columns are the measurement loop: they show, per command run, what the routing saves or costs.
