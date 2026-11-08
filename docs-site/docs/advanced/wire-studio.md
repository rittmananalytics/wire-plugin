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
| Release selector | At the top of the left-hand menu: every release in the engagement. **Console** opens the selected release's overview, and the Wire CLI view starts on it. The choice is remembered in your browser. Greyed out in a repository with no releases. |
| Theme | At the bottom of the left-hand menu: **System** (the default, following your operating system), **Light** or **Dark**. Remembered in your browser. The menu, the release views and the Wire CLI view all use it. |
| Add Files to release | The **+** at the left of the Wire CLI box. It opens your computer's own file picker, then its save dialog, starting in the release's folder. Pick any file; it is copied to the place you choose, which must be inside the repository (not `.git/`, and not a release's `status.md` or `execution_log.md`). Somewhere else reopens the save dialog with the reason. Works on macOS, and on Linux with `zenity` installed. |
| Overview | The artifact graph for the release type, with any profile applied, each artifact's generate, validate and review state, the runnable set (what can start now, in order, within the release's lane budget), and the AI spend the execution log records for the release. For a release built from tickets, each step also shows how many slices are done and how many are in progress. |
| Tickets | Only for a release built from tickets. One row per slice of the release and one column per Wire step, each cell showing its state and the tickets covering it; how far each step has got across the slices; every ticket with whether it can start, what it waits on or why it is blocked, and how many of its results are recorded; the tracker's missing "blocked by" links; and a `/wire:work` directive for each ticket. Inside each ticket: its progress, the files its branch changed and its activity (below). On the overview, the runnable set gives way to the tickets that can start. |
| Decision inbox | Parked decisions, review gates and advisory gates waiting on you, each with a directive you can edit and then copy or run |
| Lanes | Each lane's state file and when it was last written. A lane not marked complete with no write for 30 minutes is shown as stalled, with a re-dispatch directive. |
| Record and rulings | Rulings from `decisions.md`, the tickets worked inside the release (iterations), and the execution log, newest first |
| Documents | Any artifact file, with Markdown tables and Mermaid diagrams rendered |
| Session (Wire CLI, experimental) | The Wire CLI's session in the page (below). Local Studio only. |

For a release built from tickets, Studio reads the ticket map and the ticket records through the same script the Wire session uses (`scripts/ticket_delivery.py`), so its slice table and its list of what can start match `/wire:status`. A merged ticket whose work is not yet in the release record appears in the decision inbox with `/wire:status-sync`.

### Progress inside a ticket

Select a ticket on the Tickets page, or open `#/r/<release>/tickets/<ticket>`, to see three things:

| Part | What it shows |
|---|---|
| Progress | For each Wire step the ticket covers, its generate, validate and review, each marked **recorded** (the ticket record holds the result), **found, not recorded** (the ticket's log or the files its branch changed show it, the record does not) or **not done** |
| Files changed | The files the ticket's branch changed, grouped as dbt models, tests and docs, seeds, semantic layer, Wire record and design model, each opening in Studio. A merged branch is still found after it is deleted. |
| Activity | The commands and edits run for the ticket, from its own log, or from the release log rows that name it when work was done before the import |

A result is found, not recorded, when a step was done by a direct edit, or before the release was built from tickets, so nothing wrote it to the ticket record. For a merged ticket, Studio puts it in the decision inbox with `/wire:status-sync`, which proposes the results with their evidence and writes them only when you confirm. Files only show that a step's generate was done; validate and review results come from the log or the record.

### Optional steps

Business rules, the semantic layer and some other steps are optional in some release types. Studio shows an optional step as in scope when the release profile switches it on, when you ask for it, when the record already shows progress on it, or when a ticket covers it. Otherwise it shows as not applicable. Before 4.2.6, generated business rules, or a semantic layer that tickets covered, could show as not applicable.

Studio works out the runnable set with the same rule `/wire:start`, `/wire:delegate` and the release-director skill use (`specs/utils/runnable_set.md`), and reads release types and the command registry from the Wire plugin it ships with. So Studio cannot show a different answer from the one the commands act on.

## The current version

These screenshots are of Studio 4.2.6 running against the sample releases in Wire's own test suite.

![Wire Studio release overview: the artifact graph for a full_platform release grouped by phase, with complete, runnable, waiting and blocked artifacts, and the runnable set with a directive box](/img/wire-studio/studio-overview.png)

![Wire Studio overview of a release built from tickets: each step in the artifact graph shows how many slices are done and in progress, and the tickets that can start replace the runnable set](/img/wire-studio/studio-tickets-overview.png)

![Wire Studio tickets view for a release built from tickets: the slice table with each step's state and covering tickets, the ticket list with can start, waiting and blocked states and how many results each ticket has recorded](/img/wire-studio/studio-tickets.png)

![Wire Studio progress inside a ticket: a grid of generate, validate and review for each Wire step marked recorded, found but not recorded, or not done, a status-sync directive for the results found, the files the ticket's branch changed grouped by kind, and the ticket's activity](/img/wire-studio/studio-ticket-progress.png)

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

## The Session view (Wire CLI, experimental)

From 4.6.3, Studio can run the [Wire CLI](./wire-cli)'s session in the page. Open **Wire CLI** in the left-hand menu (**Console**, under it, opens the overview of the release chosen in the selector above both). It opens on one box, "What do you want to build today?": type your first command or request and press Enter (the session starts on the release chosen in the menu's release selector). Under the box are five commands to start with: the commands the release can run now, in the order `next` would take them, then any review that waits, then general ones (`status`, `next`, `plan`, `releases`, `help`) to make up five. Wire does not count which commands are used most, so the general ones are a fixed list. Clicking one runs it, as if you had typed it and pressed Enter. Once the first line is sent, the page becomes the console: the output above, the box at the bottom.

- **The model** is named in light grey at the right of the box, on the opening screen and in the console. It starts on your Wire CLI install's default, resolved as `wire` resolves it in a terminal (`WIRE_HARNESS` and `WIRE_MODEL`, the release's `budget.harness`, the engagement's `harness:` block, then the default: Claude Opus 5.5 when `ANTHROPIC_API_KEY` is set, otherwise GPT-6.1 Sol). The down arrow lists the models your keys allow: OpenAI's when `OPENAI_API_KEY` is set, Claude's when `ANTHROPIC_API_KEY` is set (on the claude harness when `claude` is installed, otherwise on codex's Anthropic provider). A model you pick is kept with the conversation and used again when you open it from the list. Changing harness or provider starts a new conversation with the agent; the transcript stays. The model can be changed between commands, not while one runs.
- **The box at the bottom** takes what you would type in the CLI: a Wire command (`dbt-validate`), plain direction ("get the semantic layer validated"), `/approve`, `/park`, `/rule`, `status` or `next`. Enter sends; Shift+Enter starts a new line.
- **The output** appears above the box as the session runs: replies as they are written, a dimmed line for each command or edit the agent starts, and `Ran:` at the end. The page follows the output while you are at the bottom; scroll up to read back, and **Jump to latest** brings you down again.
- **The bar above the box** shows the status line (release, approvals, parked decisions, claim, context), the running command and how long it has run, the agent's last command or edit, and each lane during `wire run`.
- **Questions become buttons.** When a running command asks you to choose, its numbered options appear as buttons; you can also type your own answer. A run plan's go / adjust / cancel appears the same way.
- **New session** is the blue icon button beside **Wire CLI** in the menu; it goes back to the opening box. Changing the release selector in the menu while a session runs sends `use <release>` to it; the selector follows the session's release.
- **Sessions are kept.** While the Wire CLI view is open, the menu lists the last ten sessions for the repository, under **Sessions**. Opening one shows its transcript and carries on the same conversation with the agent. **Rename** names it, **Export (.md)** saves the transcript as Markdown, **Stop** ends the session, and × deletes a stopped conversation. They are stored in the client repository under `.wire/local/sessions/`, which is not committed.

The session is the Wire CLI's, running on your machine with your harness, model and keys (`~/.wire/secrets.env`). It writes the record as a terminal session would, and if another session holds the release claim it offers join, take-over or move. Studio passes text to it and shows what comes back.

The Wire CLI ships with Studio in the Claude Code plugin (from 4.6.4), the Codex plugin and the CLI install, so there is nothing else to install. In the Claude Code plugin the steps run on Claude Code: with no API key set, they use your Claude Code sign-in and its plan limits, and the model list offers the Claude models, starting on Opus 5.5. Put `ANTHROPIC_API_KEY` in `~/.wire/secrets.env` for API billing, or `OPENAI_API_KEY` (with the Wire CLI's agent installed) for OpenAI models. With no key and neither Claude Code nor the agent installed, the view says what to install or set. Hosted Studio has no Session view.

## Why Studio never writes to the record

Under the release director model, the orchestrating session is the single writer of `status.md` and `execution_log.md`. In 3.x, several people and sessions writing those files at once corrupted rows and once discarded completed work. So Studio records nothing itself. It reads the record and hands the action to a Claude Code session, which records it as the single writer.

Studio also stays on your machine:

- It listens only on 127.0.0.1 and refuses requests addressed to any other host name.
- It serves only text files inside the repository, never `.git` or `.env`.
- Its requests that act, the one behind "Run in Claude Code" and those of the Session view, need a token issued when Studio starts and readable only by Studio's own page. Another web page cannot make your browser open a session or read one.

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
- **Files changed needs git history.** Studio lists a ticket's files from the local clone: an open branch must be fetched, and a merged one is found from the merge commit that names it. A squash merge names no branch, so its files show only while the branch is still in the clone.
