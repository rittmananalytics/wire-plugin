---
sidebar_position: 5
title: Sprints and the backlog
---

# Sprints and the backlog

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Every ticket that is in scope when a sprint starts is in that sprint, whatever state it is in. Tickets that arrive after the sprint has started wait in the backlog until they are approved.

## Starting and keeping the sprint

- When the delivery manager plans work, it puts the new tickets in the project's running sprint. If none is running, it starts the project's sprint that has been created but not started, or creates and starts a new one. The sprint length comes from the pod's [governance template](./governance).
- Every hour in UK working hours, the delivery manager's agent checks each of its projects without running a model:
  - **No sprint running, and open tickets:** it starts a sprint holding every open ticket, including tickets already being worked.
  - **A sprint running:** it adds any open ticket created before the sprint started that is missing from it, and any ticket approved since.

The project's board must have sprints turned on. Scrum boards and team-managed boards both work; a Kanban board has no sprints.

## Tickets added after the sprint starts

A ticket created after the sprint started waits in the backlog:

1. The delivery manager's agent posts **"Sprint addition requested:"** on the ticket once, mentioning the engagement lead.
2. An engineer assigned the ticket does not start it while it waits.
3. If the addition is minor and does not change scope, the engagement lead approves it into the sprint, giving the reason; the ticket's assignee is told to start. Under the strict template, or when the addition changes scope, a person decides.

## Delivery reviews

Twice each working day (10:00 and 15:00 UK time) the delivery manager reviews each project's planned tickets:

| Finding | What the delivery manager does |
|---|---|
| A ticket whose dependencies are done and has no assignee | Assigns it to the engineer with the right role and the fewest open tickets |
| A ticket in progress with no update for 24 hours | Asks its assignee on the ticket what is in the way |
| A pull request waiting for review for 48 hours | Reminds the reviewer |
| A ticket nobody in the pod can take, stuck for two days, or delivery at risk | Tells the engagement lead, with a recommendation |

A review with nothing to act on runs no agent.
