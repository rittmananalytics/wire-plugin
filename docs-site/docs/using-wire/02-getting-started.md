---
sidebar_position: 2
title: "Getting Started"
---

# Getting Started

Picture the retail operations director at Northwind Retail. She runs 40 stores, her regional managers get a store performance pack once a month, built by hand from till exports, footfall counter downloads and the staff rota, and she has just signed a statement of work for daily dashboards instead. She cannot assess a data model document or a schema diagram, and she would not pretend to, but she can tell you within thirty seconds of looking at a dashboard whether it is the one her managers need. The traditional approach, in which the data layer is built first and the dashboards appear at the end, would have her waiting six weeks to find out, and finding out at the point where changing direction is most expensive.

The same problem turns up on most dashboard engagements, whatever the industry: the person who has to approve the result is the person least able to approve it from a design document, and the moment they can finally see it is the moment it is hardest to change. Wouldn't it be better if the client could approve the dashboards before a line of the data layer was written, and then click through them on believable numbers before the warehouse even existed?

That is what a "dashboards-first" release does. The dashboards are designed and approved first, as working prototypes that open in a browser; the data model is derived from the approved designs rather than the other way round; the whole platform is then built on generated sample data, so that the client is using real dashboards in Looker before any warehouse access exists; and when the real data arrives, Wire switches the platform over to it. At Northwind, where client IT is still two weeks away from having a BigQuery project ready, it is the obvious choice.

In this chapter we will follow that release from an empty repository to live dashboards, in the words you say to Wire and the replies it gives. We will not look at how Wire does the work underneath, which is the subject of Chapter 6, and we will not type a single command, which is the subject of Chapter 7. Let's start though with what you need before you begin, and the shape of the release as a whole.

## Before You Begin

You will need Wire installed in Claude Code (see Chapter 1), a new git repository for the engagement and three things from the client in a `docs` folder inside it: the signed statement of work, a schema export from the till system, and a copy of the current monthly pack so that Wire can see what the managers get today. You will also need to know who at the client approves the dashboard designs, which at Northwind is the retail operations director.

At a high level, the release runs through seven stages:

1. Set up the engagement and agree the requirements.
2. Design the dashboards as a working prototype and get them approved.
3. Derive the data model from the approved design and generate sample data.
4. Build the models, the semantic layer and the dashboards on the sample data.
5. Switch the platform to real data once the warehouse is ready.
6. Test, and run the acceptance sessions.
7. Go live, and prepare the training.

Let's now take a look at each of these in turn.

## Stage 1: Setting Up and Agreeing the Requirements

Open Claude Code in the new repository and say what you want. Notice in the exchange below that you give Wire three kinds of thing at once: what the work is, where the source material is and the limits you want it to work within.

| You say | Wire replies |
|---|---|
| "I want to start by creating some dashboard mocks for store performance dashboards. The statement of work is in the docs folder. No warehouse access for two weeks. Two pieces of work at a time at most, nothing that queries a warehouse and stop at every decision." | "This reads as a dashboards-first release: the client wants approved dashboard designs before any data work, and there is no warehouse to query yet. Here is what I will set up, taking the client from the statement of work. Client: Northwind Retail. Engagement lead: you. Release: Store Performance. Because there is no warehouse access, the first build will run on sample data. Limits: two pieces of work at a time, no warehouse queries, stop at every decision. One question first: which email domain do the client's people use? I use it to find their meeting recordings." |
| "northwindretail.co.uk. Confirm." | "Engagement set up on a new branch. Before the design work starts, this kind of release can begin with a business rules step: agreeing what each number means, such as like-for-like sales, before anything is built on a definition. Run it now, or agree the definitions with the client at kickoff?<br/><br/>Ran: `/wire:new`" |
| "Skip it. We'll agree definitions at kickoff." | "Recorded as your decision, with the reason. Drafting the requirements from the statement of work now.<br/><br/>Running: `/wire:requirements-generate 01-store-performance`" |
| *(a few minutes)* | "Requirements drafted: 14 requirements, all checks pass. Two need clarifying with the client: how like-for-like sales is defined when a store refits, and whether footfall is counted per store or per entrance. Both are marked in the document. Approve now, ask for changes or park for the client?<br/><br/>Ran: `/wire:requirements-generate 01-store-performance`, `/wire:requirements-validate 01-store-performance`" |
| "Approve internally. Carry the two questions to the kickoff, and prepare a workshop pack for it." | "Approved under your name. The two questions are recorded as open items for kickoff. Requirements approval releases three pieces of work, none of which depends on another, so here is the run before it starts:<br/>1. The workshop pack, in the background: `/wire:workshops-generate 01-store-performance`<br/>2. The conceptual model, in the background: `/wire:conceptual_model-generate 01-store-performance`<br/>3. The dashboard prototype, with you here because it needs your input: `/wire:mockups-generate 01-store-performance`<br/>Your limit is two at a time, so the prototype starts when one of the other two finishes. Nothing here queries a warehouse. The run stops at the first review. Go, adjust or cancel?<br/><br/>Ran: `/wire:requirements-review 01-store-performance`" |
| "Go." | "Starting the workshop pack and the conceptual model; the prototype follows.<br/><br/>Running: `/wire:workshops-generate 01-store-performance`, `/wire:conceptual_model-generate 01-store-performance`, `/wire:mockups-generate 01-store-performance` (queued)" |

Four things are worth noticing here, because you will see them on every release. Wire proposed the kind of release and gave its reason, and then asked you to confirm before it did anything, so that the one irreversible-feeling step (setting up the engagement) was yours. It asked the one question it could not answer from the statement of work rather than guessing at it. When it stopped at the requirements for your decision, it told you what that decision would unlock, so that you knew what would happen next before it happened. And before it started three pieces of work at once, it set them out one line each, with the command for each and where the run would stop, and waited for your go. A single piece of work does not get a plan, just the command name on the last line; two or more do, and so does anything that queries a warehouse, because those are the runs you want to have seen before they start.

:::note
"Approve internally" records the approval under your name, not the client's. The two open questions stay on the record until you tell Wire they have been answered, which is exactly what you want when the client has not seen the document yet but the design work cannot wait.
:::

## Stage 2: The Dashboard Prototype

The prototype is built with you in the conversation rather than in the background, because it needs your reactions as it goes. What Wire produces is a single file that opens in any browser, with tabs, charts you can hover over and filters that change the numbers, and the numbers are made up but shaped to look real, so that a chart with a weekend peak looks like a chart with a weekend peak rather than a flat line.

| You say | Wire replies |
|---|---|
| *(nothing)* | "Prototype ready. Open `design/mockups/store-performance.html` in a browser. Four sections: Sales Overview (four headline tiles: sales, transactions, average basket, like-for-like), Store League Table, Footfall and Conversion, Staffing against Sales. Twelve charts, three filters: date range, region, store. Tell me what to change.<br/><br/>Ran: `/wire:mockups-generate 01-store-performance`" |
| "The region filter only works on the league table. Make it apply everywhere. And split the league table into two tabs, high street and retail park." | "Done. Region filter now applies to all four sections. League table split: High Street (26 stores), Retail Park (14 stores). Second version saved alongside the first.<br/><br/>Ran: `/wire:mockups-generate 01-store-performance` (second version)" |
| "Good. Send it to the ops director for approval. I'll come back when she has answered." | "Noted. The prototype review is parked, waiting on the retail operations director. In the meantime the conceptual model is drafted: seven business concepts (store, region, product category, transaction, footfall reading, staff shift, calendar) and how they relate. All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:mockups-review 01-store-performance` (parked), `/wire:conceptual_model-generate 01-store-performance`, `/wire:conceptual_model-validate 01-store-performance`" |
| "Approve." | "Approved. Nothing else can start until the prototype is approved, so I will stop here.<br/><br/>Ran: `/wire:conceptual_model-review 01-store-performance`" |

That is the end of the first day, and you have sent eight messages. The prototype is parked with the client, the conceptual model is approved and Wire has told you plainly that nothing else can move until the client answers, which is true: the chart catalogue, the data model and the sample data all derive from the approved design, so there is nothing sensible for it to do until the design is approved.

## Stage 3: From Approved Design to Data Model and Sample Data

The operations director approves the second version by email the next morning, and you open a new session. The first thing Wire does in any new session is tell you what is waiting on you, so you never have to remember where you left off.

| You say | Wire replies |
|---|---|
| *(open a session)* | "One decision is waiting: the dashboard prototype, parked yesterday for the retail operations director. Has she answered?<br/><br/>Ran: `/wire:start`" |
| "Approved, by email this morning. Carry on." | "Recorded as approved, with her name and the date. From the approved prototype I have derived two things: a catalogue of all twelve charts (what each shows, which filters apply, how each number is calculated) and a written statement of what the data has to provide: two sets of facts (sales by store by day, footfall by store by hour) and four dimensions (store, region, calendar, staff shift). The catalogue is complete: every chart has a source for every number. Two pieces of work are now ready and do not depend on each other, so here is the run:<br/>1. The data model, in the background: `/wire:data_model-generate 01-store-performance`<br/>2. The sample data, in the background: `/wire:seed_data-generate 01-store-performance`<br/>Two at once, within your limit. Neither queries a warehouse. The run stops at the data model review. Go, adjust or cancel?<br/><br/>Ran: `/wire:mockups-review 01-store-performance`, `/wire:viz_catalog-generate 01-store-performance`" |
| "Go." | "Starting both.<br/><br/>Running: `/wire:data_model-generate 01-store-performance`, `/wire:seed_data-generate 01-store-performance`" |
| *(later)* | "Both reports are in. **Data model:** drafted, all checks pass, but one decision is parked. Wire's library has a ready-made retail model that matches this engagement: stores, products, sales, inventory. Use it as it stands, adapt it or ignore it? **Sample data:** five files, about 9,000 rows, shaped so every chart shows something (weekend peaks, one region trailing the others). Every reference between files checks out. Approve the sample data now, changes or park?<br/><br/>Ran: `/wire:data_model-generate 01-store-performance`, `/wire:data_model-validate 01-store-performance`, `/wire:seed_data-generate 01-store-performance`, `/wire:seed_data-validate 01-store-performance`" |
| "Adapt the library model. Inventory is out of scope. Approve the sample data." | "Data model adapted from the library model with inventory removed: six warehouse tables, two facts and four dimensions, every column traced to a chart in the catalogue. Sample data approved. Approve the data model now, changes or park?" |
| "Approve. Build it." | "Approved. Building the transformation models on the sample data now. This needs no warehouse: the sample data is loaded into a local dbt project." |

The library proposal deserves a word, because it is a pattern you will meet again. Wire keeps a library of data models for the industries Rittman Analytics works in most often, and when it finds a plausible match for the engagement in hand it proposes the model as a starting point together with its reasoning. It never adopts one on its own, however, and whichever answer you give, together with your reason, goes on the record, so that a colleague reading the data model later can see where it came from and why inventory is not in it.

## Stage 4: The Build

With the data model and the sample data approved, the build proper can start, and from here the pattern of each exchange is the same: Wire reports what it built and what the checks found, and asks for your decision.

| You say | Wire replies |
|---|---|
| *(later)* | "Models built on sample data: three staging models, six warehouse models, 21 tests, all passing. Every model follows the naming convention and has its documentation. Approve the models now, changes or park?<br/><br/>Ran: `/wire:data_model-review 01-store-performance`, `/wire:seed_data-review 01-store-performance`, `/wire:dbt-generate 01-store-performance`, `/wire:dbt-validate 01-store-performance`" |
| "Approve." | "Approved. Writing the semantic layer next: the definitions Looker uses for each measure and dimension.<br/><br/>Ran: `/wire:dbt-review 01-store-performance`. Running: `/wire:semantic_layer-generate 01-store-performance`" |
| *(later)* | "Semantic layer ready: six views, two explores (store sales, footfall). Like-for-like sales is defined as agreed at kickoff: stores trading for at least 13 months, refits excluded for the refit month. All checks pass. Approve now, changes or park?<br/><br/>Ran: `/wire:semantic_layer-generate 01-store-performance`, `/wire:semantic_layer-validate 01-store-performance`" |
| "Approve." | "Approved. Building the dashboards from the chart catalogue. I only build the charts the catalogue lists; I do not invent tiles.<br/><br/>Ran: `/wire:semantic_layer-review 01-store-performance`. Running: `/wire:dashboards-generate 01-store-performance`" |
| *(later)* | "Dashboards built: twelve tiles across two pages, matching the approved prototype tile for tile. Cross-check against the prototype: pass. No chart types I could not map, no fields I could not find. Approve now, changes or park?<br/><br/>Ran: `/wire:dashboards-generate 01-store-performance`, `/wire:dashboards-validate 01-store-performance`" |
| "Park it. The ops director wants to click through it first. Set her up on the sample data." | "Parked, waiting on the retail operations director. The dashboards are deployed to the development Looker instance on the sample data. Nothing downstream can start until this is approved, so I will stop here.<br/><br/>Ran: `/wire:dashboards-review 01-store-performance` (parked)" |

By the end of the third day, then, the client can open Looker and use the dashboards. Every number in them is sample data, but every chart, filter and definition is the one she approved, which is the whole point of the exercise: what she is testing is the design, and the design is exactly what will go live.

:::note
The sample data is disposable. It exists to prove the design and to give the build something to run against, and it is replaced wholesale in the next stage. Resist the temptation to tune it to look like the real business; a flat distribution proves nothing, but a suspiciously accurate one invites the client to read meaning into it.
:::

## Stage 5: Switching to Real Data

Two weeks later client IT confirms that the BigQuery project is ready and that the till, footfall and rota data is landing in it, and the operations director has approved the dashboards on the sample data with one change. This is the stage that makes dashboards-first worth doing, so it is worth seeing how little of it falls to you.

| You say | Wire replies |
|---|---|
| *(open a session)* | "One decision is waiting: the dashboards, parked for the retail operations director.<br/><br/>Ran: `/wire:start`" |
| "Approved, with one change: rename Conversion to Footfall conversion. Warehouse access is in, so lift the no-warehouse restriction. Switch to real data." | "Rename applied to the dashboard and the catalogue. Dashboards approved. Restriction lifted and recorded. Before I change any code, I compare the real tables with the sample data layout and write a switch-over plan.<br/><br/>Ran: `/wire:dashboards-review 01-store-performance`. Running: `/wire:data_refactor-generate 01-store-performance`" |
| *(later)* | "Switch-over plan written: four column renames in the till data, one date format change in footfall, no missing fields. Approve the plan now, changes or park?<br/><br/>Ran: `/wire:data_refactor-generate 01-store-performance`, `/wire:data_refactor-validate 01-store-performance`" |
| "Approve." | "Approved. Staging models repointed from the sample files to the real tables. Built against BigQuery: nine models, 21 tests, all passing on live data. Two pieces of work are now ready, so here is the run:<br/>1. The data quality tests: `/wire:data_quality-generate 01-store-performance`<br/>2. The acceptance test plan: `/wire:uat-generate 01-store-performance`<br/>Neither queries the warehouse until its checks run. The run stops at the data quality review. Go, adjust or cancel?<br/><br/>Ran: `/wire:data_refactor-review 01-store-performance`, `/wire:dbt-validate 01-store-performance`" |
| "Go." | "Starting both.<br/><br/>Running: `/wire:data_quality-generate 01-store-performance`, `/wire:uat-generate 01-store-performance`" |

Wire wrote the plan before it touched any code, which is deliberate: the plan is where you find out that the till system calls a column something different, and it is far cheaper to find that out in a document than in a failed build.

## Stage 6: Testing and Acceptance

| You say | Wire replies |
|---|---|
| *(later)* | "**Data quality:** freshness checks on all three sources (till data by 06:00 daily), a daily reconciliation between till transaction counts and the sales fact within one percent, and a check that every store in the sales data exists in the store list. All checks pass. Approve now, changes or park? **Acceptance tests:** a plan with two sessions, one with two regional managers and one with the operations director, each step traced to a requirement. Approve now, changes or park?<br/><br/>Ran: `/wire:data_quality-generate 01-store-performance`, `/wire:data_quality-validate 01-store-performance`, `/wire:uat-generate 01-store-performance`" |
| "Approve both. Sessions are Thursday and Friday." | "Both approved. Nothing else can start until the acceptance sessions are done.<br/><br/>Ran: `/wire:data_quality-review 01-store-performance`, `/wire:uat-review 01-store-performance`" |

The two sessions raise one finding, which is that like-for-like sales should exclude stores closed for more than three days in the period, and you bring it back to Wire.

| You say | Wire replies |
|---|---|
| "One finding from acceptance: like-for-like excludes stores closed for more than three days. Fix it, then prepare for go-live." | "Finding recorded. The like-for-like definition is changed in the semantic layer and the model documentation, and the change is recorded against the decision made at kickoff. Rebuilt and retested: all passing. Acceptance is recorded as approved with the finding fixed. Writing the deployment runbook: the steps to move from the development Looker instance to production, in order, with a rollback step for each.<br/><br/>Ran: `/wire:semantic_layer-generate 01-store-performance` (revision), `/wire:dbt-validate 01-store-performance`, `/wire:uat-review 01-store-performance`. Running: `/wire:deployment-generate 01-store-performance`" |

## Stage 7: Go-Live

| You say | Wire replies |
|---|---|
| *(later)* | "Runbook written and checked. Approve now, changes or park?<br/><br/>Ran: `/wire:deployment-generate 01-store-performance`, `/wire:deployment-validate 01-store-performance`" |
| "Approve. Go live Monday. And prepare a 60-minute training session for the regional managers." | "Approved. The runbook is ready for Monday. Training material is optional for this kind of release; you have asked for it, so I am drafting a 60-minute session for regional managers: reading each dashboard, using the filters, what like-for-like means, when data refreshes, how to raise a problem.<br/><br/>Ran: `/wire:deployment-review 01-store-performance`. Running: `/wire:training-generate 01-store-performance`" |

On Monday you follow the runbook, and the dashboards are live on real data.

## What You Should Now Have

Everything below is a file in the repository, on the release branch, and alongside it all is the record: every step and when it ran, every approval with a name and every decision you made together with your reason.

| Produced | Detail |
|---|---|
| Requirements | 14 requirements, traced to the statement of work, two clarifications resolved at kickoff |
| Workshop pack | For the kickoff |
| Conceptual model | Seven business concepts and their relationships |
| Dashboard prototype | One file that opens in a browser, approved after two rounds |
| Chart catalogue and data requirements | Twelve charts; two facts and four dimensions |
| Data model | Six warehouse tables, adapted from the library retail model |
| Sample data | Five files, about 9,000 rows |
| dbt project | Three staging and six warehouse models, 21 tests, first on sample data then on BigQuery |
| Semantic layer | Six views, two explores |
| Looker dashboards | Twelve tiles across two pages, matching the approved prototype |
| Switch-over plan | Sample data to real data, written before any code changed |
| Data quality tests | Freshness, reconciliation, referential checks |
| Acceptance test plan and results | Two sessions, one finding, fixed |
| Deployment runbook | Ordered steps with rollback |
| Training | 60-minute session for regional managers |

## What If Something Goes Wrong?

Two situations account for most of what can go wrong on a first release, and Wire handles both the same way. If a check fails, Wire tells you which check and why, and it does not offer you the approval, because an artifact that has not passed its checks is not ready to approve; you can ask for changes, and Wire will redraft. If you lose track of where the release is, open a new session and read the first line, which is always the list of decisions waiting on you, and if the answer is "none", ask Wire what is runnable and it will tell you what it would do next and why.

In the next chapter we will look at a transformation-only build, where the work splits into more pieces than it did here and where one of your requests is refused until the approval it depends on is in place.
