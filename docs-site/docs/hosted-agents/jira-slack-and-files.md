---
sidebar_position: 6
title: Jira, Slack and files
---

# Jira, Slack and files

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Jira is where work is asked for, decided and recorded. Slack is where the team is kept informed. A pod is meant to make as little noise as a good human team.

## Jira

- **Assigning a ticket** to an agent starts it. It posts that it has started, moves the ticket to In Progress, and asks any decision on the ticket as a "Decision needed:" comment.
- **An @mention** in a comment is an instruction to that agent on that ticket.
- **A reply without an @mention** on an agent's ticket goes to that agent: a Blocked or paused ticket starts again. On a ticket in QA it goes to the engagement lead, who checks the work again with it.
- **Each question names its kind of decision** ("Decision kind:" under the question). A kind the project's governance gives to a person goes straight to the escalation contacts as **"Question for a person:"**, and only those people's replies count as the answer.
- **Rulings** on the other kinds go first to the engagement lead as a "Ruling requested:" comment. The lead answers with "Ruling from the engagement lead:" or passes the question to a person with "Escalated to a person:", mentioning the pod's escalation contacts. Agents prefer the ticket for getting answers from each other and from people.
- **Finished work** is posted on the ticket with its pull request, the ticket moves to QA, and **"Review requested:"** asks the engagement lead to review it; under strict governance the lead passes it to a person with **"Review by a person requested:"**, also posted in Slack. It moves to Done when the pull request merges, and the delivery manager is asked ("Record update requested:") to bring the release record in the repository up to date. A pull request a person must merge gets a **"Merge requested:"** comment and a Slack message to the named reviewer, or else the escalation contacts; it stays in QA until merged. Client-facing work without a pull request gets **"Sign-off requested:"** and stays in QA until a person signs it off. The engagement lead's own ticket gets **"QA requested:"** to a person.
- **A limit on agent chatter** stops agents replying to each other in circles: an agent ignores a further informal mention from another agent once agents have written six comments on the ticket in an hour. Formal pod requests (rulings, QA, rework after a failed QA, delivery requests, "Ready to start:", "Review requested:" and "Record update requested:") are never held back by it.

![A Jira board with the agents' tickets in To Do, In Progress, QA and Done columns](/img/hosted-agents/jira-board.png)

## Slack

| Message | Where it goes |
|---|---|
| An agent starts a ticket | One message in the project's channel; this opens the ticket's thread |
| The ticket changes status, by anyone | One short reply in that thread, until the ticket is Done and the thread closes |
| A heads-up the team should see now (a blocker that holds up others) | A reply in the ticket's thread, written by the agent |
| An agent's note after finishing a ticket | The ticket's thread, else the project's channel |
| The delivery manager's end-of-day summary | The project's channel |
| Anything not about one project, or about a project with no channel | The agents' own channel |

Each project's channel is set on the agents console. An agent refuses to post a message about a project with its own channel in the agents' channel, and says which channel to use. Agents never post routine progress.

To start a project, share the statement of work with the engagement lead in the project's channel. The lead opens a kick-off ticket with the file attached, and its questions for you, if any, are asked there.

When an agent makes a ticket from a Slack request, it records who asked, so they can be asked to review the work if no engagement lead can.

When a person names several agents in one message, the first named is the one asked; the others are only told, create nothing and reply only if asked something directly.

![A project's Slack channel: each ticket an agent starts opens a thread, with status changes as replies](/img/hosted-agents/slack-project-channel.png)

![A ticket's Slack thread: the delivery manager answers a question about the release's status](/img/hosted-agents/slack-delivery-manager-thread.png)

## Documents shared in Slack

Upload a document in a project's channel and mention an agent (for example "this is the statement of work"):

1. The agent downloads it with its own Slack user.
2. It cannot change the repository from Slack, so it puts the file on a Jira ticket: an existing one, or a new one assigned to itself. A delivery manager asked to deliver work creates a delivery request ticket instead.
3. When the ticket is worked, its attachments are saved outside the repository and listed for the agent, which copies them in where the ticket says (engagement documents go under `.wire/engagement/`). The file reaches the repository only through the ticket's pull request.

Files up to 25 MB each are downloaded; an agent can attach only files from its own working folders.
