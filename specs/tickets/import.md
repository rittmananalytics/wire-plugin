---
wire_schema: "1.0"
command: lifecycle
artifact: tickets
domain: tickets
release_types: []
action_type: lifecycle
logs_execution: true
inputs:
  required:
    - name: release_folder
      description: "Path to the release folder the tracker project belongs to"
  optional:
    - name: tracker
      description: "--tracker linear|jira. Omitted: the tracker configured in status.md (linear: or jira: block); asked when both or neither are configured"
    - name: project
      description: "--project <name or key>. The Linear project or Jira project key and filter. Omitted: the one recorded in tickets.yaml, else the linear:/jira: block, else asked"
    - name: refresh
      description: "--refresh. Compare the tracker with the existing ticket map and propose new, changed and removed tickets"
description: "Read a release's tickets from Linear or Jira and propose the ticket map (each ticket's kind, slices and Wire steps), using the release's Modality model where one is linked; on confirmation write the map, the ticket records and delivery: tickets in status.md"
argument-hint: <release-folder> [--tracker linear|jira] [--project <name-or-key>] [--refresh]
delegates_to:
  - utils/ticket_delivery
  - utils/mml_import
  - utils/execution_log
  - utils/director_operating_model
workload: planning
---

# Wire Tickets Import Command

## Purpose

Turns on ticket delivery for a release (`specs/utils/ticket_delivery.md`). It
reads the tracker project for the release, proposes for each ticket the kind of
work, the slices it covers and the Wire steps it covers, and writes the ticket
map once the consultant confirms. Run again with `--refresh`, it lists what
changed in the tracker and asks before changing anything.

Wire could create tickets before 4.2.0 (`/wire:utils-linear-create`,
`/wire:utils-jira-create`) but not read them, so every link between a ticket
and the release was kept by hand and went out of date. This command is the
read path.

The lead consultant runs it, once the platform design is agreed and the release
is cut into tickets. It needs nothing from Modality: Modality is used only when
the release has `model_source: modality`.

## Usage

```bash
/wire:tickets-import <release-folder> [--tracker linear|jira] [--project <name-or-key>] [--refresh]

/wire:tickets-import 02-customer-core --tracker linear
/wire:tickets-import 03-acquisition --tracker jira --project GRO
/wire:tickets-import 02-customer-core --refresh
```

Accept both `releases/02-customer-core` and bare `02-customer-core`.

## Workflow

### Step 1: Resolve the release and the tracker

1. Locate `.wire/releases/<release-folder>/status.md`. If absent, stop: "No
   release at `<path>`. Run `/wire:new` first."
2. Resolve the tracker from `--tracker`, else from the `linear:` or `jira:`
   block in `status.md`. If both or neither are configured, ask.
3. Check the tracker's MCP server is reachable (Linear: `list_projects`;
   Jira: `getVisibleJiraProjects`). If it is not, stop and say which server
   failed and how to connect it. Do not fall back to typed-in tickets: a map
   built from memory is the hand-kept list this command replaces.
4. Resolve the tracker project from `--project`, else `tickets.yaml`'s
   `tracker_project`, else the `linear:`/`jira:` block, else list the
   tracker's projects and ask which belong to this release.
5. If `tickets.yaml` exists and `--refresh` was not given, say so and ask
   whether to refresh. Never overwrite a ticket map.
6. Resolve the release filter (wire#423). One tracker project often holds the
   tickets of several Wire releases, so each release records which tickets
   are its own. Run `ticket_delivery.py filter <release>`:
   - `ok`: use the filter it prints, with no prompt. This is every
     `--refresh` after the first import.
   - `marker_only`: `jira.release` is set in `status.md` and no import has
     used it yet. Use it, and say so.
   - `unset`: ask once: "Which tickets in `<project>` belong to this release?
     A Jira release (Fix versions), a label, or a JQL clause." Offer the Jira
     release named after the Wire release as the default. A release that
     owns the whole tracker project answers "all of them", and no filter is
     saved.
   - `differs`: `jira.release` in `status.md` and the filter the last import
     used are not the same. Stop, show both, and ask which is right. Change
     nothing until the consultant answers.

   `jira.release` in `status.md` is the source; `tracker_filter` in
   `tickets.yaml` records the filter the last import used. `jira.epic_key`
   keeps its meaning and is never the filter: a release spans several epics,
   and epics stay free for grouping work.

### Step 2: Read the tickets

- **Linear**: `list_issues` for the project, all states. For each issue read
  key, title, description, state, labels, milestone, estimate, URL and its
  "blocked by" relations.
- **Jira**: `searchJiraIssuesUsingJql` with the `jql` that
  `ticket_delivery.py filter <release>` prints: the project, narrowed by the
  release filter from Step 1 (a Jira release through Fix versions, a label,
  or a JQL clause). With no filter, `project = "<KEY>"`. Same fields, plus
  each ticket's Fix versions; "blocked by" from issue links of type Blocks.

Also list the tracker's other projects (or epics) that look like part of this
engagement but match no Wire release, for the "Not in any release" question in
Step 5.

### Step 3: Read the design model, if there is one

If `status.md` has `model_source: modality`, follow `specs/utils/mml_import.md`
to read the model at `modality_path`:

1. The conceptual objects (entities, derivations, metrics), the data products
   and the sources, with their types.
2. The model's own ticket links: a `task` block, a `ticket` or `tracker_key`
   key on an object, or a link file named in `modality_project.yaml`. Use them
   where they exist; do not ask about them.
3. Whether `modality/models/physical/` holds tables, and which.

Without `model_source: modality`, skip this step. Nothing needs Modality.

### Step 4: Propose kind, slices and steps

A ticket whose description has both a `Kind:` line and a `Wire step:` line
states its kind and Wire steps (tickets written from a ticket template; plain
work says `Wire step: none`). Read those lines instead of proposing them: put
the ticket's description in the proposals file as `description`, and the
script uses the stated kind and steps and marks the entry
`kind_source: ticket`. The slice is still proposed as below. A ticket without
both lines, which is every ticket a person writes, takes the proposal route
unchanged.

For each other ticket, from its title and text:

1. Propose the **kind** (`specs/utils/ticket_delivery.md`, "Ticket kinds").
2. Propose the **slice** and its kind. With a Modality link, the slice is the
   linked object. Without one, propose a match to a model object, or a
   plain-text slice from the ticket's wording ("marketing spend in CPA: dbt").
3. For `review` tickets, name the reviewed steps from the text
   (`requirements.review`). For `layer`, `deliverable` and `batch` slices,
   name the steps from the text. Never guess either: ask.
4. Propose each slice's `depends_on` from the design (the physical or logical
   model with Modality; `design/data_model.md` and the ticket text without).

Write these proposals to a JSON file in the release's scratch area and run:

```bash
python3 <wire>/scripts/ticket_delivery.py propose <proposals.json>
```

The script reads stated kinds and steps, applies the recipes, uses Modality links over proposals, drops
`data_model` from build tickets whose slice a design ticket covers, marks
every proposal that needs checking, lists plain work and lists tickets in
tracker projects that are not this release's. Use its output as the proposal;
do not re-derive it.

Every step named must exist in the release type's graph (or, for a `custom`
release, in `status.md`'s artifact keys). A step that does not is reported as
an import error and asked about.

### Step 5: Present the proposal

Present, before writing anything:

1. The tracker project, the ticket count and the points total.
2. Where the slices came from: the Modality model, or Wire's proposals from
   ticket text (then: "Please check the Slice column").
3. One table: Ticket | Title | Kind | Slice | Wire steps.
4. The questions from the script, numbered: proposed slices to check, plain
   work to confirm.
5. Order: each slice dependency the tracker has no "blocked by" link for, with
   the reason from the design, and an offer to add the link.
6. Held by another release: run `ticket_delivery.py overlap <release> --keys
   <keys.json>` with the keys about to be mapped. For each ticket it lists,
   name the release that already holds it and ask: leave it there (the
   default, and it is dropped from this import), move it here, or keep it in
   both and say why. Never map a ticket twice without the consultant's
   answer.
7. In no tracker release, or in two: when the filter is a Jira release, list
   once the project's tickets that are in no Wire release's Jira release, or
   in more than one, with the question "which release?". Write the answer to
   the ticket's Fix versions only after the consultant confirms; a list of
   tickets is confirmed once, not ticket by ticket.
8. Not in any release: tracker projects with no matching Wire release, each
   with the choice: start a new release (`/wire:new`), add to an existing
   release, or ignore.
9. **confirm / adjust / cancel**.

On **adjust**, take the changes, re-run the script and present again. On
**cancel**, write nothing.

### Step 6: Write on confirmation

1. `tickets.yaml` in the release folder, in the shape of
   `specs/utils/ticket_delivery.md`, with `imported` and `imported_by`.
   `tracker_filter` holds the filter this import used (`{kind: release |
   label | jql, value: ...}`); it is left out when the release owns the whole
   tracker project. When the filter is a Jira release and `jira.release` in
   `status.md` is empty, set it to the same name.
2. One ticket record per ticket in `iterations/<key>.md`, from `/wire:work`'s
   iteration file template, with the front matter block and `state: planned`.
   An existing record (a ticket already worked with `/wire:work`) is kept;
   its front matter is added if missing and its state is not changed.
3. `status.md`: `delivery: tickets`; the `## Slices` table from
   `ticket_delivery.py status <release> --markdown`; one `## Iterations` row
   per ticket.
4. `decisions.md`: one entry per answer that sets scope (a tracker project left
   out of every release, plain work agreed), with the consultant's name and
   reason, in the ruling format of `specs/utils/director_operating_model.md`.
5. Tracker links the consultant agreed to add: Linear `save_issue` with the
   relation, Jira `createIssueLink`. Only those agreed.
6. One execution-log row:
   `/wire:tickets-import | complete | <n> tickets, <k> slices, <p> plain, from <tracker> <project>`.

These are written on the release branch. The import is a release-record
change, not a ticket.

### Step 7: Refresh (`--refresh`)

1. Read the tracker as in Step 2, with the saved filter from Step 1 and no
   prompt, and propose as in Steps 3 and 4.
2. Run `ticket_delivery.py refresh <release> <new-proposal.json>`. It lists
   **new** tickets (with their proposal), **changed** tickets (title, kind,
   slices or steps, was and now) and **removed** tickets (cancelled or gone
   from the tracker, proposal: close the record as cancelled).
3. Present the table and ask **apply all / choose / cancel**.
4. On confirmation, update `tickets.yaml`, create records for new tickets,
   set `state: cancelled` on removed ones (never delete a record), rewrite
   `## Slices`, and log
   `/wire:tickets-import | complete | refresh: <n> new, <c> changed, <r> removed`.

A changed ticket that is already open keeps its plan. The change is shown on
its next `/wire:work` open as a plan amendment to consider.

## Output

End with a plain-language report: tickets and slices written, plain work,
questions answered and how, decisions recorded, tracker links added, and what
can start now (from `ticket_delivery.py runnable <release>`). Name the command
that ran in full, as it would be typed (operating model rule 7):

```
Ran: /wire:tickets-import 02-customer-core --tracker linear
```

## Edge cases

- **A ticket in two releases.** Each release's map holds it once; the slices
  differ. Ask which release owns each step.
- **Sub-issues.** A Linear sub-issue or Jira sub-task is part of its parent
  ticket unless it names its own deliverable. Ask when unclear.
- **No tickets.** Say so and write nothing.
- **Release built from statement-of-work deliverables** (`custom`). Steps come
  from `/wire:custom-define`'s deliverable-to-command mapping in `status.md`.
  A ticket that maps to no command is plain work, and its record says so.
