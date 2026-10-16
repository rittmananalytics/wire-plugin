---
sidebar_position: 4
title: Governance
---

# Governance

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

A governance template says, for every kind of decision met on a project, who takes it: the **delivery manager** or the **engagement lead** of the pod working it, or a **person** (one of the pod's escalation contacts). Each project chooses one template, on the agents console's Projects page, so a pod working several projects can be lightly governed on one and strictly on another. The agents read it at every decision, so changing a project's template changes how it is governed from the next decision on.

Templates are a [process registry](../advanced/registries) entry type, like release types and conventions: authored in the registry, synced into Wire, and checked by a validator. Two ship with Wire; more can be added.

![Who takes a decision: some kinds always go to a person, release set-up and the delivery plan go to the delivery manager, and the rest follow the project's light or strict template](/img/hosted-agents/diagram-decisions.png)

## The kinds of decision

| Kind | What it covers | Light | Strict |
|---|---|---|---|
| `scope_change` | A change to scope, deliverables or the statement of work | Person | Person |
| `cost_or_effort` | Cost, budget, effort estimates or billing | Person | Person |
| `security_access` | Security, access, permissions, credentials or service accounts | Person | Person |
| `client_data` | Personal data, residency, retention or sharing | Person | Person |
| `client_facing` | Anything the client sees before it is signed off | Person | Person |
| `production_change` | A production deploy, a cutover, or deleting or overwriting data or code in use | Person | Person |
| `code_merge_default` | Merging code into the default branch, which can deploy to production | Person | Person |
| `business_rule` | Confirming or changing a business rule or definition | Engagement lead | Person |
| `design_decision` | Data model grain, keys and other design choices within scope | Engagement lead | Person |
| `work_plan_approval` | Approving an engineer's plan for a ticket | Engagement lead | Person |
| `sprint_addition` | Adding a minor ticket to a running sprint | Engagement lead | Person |
| `release_setup_nonstandard` | A release branch set up other than the standard way | Engagement lead | Person |
| `code_merge_release` | Merging code into a release branch, after code review | Engagement lead | Person |
| `technical_choice` | Routine technical choices within a ticket's scope | Engagement lead | Engagement lead |
| `qa_signoff` | Passing a ticket's QA | Engagement lead | Engagement lead |
| `release_setup_standard` | The standard release branch and Wire scaffolding | Delivery manager | Delivery manager |
| `delivery_plan` | Planning tickets, the sprint and assignments | Delivery manager | Delivery manager |

| Setting | Light | Strict |
|---|---|---|
| Hours an agent waits for a person's ruling before pausing | 4 | 8 |
| Failed QA checks on one ticket before a person is asked | 3 | 2 |
| Sprint length the delivery manager uses, in weeks | 2 | 2 |

### Light: the engagement lead decides all but the most significant

Use it for internal projects and for clients who want speed, where the solution is clear once the first questions are answered. A person decides only the seven kinds that are significant or hard to undo.

The aim is a release that runs through with little of a person's time: the engagement lead asks every open question once, at kick-off (`kickoff_questions`), the pod then plans, builds, checks and merges each ticket into the release branch, and a person's only other step is to review and merge the release pull request into the default branch.

### Strict: a person decides all but the routine

Use it for regulated clients, early engagements and any client who wants to approve each step. Agents still plan, build and check the work, but plans, designs, business rules, sprint changes and every merge wait for a person. The engagement lead keeps only routine, non-destructive technical choices and the first QA check.

## Standing decisions

When a person answers a question that applies beyond one ticket (who reviews the release, a list of brand terms, how to treat an edge case), the engagement lead or delivery manager records it as one of the project's **standing decisions**. Every agent reads them at every run, they are copied into the release's `decisions.md` when it is set up, and they stand until a person changes them. A standing decision that names a person for an item (a business rule's confirmer, the reviewer of a pull request) means that person decides exactly that item, whatever the template says.

## When work is two kinds at once

A template can say which decision wins (`precedence`). The light template says:

| Work that is both | Rule |
|---|---|
| Client-facing and a QA check | The engagement lead's QA comes first; a person signs off anything the client will see |
| An effort estimate and the delivery plan | Estimates inside the plan are the delivery manager's; budget, billing and any change to agreed effort are a person's |
| Named in the documents or a standing decision | The person named decides exactly that item |

## How the rules are enforced

These checks are made by the agents' own tools, not left to an agent's judgement:

| Check | What happens |
|---|---|
| **Each question names its decision kind** | An agent asking for a decision says which kind it is. A kind the template gives to a person goes straight to the escalation contacts; the engagement lead never sees it, so it cannot rule on it by misreading it. |
| **Only the people asked can answer** | A question for a person is answered only by the people it went to, not by another agent or anyone else who comments. |
| **A named reviewer** | When a person is recorded as reviewer for pull requests into the default branch, a release branch or both, no agent may approve or merge those pull requests; they are sent to that person. |
| **A person in the review** | When a person comments on a ticket after its work was handed in, an agent may no longer merge it; a person does. |
| **Client-facing work** | The engagement lead states in every QA whether the client will see the work. When the template gives client-facing work to a person, the lead cannot merge it, and work outside a pull request waits in QA for a person's sign-off ("Sign-off requested:"). |
| **The lead's own work** | A ticket held by the engagement lead goes to a person for QA. |
| **The release pull request** | The ticket that publishes a release always opens its pull request into the default branch; any other base is corrected. |
| **Finished sprints** | A running sprint with every ticket done is completed, and the next starts with the open tickets. |

## Rules every template keeps

- **Five kinds are always a person's**: scope changes, security and access, client data, production changes and code merged into the default branch. The validator refuses a template that gives any of them to an agent.
- **The delivery manager decides only** the standard release set-up and the delivery plan. The standard set-up adds only Wire's files under `.wire/`, which do not deploy, so it is the one merge into the default branch an agent may approve.
- **A person not replying is never a reason to decide.** An agent waits; after the template's wait it pauses the ticket and says so. A person's reply on the ticket starts it again, with or without an @mention.
- **The lead escalates when unsure.** Even for a kind it may decide, the engagement lead passes the question to a person when the documents do not settle it, or when the customer would reasonably expect to be asked.

## Pull request approvals

| Pull request | Decision kind |
|---|---|
| Release set-up only (Wire scaffolding under `.wire/`), into the default branch | `release_setup_standard` |
| Release set-up only, into any other branch | `release_setup_nonstandard` |
| Code into a release branch | `code_merge_release` |
| Code into the default branch | `code_merge_default` |

The agent the template names approves and merges with a plain merge, so no branch is ever deleted or rewritten. When a person must merge, the ticket passes QA but stays in QA, and a "Merge requested:" comment and a Slack message ask the escalation contacts; the ticket moves to Done when the pull request is merged. A person's comment on a ticket in QA goes to the engagement lead, who checks the work again with it. Approving code needs a written note of what was checked against the statement of work, the requirements and the business rules; it is posted on the pull request as the record of the review. Under the strict template every merge is a person's.

## Choosing and adding templates

A project's template is chosen on the agents console's Projects page; a project with none chosen is strictly governed, so a forgotten setting is the safer one.

To add a template, add a file to the process registry's `governance/` folder with every decision kind set, open a pull request there, and sync it into Wire. The schema is `wire/schemas/governance-schema.md`; `wire/tests/core/validate_governance.py` checks every template, including the always-a-person rule.
