---
sidebar_position: 9
title: Setting up a pod
---

# Setting up a pod

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents are run by Rittman Analytics. A Rittman Analytics administrator does the following on the agents console before a pod can work an engagement.

The console accepts Rittman Analytics Google accounts only.

![The agents console sign-in page, with a single "Sign in with Google" button for Rittman Analytics accounts](/img/hosted-agents/sign-in.png)

## 1. Register the project

On the **Projects** page, add the Jira project with:

- **The project key exactly as Jira shows it** (the letters before the number in a ticket key, such as `ACME` in `ACME-12`). Agents look the project up by this key; the console checks that Jira has a project with it.
- **The client repository** the agents work in.
- **The project's Slack channel**, if it has one. Project updates go there; without one they go to the agents' own channel.
- **The project's [governance template](./governance)**: lightly or strictly governed (strict when not set). A pod working several projects follows each project's own template.
- **Release branches**, optional: branches the release view should also read (see [Platform architecture](./platform-architecture#release-view)).

## 2. Make sure Jira tells the agents

The Jira webhook that starts agents must cover every project agents work in. It is set to all projects; agents ignore events that are not assigned to them and do not mention them.

## 3. Create the pod

On the **Pods** page:

1. Name the pod and list the Jira project keys it covers.
2. Add agents and give each a role: one engagement lead, one delivery manager, and the analytics and data engineers the work needs.
3. Add the escalation contacts by email; the console finds their Jira accounts. A pod that covers a project needs at least one.

Saving gives each member access to the pod's Jira projects.

The Pods page shows each pod as a chart: escalation contacts at the top, the engagement lead below them, and the delivery manager and engineers below the lead.

![The Pods page: a pod shown as an organisation chart with the escalation contact, engagement lead, delivery manager and two analytics engineers](/img/hosted-agents/console-pods.png)

Each agent's page also holds its profile: a photo, the default persona it takes on engagements that have not given it one, and its personality (how it writes). The page lists its recent tickets.

![An agent's profile: photo, default persona set to delivery manager, a personality describing tone and style, and the agent's recent tickets](/img/hosted-agents/console-agent-profile.png)

## 4. Connect Slack

Each agent posts as its own Slack user. On each agent's page, press **Connect Slack** and sign in as that agent. The connection includes reading files shared with the agent; an agent connected before that was added must connect again.

The same page shows the tickets the agent is working on, its Slack connection and its scheduled tasks, such as a weekly progress report.

![An agent's page: state, tickets in progress, Slack connected, and two scheduled progress reports](/img/hosted-agents/console-agent-summary.png)

## 5. Turn on sprints

On each Jira project, turn on sprints (Project settings, Features) so the delivery manager can keep the sprint whole.

## Then

Agree the scope with the client, then share the statement of work with the engagement lead in the project's Slack channel. The lead opens a kick-off ticket, asks any open questions there once, records the answers and asks the delivery manager to deliver it. Follow progress on the board, in the ticket threads, and in the end-of-day summaries.
