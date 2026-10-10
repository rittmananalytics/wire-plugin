---
sidebar_position: 4
title: "Working a Ticket"
---

# Working a Ticket

Six weeks after the Northwind Retail dashboards went live, the retail operations director raises a ticket. Her regional managers have started asking about returns: one region is refunding more than the others and nobody can see it. She wants a returns rate on the Sales Overview page, by store and by month, and she would like it before the next regional review, which is a fortnight away. The ticket is NWR-31 in the client's tracker, it is one paragraph long, and it is the whole of the brief.

This is how most of the work on a live platform arrives. Not a statement of work and a fresh repository, but a ticket against something that already exists, raised by someone who has been using the dashboards long enough to know what is missing. The release that built the platform is still there, with its requirements, its design documents, its business definitions and its record of every decision, and the repository now belongs to the client, whose analytics engineer reviews every pull request before it is merged. The question is how to make a change that is small, correct and consistent with everything already built, without redoing the work that built it.

In Chapter 2 Wire planned the release from the statement of work and the release-type definition. Here it plans from the ticket, inside the release that already exists. Everything else is the same: you say what you want, Wire says what it will do and why, does it, and stops where a decision is yours. The difference is what Wire plans from, and how much of the earlier work it can reuse rather than repeat.

The chapter is in two parts. Part One follows a single ticket against a release that is already live. Part Two follows a whole release that is built ticket by ticket from the start: how to set it up from the tickets in your tracker, how Wire shows it slice by slice, and how each ticket's work reaches the release record when its pull request merges.

## Part One: A Ticket on a Live Release

### Before You Begin

You will need the Northwind repository checked out, with the Store Performance release in it from Chapter 2, and the ticket text. You will also need to know who accepts the change: at Northwind the analytics engineer approves the code through the pull request, and the retail operations director owns the definition of a return, because a return is a business fact about how her stores trade and not a technical one.

At a high level, the ticket runs through five stages:

1. Open the release and find what already bears on the ticket.
2. Agree a plan, one step at a time, before anything is built.
3. Build the change, and deal with a test that fails.
4. Raise the pull request and let the client's review stand as acceptance.
5. Close the ticket, and bring the release's documents back into line with the code.

Let's take each in turn.

### Stage 1: Opening the Release

Open Claude Code in the Northwind repository and say what you want to work on. Wire's first job is not to plan but to read: it goes back through the release and tells you what it found that bears on this ticket, so that the plan it proposes in the next stage starts from what Northwind already agreed rather than from a blank page.

| You say | Wire replies |
|---|---|
| "Ticket NWR-31 on the Store Performance release. Add a returns rate to the Sales Overview page, by store and by month. The ticket text is in the tracker." | "Store Performance release opened. Two pieces of work have been done on it since go-live: ticket NWR-24 (the footfall conversion rename, merged) and ticket NWR-27 (a fix to the like-for-like exclusion for refitted stores, merged). Reading the release for anything that bears on returns. Three things. The till export already carries refund transactions: they are loaded but excluded from the sales fact by a decision made in the build, recorded on 14 March with the reason 'refunds out of scope for release one'. The business definitions register has no entry for a return, and the requirements do not mention one. The Sales Overview page has four headline tiles and the design allows six. Ticket NWR-31 opened on the release. Anything to add to the ticket text before I plan?<br/><br/>Ran: `/wire:work 01-store-performance NWR-31` (iteration NWR-31 opened)" |
| "The director has said exchanges shouldn't count as returns. Otherwise no." | "Noted against the ticket. One question the plan depends on: is a return a refund transaction, or a refund line? The till export has both, and the store league table counts transactions. I will propose transactions, matching the rest of the page, and flag it for the director to confirm." |

Notice that Wire did not ask you what a return is. It found the refund transactions in the till data, found the decision that excluded them and the reason, found that the definition had never been agreed, and proposed the one reading of the ticket that is consistent with what the page already shows. It also told you what has changed on the release since you last looked, which matters when more than one person works on it.

:::note
A ticket is opened on the release, not as a release of its own. Everything Wire found in that first reply came from the release's record: the requirements, the design, the definitions and the decisions log. Had the ticket been given a release of its own, none of that would have been in front of it, and the decision that excluded refunds in March would have been rediscovered the hard way, in a failing reconciliation.
:::

### Stage 2: The Plan

Wire proposes a plan before it touches anything, and waits for you to say go, adjust or cancel. The plan names each step in the words of the method rather than in Wire's own terms: what will be agreed, designed, built, checked and published, and in what order. Where a step is a piece of work Wire will do, it gives the command in full. Where a step belongs to a person, it says whose, and that step is where the run stops.

| You say | Wire replies |
|---|---|
| *(nothing)* | "Plan for ticket NWR-31: six steps to the pull request, then one decision that is the director's. Step 3 queries the warehouse.<br/><br/>1. **Agree the definition.** Add 'return' to the business definitions register: a refund transaction against a sale, exchanges excluded, counted in the month of the refund. Proposed, for the operations director to confirm.<br/>`/wire:business-rules-generate 01-store-performance --domain sales`<br/><br/>2. **Change the sales fact.** Two counts on the sales fact table, returned transactions and sold transactions, per store per day, citing the new definition. Nothing else in the table changes.<br/>`/wire:dbt-warehouse-generate 01-store-performance`<br/><br/>3. **Build and test.** Build the changed table and everything that reads from it, and run the tests.<br/>`/wire:dbt-validate 01-store-performance`<br/><br/>4. **Add the measure.** Returns rate in the store sales definitions Looker uses, as returned over sold.<br/>`/wire:semantic_layer-generate 01-store-performance`<br/><br/>5. **Add the tile.** One tile on the Sales Overview page, returns rate by month with the store and region filters, matching the style of the four tiles beside it.<br/>`/wire:dashboards-generate 01-store-performance`<br/><br/>6. **Publish.** A pull request on the client's template with the test results attached, for the analytics engineer to review.<br/>`/wire:utils-commit 01-store-performance work NWR-31`, `/wire:utils-pr-create 01-store-performance`<br/><br/>7. **Confirm the definition.** The operations director's decision. The run stops here; the ticket stays open until it lands.<br/><br/>Steps 4 and 5 run in parallel once step 3 passes.<br/>Not planned: `/wire:requirements-generate 01-store-performance`, `/wire:conceptual_model-generate 01-store-performance`, `/wire:data_model-generate 01-store-performance`. The ticket does not add a concept or change a table's grain, so those documents are not redrafted; the two lines in them that this change affects are patched at the end, and you see the patches first.<br/><br/>go / adjust / cancel?" |
| "Explain step 1. The director just wants a number." | "The number depends on the definition. Whether an exchange is a return changes the rate by about a fifth at the two stores with the highest exchange volume, on last quarter's till data. If the definition is written down and cited by the table, the measure and the tile, there is one thing for the director to confirm and one place to change it if she changes her mind. If it is not, there are three implementations to keep in step, and the March decision to exclude refunds shows how a reason gets lost when it lives only in code. It adds about two minutes to the plan." |
| "Approve." | "Approved under your name. Starting step 1.<br/><br/>Running: `/wire:business-rules-generate 01-store-performance --domain sales`" |

Three things are worth noticing. The plan is small, because the release already holds the requirements and the design and Wire could see that the ticket does not disturb either. It says what it leaves out and why, which is how you know Wire has considered the whole method and not just the part in front of it. And when you asked for the reasoning behind a step, you got the consequence of skipping it in Northwind's own numbers rather than a general principle.

The command under each step is the one that performs it, written in full: the `/wire:` prefix, the release folder, and any flags, exactly as you would type it. The steps are the method; the commands are how each one is invoked. Wire puts them in the plan for the same reason it ends each reply with the commands that ran, and answers "go" with a `Running:` line naming the first: so that you can see how the work maps to Wire, copy a line to re-run a step yourself, and answer when someone asks which command does what. A step that belongs to a person is a numbered step too, marked as a decision, so you see before the run starts where it will stop. Chapter 7 shows the same kind of plan typed by hand.

### Stage 3: The Build, and a Test That Fails

From here the pattern is the one you saw in Chapter 2: Wire says what it is about to do, does it, checks it and reports. The difference on a ticket is that each step is scoped to the change and no wider, and Wire tells you the scope each time.

| You say | Wire replies |
|---|---|
| *(later)* | "Step 1 done. 'Return' added to the definitions register as proposed, status: awaiting the operations director. Step 2: changing the sales fact table only. Two new counts, named to the convention, each with a description and a citation of the new definition. No other table is touched. Written. Convention checks pass.<br/><br/>Ran: `/wire:business-rules-generate 01-store-performance`, `/wire:dbt-warehouse-generate 01-store-performance`" |
| *(later)* | "Step 3: built the sales fact and the three things that read from it, and ran 23 tests. One failed. The sold-transactions count is empty for 212 store-days, all of them days when a store was closed for refit and the till recorded no sales at all. The test says the count must never be empty. Three ways to resolve this. Count zero for those days, which is what the like-for-like rule already does for closed stores; recommended. Leave those days out of the table, which changes the league table's day counts from ticket NWR-27. Or stop and ask the director. Which?<br/><br/>Ran: `/wire:dbt-validate 01-store-performance` (1 of 23 failed)" |
| "Zero." | "Recorded as a decision under your name, with the reason: consistent with the like-for-like treatment of closed stores. Plan step 2 amended to say so. Rebuilt and retested: 23 of 23 pass. Step 4: returns rate added to the store sales definitions, citing the return definition. Step 5: one tile added to Sales Overview, between Average Basket and Like-for-Like, region and store filters applied, same colour and number format as its neighbours. Cross-check against the page design: pass. Open the development dashboard to see it.<br/><br/>Ran: `/wire:dbt-warehouse-generate 01-store-performance` (amended), `/wire:dbt-validate 01-store-performance`, `/wire:semantic_layer-generate 01-store-performance`, `/wire:dashboards-generate 01-store-performance`, `/wire:dashboards-validate 01-store-performance`" |

The failing test is the useful part of that exchange. Wire did not fix it quietly, because a fix is a decision about what the data means, and it did not stop dead either. It told you what failed, on which rows and why, proposed the treatment consistent with a rule the release already had, told you what the alternative would disturb, and recorded your answer with its reason next to the decisions from the original build. The plan now shows the amendment, so that anyone reading it later sees what was approved and what changed during the work.

:::note
Wire built and tested only the changed table and the things that depend on it, not the whole project. On a platform with a few dozen models that is the difference between a minute and twenty, and it is safe because the tests on the untouched models passed when they were last built and nothing upstream of them has changed. If something had, Wire would have widened the build and said so.
:::

### Stage 4: The Pull Request, and Whose Approval Counts

On a client-owned repository the client's pull request review is the acceptance step for code, and Wire treats it as one rather than asking you to hold a separate review of your own. What it adds is the evidence the reviewer needs: the tests that ran, the checks that passed, the definitions cited and the decisions made along the way.

| You say | Wire replies |
|---|---|
| *(later)* | "Step 6: pull request 91 raised on Northwind's template. Body: the ticket, the six steps, 23 of 23 tests passing, convention checks passing, the return definition cited by the table, the measure and the tile, and the closed-store decision with its reason. Assigned to the analytics engineer for review. Two things are now waiting on other people: the pull request review, and the operations director's confirmation of the return definition. The second is not something the analytics engineer can give, because it is a business definition and not a code review, so I will keep it open until she confirms it or you tell me she has.<br/><br/>Ran: `/wire:utils-commit 01-store-performance work NWR-31`, `/wire:utils-pr-create 01-store-performance`" |

That last sentence is the point of the stage. A pull request approval accepts the code. It does not settle what a return is, and Wire will not let one stand in for the other, because the director owns that definition and a rate built on a definition she has not seen is exactly the situation the register exists to prevent.

### Stage 5: Closing the Ticket

Before Wire calls the ticket done, it does two things in order. It looks at the release's documents and tells you which of them the change has made out of date, proposing the smallest patch to each and showing it to you before writing anything. Then it brings the release's status and log up to date, so that the record shows the ticket and what ran for it.

| You say | Wire replies |
|---|---|
| *(nothing)* | "Steps 1 to 6 done. Steps waiting on others: the review, and the director's confirmation. Checking the release's documents against the change. Two are out of date. The data model design lists the sales fact's columns and does not have the two new counts: a two-line patch. The requirements say nothing about returns, and there is now a tile that the client asked for and no requirement behind it: a one-line addition, traced to ticket NWR-31, marked as raised after go-live. The business concepts and the page design need no change. Apply both patches?" |
| "Yes." | "Applied and shown in the pull request as two further files. Status updated: ticket NWR-31 is on the release's iterations list as 'awaiting client review', with its branch and pull request. The record shows what ran for it: the six steps, the failing test, the decision and the two patches, in order. The ticket is not closed. Waiting on the analytics engineer and the operations director.<br/><br/>Ran: `/wire:status-sync 01-store-performance`" |

The patches matter more than their size suggests. Without them the data model document would describe a table that no longer exists as described, and the next person to open the release, six months from now, would trust the document over the code and be wrong. Wire keeps the documents true by patching them at the end of each ticket, with your agreement, rather than by regenerating them, which would be slower and would risk changing things the ticket never touched.

### Two Days Later

The analytics engineer approves and merges the pull request the next afternoon. The operations director is harder to pin down, but she was on Tuesday's regional call, which was recorded.

| You say | Wire replies |
|---|---|
| "Ticket NWR-31. Where are we?" | "Pull request 91 was approved by the analytics engineer and merged yesterday at 16:20. That accepts the code. The return definition is still awaiting the operations director. Tuesday's regional call was recorded, and at 14 minutes in she says, of the returns tile on the development dashboard, 'that's the right number, as long as swaps aren't in it.' Exchanges are excluded, as she asked. Treat that as her confirmation and record it against the recording, or wait for her in writing?<br/><br/>Ran: `/wire:work 01-store-performance NWR-31` (resumed iteration NWR-31)" |
| "Record it." | "Return definition confirmed by the operations director, source: regional call, Tuesday, 14:10. All six steps done, both approvals in from the people who own them, tests passing, documents patched, record complete. Ticket NWR-31 closed. The tile is live in production with the Wednesday morning refresh.<br/><br/>Ran: `/wire:status-sync 01-store-performance`. Iteration NWR-31 closed" |

The ticket took two sessions and about ten messages from you, and most of the messages were decisions. Every one of them, and every step Wire took, is in the release's record beside the decisions from the original build, so that the release still tells one story from the statement of work to the latest ticket.

### A Request That Is Not a Ticket

Not every request that arrives as a ticket is one. The following week the director asks, in ticket NWR-34, for customer complaints to appear alongside sales, and the complaints live in a helpdesk system that Northwind has never connected.

| You say | Wire replies |
|---|---|
| "Ticket NWR-34. Add complaints per store from the helpdesk system, on the Store League Table." | "This is not a change I would make as a ticket on the Store Performance release, and I want to say why before proposing anything. It adds a source system that has never been assessed, it adds a business concept (a complaint) that the design does not have, and it needs a pipeline that does not exist. Any of those on its own is a design change; together they are a small release. Two ways forward. Plan it as a new release alongside this one, which starts with a short look at the helpdesk data and an agreed definition of a complaint, and would take about a week; recommended. Or add it to this release as a formal design phase, which keeps it in one place but reopens the design documents that ticket NWR-31 left settled. Which?<br/><br/>Not run: anything. Iteration NWR-34 escalated; the next step is /wire:new or a formal phase" |

Wire refused to treat the request as a small change, said exactly which of its properties made it larger than it looked, and offered the two sensible shapes for it with a recommendation. That boundary is one you will lean on. A ticket that quietly grows into a redesign is how a fortnight becomes a quarter, and it is far cheaper to notice at the planning step than in the third week.

### What You Should Now Have

| Produced | Detail |
|---|---|
| Business definitions register | One new entry, 'return', confirmed by the operations director against a recording |
| Sales fact table | Two new counts, cited to the definition, closed-store days counted as zero by a recorded decision |
| Tests | 23 passing, one of them the test that failed and drove the decision |
| Store sales definitions | Returns rate measure |
| Sales Overview page | One new tile, matching its neighbours |
| Pull request 91 | Merged, with the evidence attached, on the client's template |
| Data model and requirements | Two small patches, shown before they were written |
| The release record | Ticket NWR-31 on the iterations list, with its branch, pull request, steps, decision and approvals |

### What If Something Goes Wrong?

The commonest problem on a ticket is discovering, part way through, that it is bigger than it looked: the test that fails turns out to expose a design fault rather than a data quirk, or the change needs a second table after all. Wire's behaviour then is the one you saw at the failing test: it stops, says what it found, offers a plan amendment or, if the change has crossed the line described above, a formal release, and waits. The other common problem is an approval that never quite arrives, and there the record is your friend: the ticket stays open, the status says exactly who it is waiting on, and nothing is called done that is not.

## Part Two: Building a Whole Release from Tickets

NWR-31 arrived after go-live, against a release that Wire had built artifact by artifact. Northwind's next release is different. The discovery work for Customer Insight agreed the design in May: a customer table that joins till customers to loyalty members, a lifetime value for each customer, a semantic model over both and one dashboard for the marketing team. Before any code was written the lead consultant cut that design into tickets in Northwind's tracker, one ticket per deliverable, and the team will build it ticket by ticket, each ticket on its own branch, each merged back into the release branch by pull request.

If Wire tracked only the whole release, none of that would show in its record. Finishing the loyalty staging ticket would change nothing in the release status, the list of what can start next would be wrong, and two consultants working two tickets at once would fight over the same status file in every merge. So the first thing to do with a release like this is to tell Wire that it is built from tickets, and let it read them.

At a high level, a release built from tickets runs through six stages:

1. Set the release up from its tickets, once, and check what Wire proposes.
2. Ask what can start, and see the release slice by slice.
3. Work each ticket, scoped to the part of the release it covers.
4. Let the pull request merge, and bring the release record up to date.
5. Keep the ticket map in line with the tracker as it changes.
6. Hold the line on work that is not in any ticket.

### Before You Begin

You will need a release for Customer Insight, created in the usual way, with its conceptual model approved: here it was carried over from the discovery design. You will need the tracker connected, Linear or Jira, because Wire reads the tickets itself rather than having them typed in; a list typed from memory is exactly the hand-kept list this replaces. And the setup is done by the lead consultant, because it is a scoping decision: which tickets belong to this release, which part of it each covers and what is left out.

The tickets should follow the design, not the statement of work. A statement-of-work deliverable is usually a broad promise ("customer analytics"); a ticket is a piece of the agreed design ("build the loyalty member table"). Wire sets a release up from the second kind.

### Stage 1: Setting Up the Release from Its Tickets

Say which release and which tracker. Wire reads the tracker project and proposes, for each ticket, three things: the kind of work (requirements, design, build, test, review or plain work), the part of the release it covers, which Wire calls its slice, and the Wire steps it covers. A slice can be one table, one source system, one layer, one deliverable, one batch or the whole release. Nothing is written until you confirm.

| You say | Wire replies |
|---|---|
| "Set up the Customer Insight release from its tickets in the tracker. The project is Customer Insight 1.0." | "Customer Insight has no ticket map yet. I will read the tracker project and propose one; nothing is written until you confirm.<br/><br/>Running: `/wire:tickets-import 02-customer-insight --tracker linear --project "Customer Insight 1.0"`" |
| *(nothing)* | "Customer Insight 1.0: 9 tickets, 34 points. This release has no design model in Modality, so I have proposed each slice from the ticket's title and text. Please check the Slice column.<br/><br/>NWR-40 Customer insight requirements: requirements, whole release, steps: requirements.<br/>NWR-41 Stage the loyalty platform: build, slice source_loyalty, steps: dbt, data_quality.<br/>NWR-42 Design the customer tables: design, slices customer, loyalty_member and customer_lifetime_value, steps: data_model.<br/>NWR-43 Build customer: build, slice customer, steps: dbt, data_quality.<br/>NWR-44 Build loyalty member: build, slice loyalty_member, steps: dbt, data_quality.<br/>NWR-45 Build customer lifetime value: build, slice customer_lifetime_value, steps: dbt, data_quality.<br/>NWR-46 Customer insight semantic model: build, slice customer_insight_model, steps: semantic_layer.<br/>NWR-47 Customer Insight dashboard: build, slice customer_insight_dashboard, steps: dashboards.<br/>NWR-48 Weekly CRM export for marketing: see question 1.<br/><br/>The build tickets for the three customer tables leave out the design step, because NWR-42 designs all three.<br/><br/>Two need your answer:<br/>1. NWR-48 is a file export to the marketing team's CRM. No Wire command builds it. Track it as plain work, outside Wire's steps?<br/>2. NWR-45 is blocked by NWR-43 in the tracker. In the design, lifetime value is also built from the loyalty member table, so it waits for NWR-44 as well. Add that link in the tracker?<br/><br/>Not in any release: tracker project Data Platform Housekeeping (4 tickets). Start a new release, add to an existing one, or ignore?<br/><br/>confirm / adjust / cancel?" |
| "Confirm. Plain work for NWR-48, add the link, and ignore Housekeeping for now, it's run-the-platform work." | "Ticket map written: 9 tickets, 8 slices, 1 plain.<br/>- `tickets.yaml` in the release folder<br/>- 9 ticket records in `iterations/`, each marked as planned<br/>- The release status now has one row per slice, and the release is marked as built from tickets<br/>- Decision recorded: Data Platform Housekeeping is not part of a Wire release, with your reason<br/>- Tracker: NWR-45 now blocked by NWR-44 as well<br/><br/>Ran: `/wire:tickets-import 02-customer-insight --tracker linear --project "Customer Insight 1.0"`" |

Three things in that exchange are worth a second look. The steps for each ticket were not guessed one by one; they follow from what the ticket builds. A source system needs staging and tests, a table needs a design, a build and tests, a semantic model needs the semantic layer and a dashboard needs the dashboard step, and where a design ticket already covers a table, the build ticket for that table leaves the design out. Wire asked where it could not tell: the CRM export, which no Wire command builds, and would have asked about a review ticket or a "Tier 1" ticket whose steps cannot be read from its slice. And it checked the order of work against the design rather than taking the tracker's links on trust, because a missing link is how a build starts before the table it reads from exists.

:::note
The ticket map is Wire's own record of the split. If your team has been keeping a spreadsheet or a link file by hand, mapping tickets to tables, it can be generated from the map or dropped.
:::

#### If the Design Is in Modality

Some discoveries produce the design in Modality, down to the tables and their columns, and the tickets are cut from that model. The setup is the same with two differences: each build ticket's slice is the Modality object it builds, taken from the model's own ticket links where it has them, and a table that the physical model already designs is recorded as the design rather than designed again.

| You say | Wire replies |
|---|---|
| "Set up Customer Insight from its tickets. The design is in Modality." | "This release reads its design from Modality, so each build ticket's slice is the Modality object it builds. The model links NWR-43, NWR-44 and NWR-45 to their tables, so those need no checking. NWR-46 has no link; I have matched it to the customer insight data product, please check. The physical model already designs all three tables, so the design step for them will record the model's design and list anything that does not match Wire's naming rules, rather than design them again. confirm / adjust / cancel?<br/><br/>Running: `/wire:tickets-import 02-customer-insight --tracker linear`" |

Wire never writes to the Modality model. A ticket that changes the model is done in Modality, and what it produces becomes a design Wire can read, so the build and its checks still run through Wire. Nothing in this part of the chapter needs Modality; the rest of it follows the release without one.

### Stage 2: What Can Start?

With the map in place, the release status is shown slice by slice: one row per slice, one column per step, each cell showing its state and the tickets that cover it. A step is complete for the release only when it is complete in every slice that has it.

| You say | Wire replies |
|---|---|
| "What's next on Customer Insight?" | "Customer Insight is built from tickets. 0 of 9 tickets closed.<br/><br/>Can start now:<br/>- NWR-40 Customer insight requirements<br/>- NWR-41 Stage the loyalty platform<br/>- NWR-42 Design the customer tables<br/><br/>Waiting:<br/>- NWR-43 Build customer: waits for NWR-42 (the customer table's design)<br/>- NWR-44 Build loyalty member: waits for NWR-42 and NWR-41 (it reads the loyalty staging)<br/>- NWR-45 Build customer lifetime value: waits for NWR-42, NWR-43 and NWR-44<br/>- NWR-46 Semantic model: waits for NWR-45<br/>- NWR-47 Dashboard: waits for NWR-46<br/><br/>NWR-48 is plain work and waits for nothing in Wire.<br/><br/>Ran: `/wire:status 02-customer-insight`" |

The order is worked out for each slice, not for the release as a whole. The customer build waits for the customer table's design and nothing else; it does not wait for the loyalty platform to be staged, because it does not read from it. The loyalty staging does not wait for any design at all, because the map gives a source no design step. That is what lets two or three consultants work the release at once without stepping on each other.

### Stage 3: Working a Ticket in the Release

Each ticket is worked exactly as NWR-31 was: Wire reads the release for what bears on it, proposes a plan with a command for each step, runs only what you approve and stops where a decision is someone else's. Here is the design ticket.

| You say | Wire replies |
|---|---|
| "Work NWR-42." | "Opening ticket NWR-42 on Customer Insight. It covers the design of three tables: customer, loyalty member and customer lifetime value. The conceptual model from discovery is approved and names all three. The ticket is in the ticket map, so it is planned work.<br/><br/>Plan for ticket NWR-42:<br/>1. **Design the three tables.** One section of the data model design per table, nothing else in the document touched.<br/>`/wire:data_model-generate 02-customer-insight --slice customer`, `--slice loyalty_member`, `--slice customer_lifetime_value`<br/>2. **Check the designs.**<br/>`/wire:data_model-validate 02-customer-insight --slice customer` (and the other two)<br/>3. **Approve the designs.** The lead consultant's decision; the run stops here.<br/>4. **Publish.** A pull request into the release branch.<br/>`/wire:utils-commit 02-customer-insight work NWR-42`, `/wire:utils-pr-create 02-customer-insight`<br/>5. **Code review.** Northwind's analytics engineer.<br/><br/>Branch cut from the release branch. Left out: requirements, which NWR-40 covers for the whole release.<br/><br/>go / adjust / cancel?" |

Two things are new. Every step carries `--slice`, which limits the command to that part of the release: one table's section of the design, one table's models and tests. A sliced command never regenerates the whole document, so it cannot rewrite a table another ticket designed. And while the ticket is open, Wire writes only to the ticket's own record and its own log, plus the files its commands produce. It does not touch the release's status or execution log on the ticket branch, which is why two tickets open at once no longer collide when they merge.

The build tickets follow the same shape: build the table from its approved design, build and test it, add its tests, publish. A build ticket that adds a new table is accepted without question, because the table is in the ticket map; the boundary check you saw with NWR-34 now asks whether the work is in the map, not whether it is small.

### Stage 4: When the Pull Request Merges

The release record catches up once, on the release branch, when the ticket's pull request has merged.

| You say | Wire replies |
|---|---|
| "PR 104 for NWR-42 is merged." | "Pull request 104 (NWR-42) merged into the release branch. Technical approval: done. Bringing the release record up to date from the ticket's record:<br/>- Execution log: 7 rows from the ticket's log, in the order they ran, each with the time it actually ran noted<br/>- Decisions: 1 from the ticket (lifetime value counted over 36 months), added to the release's decisions<br/>- Status: customer, loyalty_member and customer_lifetime_value now show the design step complete<br/>- Release: the design step is complete in 3 of 3 slices<br/><br/>Apply? (yes / pick / no)" |
| "Yes." | "Applied. NWR-43 can start now. NWR-44 waits for NWR-41 only.<br/><br/>Ran: `/wire:status-sync 02-customer-insight`" |

The roll-up only ever adds to the record. The ticket's log rows are appended at the bottom of the release log, stamped with the time of the roll-up, and the time each step actually ran is kept in the row's detail, so the log still reads in the order things reached the release. Running the roll-up twice adds nothing the second time.

:::note
A merged ticket whose business approval is still outstanding stays open, as NWR-31 did while it waited for the operations director. Its cells still show complete, because the code is built and tested; the ticket record says who it is waiting on.
:::

### Stage 5: When the Tracker Changes

Trackers change. Tickets are added, rewritten and cancelled, and the map has to follow.

| You say | Wire replies |
|---|---|
| "The tracker has changed. Update the ticket map." | "3 changes since the last import:<br/>- New: NWR-52 Add loyalty tier to customer. Build, slice customer, steps dbt and data_quality.<br/>- Changed: NWR-47 is now 'Customer Insight dashboard, desktop only'. Slice and steps unchanged.<br/>- Removed: NWR-48 cancelled in the tracker. Close its ticket record as cancelled.<br/><br/>apply all / choose / cancel?<br/><br/>Ran: `/wire:tickets-import 02-customer-insight --refresh`" |

Nothing changes until you say so, a cancelled ticket's record is closed rather than deleted, and a ticket that is already open keeps its approved plan; the change is shown to you the next time it is opened.

### Stage 6: Work That Is Not in Any Ticket

| You say | Wire replies |
|---|---|
| "Work NWR-44, and add the online shop's customer accounts while you're there." | "NWR-44 is in the ticket map. The online shop's customer accounts are not: they are a new source, and no ticket in this release covers them. A new source needs its own staging, tests and matching rules, so I will not add it under NWR-44. Two ways forward: a new ticket in the tracker, which I would then add to the map (recommended, because this release was scoped to the tills and the loyalty platform), or a new ticket in this release agreed with the lead consultant first, which widens the release. Shall I start NWR-44 without it?" |

The ticket map is the agreed scope of the release. Wire will build anything in it, including new tables and new sources, and will not quietly build anything outside it.

### What You Should Now Have

| Produced | Detail |
|---|---|
| Ticket map | Nine tickets, each with its kind, slices and Wire steps, written once you confirmed it |
| Ticket records | One per ticket, each holding its plan, what ran, its decisions and its pull request |
| Release status | One row per slice, worked out from the ticket records and never edited by hand |
| Tracker links | The missing link from NWR-45 to NWR-44, added with your agreement |
| Decisions | The housekeeping project left out, with your reason; the lifetime value window from NWR-42 |
| Release record | Each merged ticket's log rows and decisions added once, on the release branch, after you confirmed |


In the next chapter we leave code behind entirely and look at a discovery, where the sources are interview recordings and the most important gate belongs to the client's sponsor rather than to you.
