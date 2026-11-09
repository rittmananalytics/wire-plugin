"""`wire` with no arguments: an interactive session.

The banner, the engagement and its releases, then a prompt. Lines are the
same commands the command line takes, with an active release so `status`
and `run` need no argument, session settings for the harness and model, and
plain text sent to the harness as a prompt (`exec`) in the repository.

    wire> use 02-data-foundation
    wire> status
    wire> plan                      the run plan only (run --dry-run)
    wire> run --yes --once
    wire> dbt-validate              a typed Wire command on the active release
    wire> gate dbt-review
    wire> harness codex | model <m> | provider <p> | settings
    wire> get the semantic layer validated      (direction: a plan, then go)
    wire> help | releases | quit
"""

from __future__ import annotations

import os
import shlex
import sys
from pathlib import Path

from . import __version__
from .banner import banner

HISTORY = Path.home() / ".wire" / "cli_history"
BUILTINS = ("help", "?", "releases", "use", "status", "run", "plan", "gate", "exec", "harness", "model",
            "provider", "sandbox", "settings", "clear", "quit", "exit", "mcp", "doctor", "persona", "repos")
MCP_ACTIONS = ("list", "add", "remove", "login", "check")
PERSONA_ACTIONS = ("show", "list", "set", "clear")
REPOS_ACTIONS = ("list", "refresh", "find")  # add and remove change context.md: /wire:utils-repos asks first


def releases_of(repo: Path) -> list:
    """Release folders, most recently changed status.md first."""
    rel_dir = repo / ".wire" / "releases"
    if not rel_dir.is_dir():
        return []
    found = []
    for p in rel_dir.iterdir():
        s = p / "status.md"
        if p.is_dir() and s.is_file():
            found.append((s.stat().st_mtime, p.name))
    return [name for _m, name in sorted(found, reverse=True)]


def engagement_name(repo: Path) -> str:
    p = repo / ".wire" / "engagement" / "context.md"
    if not p.is_file():
        return ""
    for line in p.read_text(encoding="utf-8", errors="replace").split("\n")[:40]:
        if line.startswith("engagement_name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


HELP = """Commands (the active release fills in <release> when it is omitted):
  status [release]            states, runnable set, claim, next action
  plan [release]              the run plan without dispatching
  run [release] [--yes] [--once] [--take-over] [--request <artifact>]
  gate <command> [release]    the precondition gate's answer
  <wire-command> [release] [args]   a typed Wire command, e.g. dbt-validate
  <plain text>                direction to the release director mode: the harness
                              resolves it into Wire commands, you see the plan, say go
  exec <text>                 a raw prompt to the harness, in this repository
  /approve <artifact> [--final] [--as internal|client] [--evidence <url>]
                              record an approval (review_events; --final sets review: approved)
  /park <artifact> "<question>" [--awaiting <who>]   park a decision in status.md
  /rule <PD-n | artifact.depends_on.dep> <ruling> [-- <reason>]
                              record a ruling in decisions.md (a parked decision is cleared)
  new                         start a new conversation (direction remembers the last turns)
  next                        run the next action (an empty line shows it)
  /handoff                    write a handoff for the next session to the release's lanes folder
  studio                      open Wire Studio for this repository (127.0.0.1:4800)
  mcp list | add <server> [url] | remove <server> | login <server> | check [release]
                              the engagement's MCP servers (.wire/engagement/mcp_servers.yml)
  doctor                      what this machine can run: harnesses, keys, local model server
  persona [show | list | set <persona> [--local] | clear [--local]]
                              your persona on this engagement (the team roster, or this clone only)
  repos [list | refresh [id] | find <text> [--in <id>]]
                              the client's related repositories, read only
  use <release> | releases    choose or list releases
  harness codex|claude|fake, model <id>, provider <id>, sandbox <mode>, settings
  help, clear, quit"""


class Shell:
    def __init__(self, repo: Path, env: dict, out=print, read=None, harness=None, model=None, provider=None, sandbox=None,
                 framework=None, color=None, first=None, write=None, panel=None):
        self.repo = repo
        self.env = dict(env)
        self.env["WIRE_NO_BANNER"] = "1"
        self.out = out
        self.read = read
        self.settings = {"harness": harness, "model": model, "provider": provider, "sandbox": sandbox, "framework": framework}
        self.releases = releases_of(repo)
        self.active = self.releases[0] if self.releases else None
        self.color = color
        self.thread = None  # the director conversation, resumed turn to turn
        self.first = first  # a first line given on the command line (Studio's Run in Wire CLI)
        self.thread_input_tokens = 0  # the last director turn's prompt size: the conversation's context use
        self.context_warned = False
        self.last_band = None
        # where replies are shown as they are written (ROADMAP.md phase 2); None prints them whole
        from .stream import Stream
        self.panel = panel  # the live band at the bottom of the terminal (panel.py), or None
        if panel is not None:
            self.out = panel.print
            write = panel.write
        self.stream = Stream(write, color=bool(color), on_note=panel.note if panel else None,
                             on_lane=panel.lane if panel else None,
                             pause=panel.pause if panel else None) if write is not None else None

    # ------------------------------------------------------------ input

    def _readline(self) -> str | None:
        if self.read is not None:
            try:
                return next(self.read)
            except StopIteration:
                return None
        try:
            return input(self.prompt())
        except EOFError:
            return None
        except KeyboardInterrupt:
            self.out("")
            return ""

    def ask(self, prompt: str) -> str:
        """One answer from the person, for a running command's question."""
        if self.panel is not None and self.read is None:
            with self.panel.pause():
                return self._ask(prompt)
        return self._ask(prompt)

    def _ask(self, prompt: str) -> str:
        if self.read is not None:
            try:
                return next(self.read)
            except StopIteration:
                return ""
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            self.out("")
            return ""

    def prompt(self) -> str:
        return f"wire{(' ' + self.active) if self.active else ''}> "

    # ------------------------------------------------------------ dispatch

    def common_flags(self) -> list:
        flags = ["--repo", str(self.repo)]
        for key in ("harness", "model", "provider", "sandbox", "framework"):
            if self.settings.get(key):
                flags += [f"--{key}", self.settings[key]]
        return flags

    def _release_arg(self, words: list, position: int) -> tuple:
        """(release, remaining words) with the active release as the default."""
        if len(words) > position and not words[position].startswith("-") and words[position] in self.releases:
            return words[position], words[:position] + words[position + 1:]
        if self.active:
            return self.active, words
        return None, words

    QUIET = ("help", "?", "releases", "use", "harness", "model", "provider", "sandbox", "settings", "clear",
             "quit", "exit", "new", "/approve", "/park", "/rule", "studio", "status", "gate", "persona", "repos")

    def handle(self, line: str) -> bool:
        """One line. Returns False to quit."""
        head = line.strip().split(" ", 1)[0].lower() if line.strip() else ""
        if self.panel is None or not head or head in self.QUIET:
            return self._handle(line)
        self.panel.begin(line.strip()[:60])
        try:
            return self._handle(line)
        finally:
            self.panel.end()

    def _handle(self, line: str) -> bool:
        line = line.strip()
        if not line:
            nxt = self.next_action()
            if nxt:
                self.out(f"next: {nxt}   (type `next` to run it)")
            return True
        try:
            words = shlex.split(line)
        except ValueError as exc:
            self.out(f"could not parse that line: {exc}")
            return True
        head = words[0].lower()
        from .main import main

        if head in ("quit", "exit"):
            return False
        if head in ("help", "?"):
            self.out(HELP)
            return True
        if head == "clear":
            self.out("\x1b[2J\x1b[H" if self.color else "")
            return True
        if head == "releases":
            self.releases = releases_of(self.repo)
            for r in self.releases:
                self.out(f"  {'*' if r == self.active else ' '} {r}")
            if not self.releases:
                self.out("  no releases under .wire/releases/")
            return True
        if head == "use":
            if len(words) < 2:
                self.out("use <release>")
            elif words[1] in releases_of(self.repo):
                self.active = words[1]
                self.thread = None  # a new release starts a new conversation
                self.out(f"active release: {self.active}")
            else:
                self.out(f"no release {words[1]!r}; `releases` lists them")
            return True
        if head in ("harness", "model", "provider", "sandbox"):
            if len(words) < 2:
                self.out(f"{head}: {self.settings.get(head) or 'default'}")
            elif head == "harness" and words[1] not in ("codex", "claude", "fake"):
                self.out("harness is one of codex, claude, fake")
            else:
                self.settings[head] = words[1]
                self.out(f"{head} set to {words[1]} for this session")
            return True
        if head == "settings":
            for key in ("harness", "model", "provider", "sandbox"):
                self.out(f"  {key}: {self.settings.get(key) or 'default'}")
            return True
        if head in ("status", "plan", "run"):
            release, rest = self._release_arg(words, 1)
            if not release:
                self.out("no active release; `use <release>` first")
                return True
            argv = ["run" if head == "plan" else head, release] + rest[1:] + self.common_flags()
            if head == "plan":
                argv.append("--dry-run")
            rc = main(argv, out=self.out, env=self.env, ask=self.ask, stream=self.stream)
            if rc not in (0, 3):
                self.out(f"(exit {rc})")
            return True
        if head == "gate":
            if len(words) < 2:
                self.out("gate <command> [release]")
                return True
            release, rest = self._release_arg(words, 2)
            if not release:
                self.out("no active release; `use <release>` first")
                return True
            main(["gate", release, rest[1]] + self.common_flags(), out=self.out, env=self.env)
            return True
        if head in ("/approve", "/park", "/rule"):
            self.record(head[1:], line[len(words[0]):].strip())
            return True
        if head == "new":
            self.thread = None
            self.thread_input_tokens = 0
            self.context_warned = False
            self.out("New conversation.")
            return True
        if head == "next":
            nxt = self.next_action()
            if not nxt or not nxt.startswith("/wire:"):
                self.out(f"Nothing to run: {nxt or 'no active release'}")
                return True
            return self.handle(nxt[len("/wire:"):])
        if head == "/handoff":
            self.handoff()
            return True
        if head == "studio":
            self.studio()
            return True
        if head in ("mcp", "doctor", "persona", "repos"):
            self.engagement_tool(head, words[1:])
            return True
        if head == "exec":
            text = line[len(words[0]):].strip()
            main(["exec", text] + self.common_flags(), out=self.out, env=self.env, stream=self.stream)
            return True
        # a typed Wire command when the catalogue knows it; otherwise a prompt
        from .framework import catalogue, framework_root, normalise_command
        try:
            known = catalogue(framework_root(self.settings.get("framework")))
        except FileNotFoundError:
            known = {}
        name = normalise_command(words[0])
        from .commands import NO_RELEASE
        if name in known and name in NO_RELEASE:
            rc = main([name] + words[1:] + self.common_flags(), out=self.out, env=self.env, ask=self.ask, stream=self.stream)
            if rc:
                self.out(f"(exit {rc})")
            return True
        if name in known:
            release, rest = self._release_arg(words, 1)
            if not release:
                self.out("no active release; `use <release>` first, or give the release after the command")
                return True
            rc = main([name, release] + rest[1:] + self.common_flags(), out=self.out, env=self.env, ask=self.ask,
                      stream=self.stream)
            if rc:
                self.out(f"(exit {rc})")
            return True
        return self.direct(line)

    # ------------------------------------------------------------ engagement tools (Studio's + menu sends these)

    def engagement_tool(self, head: str, rest: list) -> None:
        """`mcp` and `doctor` run the CLI's own commands; `persona` and `repos`
        run the framework's scripts (/wire:persona, /wire:utils-repos) on this
        repository. What they write (mcp_servers.yml, the team roster) is
        written here, by the session, as a typed command would be."""
        from .main import main
        if head == "doctor":
            main(["doctor", "--repo", str(self.repo)] + self._framework_flag(), out=self.out, env=self.env)
            return
        if head == "mcp":
            action = rest[0] if rest else "list"
            if action not in MCP_ACTIONS:
                self.out("mcp list | add <server> [url] | remove <server> | login <server> | check [release]")
                return
            args = rest[1:]
            if action == "check" and not args:
                if not self.active:
                    self.out("no active release; `use <release>` first")
                    return
                args = [self.active]
            if action in ("add", "remove", "login") and not args:
                self.out(f"mcp {action} <server>")
                return
            flags = ["--repo", str(self.repo)] + self._framework_flag()
            if self.settings.get("harness"):
                flags += ["--harness", self.settings["harness"]]
            try:
                rc = main(["mcp", action] + args[:2] + flags, out=self.out, env=self.env)
            except SystemExit:
                rc = 2
            if rc and action != "check":
                self.out(f"(exit {rc})")
            return
        action = rest[0] if rest else ("show" if head == "persona" else "list")
        allowed = PERSONA_ACTIONS if head == "persona" else REPOS_ACTIONS
        if action not in allowed:
            usage = ("persona [show | list | set <persona> [--local] | clear [--local]]" if head == "persona"
                     else "repos [list | refresh [id] | find <text> [--in <id>]]  (add and remove: /wire:utils-repos)")
            self.out(usage)
            return
        self.run_script("persona" if head == "persona" else "related_repos", [action] + rest[1:])

    def _framework_flag(self) -> list:
        return ["--framework", self.settings["framework"]] if self.settings.get("framework") else []

    def run_script(self, name: str, argv: list) -> int:
        """A framework script (scripts/<name>.py) on this repository; its output
        shown as it would be in a terminal."""
        import subprocess
        from .framework import framework_root
        try:
            script = framework_root(self.settings.get("framework")) / "scripts" / f"{name}.py"
        except FileNotFoundError as exc:
            self.out(str(exc))
            return 1
        try:
            proc = subprocess.run([sys.executable, str(script), "--repo", str(self.repo), *argv], cwd=str(self.repo),
                                  capture_output=True, text=True, env=self.env, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.out(f"{name} could not be run: {exc}")
            return 1
        for text in (proc.stdout, proc.stderr):
            for ln in text.rstrip("\n").split("\n"):
                if ln:
                    self.out(ln)
        if proc.returncode:
            self.out(f"(exit {proc.returncode})")
        return proc.returncode

    # ------------------------------------------------------------ the mod's parity (ROADMAP.md phase 4)

    def _release_state(self):
        """(front matter, body) of the active release's status.md, or (None, "")."""
        if not self.active:
            return None, ""
        p = self.repo / ".wire" / "releases" / self.active / "status.md"
        if not p.is_file():
            return None, ""
        try:
            from .framework import framework_root, load_script
            data, body, _ = load_script(framework_root(self.settings.get("framework")), "status_file").front_matter(
                p.read_text(encoding="utf-8"))
            return data or {}, body or ""
        except Exception:  # noqa: BLE001 - the band never stops the session
            return None, ""

    def next_action(self) -> str | None:
        if not self.active:
            return None
        try:
            from .framework import framework_root, load_script, load_studio
            root = framework_root(self.settings.get("framework"))
            gate = load_script(root, "wire_gate")
            framework, split_fm, read_rulings, resolve = load_studio(root)
            nxt = gate.next_action(framework, str(self.repo), self.active, split_fm, read_rulings, resolve)
            return nxt.get("next") or (f"{nxt.get('kind')}: {nxt.get('reason')}" if nxt.get('kind') else nxt.get('reason'))
        except Exception:  # noqa: BLE001
            return None

    def context_percent(self) -> int | None:
        if not self.thread_input_tokens:
            return None
        try:
            window = int(self.env.get("WIRE_CONTEXT_WINDOW") or 200_000)
        except ValueError:
            window = 200_000
        return min(100, round(100 * self.thread_input_tokens / max(1, window)))

    def band(self) -> str:
        from .context import approved_count, status_line
        data, _body = self._release_state()
        claim = ((data or {}).get("agents") or {}).get("coordinator_session") if isinstance((data or {}).get("agents"), dict) else None
        parked = [d for d in ((data or {}).get("parked_decisions") or []) if isinstance(d, dict)]
        return status_line(__version__, self.active, self.releases if not self.active else [],
                           (data or {}).get("release_type") or (data or {}).get("project_type"),
                           approved_count((data or {}).get("artifacts") or {}), len(parked),
                           claim.get("user") if isinstance(claim, dict) else None, self.context_percent())

    def show_band(self) -> None:
        """The mod's status line: in the live panel, or printed when it changes; one
        note at 85 percent context."""
        text = self.band()
        if self.panel is not None:
            self.panel.set_status(text, self.next_action())
            self.last_band = text
        elif text != self.last_band:
            self.out(f"\x1b[2m{text}\x1b[0m" if self.color else text)
            self.last_band = text
        pct = self.context_percent()
        from .context import CONTEXT_WARN_PERCENT
        if pct is not None and pct >= CONTEXT_WARN_PERCENT and not self.context_warned:
            self.context_warned = True
            self.out(f"Context at {pct}%. `/handoff` writes a handoff for the next session; `new` starts a fresh "
                     "conversation (the release record carries over).")

    def studio(self) -> None:
        """Wire Studio for this repository, started in the background (the mod's /wire-studio)."""
        import subprocess
        from .framework import framework_root
        try:
            script = framework_root(self.settings.get("framework")) / "studio" / "studio.py"
        except FileNotFoundError:
            script = None
        if not script or not script.is_file():
            self.out("Wire Studio is not shipped with this CLI.")
            return
        log = self.repo / ".wire" / "local" / "studio.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        subprocess.Popen([sys.executable, str(script), "--repo", str(self.repo)], stdout=open(log, "a"),
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
        self.out("Wire Studio is starting at http://127.0.0.1:4800 (log: .wire/local/studio.log). "
                 "Its Run in Wire CLI button opens a session like this one.")

    def handoff(self) -> None:
        """The handoff template, answered by the director conversation, saved to lanes/handoff-<session>.md."""
        if not self.active:
            self.out("no active release; `use <release>` first")
            return
        from .commands import settings_for
        from .director import handoff_text
        from .orchestrator import session_id

        class A:
            pass
        a = A()
        for key, value in self.settings.items():
            setattr(a, key, value)
        settings = settings_for(self.repo, self.active, a, self.env)
        text, thread = handoff_text(self.repo, self.active, settings, a, self.env, self.thread,
                                    on_text=self.stream.text if self.stream else None)
        if self.stream:
            self.stream.end()
        if not text:
            self.out("The harness wrote no handoff.")
            return
        self.thread = thread or self.thread
        path = self.repo / ".wire" / "releases" / self.active / "lanes" / f"handoff-{session_id(self.repo)}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
        self.out(f"Handoff written to {path.relative_to(self.repo)}.")

    # ------------------------------------------------------------ the director's record

    def record(self, kind: str, args: str) -> None:
        """/approve, /park and /rule: written at once, by this session (the single writer)."""
        from . import record as rec
        from . import rulings as rl
        if not self.active:
            self.out("no active release; `use <release>` first")
            return
        rel = self.repo / ".wire" / "releases" / self.active
        status_path, decisions_path = rel / "status.md", rel / "decisions.md"
        if not status_path.is_file():
            self.out(f"no status.md for {self.active}")
            return
        who = rec.git_user(self.repo)
        now = rec.utc_now()
        status = status_path.read_text(encoding="utf-8")
        if kind == "approve":
            a = rl.parse_approve(args)
            if a.get("error"):
                self.out(a["error"])
                return
            new = rl.append_review_event(status, a["artifact"], who, now.strftime("%Y-%m-%d"), a["as"], a["evidence"], a["final"])
            if isinstance(new, dict):
                self.out(new["error"])
                return
            status_path.write_text(new, encoding="utf-8")
            self.out(f"Recorded: {a['artifact']} approved ({a['as']}) by {who}" + ("; review: approved" if a["final"] else "; review event only"))
            return
        if kind == "park":
            a = rl.parse_park(args)
            if a.get("error"):
                self.out(a["error"])
                return
            new, pid = rec.append_parked_decision(status, a["artifact"], a["question"], rec.claim_ts())
            if a["awaiting"] and pid:
                lines = new.split("\n")
                i = next(j for j, l in enumerate(lines) if l == f"  - id: {pid}")
                k = i + 1
                while k < len(lines) and lines[k].startswith("    "):
                    k += 1
                lines.insert(k, f'    awaiting: "{a["awaiting"]}"')
                new = "\n".join(lines)
            status_path.write_text(new, encoding="utf-8")
            self.out(f"Parked as {pid}: {a['question']}")
            return
        if kind == "rule":
            a = rl.parse_rule(args)
            if a.get("error"):
                self.out(a["error"])
                return
            target = a["target"]
            if target.startswith("PD-"):
                pd = rl.parked_decision(status, target)
                if not pd:
                    self.out(f"{target} is not in status.md's parked_decisions")
                    return
                applies = f"{target} ({pd.get('artifact', '?')}): {pd.get('question', '')} (decision)"
            else:
                applies = f"{target} (advisory)"
            decisions = decisions_path.read_text(encoding="utf-8") if decisions_path.is_file() else ""
            text, rid = rl.append_ruling(decisions, now.strftime("%Y-%m-%d %H:%M"), who, applies, a["ruling"], a["reason"], self.active)
            decisions_path.write_text(text, encoding="utf-8")
            if target.startswith("PD-"):
                status_path.write_text(rl.remove_parked_decision(status, target), encoding="utf-8")
            self.out(f"Ruling {rid} recorded in decisions.md" + (f"; {target} cleared from status.md" if target.startswith("PD-") else ""))
            return

    # ------------------------------------------------------------ director mode

    def direct(self, text: str) -> bool:
        """Plain text is direction: the harness resolves it into Wire commands,
        the session shows the plan and waits for go, then runs them."""
        if not self.active:
            self.out("no active release; `use <release>` first (or `exec <text>` for a raw prompt)")
            return True
        from .commands import settings_for
        from .director import command_argv, direct, run_plan_lines
        from .main import main

        class A:
            pass
        a = A()
        for key, value in self.settings.items():
            setattr(a, key, value)
        settings = settings_for(self.repo, self.active, a, self.env)
        from .director import ReplyStreamer
        streamer = ReplyStreamer(self.stream.text) if self.stream else None
        reply = direct(self.repo, self.active, text, settings, a, out=self.out, env=self.env, thread=self.thread,
                       on_text=streamer.feed if streamer else None,
                       on_activity=self.stream.activity if self.stream else None)
        if reply.get("thread_id"):
            self.thread = reply["thread_id"]
        if reply.get("input_tokens"):
            self.thread_input_tokens = reply["input_tokens"]
        if streamer and streamer.shown:
            self.stream.end()
        else:
            self.out(reply["reply"])
        commands = reply.get("commands") or []
        if not commands:
            return True
        for line in run_plan_lines(commands):
            self.out(line)
        answer = (self._readline() or "").strip().lower()
        if answer.startswith("adjust"):
            more = self._readline() if answer == "adjust" else answer[len("adjust"):].strip()
            if more:
                return self.direct(text + "\nAdjustment from the director: " + more.strip())
            return True
        if answer not in ("go", "y", "yes"):
            self.out("Cancelled; nothing ran.")
            return True
        run_env = dict(self.env)
        run_env["WIRE_INVOKED_BY"] = "orchestrator"
        self.out(f"Running: {', '.join(commands)}")
        ran = []
        for c in commands:
            name, rest = command_argv(c, self.active)
            if not name:
                continue
            from .commands import NO_RELEASE
            target = [name] if name in NO_RELEASE else [name, self.active]
            rc = main(target + rest + self.common_flags(), out=self.out, env=run_env, ask=self.ask,
                      stream=self.stream)
            ran.append(c)
            if rc:
                self.out(f"Stopped at {c} (exit {rc}); the rest of the plan did not run.")
                break
        self.out(f"Ran: {', '.join(ran) or 'nothing'}")
        return True

    # ------------------------------------------------------------ the loop

    def intro(self) -> None:
        theme = None
        if self.color:
            from .theme import detect_theme
            theme = detect_theme(self.env)
        self.out(banner(color=self.color, version=__version__, theme=theme).rstrip("\n"))
        name = engagement_name(self.repo)
        if self.releases:
            shown = self.releases if len(self.releases) <= 6 else self.releases[:6] + [f"and {len(self.releases) - 6} more (`releases`)"]
            self.out(f"  Engagement: {name or self.repo.name}.")
            self.out(f"  Releases: {', '.join(shown)}.")
            self.out(f"  Active: {self.active}.")
        elif (self.repo / ".wire").is_dir():
            self.out(f"  Engagement: {name or self.repo.name}. No releases yet.")
        else:
            self.out(f"  {self.repo} has no .wire/ directory. `exec <text>` sends a prompt to the harness; `help` lists the commands.")
        self.out("  Type `help` for the commands, `quit` to leave.")
        self.out("")

    def loop(self) -> int:
        if self.panel is None:
            return self._loop()
        self.panel.start()
        try:
            return self._loop()
        finally:
            self.panel.stop()

    def _loop(self) -> int:
        self.intro()
        if self.first:
            self.out(f"{self.prompt()}{self.first}")
            if not self.handle(self.first):
                return 0
        while True:
            self.show_band()
            line = self._readline()
            if line is None:
                self.out("")
                return 0
            try:
                if not self.handle(line):
                    return 0
            except KeyboardInterrupt:
                self.out("(interrupted)")
            except Exception as exc:  # noqa: BLE001 - the session survives one bad command
                self.out(f"error: {exc}")


def _setup_readline() -> None:
    try:
        import readline  # noqa: F401
    except ImportError:
        return
    try:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        if HISTORY.exists():
            readline.read_history_file(str(HISTORY))
        readline.set_history_length(500)
        import atexit
        atexit.register(lambda: readline.write_history_file(str(HISTORY)))
    except OSError:
        pass


def run_shell(repo: Path, env: dict, out=print, read=None, **settings) -> int:
    color = sys.stdout.isatty() and not env.get("NO_COLOR")
    if read is None:
        _setup_readline()
    if "write" not in settings and out is print:
        from .stream import _stdout_write
        settings["write"] = _stdout_write
        if read is None and "panel" not in settings:
            from .panel import from_env
            settings["panel"] = from_env(env)
    return Shell(repo, env, out=out, read=read, color=color, **settings).loop()
