---
sidebar_position: 6
title: Issue Tracking
---

# Issue Tracking Integration

If your client's delivery team lives in Jira or Linear, they will want to see the state of each Wire artifact where they already look for it, rather than having to ask you. Wire therefore integrates with Jira and Linear to sync artifact status as the engagement progresses. Each integration is optional, Wire works without either, and both can be active simultaneously. In this page we will look at the Jira integration first, then Linear, and finish with what happens when both are configured.

## Jira integration

### Configuration

To use Jira, the Atlassian MCP server must be configured in `.claude/settings.json`:

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-atlassian"],
      "env": {
        "ATLASSIAN_SITE_URL": "https://your-org.atlassian.net",
        "ATLASSIAN_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Structure

Wire creates one Jira hierarchy per engagement, with three levels:

- **Epic**: one per project (e.g. "Northfield Full Platform")
- **Tasks**: one per artifact (e.g. "Problem Definition", "High-Level Design")
- **Sub-tasks**: one per lifecycle step (Generate, Validate, Review)

To create it, run `/wire:new` and answer Yes when asked whether to create the Jira hierarchy, and if the hierarchy already exists, provide the existing Epic ID and Wire links to it instead.

### Syncing

Once the hierarchy exists, how does it stay current? All generate/validate/review commands sync their status to the corresponding Jira sub-task after completing:

- **Generate completes** → sub-task transitions to In Review
- **Validate fails** → sub-task transitions to Blocked, failure details added as a comment
- **Validate passes** → sub-task transitions to In Review
- **Review approved** → sub-task transitions to Done; Task transitions to Done if all sub-tasks are Done

### `/wire:status` reconciliation

Running `/wire:status` performs a full reconciliation between the local execution log and Jira, identifying any gaps, fixing stale statuses and flagging artifacts where the local and Jira states diverge.

## Linear integration

### Configuration

For Linear, the Linear MCP server must be configured in `.claude/settings.json`:

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "@linear/mcp-server"],
      "env": {
        "LINEAR_API_KEY": "your-linear-api-key"
      }
    }
  }
}
```

### Structure

Wire creates a Linear hierarchy per engagement, again with three levels:

- **Project**: one per engagement
- **Issues**: one per artifact
- **Sub-issues**: one per lifecycle step (Generate, Validate, Review)

Run `/wire:utils-linear-create <release-folder>` to create the hierarchy, and if you are using both Jira and Linear, Wire maintains both in parallel.

### Labels and states

Wire maps artifact states to Linear issue states as follows:

| Wire state | Linear state |
|---|---|
| Not started | Backlog |
| Generate in progress | In Progress |
| Validation failures | Blocked |
| Awaiting review | In Review |
| Approved | Done |

Wire also creates a `wire-generated` label and applies it to all issues it creates, so that you can filter your Linear board down to Wire-managed issues.

## Using both simultaneously

If both Atlassian and Linear are configured, Wire syncs to both after each command, and the execution log records both sync results. If one sync fails (e.g. a network error), Wire logs the failure but does not block the command, and the next `/wire:status` will reconcile.

## Releases built from tickets (4.2.0)

Most delivery teams build a release ticket by ticket from Linear or Jira. Each ticket covers one part of the release, runs on its own branch and merges back by pull request. From 4.2.0 Wire supports this as a second way of working, set per release with `delivery: tickets` in `status.md`. The default, building artifact by artifact, is unchanged.

| Word | Meaning |
|---|---|
| Slice | The part of the release a ticket covers: one table, one source, one layer, one deliverable, one batch, or the whole release |
| Ticket map | `tickets.yaml` in the release folder: each ticket with its kind, slices and Wire steps |
| Ticket record | `iterations/<ticket>.md`, with a front matter block holding the ticket's progress |
| Ticket run log | `iterations/<ticket>.execution_log.md`, the ticket's own execution log |

**Set up.** The lead consultant runs the import once the platform design is agreed and the release is cut into tickets:

```bash
/wire:tickets-import 02-customer-core --tracker linear
/wire:tickets-import 03-acquisition --tracker jira --project GRO
```

Wire reads the tracker project and proposes, for each ticket, its kind (requirements, business rules, design, build, test, review, plain work), its slices and the Wire steps it covers. A build ticket's steps follow from what it builds: a source gets `dbt` and `data_quality`; a table gets `data_model`, `dbt` and `data_quality` (without `data_model` when a design ticket covers it); a metric or report gets `semantic_layer`; a dashboard gets `dashboards`. Nothing is written until you confirm. Tracker projects that match no release are listed with three choices: start a release, add to one, or ignore. Run it again with `--refresh` to see new, changed and removed tickets.

**Setting up a release for ticket delivery, step by step.**

1. Create the release as usual with `/wire:new`, and get its upstream design approved (for most release types, the conceptual model). The tickets should be cut from that design, one per deliverable, not from statement-of-work deliverables.
2. Connect the tracker: the Linear or Atlassian MCP server must be reachable, because Wire reads the tickets itself.
3. If the design is in Modality, link it first with `/wire:utils-modality-link <release>`. Skip this step otherwise.
4. As lead consultant, run `/wire:tickets-import <release> --tracker linear|jira [--project <name-or-key>]`.
5. Check the proposal: the Slice column (always, without Modality), any plain work, any ticket whose steps Wire asks you to name, missing "blocked by" links, and tracker projects in no release. Answer, then **confirm**.
6. Wire writes `tickets.yaml`, one ticket record per ticket in `iterations/` (state `planned`), `delivery: tickets` and the `## Slices` table in `status.md`, and a decision for each scoping answer.
7. Run `/wire:status <release>` to see what can start, then work each ticket with `/wire:work <release> <ticket>`.
8. After each pull request merges, run `/wire:status-sync <release>` on the release branch. When the tracker changes, run `/wire:tickets-import <release> --refresh`.

The "Working a Ticket" chapter of the docs site, Part Two, walks through a whole release set up and built this way.

**With or without Modality.** If the release reads its design from Modality (`model_source: modality`), each build ticket's slice is the Modality object it builds, and the model's own ticket links are used where they exist. Without Modality, Wire proposes each slice from the ticket's title and text and asks you to check it. Nothing needs Modality.

**Status per slice.** `/wire:status` shows one row per slice and one column per step, each cell with its state and the tickets covering it, then which tickets can start now, which wait and on what, and any "blocked by" link the tracker is missing. A step is complete for the release when it is complete in every slice.

**Working a ticket.** `/wire:work <release> <ticket>` works as before, with four differences:

1. A ticket that builds a new table is accepted when the table is one of its slices in the ticket map. Work outside the map (a new source, another table) is still refused, with options.
2. Every command step runs with `--slice <slice>`, so it reads and writes that slice only: one table's section of `design/data_model.md`, one table's models and tests.
3. On the ticket branch Wire writes only the ticket record, the ticket run log and the code. It does not write `status.md` or `execution_log.md`, so ticket branches no longer clash on those files.
4. When the pull request merges, `/wire:status-sync` on the release branch adds the ticket's log rows to `execution_log.md` (each row's original time kept in its Detail), copies its decisions to `decisions.md` and updates the slice table, with your confirmation.

**Where the table design comes from.**

| Release has | Design used to build the table |
|---|---|
| No design model (default) | Wire's `data_model` document, one slice at a time |
| Modality, with the table in `modality/models/physical/` | The Modality physical model. `/wire:data_model-generate` records it and lists gaps against Wire's naming rules; it does not design the table again |
| Modality, with no table there | Wire's `data_model` document, designed from the Modality conceptual and logical layers |

Wire never writes Modality files. The fixed rules (the import's recipes, the slice table, what can start, the roll-up and the design source) are in `scripts/ticket_delivery.py`, a plain script with no AI call. The convention is `specs/utils/ticket_delivery.md`.

