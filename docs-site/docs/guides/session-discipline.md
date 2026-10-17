---
sidebar_position: 2
title: Session Discipline
description: How to run Claude Code or Gemini CLI sessions on a Wire engagement so they stay reliable. One task per session, when to end and hand over, what Wire keeps for you, and the signs a session is degrading.
---

# Session Discipline

A coding agent's session gets less reliable as it gets longer. Each file read, test result, stack trace and changed decision stays in the context for every later turn. The early instructions get harder for the model to recall, and the session starts to drift: a naming rule set three hours ago is dropped, a fix brings back a pattern already corrected twice, or a long debug produces code that looks right and does not compile. Long sessions also cost more, because every turn pays for everything that came before it.

Wire now keeps most of the state that used to be lost between sessions. What it cannot do is decide when a session should end. That part is up to you, and this page sets out how.

## One task per session

A session starts when a task starts and ends when the task is validated and committed. A new task gets a new session.

On Wire, a task is usually one of these:

- One ticket, worked with `/wire:work <release> <ticket>`.
- One artifact step (generate, validate or review) or one approved run plan.
- One investigation with a stated question.

Avoid the kitchen sink session, where a modelling change, a dashboard fix and a pipeline question share one context. Each gets in the way of the others, and none is easy to review afterwards.

## Validate before you stop

Every change ends with the check that applies to it: the artifact's validate command, `dbt build` or `dbt test`, the LookML content validator, `dg check defs`. Do not commit output you have not checked. Wire's validate commands and the precondition gate already stop an unchecked artifact from moving forward; outside a command, the check is yours to run.

## Put standing rules in files, not in chat

A rule you correct mid-session is the first thing a long session forgets. Put rules that should hold for the whole engagement where every session reads them:

- Naming and modelling rules in the client's `.wire/conventions/dbt.yml` override, which the dbt checker reads.
- Decisions and rulings in the release's `decisions.md`, written when they are given.
- Project instructions in the repository's `CLAUDE.md` or `GEMINI.md`.

If you find yourself typing the same correction three times (a correction loop), stop. Write the rule into one of these files and start a new session.

## Scope investigations

"Investigate why the pipeline fails" tends to read fourteen files, list six possible causes and recommend none. Ask instead for the three most likely causes, ranked, before any fix. For a wide search, hand it to a lane or a subagent so the main session keeps a clean context and gets back one report.

## What Wire keeps between sessions

You no longer need to write a long handover by hand. Wire records the state as it goes.

| What would be lost | Where Wire keeps it |
|---|---|
| Which release is active and where each artifact stands | `status.md`, written after every command, and loaded by the `engagement-context` skill on the first message of every session |
| What ran, in what order, with what result | `execution_log.md`, one row per command and skill, with duration, tokens and cost |
| A ticket's plan, steps, decisions and pull request | `iterations/<ticket>.md`, written by `/wire:work` |
| What a run will do before it starts | The run plan, set out for go, adjust or cancel before two or more commands, a lane or a warehouse query |
| Scoped work done in parallel | Lanes, which work in their own tree and report once, so their file reads never reach your session |
| Decisions and rulings | `decisions.md`, written the moment a decision is given |
| Earlier technical research | Saved summaries under `.wire/research/`, surfaced when relevant |
| Work done outside a Wire command | `/wire:status-sync`, which compares the record with git and disk and repairs it with your confirmation |

To pick up in a new session, run `/wire:start`. It reads the record and proposes the next action. To summarise what a session did, for yourself or a client channel, run `/wire:utils-session-summary <release> session`. It drafts the summary from the execution log and sends nothing.

## When to end a session

End the session, commit, and start a new one when:

- The task is done, validated and committed.
- You are about to start a different task.
- The session shows any of the signs below.

A test for any session: if you would not be comfortable handing it to another consultant now, it is not finished. Either finish it or record where it stands.

## Signs a session is degrading

- **Hedging.** Answers grow vaguer, with more qualifications, than they were an hour ago.
- **Regressions on settled decisions.** A naming rule, pattern or ruling already agreed comes back wrong.
- **State that does not match the record.** The agent describes the release differently from `status.md` or the execution log.
- **Plausible but unchecked output.** Code that reads well and fails validation or does not compile.
- **Infinite exploration.** Many file reads and no decision.
- **The trust-then-verify gap.** You notice you have stopped checking the output because the session has been right so far.

Any one of these is a reason to stop, write down anything not yet on record (a ruling in `decisions.md`, a note on the ticket), and open a new session with `/wire:start`.

## See also

- [Working a Ticket](../using-wire/working-a-ticket)
- [The Release Director Model](../advanced/release-director): run plans, lanes and the single writer of the record
- [Core Concepts](../getting-started/core-concepts): the execution log and research persistence
