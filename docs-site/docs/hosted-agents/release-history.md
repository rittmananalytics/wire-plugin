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
| 2.2.2 | October 2026 | 4.4.3 |
| 2.2.1 | October 2026 | 4.4.3 |
| 2.2.0 | October 2026 | 4.4.3 |
| 2.1.0 | October 2026 | 4.4.3 |
| 2.0.0 | October 2026 | 4.4.3 |
| 1.1.0 | October 2026 | 4.4.3 |
| 1.0.1 | October 2026 | 4.4.2 |
| 1.0.0 | October 2026 | 4.4.2 |

Before 1.0.0, the hosted agents shipped inside Wire releases 4.3.0 to 4.4.2.

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
