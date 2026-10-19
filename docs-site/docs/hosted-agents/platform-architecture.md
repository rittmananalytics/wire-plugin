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
7. Questions and rulings go to the Jira ticket. A question for a person is also posted in the project's Slack channel, @mentioning them (the agents' own channel when the project has none). The agent waits for a reply from the engagement lead or an escalation contact, on the ticket or in the message's thread; a Slack reply is copied onto the ticket within 5 minutes.
8. The agent pushes a ticket branch and opens a pull request on GitHub.
9. The agent posts status changes to the ticket's Slack thread.
10. The supervisor writes the agent's status to Firestore and its logs to Cloud Logging.
11. When a person is a pod's delivery manager, a scheduled delivery assistant (below) does the routine delivery work for them instead of an agent.
12. The administrator uses the Cloud Run console, which reads status, pods and projects from Firestore and logs from Cloud Logging, and can start, stop or create Compute Engine machines.
13. Cloud Build builds the agent image into Artifact Registry. Each machine pulls the image by digest when it starts.

## Why it is built this way

**The agent is the same Wire a consultant runs.** Each agent runs Claude Code with the Wire plugin, the same published release a consultant installs. It uses Wire's own commands for releases, tickets and pull requests, so the record it leaves in the repository is the same as a person's. The image names one plugin release; a newer Wire reaches the agents when that pin is raised and the image rebuilt, and an earlier one can be restored the same way. There is no separate agent version of Wire to keep in step. The agents' own code is in a private Rittman Analytics repository (`rittmananalytics/wire-hosted-agents`), released on its own schedule.

**One virtual machine per agent.** Agent work is long-running and stateful. A ticket can take hours, much of it waiting for a ruling, and the agent needs a disk that keeps its repository clones, its Claude sign-in and its tool sign-ins between tickets and restarts. A Compute Engine machine gives each agent that disk and runs without the time limits of request-based services. One machine per agent also keeps agents apart: a fault, a full disk or a stuck process on one agent does not touch the others. A container cluster would add a cluster to run and pay for before any agent did any work, for no gain at this size. Each machine works up to 3 tickets at once, so a ticket waiting for a ruling does not hold up the rest.

**Managed services around the machines.** Everything that is not agent work uses a managed service, so there are no other servers to patch:

| Need | Service | Why |
|---|---|---|
| Receive Jira and Slack events | Cloud Run | Events arrive at any time and need a public address that answers in seconds. Cloud Run scales to the traffic and holds no state. |
| Hand work to the right agent | Pub/Sub, a topic per agent | A request waits safely if the agent is busy or restarting, and is delivered again if a run fails. Nothing is lost between Jira and the agent. |
| Share what agents need to know | Firestore | Projects, pods, governance choices, status, schedules and Slack threads are small records read by every agent and the console. Firestore needs no schema changes or server. Settings people make on the console are kept apart from what agents write (see below). |
| Keep credentials | Secret Manager | Each agent's Jira, GitHub and Slack tokens, the delivery assistant's tokens and the Wire Agents app's token are stored once and read at start, never written into the image or the repository. |
| Run the console | Cloud Run | The console is a web app used by a few administrators. It runs only when used. |
| Help a person delivery manager | Cloud Run job, every 15 minutes | The delivery assistant. It follows fixed rules and makes no model call, so it needs no machine of its own. It uses its own Jira account and the Wire Agents app for Slack. |
| Count people's activity | Cloud Run job, every hour | Tickets started, closed and blocked, and pull requests, for people in pods, read from Jira and GitHub, so the console shows people and agents with the same figures. |
| Show a release's progress | Cloud Run, private | Wire Studio's release view, read from the client repository. Only the console can call it, so the record is seen only by people signed in to the console. |
| See what agents did | Cloud Logging | Every run is logged in one place, and the console shows it live. |
| Ship the agent | Cloud Build and Artifact Registry | One image for every agent, built once and deployed by digest, so every agent runs exactly the same code. |

**Jira and Slack as the interface.** Agents work where the team already works. Work is asked for, decided and recorded on Jira tickets, which gives every decision an audit trail; Slack carries short heads-ups, and questions for a person, @mentioned in the project channel, whose replies are copied onto the ticket. Nobody needs a new tool to work with an agent, and the agents console is needed only to run them.

**Every agent message in a channel.** Agents send no direct messages. Questions and proposals are posted in the project's channel, or the agents' own channel, from the agent's own Slack user, so people reply to the agent itself where the team can see it. The Wire Agents app is used by the console and the delivery assistant.

**Each agent has its own identity.** Every agent has its own Jira account, Slack user, GitHub access, service account, credentials and queue. People in pods keep their own accounts: the console only links them, by email. Its actions show under its own name, its access can be granted or removed alone, and it can read only its own secrets and its own queue. The console can give a new agent only the roles on a fixed list, so it cannot give any agent more access than that.

**Agents cannot change their own permissions.** What an agent may do depends on settings people make on the console: which pods it is in and with what role, the people in each pod, each project's repository, Slack channel and governance template, and each agent's profile. These settings are kept in a store agents can read but never write. Agents write their own working state (status, schedules, Slack threads) to a separate store, and the console never takes that state as grounds for access. When an agent asks the console to record a standing decision, save to memory or record a project's repository, the console checks the request against the settings store and against Jira, which it reads with its own account: for example, whether the agent is the project's engagement lead, or whether the ticket is assigned to it. An agent misled by text in a ticket or a file cannot add itself to a pod or give itself a role. A project's repository can be recorded by an agent only once, for a project that has none, and only when a person named it on the ticket; after that, only a person changes it on the console.

**Closed to the internet.** The agent machines have no public address. They reach Jira, Slack, GitHub and Anthropic outward through Cloud NAT, and nothing can connect in to them. An administrator reaches a machine only through Identity-Aware Proxy, for example to sign an agent in to Claude. The only public entry points are the event receiver, which checks that each event really came from Jira or Slack, and the console, which accepts Rittman Analytics Google accounts only.

**People keep the decisions.** The architecture carries questions to people rather than letting an agent settle them. A question goes to the Jira ticket and the agent waits for an answer; the project's [governance template](./governance) says which decisions the engagement lead may take and which go to a person.

**Defined as code.** The machines, queues, service accounts, secrets and network are defined in Terraform, so a new agent is created the same way every time, by Terraform or by the console from the same machine template.

## Release view

Each project on the console's **Projects** page has a **View release** button beside its key. It opens a read-only view of the project's releases, built by the same code as Wire Studio, so it shows the same answer a consultant sees running Studio on a clone:

- the artifact graph and what can run next;
- for a release built from tickets, the tickets view: each slice and step, what each ticket waits on, its progress, the files its branch changed and its activity;
- what is waiting on a decision;
- rulings, iterations and the execution log;
- any document in the release.

It leaves out what does not apply to hosted work: there are no directives to copy and no "Run in Claude Code" button (work starts from Jira tickets), and no lanes (the console's agent status shows what each agent is doing).

| Question | How it works |
|---|---|
| Where does it read from? | The project's GitHub repository, read only, with a credential that can read and not write. Releases are found on the default branch, on `feature/` and `release/` branches, and on any release branches listed for the project. A release on several branches is shown from the branch where it was updated last. The most recently updated release opens first; the others are listed. |
| How fresh is it? | Read on each page load. Results are kept for up to a minute per commit, so a new commit shows within about a minute. |
| Who can see it? | People signed in to the console. The release view runs as its own private service; the console calls it for a signed-in person and passes the page back. The browser never reaches the service, and nothing else may call it. |
| Can it change anything? | No. It reads the repository and writes nothing, and it has no action that starts work. |

