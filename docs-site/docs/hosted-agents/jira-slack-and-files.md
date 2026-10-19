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

## How the delivery manager writes tickets

The delivery manager writes every ticket from a **ticket template**, chosen by the kind of work. A script fills the template and checks the result before the ticket is created. A ticket that fails the check is not created; the delivery manager fixes it and tries again. The check makes no model call, so the same ticket always gets the same result.

| Template | Used for |
|---|---|
| Wire step | One Wire step's generate and validate for the whole release (requirements, business rules, design or build) |
| Slice | One slice of a step, when the statement of work asks for the step in slices |
| Data quality | Tests and acceptance evidence against the statement of work's acceptance criteria |
| Investigation | A check or question with no artifact, such as confirming access or profiling data |
| Release pull request | The last ticket: one pull request into the default branch, which a person reviews and merges |
| Production | Work after the merge that changes production. It names the person who decides it. |
| Kick-off | The kick-off ticket the engagement lead opens with the statement of work |

Every ticket except the kick-off has these sections, in this order:

| Section | What it is for |
|---|---|
| Goal | What the ticket produces, and which deliverable or acceptance criterion in the statement of work it serves |
| Context | The statement of work and the sections that apply, the rulings and business rules, and the earlier tickets it builds on, with their files |
| Scope | What is in and what is out, including what the statement of work leaves out |
| Decisions needed from a person | Each open item a person must decide, with who, the kind of decision and what it holds up, or "None known". These are asked before work starts, not found halfway through |
| Acceptance criteria | Numbered statements that are true or false. Each says how to check it, the expected value and tolerance (or "pass"), and the file that holds the evidence |
| Tests | The named tests, and the reconciliation query with the source it is checked against |
| How to work it | The Wire commands that do the work |
| Constraints | A short fixed block pointing to the release's context file at a stated version |

The check refuses a ticket when a section is missing or empty, an acceptance criterion has no check, expected value or evidence, a placeholder is left in the text, or the title does not follow the template. It also refuses a release pull request ticket that is not blocked by every other ticket in the release, and a production ticket that names no person.

The engineer's plan, approved on the ticket, holds how the work is done. Tickets do not carry step-by-step instructions, and the definition of done is not repeated on each one.

When the project's Jira create screen has a field named **Acceptance Criteria**, the criteria are written there as well as in the description. When it has none, they are in the description only. Tickets carry no story points.

Each ticket also starts with three short lines (kind, Wire step and release folder), so Wire can link it to the release without guessing.

## Slack

| Message | Where it goes |
|---|---|
| An agent starts a ticket | One message in the project's channel; this opens the ticket's thread |
| The ticket changes status, by anyone | One short reply in that thread, until the ticket is Done and the thread closes |
| A heads-up the team should see now (a blocker that holds up others) | A reply in the ticket's thread, written by the agent |
| An agent's note after finishing a ticket | The ticket's thread, else the project's channel |
| The delivery manager's end-of-day summary | The project's channel |
| An agent asks you a question, or asks you to review, merge or sign off | The project's channel: one message from the agent, @mentioning everyone asked, one thread per question; reply in the thread. A project with no channel: the agents' own channel, the same way |
| A question has waited an hour | A reminder in that question's thread |
| The delivery manager proposes changes on a project it did not set up | The project's channel (or the agents' channel), one message from the delivery manager @mentioning the escalation contacts and any person in a lead role; reply `approve`, `always` or `reject` in its thread |
| Anything not about one project, or about a project with no channel | The agents' own channel |

Each project's channel is set on the agents console. An agent refuses to post a message about a project with its own channel in the agents' channel, and says which channel to use. Agents never post routine progress.

To start a project, share the statement of work with the engagement lead in the project's channel. The lead opens a kick-off ticket with the file attached, and its questions for you, if any, are asked there.

When an agent makes a ticket from a Slack request, it records who asked, so they can be asked to review the work if no engagement lead can.

When a person names several agents in one message, the first named is the one asked; the others are only told, create nothing and reply only if asked something directly.

![A project's Slack channel: each ticket an agent starts opens a thread, with status changes as replies](/img/hosted-agents/slack-project-channel.png)

![A ticket's Slack thread: the delivery manager answers a question about the release's status](/img/hosted-agents/slack-delivery-manager-thread.png)

### Questions in Slack

Jira stays the record of every question and answer. When an agent asks a person something on a ticket (a decision, an escalation, a review, a merge or a sign-off), the agent also posts it in the project's Slack channel, @mentioning everyone asked whose Slack account is registered on the console. It gives the ticket, the question and a link. A project with no Slack channel uses the agents' own channel the same way. Agents send no direct messages. Reply in that message's thread: the agent posts your reply on the ticket as "Reply from Pat Smith (via Slack)", with your name, and the work carries on as if you had replied in Jira.

- Replies are picked up within 5 minutes.
- Only replies from the people asked count; anything else in the thread is ignored. When several people are asked, a reply from any of them is posted as theirs.
- You can still reply in Jira. If you reply in both, the first reply is the answer.
- If a question has waited an hour, the reminder goes in the same thread, @mentioning whoever has not replied.
- People without a registered Slack account get the question on the ticket only.
- Each question or proposal has its own thread, and only replies in that thread count. Later messages in the channel are not read as answers.

## Documents shared in Slack

Upload a document in a project's channel and mention an agent (for example "this is the statement of work"):

1. The agent downloads it with its own Slack user.
2. It cannot change the repository from Slack, so it puts the file on a Jira ticket: an existing one, or a new one assigned to itself. A delivery manager asked to deliver work creates a delivery request ticket instead.
3. When the ticket is worked, its attachments are saved outside the repository and listed for the agent, which copies them in where the ticket says (engagement documents go under `.wire/engagement/`). The file reaches the repository only through the ticket's pull request.

Files up to 25 MB each are downloaded; an agent can attach only files from its own working folders.
