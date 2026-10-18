---
sidebar_position: 2.5
title: Ways to run a project
---

# Ways to run a project

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents fit a project in five ways, from a team made almost entirely of agents to an agent asked for one ticket. Pick the one that matches how much of the delivery you want agents to do. A project can move from one to another as the team changes.

| | Setup | Who does the work | Who runs the delivery |
|---|---|---|---|
| 1 | An all-agent pod | Agents | An agent engagement lead and delivery manager; a person decides only what governance gives to a person |
| 2 | A mixed pod, set up from the start | Agents, people or both | Whoever holds the lead roles, agent or person |
| 3 | Agents added to a team of people already running a project | People and agents | The people, until they agree to an agent taking on a lead role |
| 4 | Changing who is in a pod | As the pod is now | One engagement lead and one delivery manager at a time |
| 5 | An agent asked directly, with no pod | The agent asked | Whoever asked |

## 1. An all-agent pod

![An all-agent pod: a person shares the statement of work with the engagement lead agent in Slack; the delivery manager agent plans tickets on the Jira board, analytics engineer agents build and check them, progress goes to the project's Slack channel, and the escalation contact is asked in Jira and alerted in Slack, then reviews and merges the release pull request](/img/hosted-agents/setup-1-all-agent-pod.png)

Every role in the pod is an agent: engagement lead, delivery manager and engineers. The only person involved is the project's **escalation contact**, who answers the questions the governance template gives to a person: scope, security, client data, production changes and merging into the default branch, plus anything the engagement lead is unsure of.

A person shares the statement of work with the engagement lead in the project's Slack channel. The lead asks its questions once, the delivery manager plans the release as tickets, the engineers build and check them, and the release reaches the person as one pull request into the default branch to review and merge. See [The delivery process](delivery-process).

## 2. A mixed pod, set up from the start

![A mixed pod: a person engagement lead, an agent delivery manager, two agent analytics engineers and a person analytics engineer; tickets are assigned by role and capacity, and an agent asks the person lead for review in Jira and in Slack](/img/hosted-agents/setup-2-mixed-pod.png)

When you create the pod, give each role to an agent or a person: any mix. Register the people on the console first (Admin page); their existing work, chat and issue tracker accounts are linked.

Agents treat people as teammates. The delivery manager assigns tickets to people by role and free capacity; engineers ask a person who is engagement lead for reviews and decisions; agents mention people on tickets. People do their own work and reply in their own time, and agents never do it for them. When a person is the delivery manager, a scheduled assistant (not an agent) proposes assignments for them to approve and keeps the sprint and the release record up to date. See [People in a pod](pods-and-roles#people-in-a-pod).

## 3. Agents added to a running project

A team of people is already running the project: it has a sprint, tickets and assignees. You create a pod for it with those people, and add agents.

![Agents added to a running project: a team of people runs a sprint; agents join the pod, the delivery manager role moves from the person to an agent after you confirm, the agent delivery manager proposes sprint, role label, assignment and start changes to the escalation contact in Slack and acts only on the ones agreed, and an agent engineer works the tickets it is assigned](/img/hosted-agents/setup-3-agents-added-to-running-project.png)

A pod has one delivery manager. If a person held the role, giving it to an agent hands over their open tickets, after you confirm.

- **Engineer agents** take tickets as soon as they are assigned them, by a person or by the pod's delivery manager.
- **An agent delivery manager does not take over.** On a project it did not set up, it proposes instead: it sends the project's escalation contact one message listing what it would do (the sprint, role labels, assignments and starts) and changes nothing in the issue tracker until the escalation contact agrees. Agreeing is per project, on the console's Projects page or by replying to the message: everything at once, or one action at a time (for example, assignments but not sprint changes). A project the delivery manager set up itself, from a delivery request, needs no agreement: it already runs the plan it made.
- **An agent engagement lead acts when asked.** It answers what it is asked directly (a ruling, a review, a question on a ticket), and runs a kick-off when a person shares a statement of work with it. It takes on nothing else in the project by itself.

## 4. Changing who is in a pod

![Changing who is in a pod: before, an agent delivery manager holds two tickets; after a person is made delivery manager, the tickets move to the person with a comment on each and the agent is removed from the pod](/img/hosted-agents/setup-4-changing-who-is-in-a-pod.png)

You can add or remove agents and people on a pod at any time. A pod has **one engagement lead and one delivery manager**, agent or person. Giving either role to a new member removes the member who held it from the pod, after you confirm on the Pods page. Their open tickets move to the new holder, with a comment on each, and decisions waiting on them are put to the new holder. Engineers can be added or removed freely.

## 5. An agent asked directly

![An agent asked directly: a team member asks an agent in Slack or by @mention or assignment on a ticket; the agent does the work with Wire and asks that person to review in Jira and in Slack, while the pod is not involved](/img/hosted-agents/setup-5-agent-asked-directly.png)

You do not need a pod to use an agent. @mention an agent on a ticket, or assign it a ticket, in any project the agents can see, and it does what you ask with Wire. The same applies to an agent that is not a member of the pod covering that project.

Such work is not part of any pod's delivery: the pod's delivery manager does not plan, assign or chase it, and its engagement lead does not review it. The agent instead asks whoever gave it the work to review it, and puts its questions to them. See [Validation and review](governance#validation-and-review).
