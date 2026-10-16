---
sidebar_position: 1
title: Overview
---

# Hosted agents

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents are Wire agents that Rittman Analytics runs as members of its own delivery teams. They are available only on Rittman Analytics engagements. Each one has its own Jira account and its own Slack user, and works the tickets it is given the way a consultant would: it reads the engagement's Wire record, proposes a plan, asks when a decision is needed, builds the change with Wire's commands and hands the work back as a pull request.

They differ from running Wire yourself in Claude Code in three ways:

- **They are always on.** Assigning a Jira ticket, or @mentioning an agent in a comment or in Slack, starts it. Nobody needs a terminal open.
- **They work in teams.** Agents are grouped into pods, and each member of a pod has a role: delivery manager, engagement lead, analytics engineer or data engineer.
- **They work under a governance template.** Each project's template says, for every kind of decision, whether an agent may take it or a person must.

Everything they produce goes through Wire: releases are set up with `/wire:new`, tickets are linked to the release with `/wire:tickets-import`, each ticket is worked with `/wire:work` on its own branch cut from the release branch, and work is published with `/wire:utils-pr-create`. The Wire record in the repository is the same one a consultant working by hand would leave.

## This section

| Page | What it covers |
|---|---|
| [Pods and roles](./pods-and-roles) | What a pod is, the four roles and what each is responsible for |
| [The delivery process](./delivery-process) | From an agreed scope to merged work: each step, who does it and the decision points |
| [Governance](./governance) | The rules for who decides what, the light and strict templates, and pull request approvals |
| [Sprints and the backlog](./sprints-and-backlog) | How the sprint is kept whole and how late additions are approved |
| [Jira, Slack and files](./jira-slack-and-files) | How agents are asked for work, where they report, and how documents reach the repository |
| [Setting up a pod](./setting-up-a-pod) | What a Rittman Analytics administrator configures before a pod can work |
| [Diagrams](./diagrams) | The three diagrams in this section, together |
