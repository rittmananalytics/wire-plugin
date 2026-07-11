# Report Template

This is the canonical structure for a client delivery status report. The Client A 16 May 2026 report is the worked example this template is derived from.

## Title block

```
# [Client] — Delivery Status Report

**Period:** [DD–DD Mon YYYY] (close of Sprint N, start of Sprint N+1)
**Engagement:** [One-line engagement summary, e.g. "Microsoft / Power BI / SQL Server → GCP / BigQuery / dbt / Looker migration"]
**Sources:** [N] Fathom meetings ([list types]), #clients-[client], #clients-[client]-internal, [other sources used]
```

## Section 1: Milestone status

Lead with a markdown table. This is the single most important element of the report.

```
| # | Milestone | Original target | Current status | Forecast |
|---|---|---|---|---|
| M1 | [Name] | [Date or "Complete"] | [Done / In QA / In flight / Blocked + 1-line detail] | [Date or "Complete" or "At risk"] |
```

Then immediately follow with a one-paragraph narrative framing of the milestone position. If the delivery lead has given a recent ETA confirmation in Slack (e.g. Lydia confirming dates to Mark), quote it verbatim — it's the most authoritative source.

**For a closeout or suspension, adapt the column headers and content:**

```
| # | Milestone / workstream | Original commitment | Status as of [date] | Forecast for closeout |
```

In a closeout table, "Cancelled" is a legitimate status and should appear explicitly. Add new rows for asks that emerged from the suspension/closeout conversation itself (e.g. knowledge transfer, gap-analysis write-up, final handover documentation). The table then captures both what won't be finished and what's been newly committed for the notice period.

## Section 1b (closeout/suspension only): Sequence of events

For a suspension or closeout, insert this section between the milestone table and the sprint closeout section. A day-by-day or meeting-by-meeting narrative covering how the decision was reached. This matters more than sprint velocity numbers in a closeout because:

- The commercial implications differ depending on whether the client suspended for substantive internal reasons (recoverable relationship) or because they were dissatisfied with Rittman's work (harder to recover).
- Future re-engagement conversations need accurate context on what happened and why.
- It prevents the report from reading as a complaint about the client when the actual story is more nuanced.

Skip this section entirely for steady-state engagements — it's not needed.

## Section 2: Sprint closeout (or equivalent)

For a steady-state sprint engagement, a short subsection with the velocity numbers and the reasons behind them.

Include:
- Tickets completed of total
- Story points delivered of planned
- Velocity trend over last 3-5 sprints (better, worse, flat)
- Named reasons for the velocity shape (resource changes, blockers, onboarding overhead)

Pull the numbers from the sprint review transcript. The Sprint Changeover meeting on Fathom usually contains them in the first 5 minutes of the transcript.

If the sprint isn't closing in the report window, label this section "Sprint N progress" and give a partial picture instead.

**For non-sprint engagement states, replace this section with the equivalent for that state:**

- **Discovery phase:** "Discovery progress" — what's been interviewed, what's been documented, what's still open, what the PSF or scope artefact looks like.
- **Mobilisation:** "Mobilisation status" — contract status, resourcing decisions, contractor onboarding, kickoff date, dependencies on client-side access provisioning.
- **Closeout/suspension:** Skip the section entirely. The sequence-of-events section in 1b carries the equivalent narrative weight.

## Section 3: Milestone-by-milestone delivery picture

The core of the report. For each milestone, a subsection structured as:

```
### M[N] — [Name] ([status one-liner])

**Where we are:** [1-2 sentence prose framing]

**Key deliverables completed this period:**
- [Named ticket or MR, what it did]
- [Named ticket or MR, what it did]
...

**Outstanding / open:**
- [Named ticket, what it's blocked on, who owns it]
- [Decision owed by client, with framing]
...

**Bugs raised this period (if relevant):**
- **[TICKET-ID]** — [Description]. [Current status]. [Owner]
...

**Open risk (if relevant):** [Specific risk paragraph]
```

Be ruthless about specificity. "The dashboard is in progress" is useless. "Lukasz is building the customer acquisition dashboard, expected internal-QA-ready Monday 18 May, with two KPIs (First-Order Profitability, Lapsed Customer Count) still unresolved as in-scope or deferred" is the right level.

## Section 4: Cross-cutting delivery risks

Numbered list of 3-6 risks. Each risk gets a bold name and a paragraph of specifics. Common categories:

1. **Compound staffing change** — Who's rolling off, who's on AL when, who's new, what work is exposed. Name names and dates.
2. **Outstanding client decisions** — What we've asked for, when, what happens if it doesn't come. Reference the escalation path.
3. **Scope creep** — Pattern of new requests being raised as bugs or KPI clarifications rather than change requests. Reference Mark or Lewis's account management framing if they've raised it in #shopfloor.
4. **Technical / pipeline fragility** — Specific failure modes already observed (e.g. one failing test halting the DAG, ingestion reconciliation issues).
5. **Data / methodology limitations** — Reliability windows on source data (e.g. GA4 only reliable from mid-2025) that constrain what the dashboards can answer.
6. **Sign-off / QA capacity on client side** — When Rittman has completed work but client-side QA hasn't started or has fallen between the cracks.

Rank by impact on the next two weeks, not abstract severity.

## Section 5: Sentiment

Two subsections: **Client** and **Team**.

For each named individual who matters to delivery (not every attendee), 1-3 sentences covering:
- Their role in the engagement
- Their current disposition (cooperative, frustrated, disengaged, escalating)
- The specific evidence (a Slack message, a verbatim comment in a meeting)
- Anything they currently owe or are awaiting

Use verbatim quotes sparingly and only where the exact wording is the signal. Frustration, escalation, or unguarded sprint-review comments are the highest-value verbatim. Don't quote routine status updates.

End each subsection with a one-line net read: "Mixed positive", "Stretched but constructive", "Friction surfacing", etc.

## Section 6: Summary view

A short closing section with:

1. A 1-2 sentence overall read on delivery.
2. **The three things that most affect delivery in the next two weeks.** Numbered, each with one paragraph. These are not generic recommendations — they should be specific, named, and actionable within the two-week window.

## Style guide

**Mark's preferences (these are firm, not optional):**
- No em-dashes anywhere. Use commas, semicolons, parentheses, or sentence breaks instead.
- No Oxford commas. "Tim, Lukasz and Olivier" not "Tim, Lukasz, and Olivier".
- Avoid AI-characteristic phrasing: "delve", "navigate", "leverage", "robust", "stakeholder alignment", "ecosystem", "synergies", "bandwidth" (as a metaphor for capacity is OK, as a buzzword is not).
- No "It's important to note that" or "It's worth noting" or other meta-commentary openers.
- Avoid hedging adverbs (potentially, arguably, possibly) unless the uncertainty is the point.
- Write in active voice. "Lydia escalated to the client stakeholder" not "the matter was escalated to the client stakeholder".
- Prose paragraphs where the substance allows. Bullets only where content is list-shaped.

**Verbatim quotes:**
- Format: italic with em-quotes, attributed, no source needed inline (the report's source list at the bottom covers it).
- Example: *"There is truly mostly unknown unknowns at the moment, which disallow me to say whether I'm going to be able to accomplish everything."* — Lukasz, Sprint Changeover
- Use them when:
  - They convey friction, frustration, or escalation that paraphrase would dilute.
  - They contain a specific commitment or refusal.
  - They demonstrate scope tension or sentiment that the rest of the report needs to support.

**Length target:**
- 2-4 pages of Markdown.
- Single sprint review + one internal Slack + one external Slack channel should yield 3-4 pages.
- More sources (2-3 transcripts, multiple Slack windows) may go to 4-5.
- Beyond 5 pages, the report is probably trying to be a relationship report and should be cut.

## Closing references block

End the report with:

```
---

**Key references:**
- [Sprint review meeting title], [date]: [Fathom share URL]
- [Other key meeting], [date]: [Fathom share URL]
- [Notable Slack post]: [#channel], [date] [time]
- [Confluence page if relevant]: [link]
```

Only include references that materially informed the report. Don't pad with every meeting attended.
