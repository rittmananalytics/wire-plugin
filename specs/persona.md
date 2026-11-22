---
wire_schema: "1.0"
command: lifecycle
artifact: persona
domain: persona
release_types: []
action_type: lifecycle
logs_execution: false
description: Show or set your role (persona) on this engagement, so commands with a persona variant focus on it
argument-hint: "[set <persona> | clear] [--local]"

---

# Wire Persona Command

## Purpose

Show or set the role you play on this engagement: delivery manager,
analytics engineer, data engineer or engagement lead. Commands with a
variant for your role (first `/wire:status`) then show what that role needs.
The rules are in `specs/utils/personas.md`.

Your persona is kept in the engagement's team roster,
`.wire/engagement/team.yml`, committed with the rest of the record and
matched on your git email. It follows you to any clone on any machine. Each
person on the engagement has their own entry; the same person can have a
different role on another engagement.

## Usage

```bash
/wire:persona                          # your persona here, where it comes from, and the team's
/wire:persona set delivery-manager     # set yours in the team roster
/wire:persona set analytics-engineer --local   # this clone only, not shared
/wire:persona clear                    # remove yours from the roster
/wire:persona clear --local            # remove this clone's override
```

## Workflow

All steps run `python3 <wire>/scripts/persona.py` in the engagement
repository. It needs git's `user.email` for the roster; if it is not set,
say so and offer `--local`.

### Show (no arguments)

Run `persona.py show`. Present:

1. **Yours:** the persona and where it came from (`--as`, `WIRE_PERSONA`,
   this clone's override, or the team roster), or `none`.
2. **The team:** one row per roster entry: name, persona.
3. If you have none, the list of personas with their focus
   (`persona.py list`) and the `set` command to run.

### Set

1. Run `persona.py set <persona>` (or `--local`). An unknown persona is
   refused with the list; offer the closest match.
2. Say what changed. In the roster the script either adds an entry for you
   (your git `user.name` and `user.email`), changes the persona on your
   entry, or adds this machine's email to the entry with your name, so one
   person keeps one entry across machines with different emails.
3. **Roster changes are shared.** Commit `.wire/engagement/team.yml` on the
   current branch (`specs/utils/commit.md`), message
   `persona: <name> as <persona>`. A `--local` change is git-ignored and not
   committed.

### Clear

Run `persona.py clear` (or `--local`) and commit the roster change as for
set.

## Rules

1. Only your own entry. Never set or clear another person's persona; they
   run the command themselves (an engagement lead can edit the file by hand
   in a pull request).
2. Setting a persona changes no other part of the record.
3. Plain text, no emojis.
