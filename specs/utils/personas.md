---
description: Shared convention for personas (wire#301). The persona list, how a person's persona is found, how a command declares and writes a persona variant, and how the persona is recorded with each run
---

# Utils: Personas

A shared convention, not a command. It is cited by every command whose front
matter lists `personas:` (first `/wire:status`) and by
`specs/utils/execution_log.md` and `specs/utils/telemetry.md`.

## Purpose

Every Wire command gives the same output to everyone. On a team, people need
different things from the same command: a delivery manager running
`/wire:status` wants to know whether the release will close on time and what
is waiting on them; an analytics engineer wants to know which models to build
next and what is failing. Without a way to ask for that, people keep their
own instructions in local files and the next person on another engagement
starts again.

A persona is the role a person plays on an engagement. A command that has a
variant for that role uses it; every other command behaves as before.

## The persona list

A fixed list, so output is consistent across engagements. Personas defined by
an engagement may follow once these are used.

```yaml
personas:
  - id: delivery-manager
    name: Delivery manager
    focus: On time or late, blockers, decisions and sign-offs waiting on them, risks to the release date
  - id: analytics-engineer
    name: Analytics engineer
    focus: Their assigned tickets, models to build or fix next, failing tests, open review comments
  - id: data-engineer
    name: Data engineer
    focus: Pipelines, ingestion and orchestration state, failed runs, source access still missing
  - id: engagement-lead
    name: Engagement lead
    focus: Across releases, progress against plan, budget and buffer, client-facing risks
```

`wire/scripts/persona.py` and the spec lint read this block. Change the list
here only.

## Finding the persona

A persona is per person and per engagement: on one engagement there can be a
delivery manager and two analytics engineers, each with their own, and the
same person can have a different role on another engagement. Take the first
of these that is set:

1. `--as <persona>` on the command, for this run only.
2. The `WIRE_PERSONA` environment variable. Unattended sessions and agents use it.
3. `.wire/local/persona.yml` (`persona: <id>`): an override for this clone
   only. `.wire/local/` is git-ignored.
4. The team roster, `.wire/engagement/team.yml`, committed with the record:
   the entry whose `emails` include this clone's git `user.email`. Because it
   is committed and matched on email, a person's persona follows them to any
   clone on any machine.

```yaml
team:
  - name: Jane Smith
    emails: [jane.smith@example.com, jane@laptop.example]
    persona: delivery-manager
  - name: Raj Patel
    emails: [raj.patel@example.com]
    persona: analytics-engineer
```

Set it with `/wire:persona set <persona>` (`specs/persona.md`), which runs
`python3 <wire>/scripts/persona.py set <persona>`. Commands find it with
`persona.py resolve [--as <persona>]`, which prints the persona and where it
came from, or `none`. An unknown value is reported and gives no persona; it
does not fall through to the next source. Say so in one line.

A person's role on an engagement is not private: the record already shows
who ran each command. Keeping it in the shared record is what lets it follow
them between machines, and lets a report name who a step waits on.

**When none is set**, the command behaves exactly as it did before personas.
If the command has persona variants and this is the first time in the
session, add one line at the end of the output offering to set one:

```
Tip: set your role on this engagement and /wire:status will focus on it: /wire:persona set <persona> (delivery-manager, analytics-engineer, data-engineer, engagement-lead)
```

Never ask before running, and never block a command for a missing persona.

## Writing a persona variant

1. List the personas the command supports in its front matter:

   ```yaml
   personas: [delivery-manager]
   ```

2. Add one section per listed persona, headed exactly
   `## Persona: <id>`. The spec lint fails a listed persona without its
   section, and a section for a persona that is not listed or not in the
   list above.
3. The section says what the command shows for that persona, in place of or
   on top of the default output. Steps it does not mention run as normal.

## Rules

1. **A persona changes what is shown, never what is written.** A command
   writes the same files, `status.md` rows and execution log under every
   persona. Only the report on screen differs.
2. **Never blocks.** No persona, an unknown persona, or a command without a
   variant for the persona: run the default.
3. **Plain text.** Persona reports follow the house writing rules: tables over
   prose, no emojis; states as words (`On track`, `At risk`, `Late`).
4. **Recorded with each run.** When a persona is set, the execution log's
   Session column carries it (`typed as delivery-manager`;
   `specs/utils/execution_log.md`) and so does the `wire_command` telemetry
   event (`persona`; `specs/utils/telemetry.md`), so we can see whether
   personas are used before extending them to more commands.
