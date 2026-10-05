---
sidebar_position: 6
title: Wire Studio
---

# Wire Studio

Under the [release director model](./release-director), you direct a release in plain English and agents run the Wire commands. What you need to see is what is waiting on you, what can run next and what the lanes are doing. Today that means reading `status.md`, `decisions.md`, the execution log and each lane's state file. Wire Studio puts all of it on one page in your browser. This page covers what Studio shows, how to start it, how its "Run in Claude Code" button works, and why Studio never writes to the release record.

Studio 4.x runs on your own machine against a client repository you have checked out. It is a console for the release director, not a hosted service. The hosted version, for supervising several releases and persistent agents, is part of the Wire 5.0 plan.

## What Studio shows

| View | What it shows |
|---|---|
| Releases | Every release in the engagement: release type, artifacts complete, decisions waiting on you, live lanes. A release whose `status.md` cannot be read is flagged, not hidden. |
| Overview | The artifact graph for the release type, with any profile applied, each artifact's generate, validate and review state, the runnable set (what can start now, in order, within the release's lane budget), and the AI spend the execution log records for the release |
| Decision inbox | Parked decisions, review gates and advisory gates waiting on you, each with a directive you can edit and then copy or run |
| Lanes | Each lane's state file and when it was last written. A lane not marked complete with no write for 30 minutes is shown as stalled, with a re-dispatch directive. |
| Record and rulings | Rulings from `decisions.md`, the tickets worked inside the release (iterations), and the execution log, newest first |
| Documents | Any artifact file, with Markdown tables and Mermaid diagrams rendered |

Studio works out the runnable set with the same rule `/wire:start`, `/wire:delegate` and the release-director skill use (`specs/utils/runnable_set.md`), and reads release types and the command registry from the Wire plugin it ships with. So Studio cannot show a different answer from the one the commands act on.

## The current version

These screenshots are of Studio 4.x running against the sample release in Wire's own test suite.

![Wire Studio release overview: the artifact graph for a full_platform release grouped by phase, with complete, runnable, waiting and blocked artifacts, and the runnable set with a directive box](/img/wire-studio/studio-overview.png)

![Wire Studio decision inbox: a parked ruling on revenue currency and a dbt review gate, with an editable directive and the Run in Claude Code and Copy buttons](/img/wire-studio/studio-decision-inbox.png)

![Wire Studio lanes view: three lane state files, one complete, one running and one stalled after 31 minutes without a write, with a re-dispatch directive](/img/wire-studio/studio-lanes.png)

## Where Studio is heading

The design below shows the direction for the director console. 4.1.0 shows the AI spend the execution log records for each release; the design adds spend against a budget and per lane, a richer run-plan view, and Go, Adjust and Park buttons that record your decision directly. These are not in 4.x yet: recording decisions from Studio needs the request queue described under [Sending commands to Wire](#sending-commands-to-wire).

![Design for the Wire Studio release overview, with spend against budget, the artifact graph and the runnable set as one run plan](/img/wire-studio/design-release-overview.png)

![Design for the Wire Studio decision inbox, with a run plan, a review gate, a parked decision and a precondition override, and Go, Adjust and Park buttons](/img/wire-studio/design-decision-inbox.png)

![Design for the Wire Studio lanes view, with each lane's command, owned tree, elapsed time and spend against its budget](/img/wire-studio/design-lanes.png)

## Starting Studio

Studio needs Python 3.10 or later and PyYAML, which Wire's own tests already use. If PyYAML is missing, Studio says so and gives the install command (`python3 -m pip install pyyaml`). There is nothing else to install and no build step.

In a Claude Code session in the client repository, run:

```text
/wire-studio
```

That starts Studio in the background for that repository and opens it in your browser. `/wire-studio stop`, `restart` and `status` do what they say; see [the Wire mod](./wire-mod) for the details. `/wire-studio` comes with the Wire mod in 4.1.0 and answers at once, without a model turn.

To start Studio by hand, from a checkout of the Wire repository:

```bash
python3 wire/studio/studio.py --repo ~/github/acme-delivery
```

From the installed plugin, the same script sits at `studio/studio.py` in the plugin folder.

Started by hand, Studio opens http://127.0.0.1:4800 in your browser and runs until you press Ctrl+C. It reads the files on disk, so it shows whatever branch the repository has checked out, and it refreshes every 15 seconds.

| Option | What it does |
|---|---|
| `--repo <path>` | The client repository holding `.wire/`. Default: the current directory. |
| `--port <n>` | Port to serve on. Default: 4800. |
| `--launch auto\|terminal\|linux\|print` | How "Run in Claude Code" opens a session (below). Default: macOS Terminal on a Mac, `print` elsewhere. |
| `--no-browser` | Do not open a browser tab. |
| `--framework <path>` | Use a different Wire framework folder. |

The browser loads Google Fonts, marked, DOMPurify and Mermaid from public CDNs. Without a network connection, documents show as plain text.

## Run in Claude Code

Every directive in Studio is an editable box with two buttons. This applies to the run plan, a review gate, a ruling and a lane re-dispatch.

- **Copy** puts the directive on your clipboard, to paste into the Claude Code session that holds the release claim.
- **Run in Claude Code** opens a new terminal in the client repository running `claude "<directive>"`.

The second is an ordinary interactive session that you started. Studio tags it with `WIRE_INVOKED_BY=studio`, so from 4.1.0 the [Wire mod](./wire-mod) records the commands you run there as `invoked_by: studio`, and Studio's use can be measured. It runs the real Wire commands, shows its run plan and waits for your go. If another session already holds the release claim, it offers to join, take over or move, as it would if you had typed the directive yourself. The record it writes is the same as a typed run.

Studio refuses to launch a directive that still contains a placeholder such as `<your decision>` or `<why>`, so you have to write the ruling before it can run. In `print` mode, or when `claude` is not on your PATH, Studio shows the exact command to run in a terminal instead.

## Why Studio never writes to the record

Under the release director model, the orchestrating session is the single writer of `status.md` and `execution_log.md`. In 3.x, several people and sessions writing those files at once corrupted rows and once discarded completed work. So Studio records nothing itself. It reads the record and hands the action to a Claude Code session, which records it as the single writer.

Studio also stays on your machine:

- It listens only on 127.0.0.1 and refuses requests addressed to any other host name.
- It serves only text files inside the repository, never `.git` or `.env`.
- Its one write request, the one behind "Run in Claude Code", needs a token issued when Studio starts and readable only by Studio's own page. Another web page cannot make your browser open a session.

## Sending commands to Wire

Studio 4.x is stage 1 of three:

| Stage | What it adds | Status |
|---|---|---|
| 1. Launch | "Run in Claude Code" opens a session with the directive typed | In 4.x |
| 2. Request queue | Studio records your decision in its own request file. The orchestrating session picks it up, records it and carries on. This is what the Go, Adjust and Park buttons in the design need. | Planned. Needs a change to the director operating model in the process registry, alongside the 4.1 Wire mod hooks. |
| 3. Headless orchestrator | When no session holds the claim, Studio starts one in the background to work the queue within the release budget | Planned for the Wire 5.0 hosted-agent work |

## Limits in 4.x

- **Stall detection uses file times.** A fresh `git clone` or `pull` resets them, so a stall flag is only reliable on the machine where the lanes are running.
- **Older status files.** Studio reads artifact states from the front matter, and from a YAML block under `## Artifacts` or `## Artifact Status` in older 3.x files. A `status.md` with no front matter, or with front matter that is not valid YAML, is shown as unreadable. Wire's own commands have the same problem with those files, so fix them rather than work around them.
- **Launching on Linux** uses `x-terminal-emulator` and has not yet been tried on a Linux desktop.
- **Gemini CLI.** "Run in Claude Code" opens Claude Code only.
