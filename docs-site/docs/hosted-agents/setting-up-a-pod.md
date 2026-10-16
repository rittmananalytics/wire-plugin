---
sidebar_position: 7
title: Setting up a pod
---

# Setting up a pod

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents are run by Rittman Analytics. A Rittman Analytics administrator does the following on the agents console before a pod can work an engagement.

## 1. Register the project

On the **Projects** page, add the Jira project with:

- **The project key exactly as Jira shows it** (the letters before the number in a ticket key, such as `ACME` in `ACME-12`). Agents look the project up by this key; the console checks that Jira has a project with it.
- **The client repository** the agents work in.
- **The project's Slack channel**, if it has one. Project updates go there; without one they go to the agents' own channel.
- **The project's [governance template](./governance)**: lightly or strictly governed. A pod working several projects follows each project's own template.

## 2. Make sure Jira tells the agents

The Jira webhook that starts agents must cover every project agents work in. It is set to all projects; agents ignore events that are not assigned to them and do not mention them.

## 3. Create the pod

On the **Pods** page:

1. Name the pod and list the Jira project keys it covers.
2. Add agents and give each a role: one engagement lead, one delivery manager, and the analytics and data engineers the work needs.
3. Add the escalation contacts by email; the console finds their Jira accounts.

Saving gives each member access to the pod's Jira projects.

## 4. Connect Slack

Each agent posts as its own Slack user. On each agent's page, press **Connect Slack** and sign in as that agent. The connection includes reading files shared with the agent; an agent connected before that was added must connect again.

## 5. Turn on sprints

On each Jira project, turn on sprints (Project settings, Features) so the delivery manager can keep the sprint whole.

## Then

Agree the scope with the client, then ask the delivery manager to deliver it: in the project's Slack channel, or on a Jira ticket by asking the engagement lead. Follow progress on the board, in the ticket threads, and in the end-of-day summaries.
