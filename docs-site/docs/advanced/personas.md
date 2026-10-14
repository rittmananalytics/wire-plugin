---
sidebar_position: 3
title: Personas
---

# Personas

Every Wire command used to give the same output to everyone, but on a delivery team people need different things from the same command. A delivery manager running `/wire:status` wants to know whether the release will close on time and what is waiting on them, while an analytics engineer running the same command wants to know which models to build next and what is failing. Without a way to ask for that, people kept their own instructions in local files, and the next delivery manager on another engagement started again from nothing.

A persona is the role you play on an engagement. A command that has a variant for your role shows what that role needs; every other command behaves exactly as it did before. In this chapter we look at the roles Wire knows about, how you set yours, how it follows you between machines, and what `/wire:status` shows a delivery manager.

## Which personas are there?

Wire has a fixed list, so that output is consistent from one engagement to the next.

| Persona | What it focuses on |
|---|---|
| `delivery-manager` | On time or late, blockers, decisions and sign-offs waiting on you, risks to the release date |
| `analytics-engineer` | Your assigned tickets, models to build or fix next, failing tests, open review comments |
| `data-engineer` | Pipelines, ingestion and orchestration state, failed runs, source access still missing |
| `engagement-lead` | Across releases: progress against plan, budget and buffer, client-facing risks |

The first command with a persona variant is `/wire:status`, for the delivery manager. Other commands and personas will follow once we can see that this one is used.

## How do I set my persona?

Run `/wire:persona` in the engagement repository:

```
/wire:persona                          your persona here, where it comes from, and the team's
/wire:persona set delivery-manager     set yours
/wire:persona clear                    remove it
```

Your persona is per person and per engagement. On one engagement there might be a delivery manager and two analytics engineers, each with their own entry, and the same person can be the delivery manager on one engagement and an analytics engineer on another.

For a single run you can ask for a different view without changing anything, by adding `--as` to the command:

```
/wire:status --as delivery-manager
```

## How does my persona follow me to another machine?

`/wire:persona set` writes your entry into the engagement's team roster, `.wire/engagement/team.yml`, which is committed with the rest of the release record. Wire finds your entry by matching your git `user.email` against the emails listed for each person:

```yaml
team:
  - name: Jane Smith
    emails: [jane.smith@example.com, jane@laptop.example]
    persona: delivery-manager
  - name: Raj Patel
    emails: [raj.patel@example.com]
    persona: analytics-engineer
```

Because the roster travels with the repository, any clone on any laptop or workstation finds your persona with no setup. Many people commit under a different email on different machines, so when you run `/wire:persona set` on a machine whose email is not yet listed, Wire adds that email to the entry with your name rather than creating a second entry.

> **NOTE:** Your role on an engagement is not private information. The release record already shows who ran each command, and keeping roles in the shared record is what lets a report say "waiting on Raj Patel" rather than "waiting on an engineer".

If you want a different persona on one machine only, `/wire:persona set <persona> --local` writes an override to `.wire/local/persona.yml`, which is git-ignored and never shared. `/wire:persona clear --local` removes it again.

## Which setting wins?

Wire takes the first of these that is set:

1. `--as <persona>` on the command, for that run only.
2. The `WIRE_PERSONA` environment variable, for unattended sessions.
3. This clone's override, `.wire/local/persona.yml`.
4. The team roster, `.wire/engagement/team.yml`, matched on your git email.

An unknown value, such as a misspelt `--as`, gives no persona rather than falling through to the next source, and Wire says so in one line. With no persona at all, commands run exactly as before and `/wire:status` ends with a one-line tip showing how to set one. A missing persona never stops a command.

## What does a delivery manager see from /wire:status?

The delivery-manager report is a dashboard of one release, readable in about two minutes. It comes from a worked example on a live engagement, where a delivery manager had replaced the default report with their own instructions.

**Which release.** Wire works this out from your branch. A branch that a release's claim records, or that names a release folder (`release/02-dbt`, `02-dbt/data_model`), gives that release, in the same way `/wire:start` picks the active release. With only one release, that one is used. On a ticket or feature branch, Wire finds the release branch it was cut from. On `main`, or when the branch could belong to more than one release, it asks. Naming a release on the command always wins.

**A summary table first,** one row each for tickets closed, points closed, the sprint and working days left, the schedule, blockers and the steps that need you. Each row is marked `Green`, `Amber` or `Red` with a reason of a few words.

**Then four short tables,** with empty ones left out:

1. Work slices not yet complete, with their tickets.
2. Artifacts not yet ready, each with the next command; the ready ones as a count.
3. Open questions you can answer, found in the business rules, the tickets, the decisions and the latest call notes.
4. Steps needed from you: reviews, approvals, sign-offs, pull requests to merge and workshops to run. Where a step waits on someone else, the report names them from the roster.

**It ends with three prompts** you can paste to dig into any section.

The report covers that release only, including its own ticket project, so work outside it stays out even when a call mentions it.

## Does a persona change the record?

No. A persona changes what a command shows, never what it writes: `/wire:status` updates the same files and syncs the tracker in the same way whatever your persona. The only file a persona writes is the team roster, through `/wire:persona`.

Each run records the persona it was made as, so that we can see whether personas are used before extending them to more commands. The execution log's Session column reads, for example, `typed as delivery-manager`, and the `wire_command` telemetry event carries a `persona` property.

## Adding a persona variant to a command

For framework contributors: a command declares the personas it has a variant for in its front matter, `personas: [delivery-manager]`, and adds one section per persona headed exactly `## Persona: <id>`, saying what the command shows for that role. The spec lint fails a listed persona without its section, an id that is not in the list, and a section that is not listed. The convention is `specs/utils/personas.md`; the lookup and roster logic is in `scripts/persona.py` and the branch rule in `scripts/release_scope.py`, both tested under `wire/tests/core/`.
