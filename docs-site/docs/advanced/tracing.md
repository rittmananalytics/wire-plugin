---
sidebar_position: 10
title: Detailed Execution Tracing
---

# Detailed Execution Tracing

**Introduced**: v4.0.0

Every release already has an `execution_log.md`, with one terse row per command (`timestamp | command | result | a detail string capped at 120 characters`), and that is enough for a normal audit trail: what ran, when, pass or fail. What it cannot answer is "what actually happened inside that command", which files it read, what it inferred, what it proposed, what you decided, and why, and when a command has done something you did not expect, that is exactly the question you have.

Tracing is for that. It is a complete, structured, step-by-step record of every command's execution, off by default, local-only and yours to turn on when you actually want that depth, whether you are debugging something that went wrong or trying to understand exactly how an optional feature like the [data model registry](./registries) behaved on a specific engagement. In this page we will look at how you turn it on, where the trace goes, what gets logged and what tracing is not.

## Turning it on

```bash
export WIRE_TRACE=true
```

That is it: there is no command to run and no config file to edit. Every Wire command checks this on every invocation, and if it is unset or not `true`, nothing changes and there is zero overhead. Unset it (or set it to anything else) to turn it back off.

## Where it goes

The trace is written to `.wire/releases/<release_folder>/trace.jsonl` as JSON Lines, one event per line, append-only, sitting alongside that release's `status.md` and `execution_log.md`. Commands not scoped to a specific release write to `.wire/trace.jsonl` at the engagement level instead.

**This never leaves your machine.** Unlike the anonymous usage event Wire sends to Segment on every command (see the FAQ), trace files are plain local JSON in your own repo, and nothing about them is transmitted anywhere.

## What gets logged

There are three event types per command:

- `command_start`: once, before the workflow begins
- `step`: once per meaningful step within the command (not just its top-level numbered steps, since a step with distinct internal sub-parts gets one event per sub-part too)
- `command_end`: once, with the same result value that would go into `execution_log.md`

Every event carries the release and release type it ran under, together with a `detail` field with no length limit, which holds the actual account of what happened rather than a summary. Two events look like this:

```json
{"ts":"2026-07-05T14:20:11Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.1","step_name":"Resolve the registry location","result":null,"detail":"Checked wire/data-model-registry/ (not found - not the Wire source repo). Checked ~/.wire/data-model-registry/ (found - cloned via /wire:utils-data-model-registry-setup on 2026-07-01)."}
{"ts":"2026-07-05T14:20:19Z","release":"20260705_acme","release_type":"full_platform","command":"data_model-generate","event":"step","step":"1.5.2","step_name":"Resolve the vertical","result":null,"detail":"No confident vertical match for Acme (B2B SaaS, no dedicated saas vertical in the registry). Adjacent match found: subscription-commerce - proposed as a structural analogue for Acme's MRR/NRR model."}
```

That level of detail is exactly what would have made [the data model registry's automatic-detection behavior](./registries) visible without reconstructing it by hand after the fact: was the registry reachable, what did it search, what matched, what did not, what got carried into the generated model and why.

## What this is not

- **Not a replacement for `execution_log.md` or Telemetry.** Both continue exactly as before, and tracing is additive, for the subset of engagements that want much finer detail.
- **Not retroactive.** Turning it on only captures what happens from that point forward, and there is no way to reconstruct trace detail for commands that already ran before `WIRE_TRACE=true` was set.
- **Not a performance or cost concern when off.** The check is a single environment-variable comparison per command, and with it off (the default), nothing else happens.

See [`wire/specs/utils/tracing.md`](https://github.com/rittmananalytics/wire/blob/main/wire/specs/utils/tracing.md) for the exact mechanism. It is injected into every command at build time, the same way the [process registry](./registries) content is, so that it applies uniformly across all ~260 commands without any of them needing individual changes.
