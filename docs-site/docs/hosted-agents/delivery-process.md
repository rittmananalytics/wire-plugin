---
sidebar_position: 3
title: The delivery process
---

# The delivery process

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

This is the process a pod follows from an agreed scope to merged work. Each step is done by one role; each decision point is taken by whoever the pod's [governance template](./governance) names for that kind of decision. The diagram uses the light template; under the strict template more of the decision points go to a person.

![How work flows, part 1: a person agrees the scope, the engagement lead raises a delivery request, the delivery manager sets up the release, plans and assigns tickets, and the engineers branch, propose a plan and get a ruling](/img/hosted-agents/diagram-flow-1.png)

![How work flows, part 2: the engineers build and raise a pull request, the engagement lead reviews it and merges it into the release branch or sends it back, the delivery manager reviews delivery and assigns the next tickets, and a person merges the finished release](/img/hosted-agents/diagram-flow-2.png)

## The steps

| # | Step | Done by | Decision point | Decision kind |
|---|---|---|---|---|
| 1 | Agree the scope and statement of work, and share it with the engagement lead in the project's Slack channel; the lead opens a kick-off ticket with it | Person | | `scope_change` |
| 2 | Kick-off: read the SoW and ask a person every open question once, together; record the answers as the project's standing decisions | Engagement lead | Each answer | Any kind a person decides; under light, also the questions only the client can answer |
| 3 | Ask the delivery manager to deliver it: a "Delivery requested:" comment on the kick-off ticket | Engagement lead | | |
| 4 | Set up the release with `/wire:new`, which creates the release branch from the default branch, copy the standing decisions into its `decisions.md`, and publish it with `/wire:utils-pr-create` | Delivery manager or an engineer | Approve the release set-up pull request | `release_setup_standard` |
| 5 | Plan the work as tickets, one per piece an engineer can finish and review on its own, each naming its Wire commands and its role; link dependencies | Delivery manager | | `delivery_plan` |
| 6 | Link the tickets to the release with `/wire:tickets-import`, so the release is built ticket by ticket | Delivery manager | | |
| 7 | Put every in-scope ticket in the sprint and start it | Delivery manager | | `delivery_plan` |
| 8 | Assign the tickets that can start, to the engineer with the right role and the fewest open tickets | Delivery manager | | |
| 9 | Cut the ticket's branch from the release branch and propose a plan (`/wire:work`) | Engineer | Approve the plan | `work_plan_approval` |
| 10 | Build and test; ask when Wire needs a decision | Engineer | Each ruling, by its kind | `business_rule`, `design_decision`, `technical_choice`, and the always-a-person kinds |
| 11 | Publish with `/wire:utils-pr-create`; the pull request goes into the release branch and the ticket moves to QA | Engineer | | |
| 12 | QA: check the work against the ticket, and review the code against the statement of work, the requirements and the business rules | Engagement lead | Pass or fail | `qa_signoff` |
| 13 | Approve and merge the pull request into the release branch, recording what was checked | Engagement lead | | `code_merge_release` |
| 14 | Every hour: give each ticket a role, assign tickets that can start by role and free capacity, and tell engineers when theirs can start. Twice a working day: chase stalled tickets and waiting reviews, and raise risks with the lead | Delivery manager | | |
| 15 | The last ticket opens the release pull request into the default branch; after the lead's QA it stays in QA, and a person is asked to review and merge it ("Merge requested:", on the ticket and in Slack) | Engineer, engagement lead | | |
| 16 | Review and merge the release into the default branch; the ticket moves to Done when it is merged | Person | | `code_merge_default` |

A failed QA sends the ticket back to its engineer with what to change; after a number of failed checks set by the template, it goes to a person. A pull request waiting for review is QA, never Blocked. A ticket that cannot go on is moved to Blocked with its reason; when it waits on the engagement lead, the lead gets a formal ruling request and the ticket starts again when the lead rules. A person's reply on a Blocked or paused ticket starts it again without an @mention, and the delivery manager's hourly check catches any that do not. A ticket passes QA but stays in QA, not Done, until a person merges a pull request the pod may not merge.

## Rules that apply at every step

- **Branches and pull requests are Wire's.** Agents use the release and ticket branches Wire creates and publish through `/wire:utils-pr-create`. They never invent a branching scheme.
- **Published history is never rewritten.** No agent amends, rewords, rebases or force-pushes a commit that is already on GitHub, or deletes a branch. A correction is a new commit.
- **Agents never decide what is not theirs.** A question outside an agent's governance goes to the engagement lead; one outside the lead's goes to a person, and the agent waits.
- **Questions are asked on the Jira ticket.** Slack is for heads-ups; see [Jira, Slack and files](./jira-slack-and-files).
