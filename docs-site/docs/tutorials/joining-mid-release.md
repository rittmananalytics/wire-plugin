---
sidebar_position: 16
title: "Tutorial: Joining Mid-Release"
---

# Tutorial: Joining Mid-Release

## What this tutorial covers

Sooner or later you will be handed an engagement that somebody else started, with a first client session already in the diary and no time to read every artifact from the beginning, and what you need in that time is a reliable way to find out what has been built, what has been decided and what comes next. This tutorial shows how to get up to speed on an active Wire engagement that you did not start, and it covers reading the release state, surfacing the decision history, recovering meeting context from Fathom transcripts and planning your first session, using a handover scenario between two consultants on a live wealth management project.

## Scenario

| | |
|-|-|
| **Client** | Aldgate Financial Services |
| **Sector** | UK wealth management |
| **Release** | `02-aldgate-financial-platform` |
| **Release type** | `full_platform` |
| **Stack** | BigQuery, dbt Cloud, Looker |
| **Handing over** | Sarah (senior consultant, leaving the engagement) |
| **Joining** | Marcus (analytics engineer, first session on this project) |
| **Current state** | Phase 3: dbt approved, semantic layer not yet started |

Marcus has 30 minutes before his first session with the client data team, and in that time he needs to understand what has been built, what decisions were made and what the next command is. At a high level, he will do six things, each of which we look at in turn below:

1. Run `/wire:start` and `/wire:status` to see the current state of the release.
2. Run `/wire:decisions` to read the decisions log.
3. Run `/wire:execution-log` to see what was run, and when.
4. Run `/wire:utils-meeting-context` to recover what was said in client calls.
5. Run `/wire:session-plan` to plan his first session.
6. Run `/wire:semantic_layer-generate`, the next command in the release.

## Understanding the current state

Marcus opens his terminal in the engagement repository and runs `/wire:start`:

```
/wire:start
-> Wire Framework v3.9.4
-> Active release: 02-aldgate-financial-platform
-> Type:           full_platform
-> Client:         Aldgate Financial Services
-> Phase:          3 — Development (in progress)
-> Completion:     7 / 16 artifacts approved

   Requirements         approved
   Conceptual model     approved
   Pipeline design      approved
   Data model           approved
   Pipeline             approved
   dbt                  approved
   Orchestration        approved
   Semantic layer       not_started    <- next
   Dashboards           not_started
   Data quality         not_started
   UAT                  not_started
   Deployment           not_started
   Training             not_started
   Documentation        not_started

   Run /wire:status for the full artifact state and open items.
```

That gives him the shape of the engagement in ten seconds, and he follows it with `/wire:status` for the complete picture, which adds artifact versions, approval dates, reviewer names and open questions:

```
/wire:status 02-aldgate-financial-platform
-> Artifact status — 02-aldgate-financial-platform
   ─────────────────────────────────────────────────
   requirements       v2.1  approved 2026-01-14  Reviewer: Priya Shah (Head of Data)
   conceptual_model   v1.0  approved 2026-01-15  Reviewer: James Okafor (Lead Architect)
   pipeline_design    v3.0  approved 2026-01-21  Reviewer: James Okafor
   data_model         v4.0  approved 2026-01-28  Reviewer: Priya Shah
   pipeline           v1.0  approved 2026-02-04  Reviewer: James Okafor
   dbt                v2.0  approved 2026-02-11  Reviewer: Priya Shah
   orchestration      v1.0  approved 2026-02-11  Reviewer: Priya Shah
   semantic_layer     —     not_started
   ...

   Open items: 2
     OQ-3  Confirm CASS 9 data retention scope with compliance team (owner: Priya Shah)
     OQ-7  FCA reference data refresh cadence — daily or weekly? (owner: James Okafor)
```

From this Marcus learns that Priya Shah is the data reviewer and that James Okafor handles architecture sign-offs, and he notes the two open questions, since OQ-3 (CASS 9 retention scope) may affect what fields appear in the semantic layer.

## Reading the decisions log

Wire agents record non-obvious modelling choices to `decisions.md` as they work, which makes it the first place to look for the reasoning behind what has been built, and Marcus reads it with `/wire:decisions`:

```
/wire:decisions 02-aldgate-financial-platform
-> decisions.md — 02-aldgate-financial-platform (8 entries)
   ─────────────────────────────────────────────────────────
   [2026-01-15]  Grain: portfolio_position_fct modelled at daily account-instrument
                 grain. Intraday positions excluded — source system only snapshots
                 at 17:00 UTC. Ticket ref: AFS-112.

   [2026-01-21]  Surrogate keys generated using dbt_utils.generate_surrogate_key()
                 across all staging and warehouse models. Natural keys from the
                 Temenos source are not stable across system migrations; surrogate
                 keys future-proof the join layer.

   [2026-01-28]  instrument_type_code excluded from the data model scope — field
                 carries regulatory classification data subject to FCA disclosure
                 restrictions. Deferred to a separate controlled-access dataset.
                 Agreed with James Okafor and compliance lead Claire Whitmore.

   ... (5 further entries)
```

Three decisions stand out. The daily snapshot grain is a hard constraint, because the Temenos system simply does not produce intraday data; the surrogate key choice is standard Wire convention; and the `instrument_type_code` exclusion is critical, since the field cannot appear in any shared dataset, which means it cannot appear in the Looker semantic layer either.

## Reading the execution log

The decisions log shows what was decided, but what was actually run, and when? That is what the execution log shows:

```
/wire:execution-log 02-aldgate-financial-platform
-> Execution log — last 10 entries
   ──────────────────────────────────────────────
   2026-02-11 09:14  /wire:dbt-validate            PASS
   2026-02-11 09:31  /wire:dbt-review              approved (Priya Shah)
   2026-02-11 10:02  /wire:orchestration-generate  complete
   2026-02-11 10:18  /wire:orchestration-validate  PASS
   2026-02-11 10:44  /wire:orchestration-review    approved (Priya Shah)
   2026-02-11 11:03  /wire:session-end             session closed by sarah@rittmananalytics.com
   2026-02-12 08:55  /wire:start                   session opened by marcus@rittmananalytics.com
   2026-02-12 08:56  /wire:status                  viewed
   2026-02-12 08:57  /wire:decisions               viewed
   2026-02-12 08:58  /wire:execution-log           viewed
```

Sarah closed the session on 11 February after orchestration was approved, and the log sequence makes the handover point unambiguous. Marcus can see that nothing has been run since, so there is no partial semantic layer work in progress.

## Meeting context

The decisions log shows what agents recorded. But what about the things analysts and clients discuss in calls that never make it into a formal decision? Marcus pulls the Fathom transcript context:

```
/wire:utils-meeting-context 02-aldgate-financial-platform
-> Searching Fathom for calls during engagement period (2026-01-10 to present)...
-> 3 calls found:

   2026-01-10  Aldgate Financial — Kick-off call (47 min)
               Key topics: project scope, data access timelines, stakeholder names

   2026-01-14  Aldgate Financial — Requirements review (62 min)
               Key topics: KPI definitions, CASS 9 scope, dashboard audience

   2026-01-28  Aldgate Financial — Data model review (58 min)
               Key topics: grain sign-off, model naming, semantic layer scope
               Notable: "instrument_type_code will not be included in the semantic
               layer due to regulatory sensitivity — this is agreed with the
               client's compliance team." (James Okafor, 00:34:12)

-> Relevant context written to: .wire/releases/02-aldgate-financial-platform/meeting_context.md
```

The data model review transcript surfaces a specific statement from James Okafor about `instrument_type_code`, and when Marcus checks `decisions.md` again he finds the field exclusion recorded there from 2026-01-28, so the agent did capture it. The transcript adds confirmation of who said it and when.

:::note
If a decision surfaced by a transcript is missing from `decisions.md`, add it there manually before starting any generation work, since every Wire agent reads `decisions.md` before it generates.
:::

This is exactly the kind of institutional knowledge that disappears in a handover, because it is not in any Jira ticket and not in any email, and the Fathom transcript is the only reliable record.

## Planning the next session

Marcus now knows what was built, what decisions were made and what constraints apply to the semantic layer, so he runs session planning:

```
/wire:session-plan 02-aldgate-financial-platform
-> Entering Plan Mode — no commands will execute until you approve the plan.

   Proposed session plan — 02-aldgate-financial-platform
   ──────────────────────────────────────────────────────
   1. Read the approved data_model spec (v4.0) to understand the LookML
      view and explore structure expected.
   2. Run /wire:semantic_layer-generate — delegates to semantic-layer-developer
      agent, which will read decisions.md and the data model spec before generating.
   3. Run /wire:semantic_layer-validate to check referential integrity,
      field naming, and measure definitions against the data model.
   4. Schedule /wire:semantic_layer-review with Priya Shah (data team lead).

   Note: OQ-3 (CASS 9 retention scope) remains open. If unresolved before
   generation, the agent will flag it in the review prep notes.

   Approve this plan? [yes/no/edit]
-> yes
-> Plan approved. Run commands in the sequence above.
```

Four steps, clearly scoped. Marcus approves the plan and is ready for his first session.

## Running the next command

```
/wire:semantic_layer-generate 02-aldgate-financial-platform
-> [auto-delegated to semantic-layer-developer agent]
-> Reading decisions.md... 8 entries loaded.
-> Reading data_model v4.0... portfolio_position_fct, account_dim, instrument_dim,
   adviser_dim, transaction_fct — grain and field inventory confirmed.
-> instrument_type_code excluded from semantic layer scope (decisions.md, 2026-01-28).
-> Generating LookML views and explores...
-> Output: .wire/releases/02-aldgate-financial-platform/artifacts/semantic_layer/
```

:::info[Auto-delegation]

When you see `-> [auto-delegated to X agent]`, the main session has routed that command to a [specialist subagent](../advanced/wire-agents#auto-delegation-on-individual-commands) automatically, with no extra steps needed. The specialist runs with a focused brief rather than the full engagement context, which typically produces sharper domain-specific output. Review commands (`*-review`) always stay in the main session and require your direct input.

:::

The agent reads `decisions.md` before generating, which is standard behaviour for all Wire agents, and as a result the compliance decision Marcus found in the Fathom transcript surfaces immediately because it was already in `decisions.md`. The field never appears in any generated LookML view, and Marcus did not need to brief the agent explicitly; the decision log did it automatically.

## Key lesson

`decisions.md` is the institutional memory of the engagement: every Wire agent reads it before generating output and appends to it when it makes a non-obvious choice, so when you join a release mid-way, reading `decisions.md` before running any command is the single most important step, because it prevents you from generating artifacts that contradict decisions already made and approved. The Fathom meeting context provides the narrative behind those decisions, but the decisions file is the primary continuity mechanism, and it is where your next session on any release you inherit should start too.
