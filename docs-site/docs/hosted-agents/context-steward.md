---
sidebar_position: 2.7
title: Context steward
---

# Context steward

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

A context steward is a hosted agent that keeps a project's engagement record (the `.wire/` folder in its repository) up to date with what is said in the project's calls and its Slack channel. It never decides. A change to an agreed requirement, business rule or decision goes to a person first.

It is useful where much of what changes on an engagement is agreed in meetings and chat, and the record falls behind.

## How it differs from the other roles

| | Context steward | Engagement lead |
|---|---|---|
| Who can hold it | An agent only, one per pod | An agent or a person, one per pod |
| Decides anything | No. It asks the confirmation owner | Takes the rulings governance allows |
| Approves pull requests | Never. A person reviews its pull request | Where governance allows |
| Uses tickets | No | Yes |
| On the org chart | Under the engagement lead, with no line to the delivery manager | At the top |

A person can be the engagement lead with an agent as the steward. The steward needs no issue tracker: a project can be registered with tracker **None** (see [Setting up a pod](setting-up-a-pod#1-register-the-project)).

## Setting it up

1. Spawn an agent. Its default persona can be **Context steward** (under "Engagement" in the persona picker); this only pre-fills its role when it joins a pod.
2. Sign it in to Claude and to its claude.ai connectors, including the call recorder, and connect it to Slack. Invite it to the project's channel.
3. Give it write access to the project's repository.
4. Share the project's calls with the agent's call recorder account. It sees only calls shared with it.
5. Add it to the project's pod with the role **Context steward**.
6. On the project's page on the console, fill in the **Context steward** section.

## Settings

Console admins set these on the project's page. Others can see them.

| Setting | What it does |
|---|---|
| Mode | **Off**: does nothing. **Record only**: finds and records, posts nothing. **On**: also asks the confirmation owner in Slack and opens the daily pull request. |
| Call rules | Which recorded calls count, in plain words the steward applies, such as "calls with the client's attendees". |
| Call exclusions | Calls never read, one per line, applied first, such as "company stand-ups". |
| Source channel | The Slack channel it reads. Defaults to the project's channel. |
| Feedback channel | Where it asks its questions. Defaults to the project's channel. |
| Confirmation owner | The person who confirms changes. Needs a Slack account in the people registry. Defaults to a person engagement lead. |
| Reviewer | The person who reviews its pull request. Needs a GitHub login in the people registry. Defaults to a person engagement lead. |
| Working days and hours, scan interval, review time | When it works, in UTC. Default: Monday to Friday, 07:00 to 22:00, every 60 minutes, pull request at 20:00. |

Any mode except Off needs the channels, the owner, the reviewer and call rules.

## What it does each scan

Each scan interval in its working hours, for each project it stewards:

1. It reads every new message in the source channel, thread replies included. A new reply in a thread started up to 30 days ago is read with the thread's first message, for context.
2. It lists the calls recorded since the last scan, keeps those that match the call rules and no exclusion, and reads them.
3. It compares what was said with the engagement record in the repository's default branch, without changing anything.
4. It records each finding with a link to the call (and the time in it) or to the message.

Reading the same call or message again never records the same finding twice. A scan that does not finish marks nothing as read, so the next scan reads the same messages and calls.

| Kind of finding | Meaning | Goes to |
|---|---|---|
| Fact | New information that changes no agreed rule or requirement, such as a date or a contact | Ready for the pull request |
| Proposed change | Would change an agreed requirement, business rule or decision | The confirmation owner |
| Decision reported | Someone says a decision was taken | The confirmation owner |
| Question | Something unclear or contradictory | The confirmation owner |

A fact that would change a requirements, business rules or decisions file under `.wire/` also goes to the confirmation owner.

## Questions to the confirmation owner

In mode **On**, after each scan:

1. **New questions.** Findings for the owner are grouped by the file and section of the record they affect, one Slack thread per group in the feedback channel. A new thread starts with a fixed message, "🧹 @owner the engagement context steward needs your attention", and lists the findings by number, each with what was said and a link to its source. A new finding on a topic that already has an open thread goes into that thread.
2. **Replies.** The owner replies in the thread, for example "confirm 1, reject 2", or answers a question. Only the owner's replies count. At the next scan the steward records each decision and says in the thread what it recorded. A finding the reply does not mention stays open. A thread closes when nothing in it is open.

The steward never treats these threads as a conversation: a message there, even one that @mentions it, is read as a decision at the next scan, not answered.

## The daily pull request

In mode **On**, once a day at the review time on working days:

1. The findings that are ready (facts) or confirmed are applied to the engagement record on one branch for the project, by a run that only edits files under `.wire/`.
2. Before anything is pushed, the change is checked: every changed file must be under `.wire/`, and a requirements, business rules or decisions file may change only through a confirmed finding that names it. If the check fails, nothing is pushed, the findings stay as they were, and the confirmation owner is told in the feedback channel.
3. The change is committed and pushed (never amended, rebased or force pushed). The first time, a pull request opens; after that, each day's change is added to the same pull request while it is open. Its description lists every finding in it, with source links and who confirmed each change.
4. The reviewer is asked to review only when the pull request changed since they were last asked. A day with nothing new changes nothing.

After the pull request is merged, the next day's change starts a new one.

## Seeing what it found

- **The agent's page** on the console shows its live log. Each new finding is one line with its status, kind, the file and section it affects, a summary and its link. Each scan ends with a line counting the messages and calls read and the findings recorded. Questions asked and decisions recorded are logged too.
- **The feedback channel** holds the question threads and the decisions.
- **The pull request** on the project's repository lists everything applied to the record so far.
- **The project's page** shows who the steward is and its settings.

## Still to come

| Step | What it adds |
|---|---|
| Approval and merge | An approved pull request is left alone; after the merge, a new one starts. |

Start a new project in **Record only** for a few working days and check the findings before turning it **On**.
