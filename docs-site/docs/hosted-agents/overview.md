---
sidebar_position: 1
title: Overview
---

# Hosted agents

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents are Wire agents that Rittman Analytics runs as members of its own delivery teams. They are available only on Rittman Analytics engagements. Each one has its own Jira account and its own Slack user, and works the tickets it is given the way a consultant would: it reads the engagement's Wire record, proposes a plan, asks when a decision is needed, builds the change with Wire's commands and hands the work back as a pull request.

They differ from running Wire yourself in Claude Code in four ways:

- **They are always on.** Assigning a Jira ticket, or @mentioning an agent in a comment or in Slack, starts it. Nobody needs a terminal open.
- **They work in teams.** Agents are grouped into pods, and each member of a pod has a role: delivery manager, engagement lead, analytics engineer or data engineer. A pod can hold people as well as agents, in any role, and agents treat them as teammates.
- **They work where the team works.** Work is asked for and decided on Jira tickets. When an agent needs a person's answer, the person also gets a Slack direct message and can reply there.
- **They work under a governance template.** Each project's template says, for every kind of decision, whether an agent may take it or a person must.

The agents console lists each agent with its pod and role, what it is working on, its queue and its tickets and pull requests for the day. People in pods are listed below the agents, under Humans, with the same activity figures.

![The agents console: four agents, each with its pod and role, state, tickets in progress, queue, and tickets and pull requests for the day](/img/hosted-agents/console-agents.png)

Everything they produce goes through Wire: releases are set up with `/wire:new`, tickets are linked to the release with `/wire:tickets-import`, each ticket is worked with `/wire:work` on its own branch cut from the release branch, and work is published with `/wire:utils-pr-create`. The Wire record in the repository is the same one a consultant working by hand would leave.

## This section

| Page | What it covers |
|---|---|
| [Pods and roles](./pods-and-roles) | What a pod is, the four roles, people in pods, and how an agent delivery manager proposes first |
| [Ways to run a project](./ways-to-run-a-project) | Five ways to set up a project: all agents, a mixed pod, agents joining a running project, changing who is in a pod, and asking one agent |
| [The delivery process](./delivery-process) | From an agreed scope to merged work: each step, who does it and the decision points |
| [Governance](./governance) | The rules for who decides what, the light and strict templates, and pull request approvals |
| [Sprints and the backlog](./sprints-and-backlog) | How the sprint is kept whole and how late additions are approved |
| [Jira, Slack and files](./jira-slack-and-files) | How agents are asked for work, where they report, how questions reach people in Slack, and how documents reach the repository |
| [Platform architecture](./platform-architecture) | The Google Cloud services agents run on, how a request flows through them, and why |
| [Memory](./memory) | What agents remember between tickets, and how to delete a memory |
| [Setting up a pod](./setting-up-a-pod) | What a Rittman Analytics administrator configures before a pod can work |
| [Release history](./release-history) | What changed in each hosted agents release |
