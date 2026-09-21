---
sidebar_position: 7
title: "A Full Platform Build, with Commands"
---

# A Full Platform Build, with Commands

Every Monday morning Laura Hennessy, the finance director at Eversholt Brewing Co, exports last week's orders from the Shopify store, last week's production costs from the BrewMan ERP and last week's wholesale deals from HubSpot, and spends two hours in Excel turning the three exports into the margin and revenue figures the board reads on Tuesday. The three systems have never been connected. Tom Barnard, the brewery's one data engineer, has been asked to fix this for two years and has never had the six clear weeks it would take. Rittman Analytics has been engaged to deliver, in twelve days on a fixed price, a platform on BigQuery, dbt Cloud and Looker that makes margin by product and revenue by channel available every morning without anybody exporting anything.

This is a "full platform" release, the largest kind Wire runs, with pipelines, a dbt project, a semantic layer, dashboards, scheduled jobs, tests, deployment and training all in scope, and you will direct it in plain language exactly as you directed the smaller releases in Chapters 2 to 5. But now that Chapter 6 has shown you that everything Wire does is a command, a fair question arises: if Wire runs the commands for you, why would you ever type one? The answer is that on most releases there are a handful of moments when typing is quicker, clearer or leaves a better record than describing what you want, and this chapter shows seven of them, each with the reason it was the better choice at that point.

We will follow the twelve days in order, and along the way we will start a session with a command rather than a sentence, recover from a hand edit, repair the record after a colleague worked outside Wire, take the wheel for a review and hand it back, raise the pull request and close the release. Let's start with what you need before you begin.

## Before You Begin

You will need the signed statement of work and schema exports for all three source systems in the `docs` folder of a new repository, and access agreed to a BigQuery project, a dbt Cloud account and the Looker instance, since unlike Chapter 2 this build runs against real infrastructure from the start. You will need to know that Laura Hennessy approves the business definitions and the acceptance, that Tom Barnard is the client-side reviewer for the technical work and that James Whitfield leads the ops team for the second acceptance session.

At a high level, the release runs through eight stages:

1. Agree the business rules for margin and revenue, and approve the requirements.
2. Start the second day with a command, and approve the design.
3. Build the pipelines and the dbt models, and recover from a hand edit.
4. Repair the record after a colleague's weekend edits.
5. Test, and take the wheel for the acceptance review.
6. Approve the deployment runbook and go live.
7. Raise the pull request.
8. Deliver the training and documentation, and close the release.

Let's now take a look at each of these in turn.

## Stage 1: Definitions, Requirements and the Line at the End of Every Report

| You say | Wire replies |
|---|---|
| "New engagement for Eversholt Brewing, full platform on BigQuery, dbt Cloud and Looker. Statement of work and the three schema exports are in the docs folder. Up to five pieces of work at a time. Stop at every decision. Start with the business rules for margin: finance and production count duty differently." | "This reads as a full platform release: ingestion, transformation, semantic layer and dashboards are all in scope. Client: Eversholt Brewing Co. Release: Analytics Platform. Limits: five pieces of work at a time, stop at every decision. Which email domain do the client's people use?" |
| "eversholtbrewing.co.uk. Confirm." | "Engagement set up. Starting the business rules step for margin and revenue." |
| *(later)* | "Business rules register, two domains, nine rules. Six agreed. Two disputed: gross margin (the finance spreadsheet deducts duty, the BrewMan report does not; they differ by 11 points on last quarter) and the definition of a wholesale sale (HubSpot deal stage, or a custom field the reps fill in inconsistently). One unknown: how duty drawback on exported volume should be treated. Nobody has a definition, so it is recorded as unknown. Reconciliation queries for the two disputed rules are written and run. Approve now, changes or park for the finance director?" |
| "Park for Laura. Draft the requirements." | "Parked, waiting on Laura Hennessy. Drafting the requirements from the statement of work and the recording of the discovery call." |
| *(later)* | "Requirements drafted: seven functional requirements with acceptance criteria and four non-functional (data by 07:00 daily, row-level security by role, dashboards under three seconds, 99.5 percent pipeline uptime). Two decisions I made are on the record: sales modelled at product-per-day grain rather than order line, because order-line grain multiplies the ingestion volume twelve times for no reporting benefit; and wholesale identified by HubSpot deal stage, because the custom field is unreliable. All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:requirements-generate 01-eversholt-analytics-platform`, `/wire:requirements-validate 01-eversholt-analytics-platform`" |

That last line, "Ran:", has ended every report Wire made since Chapter 1, and Chapter 6 explained what it means: it names the commands that ran, and everything Wire does is a command. It follows, therefore, that you could have typed that one yourself,

```
/wire:requirements-generate 01-eversholt-analytics-platform
```

and the result would have been identical, down to the row in the record, the only difference being that the Session column would say the command was typed rather than run by the orchestration agent. Typing is how Gemini CLI users run Wire and how anyone runs it in manual mode, so nothing in this chapter is exotic; what we are interested in is when typing is the better choice in Claude Code too.

## Stage 2: Starting a Session With a Command

Laura rules by phone that evening: gross margin deducts duty, wholesale is by deal stage and duty drawback stays unknown for now. The next morning you open a new session and, instead of a sentence, you type the session-start command.

```
/wire:start
```

Wire prints where the release is, the decisions waiting on you and the next thing it would do:

```
Release: 01-eversholt-analytics-platform (full platform), day 2
Phase: requirements. 1 of 14 artifacts complete.

Waiting on you (2):
  PD-1  Business rules register: approve now, or park for the finance director?
  PD-2  Requirements: approve now, changes or park?

After that: conceptual model and pipeline design can start together.
  /wire:conceptual_model-generate 01-eversholt-analytics-platform
  /wire:pipeline_design-generate 01-eversholt-analytics-platform

Shall I run them? (yes / no / show me the command)
```

So why type this rather than simply saying good morning? A session that opens with a sentence gets the parked decisions as the first line of the reply, which is usually enough. The start command, however, gives you the whole picture in one block: the phase, the progress, what is waiting, what comes next and the command for it, together with the offer to run it. As such it is the right first move when you have been away from a release for a day or more, when you are picking up a release that somebody else started, or when you simply want to see the state of things before you commit to anything.

| You say | Wire replies |
|---|---|
| "Register approved with Laura's rulings: margin deducts duty, wholesale by deal stage, drawback stays unknown. Requirements approved. Yes, run them." | "Register updated and approved under Laura Hennessy's name. Requirements approved. Two pieces of design work are released and neither depends on the other, so here is the run:<br/>1. The conceptual model, in the background: `/wire:conceptual_model-generate 01-eversholt-analytics-platform`<br/>2. The pipeline design, in the background: `/wire:pipeline_design-generate 01-eversholt-analytics-platform`<br/>Neither queries a warehouse. The run stops at the conceptual model review. Go, adjust or cancel?<br/><br/>Ran: `/wire:business-rules-review 01-eversholt-analytics-platform`, `/wire:requirements-review 01-eversholt-analytics-platform`" |
| "Go." | "Starting both.<br/><br/>Running: `/wire:conceptual_model-generate 01-eversholt-analytics-platform`, `/wire:pipeline_design-generate 01-eversholt-analytics-platform`" |
| *(later)* | "Conceptual model: nine business concepts, all checks pass. Pipeline design: three Fivetran connectors (Shopify, HubSpot and BrewMan by change data capture through a Cloud SQL proxy, which needs a small Cloud Function for authentication), landing in BigQuery, with an estimate of 2.1 million rows a month. All checks pass. Both need your approval.<br/><br/>Ran: `/wire:conceptual_model-generate 01-eversholt-analytics-platform`, `/wire:conceptual_model-validate 01-eversholt-analytics-platform`, `/wire:pipeline_design-generate 01-eversholt-analytics-platform`, `/wire:pipeline_design-validate 01-eversholt-analytics-platform`" |
| "Approve both. Then the data model, and a mockup of the margin dashboard for Laura." | "Approved. Drafting the data model in the background. Dashboard mockups are optional in this kind of release; you have asked for one, so I will build it with you once the data model is approved, because in a full platform release the mockup illustrates the approved model.<br/><br/>Ran: `/wire:conceptual_model-review 01-eversholt-analytics-platform`, `/wire:pipeline_design-review 01-eversholt-analytics-platform`. Running: `/wire:data_model-generate 01-eversholt-analytics-platform`" |
| *(later)* | "Data model drafted: seven staging models, one integration model that resolves a product across Shopify and BrewMan through a crosswalk file, five warehouse models including a margin summary. I looked for a matching model in Wire's library and found none for brewing, so nothing was proposed. One open question is parked: BrewMan records production by batch; is the reporting grain the brew day or the individual batch? All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:data_model-generate 01-eversholt-analytics-platform`, `/wire:data_model-validate 01-eversholt-analytics-platform`" |
| "Brew day. Approve." | "Grain recorded as brew day. Approved. Building the margin dashboard mockup with you now." |

The mockup takes one round of changes, since Laura wants duty shown as its own column, and is approved. Design is complete at the end of the third day.

:::note
Notice that the library check came back empty this time and Wire said so in one sentence rather than staying silent. That is the normal outcome for most industries, and it is worth knowing that a proposal only appears when there is a plausible match, so that its absence is not a fault.
:::

## Stage 3: The Build, and a Command After a Hand Edit

| You say | Wire replies |
|---|---|
| "Build everything that's ready." | "Ready now: the pipelines, and the dbt models. Here is the run:<br/>1. The pipelines, one lane: `/wire:pipeline-generate 01-eversholt-analytics-platform`<br/>2. The 13 dbt models in three waves (two staging lanes at the same time, then the integration model, then two warehouse lanes): `/wire:dbt-generate 01-eversholt-analytics-platform`<br/>3. Build and test against BigQuery: `/wire:dbt-validate 01-eversholt-analytics-platform` (queries the warehouse)<br/>At most three lanes at once, within your limit of five. Not planned yet: the semantic layer and the scheduling, which wait for the dbt checks and the pipeline checks. The run stops at the pipeline review. Go, adjust or cancel?" |
| "Go." | "Starting.<br/><br/>Running: `/wire:pipeline-generate 01-eversholt-analytics-platform`, `/wire:dbt-generate 01-eversholt-analytics-platform` (five lanes)" |
| *(later)* | "Pipelines: three connector configurations, the BrewMan Cloud Function with its key in Secret Manager, failed syncs written to an errors table, three consecutive failures alerting the data channel. Checks pass. dbt: 13 models, 41 tests, documentation complete. Two decisions on the record from the lanes: the unified product key falls back from Shopify SKU to BrewMan product code, and duty is a separate column in the production cost fact, which resolves Laura's mockup request. Running the dbt checks and build against BigQuery now.<br/><br/>Ran: `/wire:pipeline-generate 01-eversholt-analytics-platform`, `/wire:pipeline-validate 01-eversholt-analytics-platform`, `/wire:dbt-generate 01-eversholt-analytics-platform` (five lanes)" |
| *(later)* | "dbt build: 13 models built, 40 of 41 tests pass. One failure: the ingredient cost conversion produces negative values for two rows where BrewMan stores a credit note. Approve with the failure recorded, ask me to fix it or fix it yourself?" |

You know the BrewMan credit note convention and would sooner write the two-line fix than describe it, so you edit the staging model by hand and save it. Then you type two commands, one to rebuild the models and one to re-run the checks and record the result.

```
/wire:utils-run-dbt 01-eversholt-analytics-platform
/wire:dbt-validate 01-eversholt-analytics-platform
```

```
dbt run: 13 models built, 0 errors
dbt test: 41 of 41 tests pass
Naming, structure, keys, documentation: pass
Recorded: dbt validate PASS (typed)
```

Why type these rather than asking Wire to "rebuild and check again"? Either would have worked, but you have just changed a file outside Wire, and what you want is a record that says, unambiguously, that the models passed every check after your edit and that a person ran the checks. The run command rebuilds the models; the validate command re-runs the tests and every other check and writes the result to the record as a typed run, which is exactly that record. Furthermore, when you come to explain the fix to Tom Barnard, "I edited the staging model and re-ran validate" is a sentence he can follow in the log.

| You say | Wire replies |
|---|---|
| "Approve the models. Carry on." | "Approved. The dbt checks passing releases the semantic layer; the pipeline checks passing releases the scheduling. Starting both." |
| *(later)* | "Semantic layer: views for all five warehouse models, four explores (product performance, channel revenue, production margin, wholesale accounts). Scheduling: a dbt Cloud production job daily at 06:00 UTC and a job on every pull request. Checks pass on both. Approve now, changes or park?<br/><br/>Ran: `/wire:semantic_layer-generate 01-eversholt-analytics-platform`, `/wire:semantic_layer-validate 01-eversholt-analytics-platform`, `/wire:orchestration-generate 01-eversholt-analytics-platform`, `/wire:orchestration-validate 01-eversholt-analytics-platform`" |
| "Approve both. Dashboards." | "Approved. Building the three dashboards from the approved mockup and the model: Margin by SKU, Channel Revenue, Production Cost." |

## Stage 4: A Command After Someone Else's Edits

Over the weekend Tom Barnard, keen to get involved, edits two of the LookML views directly in the repository and commits them. Nothing about that went through Wire, so the record still says the semantic layer was last written by Wire on the seventh day, and if you left it there the record would be wrong in a way that nobody would notice until it mattered. On Monday you type:

```
/wire:status-sync 01-eversholt-analytics-platform
```

```
Drift report: 01-eversholt-analytics-platform

1. semantic_layer: record behind. Two files under development/lookml/ changed
   in commit 4f2c1e9 (Tom Barnard, Sat 14:12) after the recorded generate.
   Repair: add an execution log row for the change, mark validate as stale.
2. dashboards: record behind. Generated at 17:40 Friday, no log row.
   Repair: add the log row.

Apply repairs 1–2? (yes / pick numbers / no)
```

The record updates itself only when work runs through a Wire command, so when somebody edits by hand the record falls behind reality. The sync command compares the record with the git history and the files on disk, lists every difference it finds and repairs the record only with your confirmation; a drift report you decline to apply is a perfectly valid outcome and writes nothing. It is the right thing to run whenever work has happened outside Wire, and it is on the checklist to run before raising a pull request for exactly that reason.

:::note
The sync command never downgrades a recorded state merely because it cannot find evidence for it. Where the record says a step is complete and the file is missing, it asks you what happened rather than assuming, so that a moved file does not become a lost artifact.
:::

You apply both repairs and say "re-check the semantic layer". Wire re-runs the checks on Tom's edits, which pass, and the dashboards are built and approved after one rename.

## Stage 5: Testing, and Handing Control Back and Forth

| You say | Wire replies |
|---|---|
| "Data quality tests and the acceptance plan." | "Data quality: a freshness check that yesterday's sales are present by 07:00, a daily reconciliation between Shopify order count and the sales fact within five percent, a null-rate check on margin percentage and a check that every product key in sales exists in the product dimension. Acceptance plan: two sessions, ops team and finance director, each step traced to a requirement. Checks pass on both. Approve now, changes or park?<br/><br/>Ran: `/wire:data_quality-generate 01-eversholt-analytics-platform`, `/wire:data_quality-validate 01-eversholt-analytics-platform`, `/wire:uat-generate 01-eversholt-analytics-platform`" |
| "Approve both. Sessions Thursday and Friday." | "Approved. Nothing else can start until acceptance is done." |

The finance session raises one finding: the margin summary does not account for duty drawback, the excise refund on exported wholesale volume, which is precisely the rule the register recorded as unknown on the first day. Laura accepts deferring it to a second phase. You want the acceptance record written in her words rather than in a summary of yours, so you take the wheel.

| You say | Wire replies |
|---|---|
| "You drive." | "Understood. I will not start or dispatch anything until you hand back. Recorded." |

You then type the review command and answer its questions directly:

```
/wire:uat-review 01-eversholt-analytics-platform
```

It walks you through the two sessions, asks for each finding with its severity and its disposition, and records the approval under Laura Hennessy's name with the drawback finding deferred, together with a decision in the record that the production cost fact needs a drawback adjustment column in the next release.

Why type a review, when the whole point of directing is that Wire runs the reviews for you? Because review commands ask questions and record your answers, and there are occasions, an acceptance session with a client sponsor being the obvious one, when you want the record in your own words and hers rather than in a paraphrase of a sentence you typed. "You drive" keeps the orchestration agent from starting anything else while you do it, and it stays in force for the rest of the session until you hand back.

| You say | Wire replies |
|---|---|
| "I'll drive. Deployment." | "Control back to me, recorded. Acceptance is approved and data quality passed, so the deployment runbook is released. Drafting it." |

## Stage 6: The Runbook and Go-Live

| You say | Wire replies |
|---|---|
| *(later)* | "Runbook: connector activation order, BigQuery datasets and permissions, dbt Cloud environments and jobs, the Looker connection and dashboard publish, monitoring and a rollback step for each layer. Checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:deployment-generate 01-eversholt-analytics-platform`, `/wire:deployment-validate 01-eversholt-analytics-platform`" |
| "Approve. We go live Friday." | "Approved. The runbook is ready." |

You and Tom follow the runbook on Friday morning. The connectors sync, the scheduled job runs, the dashboards are published and the alerts are live, and Laura's Monday morning is her own again.

## Stage 7: The Pull Request

With the platform live, the release branch needs to become a pull request with the evidence attached, and this is a job with a fixed shape and no decision in it, which makes it a natural one to type.

```
/wire:utils-commit 01-eversholt-analytics-platform deployment review
/wire:utils-pr-create 01-eversholt-analytics-platform
```

The first command stages the release folder's changes and commits them with a message naming the artifact and the step. The second opens the pull request with a body built from the record: the artifacts completed, the checks passed, the approvals with names, the decisions made and a note that the status-sync run happened. Typing them is quicker than describing them, and the pull request body is built from the record either way.

:::note
The commit utility never pushes, never amends an earlier commit and never bypasses hooks; if a pre-commit hook fails it reports the failure and leaves the files staged for you to deal with. Pushing is always your decision.
:::

## Stage 8: Enablement, and Closing the Release

| You say | Wire replies |
|---|---|
| "Training and documentation." | "Training: a two-hour data team session for Tom Barnard (connectors, the Cloud Function and key rotation, extending the dbt layers, the jobs, tracing a batch from BrewMan to the margin summary) and a 90-minute end-user session (dashboards, filters, freshness, how to raise an issue, what the deferred drawback item means). Documentation: architecture, dbt model reference, job reference, LookML field catalogue, operational runbook. Checks pass on both. Approve now, changes or park?<br/><br/>Ran: `/wire:training-generate 01-eversholt-analytics-platform`, `/wire:training-validate 01-eversholt-analytics-platform`, `/wire:documentation-generate 01-eversholt-analytics-platform`, `/wire:documentation-validate 01-eversholt-analytics-platform`" |
| "Approve both." | "Approved. Every artifact is complete. The release is done." |

You close the release with the archive command, which moves the release folder and its whole record into the archive so that it no longer appears among the active releases but is still there for anyone who needs it:

```
/wire:archive 01-eversholt-analytics-platform
```

```
Archive 01-eversholt-analytics-platform? 14 of 14 artifacts complete. (yes / no)
> yes
Release archived. Moved to .wire/releases/_archive/01-eversholt-analytics-platform/
```

The record goes with it: 14 artifacts, 44 command runs of which six were typed and nine decisions.

## What You Should Now Have

| Produced | Detail |
|---|---|
| Business rules register | Margin and revenue, nine rules, one still unknown and carried to phase 2 |
| Requirements | Seven functional, four non-functional |
| Design | Conceptual model, pipeline design, data model, one dashboard mockup |
| Pipelines | Three Fivetran connectors, one Cloud Function |
| dbt project | Seven staging, one integration and five warehouse models; 41 tests |
| Scheduling | dbt Cloud daily and pull-request jobs |
| Semantic layer | Views for five models, four explores |
| Looker dashboards | Three |
| Data quality tests | Freshness, reconciliation, null rate, key integrity |
| Acceptance | Two sessions, one finding deferred with a recorded decision |
| Deployment runbook | Followed on go-live day |
| Training and documentation | Two sessions; five documents |

## So When Should You Type a Command?

Drawing the seven occasions in this chapter together, together with two that did not arise at Eversholt but come up often enough to list:

| Situation | Type |
|---|---|
| Starting a session after time away, or picking up someone else's release | `/wire:start` |
| Wanting the full state of every artifact | `/wire:status <release>` |
| You edited a dbt model by hand | `/wire:utils-run-dbt <release>`, then `/wire:dbt-validate <release>` |
| Someone worked outside Wire and the record is behind | `/wire:status-sync <release>` |
| A ticket against a release that is already live (Chapter 4) | `/wire:work <release> <ticket>` |
| You want to answer a review's questions yourself | "You drive", then `/wire:<artifact>-review <release>`, then "I'll drive" |
| Committing and raising the pull request | `/wire:utils-commit <release> <artifact> <step>`, `/wire:utils-pr-create <release>` |
| Closing a finished release | `/wire:archive <release>` |
| You have forgotten a command | `/wire:help` |

Every command name you will ever need is on the last line of a Wire report, and on Gemini CLI or in manual mode you type all of them. Part 2 begins with [the full command reference](../reference/commands.md), and from here on that is where to look.
