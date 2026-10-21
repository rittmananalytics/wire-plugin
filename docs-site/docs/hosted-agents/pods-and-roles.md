---
sidebar_position: 2
title: Pods and roles
---

# Pods and roles

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

A pod is a team of hosted agents for one or more engagements. An engagement is identified by its project key, as the console's Projects page lists it: the Jira project key, or, for a project with no issue tracker, the key it was registered with. Each member of a pod has one role in it; an agent can belong to several pods, with a different role in each. A pod also names its **escalation contacts**: the people who take the decisions agents may not.

![Pod structure: the escalation contacts at the top, the engagement lead below them, and the delivery manager, analytics engineers and data engineers reporting to the lead; the engineers take day-to-day work from the delivery manager](/img/hosted-agents/diagram-structure.png)

Everyone reports to the engagement lead. The engineers take their day-to-day work from the delivery manager.

## The roles

| Role | Responsible for | Never does |
|---|---|---|
| **Engagement lead** | Acting for the customer. Runs the kick-off: reads the statement of work, asks a person every open question once (including whether any required Wire step may be skipped) and records the answers as standing decisions. Refuses requests to skip a required step unless a person has allowed it. Takes the rulings the project's governance allows and passes the rest to a person. Reviews finished work when asked ("Review requested:"), against the statement of work, the requirements and the business rules: approves it or sends it back for rework; under strict governance asks a person to review instead. Says whether the client will see the work. Approves additions to a running sprint and merges into release branches where governance allows. Asks the delivery manager to deliver agreed work. | Create, plan or assign delivery tickets, or set up releases; check its own work (a person does) |
| **Delivery manager** | Turning agreed work into a plan: sets up the release with Wire, creates the tickets, links them to the release with `/wire:tickets-import`, puts them in the sprint and, every hour, assigns those that can start by role and free capacity. Reviews delivery twice a day, chases stalled tickets, and tells the engagement lead when delivery is at risk. Approves the standard release set-up. Posts an end-of-day summary. | Engineering work |
| **Analytics engineer** | Data models, dbt, the semantic layer, dashboards, data quality and testing, through `/wire:work` | Approve its own work |
| **Data engineer** | Ingestion, pipelines and orchestration, through `/wire:work` | Approve its own work |
| **Context steward** | Keeping the engagement record up to date from the project's calls and Slack channel, and asking a person before changing an agreed rule or requirement. An agent only, one per pod. See [Context steward](context-steward). | Decide, rule, approve pull requests or do delivery work |

An agent's default persona on its profile pre-fills its role when it is added to a pod; the role is what counts. A role changes what an agent is told about its duties; it never widens what governance lets it decide. The same lists of roles are used by Wire's [personas](../advanced/personas), so a person and an agent in the same role see the same views.

## People in a pod

A pod can hold people as well as agents, in any role. People are registered on the console by email and linked to the accounts they already have (work, chat and issue tracker); nothing is created for them. They can be imported from the company directory, an issue tracker project or a chat channel.

- **Agents treat people as teammates.** The delivery manager assigns tickets to people by role and free capacity; engineers ask a person who is engagement lead for reviews and decisions, with a chat note; agents mention people on tickets. People do their own work and reply in their own time. Agents never do a person's work and never tell a person to start.
- **One engagement lead and one delivery manager per pod**, agent or person. Giving either role to another member removes the member who held it from that pod, after you confirm. Their open tickets move to the new holder, with a comment on each, and decisions waiting on them are put to the new holder.
- **Governance follows the role.** Decisions the project's template gives the engagement lead or delivery manager go to the person who holds that role.
- **A delivery assistant helps a person delivery manager.** When a person is the delivery manager, a scheduled assistant (not an agent) does the routine work: it proposes who should take each ready ticket for the person to approve (or assigns directly, if the team allows), tells agents when they can start, keeps the sprint up to date, updates the release record after merges with Wire's own scripts, and drafts a weekly summary. It is on by default and can be turned off per pod.
- **Activity.** People get the same activity stats as agents (tickets started, closed and blocked, pull requests), taken from the issue tracker and the code host. The console's Agents page lists them under Humans, with their photos, pods and roles.

## An agent delivery manager proposes first

An agent delivery manager does not change a project it did not set up. Each hour it works out what it would do (sprint changes, role labels, assignments, start notes and requests to add late tickets to a sprint) and, instead of doing it, posts one message listing the changes in the project's Slack channel, @mentioning the project's escalation contacts and any person in a lead role. It sends a new proposal only when the list changes, and at most every 4 hours when the list has only got shorter.

The project's people agree on the console's project page, where each group of changes has its own switch, or by replying to the message: `approve` (this time), `approve assign` (one group, this time), `always assign` or `always all` (from now on), or `reject`. Console admins can also set it.

A project the delivery manager set up itself, from a delivery request, needs no agreement. On any project, it always acts on the tickets it created itself for a delivery request.

## Asking a pod for work

- **Assign a Jira ticket** to an engineer. It starts on the ticket within a minute.
- **@mention an agent** in a Jira comment. The comment is its instruction, on that ticket.
- **Share a statement of work with the engagement lead** in the project's Slack channel. It opens a kick-off ticket, asks you its questions once, then asks the delivery manager to deliver.
- **Ask the delivery manager to deliver something**, in the project's Slack channel or on a ticket. It plans the work as tickets and starts the team.

When a person names several agents in one Slack message, the first agent named is the one being asked; the others are only being told, and stay out of it.
