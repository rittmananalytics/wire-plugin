# Wire Studio 4.x

A local console for the release director that never writes to the release record. It reads a client repository's `.wire/` record and the Wire framework's release-type graph, and shows:

| View | What it shows |
|---|---|
| Releases | Every release in the engagement: type, artifacts complete, decisions waiting, live lanes. Flags pre-3.4 layouts and records that cannot be read. |
| Overview | The artifact graph for the release type and profile, each artifact's state and generate/validate/review steps, and the runnable set within `budget.lanes_max`. |
| Tickets | Only for a release built from tickets (`delivery: tickets`, 4.2.0). The slice table (one row per slice, one column per Wire step, each cell's state and tickets), each step's progress across slices, every ticket with what it waits on or why it is blocked, the tracker link check, and a `/wire:work <release> <ticket>` directive per ticket. A merged ticket whose log rows are not yet in the release record goes to the decision inbox with `/wire:status-sync`. |
| Decision inbox | Parked decisions, review gates and advisory gates waiting on the director, each with an editable directive to copy or to run in Claude Code. |
| Lanes | Each lane's state file, last write and state. A lane not marked complete with no write for 30 minutes is shown as stalled. |
| Record and rulings | Rulings from `decisions.md`, iterations, and the execution log, newest first. |
| Documents | Any artifact file, with Markdown and Mermaid rendered. |

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

Recording decisions from Studio without opening a session needs a request queue the orchestrating session reads (stage 2). That is a change to the director operating model spec, so it goes through the process registry first.

## How it stays correct

- **Same rule as the commands.** `wire_studio/runnable.py` implements `specs/utils/runnable_set.md`. `wire/tests/studio/validate_studio.py` runs every case in the core runnable-set fixture through it and compares the result with the core test's expected output.
- **No copy of the method.** Studio reads release types, the command registry and `auto_validate` flags from the framework it ships with, in either layout (repository checkout or built plugin). The 3.x Studio bundled its own copy of the specs, which drifted.
- **Same rules for tickets.** For a release built from tickets, Studio imports `scripts/ticket_delivery.py` from the framework it ships with, the script the Wire session uses, rather than keeping its own copy. The test runs the core ticket-delivery fixtures through Studio and compares ticket states, waits and the tracker link check with the core test's expected output. A framework older than 4.2.0 has no script, and Studio says so.
- **Local, and no writes to the repository.** Binds to 127.0.0.1, refuses requests whose Host header is not this machine, answers GET and HEAD plus the one token-protected launch endpoint, and serves files only from inside the repository (not `.git`, not `.env`, text files under 2 MB).

## Layout

```text
studio/
├── studio.py                 launcher
└── wire_studio/
    ├── framework.py          release types, command registry, auto_validate flags
    ├── runnable.py           runnable set (specs/utils/runnable_set.md)
    ├── record.py             reads .wire/: status, log, decisions, lanes, iterations; builds the inbox
    ├── tickets.py            releases built from tickets, through scripts/ticket_delivery.py
    ├── launcher.py           opens claude "<directive>" in a new terminal (stage 1)
    ├── server.py             HTTP server (standard library)
    └── static/               index.html, app.js, app.css (no build step)
```
