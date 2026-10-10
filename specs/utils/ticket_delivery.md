---
description: Shared convention for releases built ticket by ticket from Linear or Jira (wire#279). The ticket map, slices, the --slice option, per-slice status and runnable set, the ticket branch write rule, the roll-up on merge, and where a slice's table design comes from
---

# Utils: Ticket Delivery

A shared convention, not a command. It is cited by `/wire:tickets-import`,
`/wire:work`, `/wire:status`, `/wire:status-sync`, `specs/utils/runnable_set.md`,
`specs/utils/precondition_gate.md` and every command that accepts `--slice`.

## Purpose

Wire's default is to build a release artifact by artifact, each artifact for
the whole release. Most delivery teams build a release ticket by ticket from a
tracker instead. Each ticket covers one part of the release, runs on its own
branch and merges back by pull request. Before 4.2.0 Wire tracked the whole
release only, so finishing a ticket did not change the release status, the
list of what can start next was wrong, and ticket branches clashed on
`status.md` and `execution_log.md`.

This convention adds a second way of working, chosen per release with
`delivery: tickets` in `status.md`. The default, `delivery: artifacts` (or the
field absent), is unchanged.

The deterministic parts are implemented by `scripts/ticket_delivery.py` (plain
script, no AI call). Run it; do not work these rules out by hand. Behavioural
tests: `wire/tests/core/validate_ticket_delivery.py`.

## Words

| Word | Meaning |
|---|---|
| Release | A Wire release folder, for example `.wire/releases/02-customer-core`. Usually matches one tracker project |
| Ticket | One Linear or Jira issue |
| Slice | The part of the release a ticket covers: one table, one source, one layer, one deliverable, one batch, or `whole_release` |
| Ticket map | `tickets.yaml` in the release folder: every ticket with its kind, slices and Wire steps |
| Ticket record | `iterations/<ticket>.md`, as written by `/wire:work`, with a front matter block for its progress |
| Ticket run log | `iterations/<ticket>.execution_log.md`, the ticket's own execution log, same format as `execution_log.md` |
| Design source | Where a slice's table design comes from: Wire's `data_model` document (default) or the client's Modality physical model |

## Who sets it up

The lead consultant runs `/wire:tickets-import` once the platform design is
agreed and the tracker project for the release is cut. Discovery produces the
design; the design is split into releases; each release is split into tickets,
one per deliverable. The import reads that split. It does not plan a release
from a statement of work: statement-of-work deliverables are usually broader
promises than a ticket, and a release planned from them skips the design.

Ticket delivery works for every release type, `custom` included. For a `custom`
release the Wire steps are the artifact keys `/wire:custom-define` recorded;
a ticket that matches no artifact key is plain work.

## The ticket map: `tickets.yaml`

```yaml
schema: 1
release: 02-customer-core
tracker: linear                 # linear | jira
tracker_project: "Customer Core 1.0"
imported: "2026-10-10 14:00"
imported_by: "<lead consultant>"
design_source: modality         # wire | modality, from status.md model_source

slices:
  - id: whole_release
    kind: release
  - id: source_crm
    kind: source
  - id: core.organisation
    kind: entity
    modality_object: core.organisation      # with Modality only
    depends_on: [source_crm]                # slices this one is built from
  - id: core.legal_entity
    kind: entity
    modality_object: core.legal_entity
  - id: derivations.customer_master
    kind: derived
    depends_on: [core.organisation, core.legal_entity]

tickets:
  - key: CUS-8
    title: Build Organisation
    url: https://linear.app/example/issue/CUS-8
    kind: build                 # requirements | business_rules | design | build | test | review | plain
    slices: [core.organisation]
    steps: [dbt, data_quality]  # Wire artifact ids; "<artifact>.review" for a review step
    blocked_by: [CUS-6]         # the tracker's links, as read
    record: iterations/CUS-8.md
```

Rules:

1. The ticket map is Wire's record. Hand-kept link files (a `linear_map.json`,
   a `jira:` block filled in by hand) can be generated from it or dropped.
2. A ticket may cover several slices (a design ticket for four tables) and a
   slice may be covered by several tickets (a build ticket and a review
   ticket).
3. A step is a Wire artifact id from the release type's graph, or for a
   `custom` release an artifact key from `status.md`. `<artifact>.review`
   names that artifact's review step only. A step the graph does not know is
   an import error, not a guess.
4. A ticket with no steps is **plain work**. It is tracked in the map and has a
   ticket record, but no Wire command runs for it and it has no cell in the
   status table. The record says so.
5. Slice `depends_on` comes from the design: one table built from another. The
   tracker's `blocked_by` links are recorded as read and compared, never
   trusted in place of the design.

## Ticket kinds

| Kind | Steps it covers |
|---|---|
| `requirements` | `requirements` |
| `business_rules` | `business_rules` |
| `design` | `data_model` (or `conceptual_model`, `logical_model`, `pipeline_design` when the ticket says so) |
| `build` | From the slice kind, below |
| `test` | `data_quality` (or `uat` when the ticket says so) |
| `review` | `<artifact>.review`, named from the ticket text. Never guessed |
| `plain` | None |

## Slice kinds and their recipes

A deliverable type gives the steps needed to finish it. A `build` ticket
covers these steps for its slice:

| Slice kind | Example | Steps |
|---|---|---|
| `source` | Stage the CRM | `dbt`, `data_quality` |
| `entity` | Organisation table | `data_model`, `dbt`, `data_quality` |
| `derived` | Customer master | `data_model`, `dbt`, `data_quality` |
| `metric` | Three agreed metrics | `semantic_layer` |
| `report` | Customer master semantic model | `semantic_layer` |
| `dashboard` | Sales overview | `dashboards` |
| `layer`, `deliverable`, `batch` | dbt build of a feature, D04, batch 3 | From the ticket text, confirmed by the consultant |
| `app`, `other` | A notebook page, a nightly load | None: plain work unless the consultant names steps |

Where a `design` ticket already covers a slice's `data_model` step, the build
tickets for that slice leave `data_model` out.

The import asks, rather than guesses, in three cases: a `review` ticket, whose
reviewed steps come from its text; a `layer`, `deliverable` or `batch` slice
whose steps the ticket does not name; and a ticket with no steps, which is
offered as plain work.

## Where a slice comes from

| Release has | Slice comes from |
|---|---|
| No design model (default) | Wire's proposal, from the ticket's title and text. Any wording works. Every proposed slice is marked for the consultant to check |
| `model_source: modality` | The Modality object the ticket builds. Wire uses the model's own ticket links where they exist and does not ask about them. Otherwise it proposes a match, marked for checking. A ticket with no object gets a plain-text slice, also marked |

Slice kind from a Modality object: `entity` from `type = entity`; `derived` from
`derived`, `derivation` or `aggregate`; `metric` from `metric`; `report` from a
`data_product`; `source` from a `source` block (`specs/utils/mml_import.md`).

## The ticket record's front matter

`/wire:work` writes the iteration file it always has. In a ticket-built
release the file starts with a front matter block that holds the ticket's
progress, so the status can be worked out without reading prose:

```yaml
---
ticket: CUS-216
state: awaiting_owner     # planned | open | awaiting_review | awaiting_owner | closed | escalated | cancelled
merged: true              # its pull request has merged into the release branch
blocked: null             # or the reason, e.g. "no access to the existing dbt project"
results:                  # one entry per step, written as each command reports
  data_model: pass
  dbt: pass
  data_quality: pass
---
```

`planned` is new: the import created the record and nobody has opened it yet.
The other states are `/wire:work`'s.

## The status table, per slice

`ticket_delivery.py status <release> --markdown` prints it. One row per slice,
one column per step, each cell the step's state and the tickets covering it.
Nobody edits it by hand.

| Cell | Rule |
|---|---|
| ✅ complete | Every live ticket covering the cell has merged and recorded `complete`, `pass` or `approved` for the step |
| ⚠️ blocked | Not complete, and a covering ticket records a blocker |
| 🔄 in progress | Not complete or blocked, and a covering ticket is `open`, `awaiting_review` or `awaiting_owner` |
| ⏸️ not started | Otherwise |

Cancelled and escalated tickets do not count. A step is **complete for the
release** when it is complete in every slice that has it; otherwise it is
`partial` (some slices complete, reported as `<k> of <n> slices`) or `none`.

The table is written to `status.md` under `## Slices`, after
`## Artifact Status Summary`. The `artifacts:` block keeps its shape so every
reader of it (the runnable set, the precondition gate, Wire Studio) still
works: `/wire:status-sync` proposes `artifacts.<id>` as done only when the step
is complete for the release, and notes `<k> of <n> slices` in the
`revision_history` until then.

## What can start next, per slice

`ticket_delivery.py runnable <release>` applies `specs/utils/runnable_set.md`
to each slice. For each ticket, each step it covers, and each `depends_on`
entry of that step in the release type's graph (profile applied):

1. A dependency on a step the same ticket covers for the same slice is
   ignored. The ticket runs its own steps in order.
2. The dependency resolves to the first of: the same slice's cell; the cells of
   the slice's upstream slices that have the step; the `whole_release` cell.
   If other slices have the step but none of these do, the step does not
   apply to this slice and the dependency is met: the confirmed ticket map
   gives a source slice no design step, so staging a source does not wait for
   the tables' designs. If no slice has the step, the release-level state in
   `status.md`'s `artifacts:` block decides, compared as the runnable set
   compares it.
3. A cell meets the dependency only when it is complete, whatever action the
   graph entry names. The build for one table waits for that table's design to
   be approved, not for every table's.
4. A build step (`pipeline`, `seed_data`, `dbt`, `semantic_layer`,
   `dashboards`) also waits for the same step in each upstream slice, because
   it reads their tables. The customer master's dbt build waits for the
   Organisation and legal entity dbt builds. Design and test steps do not.
5. Advisory entries park for a ruling once per release, as in the runnable
   set. A ruling covers every slice. A blocking entry is never met by a ruling.
6. A dependency on an artifact in a profile-disabled phase is met.

Each ticket gets one state: `done`, `in_progress`, `blocked` (with the
blocker), `waiting` (with the tickets and steps it waits on), `parked` (needs
a ruling), `can_start`, or `plain` (plain work: no Wire steps to wait for).

**Link check.** For each ticket that is not done, Wire compares the tickets it
depends on (by the rules above, not done yet) with the tracker's `blocked_by`
links. A missing link is reported with the reason from the design and an offer
to add it in the tracker. A link the tracker has and Wire's order does not is
reported as information. Wire never changes tracker links without asking.

## The `--slice` option

Commands that make or check release documents and code take
`--slice <slice>`. With it, the command reads and writes only that slice:

| Command | With `--slice core.legal_entity` |
|---|---|
| `data_model-generate` / `-validate` | The `legal_entity` table's section of `design/data_model.md` only. Other sections are left as they are |
| `dbt-generate` / `-validate` (and the `dbt-staging`, `dbt-integration`, `dbt-warehouse` variants) | The models, seeds, tests and `schema.yml` entries for that table only. `dbt build --select` limited to them |
| `data_quality-generate` / `-validate` | Tests for that table only |
| `semantic_layer-generate` / `-validate` | The views, explores or measures for that slice only |
| `dashboards-generate` / `-validate` | The named dashboard or tiles only |

Rules:

1. Without `--slice`, every command works as before.
2. A slice the ticket map does not hold is an error: name the valid slices.
3. A sliced generate never regenerates the whole document. It adds or replaces
   the slice's section and leaves every other line alone.
4. The precondition gate evaluates the slice's dependencies by the rules in
   "What can start next, per slice" (`specs/utils/precondition_gate.md`,
   "Sliced runs").
5. In a ticket-built release the command writes its progress to the ticket
   record and its log row to the ticket run log, not to `status.md` and
   `execution_log.md` (next section).

## One record per ticket, added to the release on merge

On a ticket branch the Wire session writes only:

- the ticket record, `iterations/<ticket>.md` (front matter and body);
- the ticket run log, `iterations/<ticket>.execution_log.md`;
- the files the plan's commands produce (code, the slice's document sections).

It does not write `status.md`, `execution_log.md`, `tickets.yaml` or
`decisions.md` on the ticket branch. A decision made during the ticket is
written to the ticket record's "Decisions made during the work" section and
copied to `decisions.md` at roll-up. Ticket branches therefore never clash on
the shared record files.

**Roll-up.** When the pull request merges into the release branch,
`/wire:status-sync <release>` (Step 4g) on the release branch:

1. Runs `ticket_delivery.py merge-log <release> <ticket>` and shows the rows.
   Each row keeps its command, result, by, session and metric cells. Its
   Timestamp is the time of the roll-up, and its Detail starts
   `ticket <key>, ran <original time>:`. `execution_log.md` is append-only and
   its timestamps never go backwards (`specs/utils/execution_log.md` rules 1
   and 6), so the original time goes in Detail, as for any backfilled row.
   Rows are added in the order the ticket ran them; a row already rolled up is
   not added again.
2. Copies the ticket's decisions to `decisions.md`, next ids in sequence.
3. Rewrites the `## Slices` table and the `## Iterations` row.
4. Proposes `artifacts.<id>` changes for steps now complete for the release.
5. Writes nothing until the consultant confirms (status-sync's contract).

The Wire session stays the single writer of the release record
(`specs/utils/director_operating_model.md`). On the ticket branch it writes
the ticket's own files; on the release branch it writes the release record.

## Where a slice's table design comes from

`ticket_delivery.py design-source <release> [--slice <slice>]`:

| Release has | Table design used by `/wire:dbt-generate` |
|---|---|
| No design model (default) | `wire_data_model`: Wire's `data_model` document, as now, written one slice at a time |
| `model_source: modality` and the slice's table in `modality/models/physical/` | `modality_physical`: the Modality physical model. `/wire:data_model-generate` reads it and records it as the slice's design, listing any gaps against Wire's naming rules. It does not design the table again. `/wire:data_model-validate` checks it against Wire's rules |
| `model_source: modality` but no tables in `modality/models/physical/` (or not this slice's) | `wire_data_model_from_modality`: Wire's `data_model` document, designed from the Modality conceptual and logical layers, as now |

Wire never writes Modality files. A ticket that changes the Modality model
(a physical design ticket) stays outside Wire commands; what it produces is a
design Wire can read, so the build and its checks run through Wire.

## Relation to migration batches

Platform migrations already keep a status, a tracker key and their own checks
per batch. Ticket delivery reuses that shape (state per part of the release,
tracker key per part, checks scoped to the part) but not the batching
commands, which carry migration rules (checks between batches, a cutover per
batch) that do not fit a table or a layer.

## Gemini CLI

Gemini has no mod and no skills. The import, the map, the script and the
roll-up work the same; the consultant types each command.
