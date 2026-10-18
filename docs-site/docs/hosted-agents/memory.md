---
sidebar_position: 8
title: Memory
---

# Memory

:::note[Rittman Analytics only]
Hosted agents are a Rittman Analytics-only feature. Rittman Analytics runs them for its own engagements; they are not part of the Wire plugin or extension, and cannot be installed or run outside Rittman Analytics. The rest of Wire works the same without them.
:::

Hosted agents keep what they learn from one ticket to the next. Memory is a set of short Markdown files, grouped into stores. An agent reads and writes them with its ordinary file tools; every change is kept as a version. The design follows Claude Managed Agents memory stores, so the agents could move to Anthropic's stores later without changing how they use memory.

Task state does not go in memory. Progress, ticket status and next steps stay in Wire's release record and in Jira. Memory holds what will still be true and useful a month from now.

## Stores

| Store | Holds | Agents |
|---|---|---|
| Project | What agents have learned on one Jira project: the client's conventions, data quirks, why choices were made, fixes that worked, open problems | Read and write, for agents in a pod covering the project or working one of its tickets |
| Agent | One agent's own lessons on tools, Wire commands and its role, with no client detail | Read and write, that agent only |
| Practice | Rittman Analytics patterns and house conventions | Read only |
| Toolset | Lessons true for every client on one toolset | Read only |

A project store has fixed folders: `/conventions/`, `/data/`, `/rationale/`, `/solutions/`, `/issues/`, and each agent's own notes under `/agents/<name>/`. Writing to its own notes folder keeps agents in a pod from overwriting each other.

## Memory and standing decisions

A project's [standing decisions](./governance.md) are people's rulings, and the agents must follow them. Memory is not. `/rationale/` records why a choice was made and points to the standing decision or ruling behind it, where there is one. Memory never overrides a standing decision or the project's governance template, and an agent never treats a memory note as a standing decision.

## During a run

1. When an agent starts a ticket, it gets a copy of the project store and its own store, plus the read-only stores, in a folder for that run.
2. Its instructions list each store, the writing rules, and an index of every file with its first line. It reads the files it needs.
3. It writes a lesson when it finds one: the fact, the evidence and the ticket key. Changes are saved within about 15 seconds.
4. If two agents change the same file at once, the saved copy wins and the other agent's text is kept aside for a person, or a later automated merge, to fold in.
5. At the end of a run that hit a QA failure, needed a ruling, worked past an error or took more than one attempt, and wrote nothing to memory, the agent is asked once to record a lesson or say there is nothing to record. Routine runs are not asked.
6. The full record of the run is kept for later review, with secrets removed.

## Controls

Agents can read memory but cannot save to it directly. Every change goes through the agents console, which checks:

- the agent is a hosted agent and, for a project store, is in a pod covering the project or has the ticket it is working assigned to it in Jira (the console checks Jira itself; what the agent reports about its own work does not count); for an agent store, owns it;
- the file is under a project store's fixed folders, and under `/agents/` only in the agent's own folder;
- the file holds no secrets (keys, tokens, passwords) and no text that reads as instructions to an agent;
- an agent store names no client: no project key, client name, repository, dataset or table. Client detail goes in the project store, so it never reaches another client's work.

A refused change is undone in the agent's folder, with the reason beside it. The practice and toolset stores are read-only to agents.

Run records are kept for a set number of days, shorter where a client's contract asks, and a project's records are deleted when the engagement closes.

## Viewing memory

The console's Memory page lists the stores and shows the files in each. Escalation contacts and console admins can delete, restore and redact memories there (see below).

## Deleting a memory

If an agent remembered something wrongly, delete the memory on the console's Memory page. Open the store, open the file and choose Delete. The confirmation shows the path and the first lines, and you can add a reason. The memory leaves the store at once. The deletion is kept as a version with who deleted it, when and why.

Agents stop seeing a deleted memory within about 15 seconds, including runs already in progress. A run that changed the file after it was deleted loses that change. A run that starts later does not get the file.

- **Restore.** Each store lists memories deleted in the last 30 days under Recently deleted. Restore brings one back as a new version. If another memory now exists at the same path, the restore is refused and nothing changes.
- **Redact.** For text that must not be kept, such as a secret or personal data, delete the memory first, then choose Redact all versions on it under Recently deleted. This removes the text of every stored version of that memory for good. It cannot be undone, and the memory can no longer be restored.
- **Who can do this.** Console admins on any store. On a project's store, also the people named as escalation contacts for that project. Agent stores and shared stores: admins only.

## Not yet

- Automated review and merging of memory ("dreaming"), and promotion of lessons from a project to the practice store, through the project's governance template.
- Editing memory and its versions in the console.
- Search across past run records.

When one virtual machine works tickets for two clients at once, each run's memory folder is hidden from the others but not locked. Until runs are separated further, keep each agent to one client's tickets at a time where that matters.
