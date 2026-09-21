---
sidebar_position: 3
title: "Data Modelling and Transformation"
---

# Data Modelling and Transformation

At Vantage Financial Reporting the data is already in the warehouse. Stripe payments, the Salesforce pipeline and a PostgreSQL product database all land in Snowflake every few hours through Fivetran, and have done for a year. What Vantage does not have is anything between those raw tables and the people who use them: the analysts write SQL straight against the landed data, each with their own idea of what a customer is, and in the monthly review the finance team and the sales team quote two different figures for monthly recurring revenue and spend ten minutes arguing about which is right. Both are right, as it turns out, by their own definitions; nobody has ever written either definition down.

This is the commonest shape of engagement we see, and the ingestion is rarely the problem. The problem is the missing transformation layer, the tested and documented models that turn raw tables into figures people agree on, and beneath that the missing agreement about what the figures mean. Wouldn't it be better to settle what the numbers mean once, in writing and with the owner's name against each definition, before anyone builds a model on top of a definition that half the company disputes?

That is the shape of a "dbt development" release, and in this chapter we will use the optional first step that Chapter 2 skipped, "business rules discovery", to do exactly that. A dbt development release produces the dbt project only: staging, integration and warehouse models, tests, documentation and the scheduled jobs that run them, with no pipelines and no dashboards in scope. As such it suits any client whose ingestion is solved and whose analysts are blocked on clean models, and at Vantage it is precisely what the statement of work asks for.

We will follow the release across five working days. We will first see the business rules register settle the MRR argument, then the requirements and the data model, and then we will watch Wire split the build into layers that run at the same time where they can and in sequence where they must. Along the way one of your requests will be refused, which is worth seeing, because the refusal is the method working rather than failing. Let's start with what you need before you begin.

## Before You Begin

You will need the signed statement of work and schema exports for the three raw Snowflake schemas in the `docs` folder of a new repository, together with the finance team's definitions spreadsheet, since that is one of the places the competing definitions live. You will also need to know who approves what: at Vantage the analytics engineering lead approves the technical work, and the finance lead owns the revenue definitions.

At a high level, the release runs through six stages:

1. Agree the business rules for revenue.
2. Draft and approve the requirements.
3. Design and approve the data model.
4. Build the models, in layers.
5. Check, build and review the models against Snowflake.
6. Add the data quality tests and the deployment runbook.

Let's now take a look at each of these in turn.

## Stage 1: Agreeing the Definitions First

You start the engagement as you did in Chapter 2, but this time you ask for the business rules step by name and say why.

| You say | Wire replies |
|---|---|
| "New engagement for Vantage Financial Reporting, dbt project on Snowflake. Statement of work in the docs folder, schema exports for the three raw schemas in the same place. Up to four pieces of work at a time. Stop at every decision. Start with the business rules for revenue, because finance and sales disagree on MRR." | "This reads as a dbt development release: ingestion is in place and the scope is the transformation layer only. Client: Vantage Financial Reporting. Release: dbt Foundation. Limits: four pieces of work at a time, stop at every decision. Which email domain do the client's people use?" |
| "vantagefr.com. Confirm." | "Engagement set up. Starting the business rules step for the revenue domain. I read the raw schemas, the statement of work and the finance team's definitions spreadsheet in the docs folder.<br/><br/>Ran: `/wire:new`. Running: `/wire:business-rules-generate 01-dbt-foundation --domain revenue`" |
| *(later)* | "Business rules register for revenue: nine rules. Six are agreed, with one definition each. Two are disputed. Monthly recurring revenue has three competing definitions: the Stripe subscription amount, Salesforce annual value divided by twelve, and the finance spreadsheet's figure, which excludes discounts. Customer status has two. For each disputed rule I have written a query that shows how far the definitions differ on last month's data, and run it: the MRR definitions differ by 4.2 percent. One rule, the treatment of refunds in MRR, has no definition anywhere. It is recorded as unknown rather than left out. Approve the register now, changes or park for the finance team?<br/><br/>Ran: `/wire:business-rules-generate 01-dbt-foundation`, `/wire:business-rules-validate 01-dbt-foundation`" |
| "Park it for the finance lead. She's on the call tomorrow. Draft the requirements meanwhile." | "Parked, waiting on the finance lead. Drafting the requirements.<br/><br/>Ran: `/wire:business-rules-review 01-dbt-foundation` (parked). Running: `/wire:requirements-generate 01-dbt-foundation`" |

The register is where the argument gets settled once. Every rule in it has its source, every disputed rule has a query that shows the size of the disagreement in real numbers rather than in opinions, and the rule that nobody has ever defined is on the record as unknown, because a rule nobody has decided is far more useful written down than silently missing. Furthermore, once the register is approved, the models that implement each rule cite it, so that the definition and the code that carries it can never quietly drift apart.

## Stage 2: The Requirements, and a Gate That Waits

| You say | Wire replies |
|---|---|
| *(later)* | "Requirements drafted: 11 requirements, all checks pass. One clarification: whether the MRR fact needs movement between months, or only the month-end position. Approve now, changes or park?<br/><br/>Ran: `/wire:requirements-generate 01-dbt-foundation`, `/wire:requirements-validate 01-dbt-foundation`" |
| "Approve. The finance lead can answer the MRR question tomorrow too." | "Approved. The clarification is recorded as an open item for tomorrow. The next step, the data model, is released by the requirements approval, but its business rules gate is still open: the register is parked. That gate is advisory, so I can proceed with a reason, or wait. Which?<br/><br/>Ran: `/wire:requirements-review 01-dbt-foundation`. Not run: `/wire:data_model-generate 01-dbt-foundation`, gate: business rules (advisory)" |
| "Wait." | "Waiting. Nothing else can start, so I will stop here. Two decisions are open for tomorrow." |

Notice the distinction Wire draws in that second reply. The requirements approval is a hard condition for the data model, and it is met. The business rules gate is an "advisory" one, which means Wire will warn you and let you proceed with a recorded reason rather than refusing outright, since a hard gate on a step that teams routinely skip tends to produce a skipped gate rather than a followed one. You chose to wait, and that choice is on the record too.

## Stage 3: The Data Model, and a Request That Is Refused

The finance lead rules on the next day's call: MRR is the Stripe subscription amount less discounts, refunds are excluded and the fact is a month-end snapshot per customer.

| You say | Wire replies |
|---|---|
| *(open a session)* | "Two decisions are waiting: the business rules register, parked for the finance lead, and the MRR grain question.<br/><br/>Ran: `/wire:start`" |
| "Finance lead has ruled. MRR is Stripe subscription amount less discounts. Refunds excluded. Month-end snapshot per customer, no intra-month movement. Approve the register with those answers." | "Register updated: MRR resolved to the Stripe definition less discounts, approved under the finance lead's name; refunds rule resolved from unknown to agreed; customer status resolved to the Salesforce definition. Register approved. The MRR grain is recorded as a decision. Drafting the data model now.<br/><br/>Ran: `/wire:business-rules-review 01-dbt-foundation`. Running: `/wire:data_model-generate 01-dbt-foundation`" |
| *(later)* | "Data model drafted, all checks pass. Six staging models (Stripe charges, customers and refunds; Salesforce accounts and opportunities; product users), one integration model that resolves a customer across the three systems by matching email addresses with a fallback key for the unmatched, and four warehouse models (customer, opportunity, charge, monthly MRR snapshot). The MRR snapshot uses customer and month as its key, as ruled. Each disputed rule from the register is cited on the column that implements it. Approve now, changes or park?<br/><br/>Ran: `/wire:data_model-generate 01-dbt-foundation`, `/wire:data_model-validate 01-dbt-foundation`" |
| "Start the dbt models." | "Not yet. The dbt models wait on the data model being approved, and it is not. It is drafted and checked. Approve now, changes or park?<br/><br/>Not run: `/wire:dbt-generate 01-dbt-foundation`, gate: data_model review" |
| "Changes: the analytics lead wants a net MRR movement column on the snapshot, for churn analysis." | "Change recorded. Redrafting the data model with a net MRR movement column on the snapshot, calculated from the previous month's row.<br/><br/>Ran: `/wire:data_model-review 01-dbt-foundation` (changes requested). Running: `/wire:data_model-generate 01-dbt-foundation`" |
| *(later)* | "Redrafted, all checks pass. The new column is traced to the churn requirement. Approve now, changes or park?<br/><br/>Ran: `/wire:data_model-generate 01-dbt-foundation`, `/wire:data_model-validate 01-dbt-foundation`" |
| "Approve." | "Approved under the analytics lead's name, with today's date. The dbt models are now released: eleven models across three layers, each layer depending on the one before, so here is the run:<br/>1. The staging layer, six models in two lanes at the same time: `/wire:dbt-staging-generate 01-dbt-foundation`<br/>2. The integration model: `/wire:dbt-integration-generate 01-dbt-foundation`<br/>3. The warehouse layer: `/wire:dbt-warehouse-generate 01-dbt-foundation`<br/>4. Build and test in Snowflake: `/wire:dbt-validate 01-dbt-foundation` (queries the warehouse)<br/>At most two lanes at once, within your limit of four. The run stops at the dbt review. Go, adjust or cancel?<br/><br/>Ran: `/wire:data_model-review 01-dbt-foundation`" |
| "Go." | "Starting the staging layer.<br/><br/>Running: `/wire:dbt-staging-generate 01-dbt-foundation` (two lanes)" |

The refusal is the point of that exchange. Wire will not start work whose approval is missing, and it tells you exactly which approval, so that you are never left guessing at what it is waiting for. You could have approved and started in one message; you chose to ask for changes instead, which is a perfectly normal answer at a gate rather than an exception, and the record now shows the first draft, your change and the redraft in order.

:::note
Asking for changes is not a failure of the process. The three answers at every gate, approve, changes or park, are equal citizens, and a review that goes straight to approval every time is more often a sign that nobody is reading the drafts than a sign that they are perfect.
:::

## Stage 4: The Build, in Layers

A dbt project is built in layers because each layer reads from the one below it: the staging models tidy the raw tables one source at a time, the integration model joins across sources, and the warehouse models present the result. It follows, therefore, that the six staging models can be written at the same time, in as many pieces as your limit allows, but that the integration model cannot start until all of them are finished, and the warehouse models cannot start until it is. Wire works this out from the model dependencies rather than from a rule of thumb, and it tells you the plan before it starts.

| You say | Wire replies |
|---|---|
| *(later)* | "Staging layer done: six models, documented, each with its tests. Starting the integration model.<br/><br/>Ran: `/wire:dbt-staging-generate 01-dbt-foundation`, `/wire:dbt-staging-validate 01-dbt-foundation`. Running: `/wire:dbt-integration-generate 01-dbt-foundation`" |
| *(later)* | "Integration model done. Customer resolution matches 91 percent of Stripe customers to a Salesforce account by email; the rest carry a fallback key and are flagged. Starting the warehouse layer.<br/><br/>Ran: `/wire:dbt-integration-generate 01-dbt-foundation`, `/wire:dbt-integration-validate 01-dbt-foundation`. Running: `/wire:dbt-warehouse-generate 01-dbt-foundation`" |
| *(later)* | "Warehouse layer done. Eleven models in total, 38 tests written, every model and column documented. Two decisions I made are on the record for you: the MRR snapshot's key is built from customer and month, and soft-deleted rows from Stripe are excluded in staging. Now building the models in Snowflake and running the checks, because for dbt the checks run the tests for real against the warehouse.<br/><br/>Ran: `/wire:dbt-warehouse-generate 01-dbt-foundation`, `/wire:dbt-warehouse-validate 01-dbt-foundation`. Running: `/wire:dbt-validate 01-dbt-foundation`" |

Wire made two modelling decisions of its own during the build and told you what they were. Anything it decides goes on the record next to the decisions you made, so that nothing it chose is hidden in the code for a later developer to stumble over.

## Stage 5: Checking, Building and Reviewing Against Snowflake

For most of what Wire produces, the checks are a matter of reading files: does the document have every section, does every column trace to a requirement. For a dbt project the checks include building the models and running the tests against the real warehouse, which is why they are reported as a separate step and why they take a little longer.

| You say | Wire replies |
|---|---|
| *(later)* | "Build complete. 11 models built, 38 of 38 tests pass, no warnings. Naming, structure, key and documentation checks all pass. From the recording of Tuesday's call: the analytics lead asked whether refunds appear as negative charges. They do, in the charge fact, and they are excluded from MRR as ruled. Approve the models now, changes or park?<br/><br/>Ran: `/wire:dbt-validate 01-dbt-foundation`" |
| "Approve." | "Approved. This kind of release can also produce a semantic layer. Your statement of work leaves it out. Skip it?<br/><br/>Ran: `/wire:dbt-review 01-dbt-foundation`" |
| "Skip. Out of scope." | "Recorded as your decision. The data quality tests are released. Starting them.<br/><br/>Running: `/wire:data_quality-generate 01-dbt-foundation`" |

That reference to Tuesday's call is Wire reading the recording of the review meeting and bringing the relevant question to the review, so that you are reminded of it at the moment it matters rather than three weeks later.

:::note
The dbt checks need a working Snowflake connection and they use warehouse time, so on a client account with tight credit limits it is worth telling Wire at the start what it may spend, as you did with the "nothing that queries a warehouse" limit in Chapter 2.
:::

## Stage 6: Data Quality and Deployment

| You say | Wire replies |
|---|---|
| *(later)* | "Data quality tests written and checked. Freshness: Stripe within six hours, Salesforce within 24, product database within six. A daily row count reconciliation between staged Stripe charges and the raw table, within one percent. Any failure alerts the client's data channel. All pass. Approve now, changes or park?<br/><br/>Ran: `/wire:data_quality-generate 01-dbt-foundation`, `/wire:data_quality-validate 01-dbt-foundation`" |
| "Approve." | "Approved. Writing the deployment runbook.<br/><br/>Ran: `/wire:data_quality-review 01-dbt-foundation`. Running: `/wire:deployment-generate 01-dbt-foundation`" |
| *(later)* | "Runbook written and checked. Two dbt Cloud jobs: a daily production run at 04:00 UTC that builds then tests, and a job that runs on every pull request and builds only what changed. Failure alerts go to the client's data channel. Approve now, changes or park?<br/><br/>Ran: `/wire:deployment-generate 01-dbt-foundation`, `/wire:deployment-validate 01-dbt-foundation`" |
| "Approve, and hand over to the analytics lead." | "Approved. The release is complete: every step done, every approval named. Summary written for the handover.<br/><br/>Ran: `/wire:deployment-review 01-dbt-foundation`, `/wire:utils-session-summary 01-dbt-foundation`" |

## What You Should Now Have

Five days, and around 20 messages from you, most of them approvals. Everything below is in the repository, together with the record of every step, approval and decision, including the two decisions Wire made itself.

| Produced | Detail |
|---|---|
| Business rules register | Revenue domain: nine rules, all resolved, each with its source and approver |
| Requirements | 11 requirements, one clarification resolved |
| Data model | 11 models across three layers, one change round, every column traced |
| dbt project | Six staging, one integration and four warehouse models; 38 tests; documentation for every model and column |
| Data quality tests | Freshness on three sources, daily reconciliation, alerting |
| Deployment runbook | Two dbt Cloud jobs, daily production and pull request |

## What If Something Goes Wrong?

The likeliest problem on a build like this is a failing test when the models are first run against the warehouse, and Wire's behaviour then is the same as at any other check: it tells you which test failed and on which rows, it does not offer you the approval, and you can ask it to fix the model, ask for changes to the design if the test has exposed a design fault, or fix the model yourself and ask Wire to run the checks again (Chapter 7 shows that last path in detail). The other common surprise is the one you saw in Stage 3, where a request is refused because an approval is missing, and the remedy is simply to give the approval, or the changes, that Wire has asked for.

In the next chapter the platform is live and the work arrives as a ticket: a small change to the Northwind dashboards from Chapter 2, planned from the ticket rather than from a statement of work, inside the release that built them.
