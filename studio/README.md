# Wire Studio 4.x

A local console for the release director that never writes to the release record. It reads a client repository's `.wire/` record and the Wire framework's release-type graph, and shows:

| View | What it shows |
|---|---|
| Release selector | At the top of the menu: every release in the engagement. **Console** opens the selected release's overview (there is no page listing the releases); the Wire CLI view starts on it and sends `use <release>` when it changes. Kept per browser (`localStorage`); greyed out with no releases. |
| Theme | At the bottom of the menu: System (default), Light or Dark (`static/theme.js`, loaded in the page head; sets `data-theme` on `<html>`, kept in `localStorage`). The menu takes the page's colours, with a `#C0C0C0` line between them. |
| Add Files to release | The `+` at the left of the Wire CLI box (opening screen and console). Opens the operating system's file picker, then its save dialog starting in the release's folder, on the machine Studio runs on (AppleScript on macOS, `zenity` on Linux; `wire_studio/addfile.py`, `POST /api/files/add`, token and Origin checked). Any file can be picked; the copy goes only inside the repository, never into `.git/` or onto a release's `status.md` or `execution_log.md`; a refused place reopens the save dialog with the reason. The one place Studio writes to the repository, and only a file the person chose. Local mode only. |
| Overview | The artifact graph for the release type and profile, each artifact's state and generate/validate/review steps, and the runnable set within `budget.lanes_max`. An optional artifact is shown in scope when it was requested, the record shows progress on it, or a ticket covers it (4.2.6). For a release built from tickets, each step also shows how many slices are done and in progress. |
| Tickets | Only for a release built from tickets (`delivery: tickets`, 4.2.0). The slice table (one row per slice, one column per Wire step, each cell's state and tickets), each step's progress across slices, every ticket with what it waits on or why it is blocked, the tracker link check, and a `/wire:work <release> <ticket>` directive per ticket. A merged ticket whose log rows are not yet in the release record goes to the decision inbox with `/wire:status-sync`. Inside each ticket (4.2.6): a progress grid (each step's generate, validate and review, marked recorded, found but not recorded, or not done), the files its branch changed, grouped, each opening in Studio, and its activity. A merged ticket with results found but not recorded goes to the inbox with `/wire:status-sync`. `#/r/<release>/tickets/<ticket>` opens one ticket. |
| Decision inbox | Parked decisions, review gates and advisory gates waiting on the director, each with an editable directive to copy or to run in Claude Code. |
| Lanes | Each lane's state file, last write and state. A lane not marked complete with no write for 30 minutes is shown as stalled. Session handoffs the Wire mod wrote (`lanes/handoff-<session>.md`, 4.5.0) are listed apart, never as lanes; the warehouse spend ledger (`lanes/_spend.jsonl`) is summed on the Overview. |
| Record and rulings | Rulings from `decisions.md`, iterations, and the execution log, newest first. |
| Documents | Any artifact file, with Markdown and Mermaid rendered. |
| Session (Wire CLI, experimental) | The Wire CLI's session in the page, for one release at a time. It opens on one centred box ("What do you want to build today?"); the first line sent starts the session and the page becomes the console. Type Wire commands or plain direction in the box at the bottom; the output scrolls above it as the session runs, with the status line, the running command and the lanes in a bar above the box. A question from a running command, or the run plan's go / adjust / cancel, shows as buttons. Conversations are kept and can be opened again (the director conversation carries on), renamed, exported as Markdown or deleted. Local mode only, and only where the Wire CLI is installed beside Studio. |

## Run it

```bash
python3 wire/studio/studio.py --repo ~/github/<client>-delivery
```

Then open http://127.0.0.1:4800. Options: `--port`, `--no-browser`, `--framework <path>`, `--launch auto|terminal|linux|print`.

From an installed plugin, the same script sits at `<plugin root>/studio/studio.py` and uses the plugin's own release types and command registry.

Needs Python 3.10 or later and PyYAML (already a Wire test dependency). No other install. The browser loads Google Fonts, `marked`, `DOMPurify` and `mermaid` from public CDNs; without a network connection documents show as plain text.

## Why Studio writes nothing to the record

The orchestrating session is the single writer of `status.md` and `execution_log.md` (`specs/utils/director_operating_model.md`, rule 6). A second writer is how concurrent writes corrupted rows and discarded work in 3.x. So Studio never records a decision. Each action gives a directive, a real Wire command or a ruling in the operating model's words, that the director can edit and then:

- **Copy** into the session that holds the release claim, or
- **Run in Claude Code**: Studio opens a new terminal in the client repository running `claude "<directive>"`. That is an ordinary interactive session started by the director: it runs the real Wire commands, shows its run plan and waits for go, and if another session holds the claim it offers join, take-over or move. The record on disk stays identical to a typed run.

Studio refuses to launch a directive that still holds a placeholder such as `<your decision>`. Launch modes: `terminal` (macOS Terminal, the default on macOS), `linux` (`x-terminal-emulator`, not yet tested on a Linux desktop) and `print` (show the command instead; the default elsewhere, and what Studio does when `claude` is not on PATH).

The launch endpoint (`POST /api/launch`) needs a token issued when Studio starts, served only inside Studio's own page, and an `Origin` header naming this server, so another web page cannot make the browser open a session.

**The Session view** runs the same session as `wire` in a terminal, inside Studio's process: Studio loads the CLI's session code (`<framework root>/cli/wire_cli/web_session.py`, through `wire_studio/session_bridge.py`), passes each line typed in the page to it, and sends its output back as events. Studio itself still writes nothing; the session writes the record exactly as a terminal session would, takes the release claim when it runs `wire run`, and meets another session's claim with the same join, take-over or move. Conversations are kept in the client repository at `.wire/local/sessions/<id>.jsonl` (the events) and `<id>.json` (title, release, the director conversation's thread, times); `.wire/local/` is git-ignored. The page names the model the next command runs on and lists the models the keys in `~/.wire/secrets.env` allow (`Sessions.models()`); the default is the CLI's own resolution (`Sessions.default_model()`), a pick is stored in the conversation's `.json` as `model` and applied when it is opened again (`POST /api/session/<id>/model`, or `model` on `start` from the opening box). The menu calls the view **Wire CLI** and the release views **Console**; the release selector above both is shared. Under the opening box are five commands (`opening_commands` in `web_session.py`, from `wire_gate.actions`: the release's runnable commands in the runnable set's order, then the reviews that wait, then the fixed `GENERAL_OPENING` list); `/api/sessions?release=<name>` returns them as `opening`; a click sends the command as the first line. New session is an icon button (Lucide `message-square-dot`) beside the Wire CLI link, and on the Wire CLI view the menu lists the last ten sessions, as it lists Overview and the other release views on the Console. Every session endpoint, GET included, needs the page's token; the POSTs also need the `Origin` header. The Claude Code plugin ships Studio without the CLI, so there the view says the CLI is not installed. Hosted mode has no sessions.

Recording decisions from Studio without opening a session needs a request queue the orchestrating session reads (stage 2). That is a change to the director operating model spec, so it goes through the process registry first.

## How it stays correct

- **Same rule as the commands.** `wire_studio/runnable.py` implements `specs/utils/runnable_set.md`. `wire/tests/studio/validate_studio.py` runs every case in the core runnable-set fixture through it and compares the result with the core test's expected output.
- **No copy of the method.** Studio reads release types, the command registry and `auto_validate` flags from the framework it ships with, in either layout (repository checkout or built plugin). The 3.x Studio bundled its own copy of the specs, which drifted.
- **Same rules for tickets.** For a release built from tickets, Studio imports `scripts/ticket_delivery.py` from the framework it ships with, the script the Wire session uses, rather than keeping its own copy. The test runs the core ticket-delivery fixtures through Studio and compares ticket states, waits and the tracker link check with the core test's expected output. A framework older than 4.2.0 has no script, and Studio says so.
- **Local, and no writes to the repository.** Binds to 127.0.0.1, refuses requests whose Host header is not this machine, answers GET and HEAD plus the token-protected launch and session endpoints (the session, not Studio, writes the record), and serves files only from inside the repository (not `.git`, not `.env`, text files under 2 MB).

## Hosted mode

`python3 studio/studio.py --hosted` serves the same views, read only, for releases read from GitHub repositories, for a site that puts its own sign-in in front of it (wire#335). Local mode is unchanged.

| | Local mode | Hosted mode |
|---|---|---|
| Record read from | A clone on this machine (`--repo`) | A GitHub repository named on each request (`X-Wire-Repo: <owner>/<repo>`), set by the site serving the page, never by the browser |
| Releases | `.wire/releases/` (and pre-3.4 folders) in the clone | `.wire/releases/` on the default branch, the branches the request names (`X-Wire-Branches`), and `feature/*` and `release/*` branches. A release on several branches is shown from the one whose `status.md` `last_updated` is latest (a tie goes to a named branch, then a discovered one, then the default). Most recent first. |
| Actions | Directives to copy, Run in Claude Code | None. No `/api/launch`: every POST, PUT, PATCH and DELETE gets 405. The page shows no directive, Copy or Run in Claude Code, and no lanes. |
| Binds to | 127.0.0.1, Host header checked | 0.0.0.0 on `PORT`; access is the job of the platform in front (a private service that only the signed-in site may call) |

How it reads a repository: `wire_studio/hosted.py`. A blobless bare clone per repository (every branch's history and trees; file contents fetched when read) and a detached worktree per commit shown, so the same readers (`record.py`, `runnable.py`, `tickets.py`) run on a real checkout and a ticket's changed files still come from git. The read-only token reaches git only through `GIT_CONFIG_*` environment variables. Branch heads are cached for 30 seconds and loaded releases for 60 seconds, keyed by repository, branch and commit.

Settings, from the environment: `GITHUB_TOKEN` (read-only Contents and Metadata), `PORT` (default 8080), `STUDIO_CACHE_DIR` (default a temporary folder), `STUDIO_ALLOWED_OWNERS` (comma-separated GitHub organisations; empty allows any the token can read). The page's requests go to the base path in `X-Wire-Base`, so a site can serve Studio under its own path; `X-Wire-Back` adds a link back to that site.

The repository is reached through a client with four methods (`refs`, `list_releases`, `read`, `checkout`), so `wire/tests/studio/validate_studio_hosted.py` runs Studio's fixtures through the hosted loader with a fake client and checks they give the same result as local mode, then runs the real git client against a local repository.

## Layout

```text
studio/
├── studio.py                 launcher
└── wire_studio/
    ├── framework.py          release types, command registry, auto_validate flags
    ├── runnable.py           runnable set (specs/utils/runnable_set.md)
    ├── record.py             reads .wire/: status, log, decisions, lanes, iterations; builds the inbox
    ├── tickets.py            releases built from tickets, through scripts/ticket_delivery.py
    ├── addfile.py            Add Files to release: the OS file dialogs, copy inside the repository only
    ├── launcher.py           opens claude "<directive>" in a new terminal (stage 1)
    ├── session_bridge.py     the Session view: loads the Wire CLI's session beside Studio
    ├── hosted.py             hosted mode: releases read from GitHub, read only, no launch
    ├── server.py             HTTP server (standard library)
    └── static/               index.html, app.js, session.js, app.css (no build step)
```
