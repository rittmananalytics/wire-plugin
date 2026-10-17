---
sidebar_position: 5
title: Sprints and the backlog
---

# Sprints and the backlog

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Every ticket that is in scope when a sprint starts is in that sprint, whatever state it is in. Tickets that arrive after the sprint has started wait in the backlog until they are approved.

## Planning the tickets

When the engagement lead asks for a release to be delivered, the delivery manager:

1. **Writes the release context file.** A short file in the release folder holds the release branch, the statement of work and the sections in scope, where the standing decisions and rulings are, the development-only and no-new-grants rules, and the pull request route. It has a version number, which goes up whenever the file changes. Each ticket cites the version it was written against, so QA can see what applied.
2. **Checks for tickets already written for the release.** If any exist, open or done, it asks the engagement lead before creating another set. One release has one set of tickets.
3. **Plans one ticket per Wire step**, from the [ticket templates](./jira-slack-and-files#how-the-delivery-manager-writes-tickets). Expected values come from the statement of work, the business rules register and earlier slices. Every open item that the business rules or design documents give to a person is listed on the ticket it holds up, and again on the release pull request ticket.
4. **Creates the tickets**, each checked against its template, and links each to the tickets it waits for.

## Starting and keeping the sprint

- When the delivery manager plans work, it puts the new tickets in the project's running sprint. If none is running, it starts the project's sprint that has been created but not started, or creates and starts a new one. The sprint length comes from the pod's [governance template](./governance).
- Every hour, every day, the delivery manager's agent checks each of its projects without running a model:
  - **No sprint running, and open tickets:** it starts a sprint holding every open ticket, including tickets already being worked.
  - **A sprint running:** it adds any open ticket created before the sprint started that is missing from it, and any ticket approved since.
  - **A sprint running with every ticket in it done:** it completes the sprint, and starts the next with the open tickets, so new work is not held back as an addition to a finished sprint.

The project's board must have sprints turned on. Scrum boards and team-managed boards both work; a Kanban board has no sprints.

## Tickets added after the sprint starts

Kick-off and delivery request tickets are never sprint work: they don't start a sprint or count in one. The tickets the delivery manager creates for her delivery plan join the running sprint straight away, because the plan is hers to decide.

Any other ticket created after the sprint started waits in the backlog:

1. The delivery manager's agent posts **"Sprint addition requested:"** on the ticket once, mentioning whoever the project's governance names: the engagement lead (light) or the escalation contacts (strict). Under strict, a person approves by moving the ticket into the sprint on the board.
2. An engineer assigned the ticket does not start it while it waits.
3. If the addition is minor and does not change scope, the engagement lead approves it into the sprint, giving the reason; the ticket's assignee is told to start. Under the strict template, or when the addition changes scope, a person decides.

## Assigning work every hour

In the same hourly check, the delivery manager goes through every open ticket in each of its projects, however the ticket was created, the way a person in the role would:

1. **Gives each ticket a role.** A ticket with no role label gets one from the engineer it is assigned to, or from its summary and description (dbt models, the semantic layer and dashboards are analytics engineering; ingestion, pipelines and orchestration are data engineering). When the rules cannot tell, the delivery manager reads the ticket and decides: analytics engineer, data engineer, or not engineering work (a review with the customer, a decision). It is asked once per ticket.
2. **Tells assigned engineers when to start.** A ticket that is assigned to an engineer, still in To Do, has nothing left blocking it and has not been started gets a **"Ready to start:"** comment mentioning the engineer, which starts it. So does a Blocked or paused ticket once a person has replied on it, and a ticket blocked on earlier tickets once those are all done. If the engineer does not start within a day, it is told again.
3. **Assigns unassigned tickets that can start.** A ticket with no open blockers, not waiting in the backlog, goes to the engineer with its role who has the most free capacity: the number of tickets it can work at once, less the tickets it is working now. No engineer is given more than it has room for; a ticket that has to wait stays unassigned until someone has room.

Tickets assigned to people, to the engagement lead or to the delivery manager are left alone. Tickets that are still blocked stay as they are until what they wait for is done.

## Delivery reviews

Twice each working day (10:00 and 15:00 UK time) the delivery manager reviews each project's planned tickets:

| Finding | What the delivery manager does |
|---|---|
| A ticket that can start and has no assignee | Leaves it to the hourly check, which assigns it when an engineer with the role has room |
| A ticket in progress with no update for 24 hours | Asks its assignee on the ticket what is in the way |
| A pull request waiting for review for 48 hours | Reminds the reviewer |
| A ticket nobody in the pod can take, stuck for two days, or delivery at risk | Tells the engagement lead, with a recommendation |

A review with nothing to act on runs no agent.
