---
sidebar_position: 7
title: Platform architecture
---

# Platform architecture

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents run on Google Cloud, in a project Rittman Analytics owns. Each agent is a Google Compute Engine virtual machine running Claude Code with the Wire plugin. A small set of managed Google Cloud services carries work to the agents, holds what they share and lets an administrator run them.

![Wire Hosted Agents architecture: people and work tools on the left and top, the Google Cloud project in the centre with the event receiver, a Pub/Sub queue per agent, Firestore, Secret Manager, the agents console, Cloud Logging and four agent virtual machines, and Anthropic and the Wire framework on the right](/img/hosted-agents/architecture.png)

## How a request flows

1. A person assigns or mentions an agent on a Jira ticket, or mentions it in Slack.
2. Jira and Slack send the event to the Cloud Run event receiver.
3. The event receiver checks the event and publishes it to the named agent's Pub/Sub topic.
4. The supervisor on that agent's Compute Engine machine pulls the request from its subscription.
5. The supervisor reads the project, pod and governance template from Firestore, and the agent's credentials from Secret Manager.
6. Claude Code runs the ticket with Wire in its own working folder, calling Anthropic through Cloud NAT.
7. Questions and rulings go to the Jira ticket. The agent waits for a reply from the engagement lead or an escalation contact.
8. The agent pushes a ticket branch and opens a pull request on GitHub.
9. The agent posts status changes to the ticket's Slack thread.
10. The supervisor writes the agent's status to Firestore and its logs to Cloud Logging.
11. The administrator uses the Cloud Run console, which reads status, pods and projects from Firestore and logs from Cloud Logging, and can start, stop or create Compute Engine machines.
12. Cloud Build builds the agent image into Artifact Registry. Each machine pulls the image by digest when it starts.

## Why it is built this way

**The agent is the same Wire a consultant runs.** Each agent runs Claude Code with the Wire plugin, the same build a consultant installs. It uses Wire's own commands for releases, tickets and pull requests, so the record it leaves in the repository is the same as a person's, and any improvement to Wire reaches the agents with the next image. There is no separate agent version of Wire to keep in step.

**One virtual machine per agent.** Agent work is long-running and stateful. A ticket can take hours, much of it waiting for a ruling, and the agent needs a disk that keeps its repository clones, its Claude sign-in and its tool sign-ins between tickets and restarts. A Compute Engine machine gives each agent that disk and runs without the time limits of request-based services. One machine per agent also keeps agents apart: a fault, a full disk or a stuck process on one agent does not touch the others. A container cluster would add a cluster to run and pay for before any agent did any work, for no gain at this size. Each machine works up to 3 tickets at once, so a ticket waiting for a ruling does not hold up the rest.

**Managed services around the machines.** Everything that is not agent work uses a managed service, so there are no other servers to patch:

| Need | Service | Why |
|---|---|---|
| Receive Jira and Slack events | Cloud Run | Events arrive at any time and need a public address that answers in seconds. Cloud Run scales to the traffic and holds no state. |
| Hand work to the right agent | Pub/Sub, a topic per agent | A request waits safely if the agent is busy or restarting, and is delivered again if a run fails. Nothing is lost between Jira and the agent. |
| Share what agents need to know | Firestore | Projects, pods, governance choices, status, schedules and Slack threads are small records read by every agent and the console. Firestore needs no schema changes or server. |
| Keep credentials | Secret Manager | Each agent's Jira, GitHub and Slack tokens are stored once and read at start, never written into the image or the repository. |
| Run the console | Cloud Run | The console is a web app used by a few administrators. It runs only when used. |
| See what agents did | Cloud Logging | Every run is logged in one place, and the console shows it live. |
| Ship the agent | Cloud Build and Artifact Registry | One image for every agent, built once and deployed by digest, so every agent runs exactly the same code. |

**Jira and Slack as the interface.** Agents work where the team already works. Work is asked for, decided and recorded on Jira tickets, which gives every decision an audit trail; Slack carries short heads-ups. Nobody needs a new tool to work with an agent, and the agents console is needed only to run them.

**Each agent has its own identity.** Every agent has its own Jira account, Slack user, GitHub access, service account, credentials and queue. Its actions show under its own name, its access can be granted or removed alone, and it can read only its own secrets and its own queue. The console can give a new agent only the roles on a fixed list, so it cannot give any agent more access than that.

**Closed to the internet.** The agent machines have no public address. They reach Jira, Slack, GitHub and Anthropic outward through Cloud NAT, and nothing can connect in to them. An administrator reaches a machine only through Identity-Aware Proxy, for example to sign an agent in to Claude. The only public entry points are the event receiver, which checks that each event really came from Jira or Slack, and the console, which accepts Rittman Analytics Google accounts only.

**People keep the decisions.** The architecture carries questions to people rather than letting an agent settle them. A question goes to the Jira ticket and the agent waits for an answer; the project's [governance template](./governance) says which decisions the engagement lead may take and which go to a person.

**Defined as code.** The machines, queues, service accounts, secrets and network are defined in Terraform, so a new agent is created the same way every time, by Terraform or by the console from the same machine template.
