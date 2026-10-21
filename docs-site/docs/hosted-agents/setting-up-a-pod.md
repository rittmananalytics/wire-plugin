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

On the **Projects** page, add the project with:

- **Its tracker**: Jira, or **None** for a project that needs no tickets (for example one that only has a [context steward](context-steward)). A project with no tracker needs a repository and a Slack channel, and agents make no Jira calls for it.
- **The project key**. For a Jira project, exactly as Jira shows it (the letters before the number in a ticket key, such as `ACME` in `ACME-12`); agents look the project up by this key, and the console checks that Jira has a project with it. For a project with no tracker, any key of capital letters and digits.
- **The client repository** the agents work in.
- **The project's Slack channel**, if it has one. Project updates go there; without one they go to the agents' own channel.
- **The project's [governance template](./governance)**: lightly or strictly governed (strict when not set). A pod working several projects follows each project's own template.
- **Release branches**, optional: branches the release view should also read (see [Platform architecture](./platform-architecture#release-view)).

## 2. Make sure Jira tells the agents

The Jira webhook that starts agents must cover every project agents work in. It is set to all projects; agents ignore events that are not assigned to them and do not mention them.

## 3. Register any people

Console admins register people on the **Admin** page, which also holds spawning agents and the list of admins. Import a person from the company directory, an issue tracker project or a Slack channel, or add them by email; the console links their existing Jira, Slack and GitHub accounts and their photo. Check that each person has a Slack account linked: without one, agents ask them on Jira tickets only, with no Slack message. For a person who will be an engineer, you can set how many tickets they take at once (3 unless changed). Only console admins see the Admin page and can spawn agents, register people or manage admins; everyone signed in can view agents, people, pods, projects and release views.

## 4. Create the pod

On the **Pods** page:

1. Name the pod and list the projects it covers, by the keys the Projects page lists. The registered keys are shown under the field; click one to add it.
2. Add agents, people or both, and give each a role: one engagement lead, one delivery manager, and the analytics and data engineers the work needs. People must be registered first (step 3). Giving the engagement lead or delivery manager role to someone new removes the member who held it from the pod, after you confirm, and hands their open work to the new holder.
3. If a person is the delivery manager, choose whether the delivery assistant is on (it is by default) and whether it may **assign ready tickets directly** instead of proposing them for the person to approve.
4. Add the escalation contacts by email; the console finds their Jira accounts. A pod that covers a project needs at least one.

Saving gives each member access to the pod's projects that are in Jira. A pod covering only projects with no tracker needs no delivery manager or analytics engineer.

The Pods page shows each pod as a chart, with each member's photo: escalation contacts at the top, the engagement lead below them, and the delivery manager, engineers and any context steward below the lead. Each project key on the Projects page links to the project's page, which holds its delivery settings and context steward settings.

![The Pods page: a pod shown as an organisation chart with the escalation contact, engagement lead, delivery manager and two analytics engineers](/img/hosted-agents/console-pods.png)

Each agent's page also holds its profile: a photo, the default persona it takes on engagements that have not given it one, and its personality (how it writes). The page lists its recent tickets.

![An agent's profile: photo, default persona set to delivery manager, a personality describing tone and style, and the agent's recent tickets](/img/hosted-agents/console-agent-profile.png)

## 5. Connect Slack

Each agent posts as its own Slack user. On each agent's page, press **Connect Slack** and sign in as that agent. The connection includes reading files shared with the agent; an agent connected before that was added must connect again.

Questions for people are posted in the project's channel by the asking agent, so each agent must be a member of each project channel it works in. On a project with no channel, they go to the agents' own channel, so every agent and every person who may be asked should be a member of it. Agents send no direct messages.

The same page shows the tickets the agent is working on, its Slack connection and its scheduled tasks, such as a weekly progress report.

![An agent's page: state, tickets in progress, Slack connected, and two scheduled progress reports](/img/hosted-agents/console-agent-summary.png)

## 6. Turn on sprints

On each Jira project, turn on sprints (Project settings, Features) so the delivery manager can keep the sprint whole.

## 7. Agree how an agent delivery manager may act

On a project it did not set up (for example a running project agents are joining), an agent delivery manager proposes its changes first and acts only on what is agreed. On the project's page, switch on each group of changes it may make (sprint, role labels, assignments, starts, sprint additions), or leave them off and answer its proposals in Slack. See [An agent delivery manager proposes first](./pods-and-roles#an-agent-delivery-manager-proposes-first).

## Then

Agree the scope with the client, then share the statement of work with the engagement lead in the project's Slack channel. The lead opens a kick-off ticket, asks any open questions there once, records the answers and asks the delivery manager to deliver it. Follow progress on the board, in the ticket threads, and in the end-of-day summaries. When an agent needs your answer, it @mentions you in the project's channel; reply in that message's thread or on the ticket.
