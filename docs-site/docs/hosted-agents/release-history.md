---
sidebar_position: 10
title: Release history
---

# Release history

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

The hosted agents have their own version numbers, separate from Wire's, and each release runs a pinned, published Wire release, as any client project does. A major version means the rollout needs more than building, applying and restarting; a minor version adds behaviour; a patch fixes. Releases are announced in the `#wire-framework` Slack channel.

| Version | Released | Runs on Wire |
|---|---|---|
| 2.9.0 | October 2026 | 4.4.3 |
| 2.8.2 | October 2026 | 4.4.3 |
| 2.8.1 | October 2026 | 4.4.3 |
| 2.8.0 | October 2026 | 4.4.3 |
| 2.7.2 | October 2026 | 4.4.3 |
| 2.7.1 | October 2026 | 4.4.3 |
| 2.7.0 | October 2026 | 4.4.3 |
| 2.6.0 | October 2026 | 4.4.3 |
| 2.5.0 | October 2026 | 4.4.3 |
| 2.4.2 | October 2026 | 4.4.3 |
| 2.4.1 | October 2026 | 4.4.3 |
| 2.4.0 | October 2026 | 4.4.3 |
| 2.3.3 | October 2026 | 4.4.3 |
| 2.3.2 | October 2026 | 4.4.3 |
| 2.3.1 | October 2026 | 4.4.3 |
| 2.3.0 | October 2026 | 4.4.3 |
| 2.2.4 | October 2026 | 4.4.3 |
| 2.2.3 | October 2026 | 4.4.3 |
| 2.2.2 | October 2026 | 4.4.3 |
| 2.2.1 | October 2026 | 4.4.3 |
| 2.2.0 | October 2026 | 4.4.3 |
| 2.1.0 | October 2026 | 4.4.3 |
| 2.0.0 | October 2026 | 4.4.3 |
| 1.1.0 | October 2026 | 4.4.3 |
| 1.0.1 | October 2026 | 4.4.2 |
| 1.0.0 | October 2026 | 4.4.2 |

Before 1.0.0, the hosted agents shipped inside Wire releases 4.3.0 to 4.4.2.

## 2.9.0: the context steward asks the confirmation owner

- **Questions in Slack.** In mode On, findings that need the owner are posted in the feedback channel, one thread per part of the record, and the owner confirms or rejects each by number in the thread. Findings a reply does not mention stay open. See [Questions to the confirmation owner](context-steward#questions-to-the-confirmation-owner).

## 2.8.2: the context steward reads Slack threads

- **Thread replies.** Each scan reads every new message in the source channel, thread replies included, with no limit on how many. A new reply in a thread started up to 30 days ago is read with the thread's first message, and its link opens the reply in its thread.

## 2.8.1: photos on the Pods page

- **People's photos** now show on the Pods page, and an agent shows the photo on its console profile before its issue tracker photo.

## 2.8.0: the context steward's scan, record only

- **Hourly scan.** For each project it stewards, the context steward reads the project's new Slack messages and the recorded calls that match its call rules, compares them with the engagement record, and records each finding with a link to its source. Nothing is posted yet. See [Context steward](context-steward).

## 2.7.2: project page links

- **Each project key on the Projects page links to the project's page.** A project with no tracker had no link to it.

## 2.7.1: the Pods page Projects field

- **Projects, not Jira keys.** The Pods page asks for the projects a pod covers by the keys the Projects page lists, and shows the registered keys to add with a click.

## 2.7.0: the context steward persona and settings

- **A new role, the context steward.** A hosted persona and pod role, under "Engagement" in the persona picker: an agent only, one per pod, under the engagement lead on the org chart.
- **Its settings on each project's page**, changed by console admins: mode, which calls count, the channels it reads and asks in, the confirmation owner, the pull request reviewer and its schedule. See [Context steward](context-steward#settings).

## 2.6.0: one persona list, and projects with no tracker

- **One list of personas and roles** for the agents and the console. An agent added to a pod starts with its default persona as its role, when that persona is a pod role.
- **Projects with no tracker.** A project can be registered with tracker None: no Jira project, for work that needs no tickets. Agents and the console make no Jira calls for it. See [Setting up a pod](setting-up-a-pod#1-register-the-project).

## 2.5.0: Slack follow-ups and connectors in every run

- **Connectors in every run.** Each run waits for the agent's claude.ai connectors to connect before it starts, so it can use them.
- **Reply in a thread without @mentioning the agent.** A reply in a Slack thread an agent answered in within the last day reaches that agent.

## 2.4.2: the Marketing persona asks before changing the website

- Before any change to the company website, and again before publishing it, the Marketing persona asks a person and acts only on a clear yes.

## 2.4.1: agent image fix

- The agent image builds again after 2.4.0.

## 2.4.0: charts in Slack and plugins per operations persona

- **Charts and files in Slack.** Agents can show a chart or file in their Slack reply, in the same thread.
- **Plugins per operations persona.** Each operations persona loads its own plugin in place of the Wire plugin.

## 2.3.3: agents write in their personality

- The personality set on the console now shapes how an agent writes and works, ahead of the house style. A short list of fixed writing rules still applies to every agent.

## 2.3.2: a Slack mention is not lost after connecting

- An agent mentioned in Slack just after it was connected no longer drops the message.

## 2.3.1: Agents page tabs

- The Agents page has three tabs: Delivery agents, Operations agents and Humans.

## 2.3.0: operations personas

- **Agents for work outside data delivery.** Marketing, Accountant and HR assistant personas work without a repository and take tasks from their board's Slack channel.
- **A project can have no repository**, for an operations agent's board.

## 2.2.4: no direct messages from agents

- **Proposals go to the project's Slack channel.** The delivery manager's proposals are posted in the project's channel from its own Slack user, @mentioning the project's contacts. Reply in the thread as before.
- **No project channel: the agents' own channel.** Questions, proposals and reminders on a project with no Slack channel go to the agents' own channel the same way. Agents no longer send direct messages.

## 2.2.3: questions in the project channel, agents shown by name

- **Questions go to the project's Slack channel.** A question for a person (a decision, an escalation, a review, a merge or a sign-off) is posted in the project's channel, @mentioning everyone asked, one thread per question. Replies in the thread are posted on the ticket, and reminders go in the same thread. A project with no channel keeps the direct message. See [Questions in Slack](jira-slack-and-files#questions-in-slack).
- **The console shows agents by name.** The Agents page and each agent's page show the agent's name as people know it (for example Bob Smith), not its internal name.

## 2.2.2: direct messages from the Wire Agents app

- Questions, their reminders and the delivery manager's proposals now come from the Wire Agents app, shown with the agent's name and photo, so replies in their threads can be read for every agent without each agent reconnecting to Slack. Everything else the agents post still comes from each agent's own Slack account.

## 2.2.1: questions in Slack

- **Questions reach people in Slack.** When an agent asks a person something on a ticket, the person also gets a Slack direct message, and a reply in its thread is posted on the ticket as their answer. See [Questions in Slack](jira-slack-and-files#questions-in-slack).
- **Agent machines remove old software images** after each update, so they no longer run out of disk space.

## 2.2.0: propose first, one lead per role, and deleting memories

- **An agent delivery manager proposes first** on a project it did not set up, and acts only when the project's people agree, all at once or one group of changes at a time. See [An agent delivery manager proposes first](pods-and-roles#an-agent-delivery-manager-proposes-first) and [Ways to run a project](ways-to-run-a-project).
- **One engagement lead and one delivery manager per pod**, agent or person, with a handover when the role changes hands.
- **Deleting memories** on the console, with restore and redact. See [Deleting a memory](memory#deleting-a-memory).

## 2.1.0: the Admin page

- **Admin page.** Spawning agents, registering people and managing console admins are on one Admin page, for console admins only; the console checks this on the server. Admins add and remove other admins from the organisation's domain; the last admin cannot be removed.
- **People's photos** come from the company directory, else the issue tracker.
- **The Agents page** lists agents and people 5 at a time, and no longer has a spawn button.

## 2.0.0: people in pods

A major release: its rollout needed setup outside Google Cloud (an issue tracker service account and a chat bot for the delivery assistant, and directory access for import).

- **People in pods** with any role, working alongside agents; a person in a lead role replaces the agent, with a handover. See [People in a pod](pods-and-roles#people-in-a-pod).
- **The delivery assistant** for pods whose delivery manager is a person.
- **People's activity stats**, taken from the issue tracker and the code host.

## 1.1.0: Wire 4.4.3, the review gate and record fixes

Most of this release comes from the first Wire project review of a release delivered end to end by the hosted agents.

- **The review gate.** A ticket whose Wire step depends on another step's review is not assigned or started until that review is approved. The engagement lead is told once. Before, the data model on that release was built on requirements nobody had reviewed.
- **Reviews say who approved them.** When an approved pull request stands as an artifact's review, the release record names the person or agent who approved it and the pull request, and records who reviewed it, when, and the link. If nobody approved the pull request, the review is still owed.
- **One time zone.** Every row the agents write to the execution log is in UTC.
- **Rework is on the record.** After a failed QA check or a reviewer's finding, the engineer logs the finding, the fix and a fresh validation on the ticket.
- **Nothing lost at roll-up.** The delivery manager reads the merged result, so measured time and cost reach the release record, and tickets with no Wire step (an access check, for example) are closed in the record when QA passes.
- **Rows are labelled as agent work,** with the run's session, never as typed by a person. After each roll-up, the rows it added are checked and any rule break is reported to the engagement lead.
- **Wire 4.4.3.** The agents use Wire's own scripts to write roll-up and review rows.

## 1.0.1: Wire Studio in the console

- **Wire Studio button.** The agents console's Projects page has a Wire Studio button for each project: a read-only view of the project's releases, read from its repository, behind the console sign-in.
- Version numbers and a release script for the hosted agents.

## 1.0.0: own repository

- **Own repository and pinned Wire.** The hosted agents moved out of the Wire repository into their own private repository and run the published Wire 4.4.2 plugin.
- **Ticket templates.** The delivery manager writes every ticket from a template: goal, context, scope, decisions needed from a person, numbered acceptance criteria (each with a check, an expected value and where the evidence goes), tests and how to work it. A ticket missing a section is refused. Before planning, the delivery manager checks for an existing set of tickets for the release.
- **[Memory](memory), phase 1.** A shared memory per project and one per agent, with every write checked, and full run transcripts kept for a limited time.
- **Pods and projects changed only on the console.** Agents read them but cannot change them, so an agent cannot give itself a role.
- **Fixes from the first runs:** a ticket blocked on a person asks that person; only the agent holding a ticket moves it to QA; kick-off tickets are not sprint work and the plan's tickets join the running sprint; standing decisions reach the release record.
