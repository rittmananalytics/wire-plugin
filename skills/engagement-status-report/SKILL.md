---
name: engagement-status-report
description: >
  Generates a delivery-focused status report for a named Rittman Analytics client
  engagement. Anchored on SOW milestones and sprint cadence — not a relationship
  or commercial report. Reports milestone status (on track / at risk / slipping),
  tickets and MRs delivered, bugs raised and resolved, decisions owed by the
  client, cross-cutting risks, and client and team sentiment. Pulls from Fathom
  meeting transcripts, client Slack channels (external and internal), and
  Atlassian where available. Use when Mark asks for delivery status, project
  status, milestone status, sprint status, "where are we on [client]", "is
  [client] on track", or "what's slipping on [client]". Triggers on any client
  name (Client A, Client B, Client C, Client D, Client E, Barton Peveril, Client F,
  Client H, Client I, Client J) plus a delivery framing.
---

# Client Delivery Status Report

Produces a delivery-focused status report for a single Rittman Analytics client
engagement. The report is anchored on SOW milestones and sprint cadence and is
explicitly **not** a relationship or commercial expansion report — sales
opportunities, pipeline, and new SOW work are out of scope unless they directly
affect delivery capacity.

## When to use this skill

Trigger this skill when Mark asks anything in the shape of:

- "Give me a delivery status report on [client]"
- "Where are we on [client]?"
- "Is [client] on track?"
- "What's slipping on [client]?"
- "Project status for [client]"
- "Milestone status for [client]"
- "How is the [client] engagement going?"
- "Sprint status for [client]"

If the framing is broader (overall account health, commercial expansion,
sentiment), prefer `cowork-client-meeting-intelligence` instead. If both are
wanted, run this skill first for delivery, then add a brief commercial section
at the end.

## Core principles

1. **Anchor on milestones, not meetings.** The report leads with the SOW
   milestone table (planned vs forecast) and works down to tickets, MRs, and
   bugs. Meetings and Slack are *evidence*, not the structure of the report.
2. **Be specific.** Name the tickets (RAP-287, [CLIENT B]-142 etc), name the MRs
   (#116), quote velocity numbers (story points, ticket counts), name the people
   and what they owe each other.
3. **Distinguish "done" from "in QA" from "blocked".** A milestone with the
   build complete but unsigned is not done.
4. **Surface decisions owed by the client.** These are usually the single
   biggest delivery risk.
5. **Be honest about staffing exposure.** Compound leave/handover risks are the
   most common cause of slippage and need calling out explicitly.
6. **Match Mark's voice.** Direct, grounded, no corporate hedging, no em-dashes,
   no Oxford commas. Use prose rather than bullet-soup where the substance allows.
7. **Adapt the report shape to the engagement state.** A steady-state sprint
   engagement, a discovery phase, a closeout/suspension, and a mobilisation all
   need different emphasis. The six-section template is a default, not a
   constraint. For a suspension or closeout, "Cancelled" is a legitimate
   milestone status and the table should make that explicit; the report should
   also include a clear sequence-of-events narrative covering how the closeout
   decision was reached. For a mobilisation, sprint velocity numbers don't yet
   exist and the report should anchor on contract status, resourcing, and
   discovery progress instead.

## Workflow

### 1. Identify the client and time window

Extract the client name from the request. If ambiguous (e.g. "Client C" could
mean a specific carve-out sub-project or the broader engagement), confirm with Mark.

Default time window: **past 5 working days**, ending on the most recent working
day. Calculate from today, excluding weekends and UK bank holidays. User can
override ("past two weeks", "this sprint", "since the last status").

Look up the client in `references/client_directory.md` to derive:
- Email domain (client-a.example, client-c.example, client-b.example, etc.)
- Slack channels: `clients-[shortname]` (external) and
  `clients-[shortname]-internal` (internal). If not found, use
  `Slack:slack_search_channels` to confirm.
- Jira project key if relevant (RAP, [CLIENT B], CAR, etc.)

### 2. Establish the milestone baseline

This is the most important step and the most commonly skipped. Before reporting
on delivery, you need to know **what was committed**. Sources in priority order:

1. **Past conversation memory** — Mark has likely discussed the SOW, milestones,
   and dates in prior sessions. Use `conversation_search` with queries like
   `[client] SOW milestones deliverables`, `[client] milestone 1 milestone 2`,
   `[client] sprint roadmap` if available in this environment.
2. **Confluence** — search for `[client] roadmap`, `[client] SOW`,
   `[client] milestone` via the Atlassian MCP if available.
3. **Recent Slack messages** — Mark or Lewis often ask delivery leads for
   milestone ETAs in `#delivery-and-invoicing` or `#shopfloor`. Search with
   `[client] milestone` to find recent confirmed dates quickly.
4. **Sprint review decks** linked in `#clients-[client]-internal` — these
   often contain the milestone tracker.

If milestones cannot be established with confidence, **say so explicitly** in
the report rather than inventing them. The report can still proceed using
sprint-level commitments as the anchor.

### 3. Retrieve client-facing delivery ceremonies

**Fathom tools may be split across two connectors** depending on how this
session is configured — a custom listing server and the official Fathom
connector for transcripts/summaries. If a listing call fails with a schema
error, the wrong connector is being addressed; check what's available.

Prioritise transcripts based on what the engagement is doing this week:

- **Sprint review / Sprint Changeover** — usually the single richest source
  for delivery status when the engagement is in steady-state sprint cadence.
  Pull the transcript.
- **Sprint planning** — covers what's been pulled into the next sprint and
  what's been deferred.
- **Daily scrums** — useful for blockers but often redundant if you have the
  sprint review.
- **Technical syncs** — relevant if there are specific architecture or
  reconciliation issues.

**Override the default when the engagement is in flux.** When you can see from
Slack signals that something significant happened in the period (a major
decision called, a workshop, a definition meeting, an executive 1:1 between
Mark/Lewis and the client sponsor, a suspension or scope change), those meetings
outrank the sprint review for understanding what's actually going on. Signals to
watch for in `#shopfloor` and the client-internal channel: words like "pause",
"churn", "escalation", "definition workshop", "playback", "joint workplan",
any meeting where Mark or Lewis attends a client call they don't normally attend.

**A prior Client D report turned on a Funnel Definition Sync and a Joint
Workplan meeting, not on routine stand-ups.** Without those transcripts the
suspension narrative would have been framed wrongly as the client being
capricious, when in fact they had substantive internal misalignment that
emerged in the workshop.

Do **not** pull every meeting transcript. Fetch at most 3 transcripts to stay
within tool-call budgets. Pick the three that have the highest narrative density
for the period.

### 4. Retrieve internal team discussions about the client

Search Slack (or the equivalent available tool) for the client name, scoped to
the past 5 working days. Specifically look in:

- `#clients-[client]-internal` — read the full channel for the time window
- `#shopfloor` — look for delivery lead EOD updates mentioning the client
  (Move / Stuck / Watch framing)
- `#delivery-and-invoicing` — Mark and Lewis often probe ETAs here

### 5. Retrieve external client Slack discussions

Read `#clients-[client]` (external channel). What the client is asking, raising,
or escalating in Slack often differs from what they say in meetings, and the
delta is signal.

### 6. Retrieve Jira and Confluence context (optional but valuable)

If Atlassian tools are available, use them to:
- Confirm ticket statuses for specific tickets named in Slack/meetings
- Pull bug ticket detail (description, comments, current state) for any bugs
  raised in the period
- Check Confluence for QA documentation, methodology documents, sprint review
  decks referenced in Slack

This is most useful when the report needs to be unambiguous about whether a
specific ticket is closed, in QA, or open.

### 7. Synthesise into the report

Use the structure in `references/report_template.md`. The report has six
sections:

1. **Milestone status table** (the most important thing — leads the report)
2. **Sprint closeout numbers** (story points, ticket burndown, velocity context)
3. **Milestone-by-milestone delivery picture** (what shipped, what's
   outstanding, what's blocked, named tickets and MRs)
4. **Cross-cutting delivery risks** (staffing, scope creep, technical fragility,
   client decisions owed)
5. **Sentiment** (client side and team side, with named verbatim where it adds
   signal)
6. **Summary view** with the three highest-leverage actions for the next two
   weeks

### 8. Match Mark's writing style

- Direct, grounded, opinionated where warranted.
- **No em-dashes. No Oxford commas.** Both are explicit Mark preferences.
- Avoid AI-characteristic phrasing ("delve into", "navigate", "leverage",
  "robust", "stakeholder alignment").
- Use specific names, ticket IDs, dates, story-point numbers. Vagueness erodes
  the report's value.
- Quote verbatim sparingly — only where the exact wording is the signal
  (frustration, escalation, an unguarded comment in a sprint review).
- Prose paragraphs where the substance allows. Bullets only where the content
  is genuinely list-shaped (e.g. outstanding tickets).
- Length: usually 2-4 pages. Don't pad.

## Output

The report is produced inline in the conversation as markdown prose. Do not
create a file unless Mark explicitly asks for one (e.g. "save this as a doc" or
"I want a PDF"). If a file is requested, default to a `.md` file named
`[client]-delivery-status-[YYYY-MM-DD].md`.

## What NOT to include

- Commercial pipeline, sales opportunities, expansion conversations (unless they
  materially affect delivery capacity, e.g. "Client C ramp-up is pulling Tim off
  Client A").
- Generic platitudes about "great collaboration" or "strong partnership".
- Speculation about client motivations beyond what's supported by direct
  evidence.
- Account management advice beyond the three-action summary at the end.

## Reference files

- `references/report_template.md` — the full report structure with
  section-by-section guidance and a worked example skeleton.
- `references/client_directory.md` — mapping of client names to domains, Slack
  channels, Jira keys, and current delivery leads. Read this whenever a new
  client engagement is referenced.

## Worked examples

Two canonical examples, each demonstrating a different engagement state.

### Client A (steady-state sprint engagement)

Generated from one sprint review transcript + one internal Slack channel + one
external Slack channel. Demonstrates the default report shape:

- Led with a 4-row milestone table showing planned vs forecast dates, with one
  milestone slipping by a week, one at risk, one blocked.
- A sprint closed at 35% of story points (20/57). The report named this number,
  named why (a contractor rolling off, an engineer blocked, another engineer
  still onboarding), and contextualised against a 5-sprint velocity trend.
- For each milestone: named the specific tickets and MRs completed (RAP-287,
  RAP-288, MR #112, #115, #116), named the outstanding items by ticket where
  possible, and called out the specific decisions owed by the client.
- Cross-cutting risks section flagged compound staffing change, an unsent
  escalation, a pattern of scope creep dressed as bugs, single-failure-halts-
  pipeline fragility, and a known analytics-platform attribution limitation.
- Sentiment named individual stakeholders with specific evidence for each, plus
  an internal team picture with verbatim quotes where they conveyed real
  friction.
- Closed with three high-leverage actions for the next two weeks rather than an
  open-ended list.

### Client D (engagement suspended mid-sprint)

Generated from three Fathom transcripts (a 1:1, a definition-workshop sync, and
a joint workplan meeting) plus the client-internal and internal team channels.
Demonstrates the closeout/suspension shape:

- **Three transcripts, not one.** Steady-state engagements need the sprint
  review. A suspension needs the meetings where the decision was made and the
  meeting that triggered it. In this case a mid-week workshop was the trigger
  and a later joint workplan meeting was the moment of suspension; without
  those two, the report would have framed the suspension as capricious rather
  than as the outcome of substantive client-side internal misalignment
  surfaced in the workshop.
- **A sequence-of-events narrative section was added** between the headline
  and the milestone table, walking through the week day by day. For a
  suspension, sequencing matters more than for steady state.
- **Milestone table adapted for closeout.** Columns shifted from "Original
  target / Current status / Forecast" to "Original commitment / Status as of
  [date] / Forecast for closeout". Multiple rows showed "Cancelled" explicitly.
  New rows were added for asks that emerged in the suspension call itself
  (knowledge transfer, gap-analysis write-up).
- **The "Cross-cutting risks" section reoriented to closeout-period risks**
  rather than sprint risks: collision of staff PTO with the notice period, the
  fact that the new gap-analysis ask was being produced by someone who had
  only just joined the engagement, novel engineering patterns at risk of decay
  without proper handover documentation, and reputational risk if the closeout
  itself was poor.
- **Sentiment section surfaced the relationship state.** The client sponsor's
  closing remarks made clear it wasn't a reflection of the team's work and
  that the door wasn't closed — calling this out explicitly mattered because
  the commercial implications differ between "lost relationship" and "paused
  relationship".
- **Three closeout actions rather than three next-sprint actions.** Same
  three-action template, different time horizon (four-week notice period
  rather than two-week sprint).
