---
sidebar_position: 4
title: Governance
---

# Governance

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

A governance template says, for every kind of decision met on a project, who takes it: the **delivery manager** or the **engagement lead** of the pod working it, or a **person** (one of the pod's escalation contacts). Each project chooses one template, on the agents console's Projects page, so a pod working several projects can be lightly governed on one and strictly on another. The agents read it at every decision, so changing a project's template changes how it is governed from the next decision on.

**When a person holds a role.** The engagement lead or delivery manager can be a person. Decisions the template gives that role then go to that person: an agent asks them on the ticket, with a Slack direct message, and waits. A person in the role is never overruled by an agent.

Templates are a [process registry](../advanced/registries) entry type, like release types and conventions: authored in the registry, synced into the hosted agents' private repository (`rittmananalytics/wire-hosted-agents`), and checked by a validator there. Two ship; more can be added.

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
| `artifact_review` | Reviewing a generated Wire artifact in QA: approve it, or send it back for rework and resubmission | Engagement lead | Person (the lead asks a human reviewer) |
| `precondition_override` | Skipping a required Wire step | Engagement lead, under a fixed rule: refused unless a person allowed it | Same |
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

## Preconditions: required steps are not skipped

Each Wire release type has required steps in a fixed order; for `dbt_development`, requirements, then the data model, then dbt. A later step's command checks that the earlier ones are done and reviewed (a precondition) before it runs.

- **The delivery plan covers every required step** that is not complete, in Wire's order, each as its own ticket, plus the optional steps the statement of work or a person asks for. Each ticket waits for the tickets of the steps it depends on.
- **A step is skipped only when a person says so.** At kick-off the engagement lead asks whether any required step may be skipped, recommending none. A person's yes is recorded as a standing decision naming the step. Nothing else allows a skip.
- **The engagement lead refuses every other request to skip a step.** An engineer that meets an unmet precondition ends its ticket blocked on the earlier step, and starts again when that step is done. The agents' tools turn a lead's approval that does not cite a person's standing decision into a refusal.
- **A technical blocker goes to a person.** When an engineer cannot complete a prerequisite for a technical reason, it asks with the `precondition_override` kind and says what stops it; the lead escalates it to a person, who decides.
- **Slices only when the statement of work asks.** Building an artifact in parts on separate tickets, which together make up the whole, is for human-delivered projects; for hosted agents, only when the statement of work asks for it.

## Validation and review

| Stage | Who | What happens |
|---|---|---|
| **Validate** | The engineer that generated the artifact | Wire 4.x validates automatically after each generate step; where a command does not, the engineer runs its validate step. The engineer reads the result, fixes every issue, regenerates and validates again until it passes. Only validated work is handed in. |
| **Hand in** | The engineer | Moves the ticket to QA and posts **"Review requested:"** @mentioning the engagement lead |
| **Review, light** | The engagement lead | Reviews the work and either approves it, or comments with what to change; the engineer reworks and resubmits. The lead escalates only a question that a person must answer. When the lead is a person, the engineer asks them with **"Review by a person requested:"** instead, on the ticket and in Slack. |
| **Review, strict** | A person | The lead asks a human reviewer (**"Review by a person requested:"**, on the ticket and in Slack): the named reviewer when one is recorded, else the escalation contacts. The person approves, or says what to change and the work goes back for rework and resubmission. The lead reports the person's review, not its own judgement. |
| **Record** | The delivery manager, or the delivery assistant when a person is delivery manager | When the work merges, the review result and who approved it are recorded in the release record, as the step's `/wire:<artifact>-review` records it |

The engagement lead's own work is reviewed by a person under both templates.

**When there is no engagement lead.** An agent working without an engagement lead (its pod has none, or it was asked outside its pods, for example @mentioned on a ticket or in Slack in another project) asks whoever gave it the work to review it: the person or agent that assigned it the ticket, else the one that @mentioned it, else the person who asked in Slack, else the ticket's reporter. A person is asked with **"Review by a person requested:"** and replies on the ticket; an agent gets a formal **"Review requested:"**. The agent then reports their review; it never approves its own work. A pull request still to be merged goes to the same person. If that person asks for changes, the agent reworks the ticket at once. Questions an agent outside a pod must put to a person go to the same person.

**Rework and merge conflicts.** Changes a person asks for in their own review are not counted towards the template's limit of failed checks before a person is asked, as a person is already the reviewer. A pull request that passes review but conflicts with the branch it goes into is sent back to its engineer to merge that branch in and resolve the conflict, never to a person.

## Standing decisions

When a person answers a question that applies beyond one ticket (who reviews the release, a list of brand terms, how to treat an edge case), the engagement lead or delivery manager records it as one of the project's **standing decisions**. Every agent reads them at every run, they are copied into the release's `decisions.md` when it is set up, and those recorded later are added each time the delivery manager updates the release record, so Wire Studio lists them all; they stand until a person changes them. A standing decision that names a person for an item (a business rule's confirmer, the reviewer of a pull request) means that person decides exactly that item, whatever the template says.

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
| **Required steps** | A lead's approval to skip a required Wire step that cites no person's standing decision becomes a refusal. |
| **Each question names its decision kind** | An agent asking for a decision says which kind it is. A kind the template gives to a person goes straight to the escalation contacts; the engagement lead never sees it, so it cannot rule on it by misreading it. |
| **Only the people asked can answer** | A question for a person is answered only by the people it went to, not by another agent or anyone else who comments. A reply in Slack counts only when it comes from a person asked, in that question's thread. |
| **A named reviewer** | When a person is recorded as reviewer for pull requests into the default branch, a release branch or both, no agent may approve or merge those pull requests; they are sent to that person. |
| **A person in the review** | When a person comments on a ticket after its work was handed in, an agent may no longer merge it; a person does. |
| **Client-facing work** | The engagement lead states in every QA whether the client will see the work. When the template gives client-facing work to a person, the lead cannot merge it, and work outside a pull request waits in QA for a person's sign-off ("Sign-off requested:"). |
| **The lead's own work** | A ticket held by the engagement lead goes to a person for QA. |
| **The release pull request** | The ticket that publishes a release always opens its pull request into the default branch; any other base is corrected. |
| **Blocked on a person** | A ticket that ends blocked waiting on a person, with no question to a person open, asks them: a "Question for a person:" on the ticket @mentioning them, and a Slack message. This includes a person who is the engagement lead. Their reply, on the ticket or in Slack, starts the ticket again. |
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

The agent the template names approves and merges with a plain merge, so no branch is ever deleted or rewritten. When a person must merge, the ticket passes QA but stays in QA, and a "Merge requested:" comment and a Slack message ask the named reviewer if one is recorded; else, for a release branch, a person who is the engagement lead; else the escalation contacts; the ticket moves to Done when the pull request is merged. A person's comment on a ticket in QA goes to the engagement lead, who checks the work again with it. Approving code needs a written note of what was checked against the statement of work, the requirements and the business rules; it is posted on the pull request as the record of the review. Under the strict template every merge is a person's.

## Choosing and adding templates

A project's template is chosen on the agents console's Projects page; a project with none chosen is strictly governed, so a forgotten setting is the safer one. Agents read the choice, and pod membership and roles, but cannot change them: only a person does, on the console (see [Platform architecture](./platform-architecture)).

To add a template, add a file to the process registry's `governance/` folder with every decision kind set, open a pull request there, and sync it into the hosted agents repository (`rittmananalytics/wire-hosted-agents`, private). The schema and the validator that checks every template, including the always-a-person rule, are in that repository.
