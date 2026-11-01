---
sidebar_position: 2.8
title: Instructions, tasks and routines
---

# Instructions, tasks and routines

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

You can change how an agent works, in plain language, on the agents console. No code change or release is needed. There are three things you can set:

| What | Where on the console | Who can change it | Applies to |
|---|---|---|---|
| **Purpose** | The agent's page | Console admins | Every run of that agent, on every project |
| **Agent task** | The agent's page, Tasks | Console admins | The kinds of run you choose, on every project |
| **Project task** | The project's page, Tasks | The project's contacts and console admins | The kinds of run you choose, on that project only |

Every save is kept as a new version with who made it, when and why. You can restore an earlier version at any time; the restore is saved as a new version too.

## When to use which

| You want to... | Use |
|---|---|
| Say what an agent is for, or that its work does not come from Jira tickets | Its **purpose** |
| Set a habit for an agent on every client, such as how it lays out a summary | An **agent task** |
| Tell agents something about one client: what to report, what to leave out, the client's terms | A **project task** |
| Have an agent do something on a schedule with no ticket, such as a weekly summary in Slack | A task with a **schedule** (a routine) |
| Change something structured, such as the steward's channels, times or how its questions are grouped | The project's **Context steward** settings, not a task ([Context steward](./context-steward#settings)) |
| Change how an agent talks to one person | Nothing to set: tell the agent in Slack, and it remembers ([Memory](./memory#preferences)) |

Purposes and agent tasks apply to every client the agent works for, so they cannot name a client, project, repository or private name; the console refuses the save if they do. Put client detail in a project task.

## An agent's purpose

1. Open the agent's page on the console and find **Purpose**.
2. Write what the agent is for and how it works, in a few short paragraphs. For example, for a context steward: what it keeps up to date, from which sources, and that it asks before changing an agreed rule.
3. Tick **Its work does not come from Jira tickets** if that is true. The agent then never says it is idle or waiting for a ticket, and it may do the work its purpose describes when asked in Slack. It still opens a pull request for any change to a repository, never pushes to a default branch, and still makes a ticket for delivery work its purpose does not cover.
4. Give a reason for the change and save.

The purpose goes into every run the agent starts.

## Tasks

A task is a short set of instructions with a title. You choose which kinds of run read it:

| Kind of run | When it happens |
|---|---|
| Ticket work | The agent works a Jira ticket |
| Slack answers | The agent answers in Slack |
| Steward scan | The context steward reads calls, Slack and pull requests |
| Steward pull request | The context steward updates the engagement record |
| End-of-day summary | The delivery manager posts its daily summary |

To add one: open the project's page (or the agent's page), choose **Add task**, give it a title, write the instructions, tick the kinds of run, give a reason and save. To change one, edit the text and save: that is the next version. **Remove** stops it applying and keeps its versions.

Good task instructions are short and specific. For example:

> Report what concerns the client's data platform and its business rules.
> - One short sentence per finding, with no jargon.
> - From calls with only Rittman Analytics people, report only what is about this client.
> - Leave out scheduling, small talk and anything about other clients.

A run reads its agent's purpose, the agent's tasks for that kind of run, and the tasks of the project it is working on. It never reads another project's tasks.

## Routines

A task can also have a schedule. It then runs on its own, with no ticket, and its result is posted in a Slack channel.

1. In the task, tick **Also run on a schedule and post the result in Slack**.
2. Set the schedule as five cron fields (minute, hour, day, month, weekday), such as `0 9 * * 1` for 09:00 every Monday, and a time zone, such as Europe/London. Clock changes are handled.
3. Choose the channel. A project's routine can post only in that project's channel or its steward's channels; an agent's routine only in the channels of the projects its pods cover.
4. For a project task, choose which agent in the project's pod runs it.

A new routine first runs at its next scheduled time after you save it. If the agent leaves the pod or the channel stops belonging to the project, the routine stops running.

## Changing a project task from Slack

People can ask an agent in Slack to change a project's task, for example "keep your questions to one line". The agent:

1. drafts the new text and proposes it;
2. posts the exact text in the thread with an 8-character code and a link to the project's page.

Nothing changes until a contact of the project, its steward's confirmation owner or a console admin confirms it, in either of two ways:

- **In the thread:** reply `confirm <code>`, for example `confirm a1b2c3d4`. The console reads that reply in Slack itself and records who wrote it, so only a reply from someone who may confirm counts. The agent then replies with the new version, or says why it was not saved. If the agent has not spoken in the thread for a day, or another agent has spoken since, mention it: `@Julien confirm a1b2c3d4`.
- **On the console:** on the project's page, where waiting changes are listed. You can also reject a change there.

A confirmed change is saved as a new version marked as asked for in Slack, with who confirmed it. A proposal lapses after 7 days, and is refused if the task changed in the meantime.

An agent's purpose and agent tasks cannot be changed from Slack; ask a console admin.

## What instructions cannot do

Instructions are text the agent reads. They never:

- give an agent a tool, a permission or access it does not already have;
- switch off the writing rules, the check that keeps other clients' names out, client separation, approvals, standing decisions or any check the agents make in code.

Where they conflict with those, the rules win. Instructions also cannot hold secrets, or phrases that try to replace an agent's own instructions; the console refuses the save.

## Seeing why an agent ran

The agent's page lists its recent runs and why each started: a ticket assigned, a mention, a Slack message, the steward's scan or pull request, a summary, a routine, and others. Use it to check that a routine ran, or that an agent with no tickets is still working.
