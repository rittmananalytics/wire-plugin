"""The CLI session behind a web page: Wire Studio's Session view.

The session is the same `Shell` the terminal runs (shell.py), with its input
taken from a queue and its output sent as events. Studio only relays: the
session process stays the single writer of status.md and the execution log,
as it is when Studio's "Run in Wire CLI" opens a terminal.

    browser --POST input--> Studio --queue--> Shell (its own thread)
    browser <--GET events-- Studio <--events-- Shell (out, text, status, ask)

Conversations are kept in <repo>/.wire/local/sessions/ (git-ignored with the
rest of .wire/local/): <id>.jsonl, one event per line, and <id>.json, the
title, release, director thread id and times. Opening a saved conversation
shows its transcript and resumes the same director thread, so the agent keeps
its context.

Events (each has `seq` and `ts`):
    out       a line the session printed
    text      reply text as it streams (no newline added)
    input     a line the person sent
    ask       a running command asks the person a question (`prompt`)
    ready     the session waits for the next line (`prompt`)
    status    the status line and the next action (`text`, `next`)
    busy      a command started (`label`) or ended (label null)
    note      the agent's last command or edit (`text`)
    lane      a lane's state during `wire run` (`label`, `state`)
    end       the session stopped
"""

from __future__ import annotations

import json
import queue
import re
import secrets
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

from .shell import Shell

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07|\x1b[78]")
ID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
MAX_LINE = 8000


def clean(s: str) -> str:
    return ANSI.sub("", str(s))


def sessions_dir(repo: Path) -> Path:
    return Path(repo) / ".wire" / "local" / "sessions"


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- models

# The models the Session view offers, each shown only when the key it needs is
# set (secrets.py: ~/.wire/secrets.env, the Keychain or keyring (Studio's Settings
# page), or the repository's .wire/local/secrets.env,
# or the environment). The ids are the ones the eval suites ran (EVALS.md).
# Claude models run on the claude harness when `claude` is installed, else on
# the codex harness with the native Anthropic provider. With `claude` installed
# they are offered without ANTHROPIC_API_KEY too: Claude Code then runs on the
# person's own sign-in (the Claude Code plugin case, where no key is set).
OPENAI_MODELS = (("gpt-6.1-sol", "GPT-6.1 Sol"), ("gpt-6-astra", "GPT-6 Astra"), ("gpt-6-luna", "GPT-6 Luna"))
CLAUDE_MODELS = (("claude-opus-5-5", "Claude Opus 5.5"), ("claude-sonnet-5-5", "Claude Sonnet 5.5"),
                 ("claude-haiku-5-5", "Claude Haiku 5.5"), ("claude-fable-5-1", "Claude Fable 5.1"))
CODEX_DEFAULT = "gpt-6.1-sol"  # what codex runs with no model set (EVALS.md, "default")
LABELS = dict(OPENAI_MODELS + CLAUDE_MODELS)


def model_key(harness: str | None, provider: str | None, model: str | None) -> str:
    return f"{harness or ''}|{provider or ''}|{model or ''}"


def model_choices(env: dict, claude_bin: str | None = "auto") -> list:
    """[{key, label, harness, provider, model}] for the keys that are set."""
    if claude_bin == "auto":
        claude_bin = shutil.which("claude", path=env.get("PATH"))  # on the session's own PATH
    out = []
    if env.get("OPENAI_API_KEY") or env.get("CODEX_API_KEY"):
        for mid, label in OPENAI_MODELS:
            out.append({"harness": "codex", "provider": None, "model": mid, "label": label})
    if env.get("ANTHROPIC_API_KEY") or claude_bin:
        harness, provider = ("claude", None) if claude_bin else ("codex", "anthropic")
        for mid, label in CLAUDE_MODELS:
            out.append({"harness": harness, "provider": provider, "model": mid, "label": label})
    for c in out:
        c["key"] = model_key(c["harness"], c["provider"], c["model"])
    return out


def model_label(harness: str, provider: str | None, model: str | None) -> str:
    """What the person sees for the model a run would use."""
    if not model and harness == "codex" and not provider:
        model = CODEX_DEFAULT
    if not model:
        return f"{harness} default model"
    label = LABELS.get(model, model)
    return f"{label} ({provider})" if provider and provider != "anthropic" else label


# ---------------------------------------------------------------- opening commands

# Opening commands that suit any release, in order, to fill the list when the
# release has fewer than five commands to run. Wire keeps no count of which
# commands are used most, so these are a fixed list.
GENERAL_OPENING = (("status", "Where the release stands"), ("next", "Run the next command"),
                   ("plan", "The run plan, without running it"), ("releases", "The releases in this repository"),
                   ("help", "What the session understands"))


def opening_commands(repo: Path, release: str | None, framework: str | None = None, limit: int = 5) -> list:
    """[{line, why, kind}] for the opening screen: the commands the release
    can run now, in the runnable set's order (wire_gate.actions, what `next`
    runs first), then the reviews that wait, then GENERAL_OPENING. A line is
    what the session takes on the release it starts on (`requirements-generate`
    for `/wire:requirements-generate <release>`)."""
    out = []
    if release:
        try:
            from .framework import framework_root, load_script, load_studio
            root = framework_root(framework)
            gate = load_script(root, "wire_gate")
            fw, split_fm, read_rulings, resolve = load_studio(root)
            for a in gate.actions(fw, str(repo), release, split_fm, read_rulings, resolve):
                line = a["command"].split(" ", 1)[0][len("/wire:"):]
                out.append({"line": line, "why": a["reason"], "kind": a["kind"]})
        except Exception:  # noqa: BLE001 - a release that does not resolve still gets the general list
            pass
    seen = {c["line"] for c in out}
    for line, why in GENERAL_OPENING:
        if line not in seen:
            out.append({"line": line, "why": why, "kind": "general"})
    return out[:limit]


def resolved_model(repo: Path, release: str | None, chosen: dict, env: dict) -> dict:
    """The model a run would use: the choice made in the page, else the CLI's
    own order (flags, WIRE_* environment, the release, the engagement, the
    harness default), as `wire` resolves it in a terminal."""
    from types import SimpleNamespace
    from .commands import settings_for
    chosen = chosen or {}
    args = SimpleNamespace(framework=chosen.get("framework"), harness=chosen.get("harness"), model=chosen.get("model"),
                           provider=chosen.get("provider"), sandbox=chosen.get("sandbox"))
    try:
        s = settings_for(Path(repo), release, args, env)
        harness, provider, model = s.harness, s.provider, s.model
    except Exception:  # noqa: BLE001 - a status.md that does not parse still shows a label
        harness, provider, model = chosen.get("harness") or "codex", chosen.get("provider"), chosen.get("model")
    if harness == "codex" and not provider and not model:
        model = CODEX_DEFAULT  # the same run, named, so it matches its entry in the list
    return {"key": model_key(harness, provider, model), "harness": harness, "provider": provider,
            "model": model, "label": model_label(harness, provider, model)}


# ---------------------------------------------------------------- the store

class Store:
    """Saved conversations for one repository."""

    def __init__(self, repo: Path):
        self.dir = sessions_dir(repo)

    def _paths(self, cid: str) -> tuple:
        if not ID.match(cid or ""):
            raise KeyError(cid)
        return self.dir / f"{cid}.json", self.dir / f"{cid}.jsonl"

    def list(self) -> list:
        if not self.dir.is_dir():
            return []
        out = []
        for p in self.dir.glob("*.json"):
            try:
                meta = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            meta["id"] = p.stem
            out.append(meta)
        return sorted(out, key=lambda m: m.get("updated", ""), reverse=True)

    def meta(self, cid: str) -> dict:
        mp, _ = self._paths(cid)
        if not mp.is_file():
            raise KeyError(cid)
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta["id"] = cid
        return meta

    def save_meta(self, cid: str, meta: dict) -> None:
        mp, _ = self._paths(cid)
        self.dir.mkdir(parents=True, exist_ok=True)
        body = {k: v for k, v in meta.items() if k != "id"}
        mp.write_text(json.dumps(body, indent=1), encoding="utf-8")

    def append(self, cid: str, event: dict) -> None:
        _, lp = self._paths(cid)
        self.dir.mkdir(parents=True, exist_ok=True)
        with lp.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    def events(self, cid: str) -> list:
        _, lp = self._paths(cid)
        if not lp.is_file():
            return []
        out = []
        for line in lp.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out

    def delete(self, cid: str) -> None:
        for p in self._paths(cid):
            if p.is_file():
                p.unlink()

    def rename(self, cid: str, title: str) -> dict:
        meta = self.meta(cid)
        meta["title"] = clean(title).strip()[:120] or meta.get("title", "")
        self.save_meta(cid, meta)
        return meta

    def markdown(self, cid: str) -> str:
        """The conversation as Markdown: what was typed, and what the session showed."""
        meta = self.meta(cid)
        lines = [f"# {meta.get('title') or cid}", "",
                 f"Release: {meta.get('release') or 'none'}. Started {meta.get('created', '')}, "
                 f"last used {meta.get('updated', '')}.", ""]
        buf: list = []

        def flush():
            text = "".join(buf).rstrip("\n")
            if text.strip():
                lines.extend(["```", text, "```", ""])
            buf.clear()
        for e in self.events(cid):
            t = e.get("type")
            if t == "input":
                flush()
                lines.extend([f"**> {e.get('text', '')}**", ""])
            elif t == "out":
                buf.append(e.get("text", "") + "\n")
            elif t == "text":
                buf.append(e.get("text", ""))
            elif t == "ask":
                buf.append(e.get("prompt", "") + "\n")
        flush()
        return "\n".join(lines)


# ---------------------------------------------------------------- the panel, as events

class WebPanel:
    """The live panel's interface (panel.py), sending events in place of
    drawing the terminal's bottom rows."""

    def __init__(self, emit):
        self.emit = emit

    def start(self):
        pass

    def stop(self):
        pass

    def write(self, s: str) -> None:
        if s:
            self.emit("text", text=clean(s))

    def print(self, *parts) -> None:
        self.emit("out", text=clean(" ".join(str(p) for p in parts)))

    def set_status(self, status: str, next_action: str | None = None) -> None:
        self.emit("status", text=clean(status or ""), next=clean(next_action) if next_action else None)

    def begin(self, label: str) -> None:
        self.emit("busy", label=clean(label))

    def end(self) -> None:
        self.emit("busy", label=None)

    def note(self, line: str) -> None:
        self.emit("note", text=clean(line))

    def lane(self, label: str, state: str) -> None:
        self.emit("lane", label=clean(label), state=clean(state))

    def pause(self):
        class _Nothing:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False
        return _Nothing()


class WebShell(Shell):
    """The terminal session with its questions sent to the page."""

    def __init__(self, *a, session=None, **kw):
        super().__init__(*a, **kw)
        self.session = session

    def ask(self, prompt: str) -> str:
        self.session.emit("ask", prompt=clean(prompt))
        return self.session.next_line(asking=True) or ""

    def _readline(self):
        return self.session.next_line(prompt=self.prompt())


# ---------------------------------------------------------------- one live session

class WebSession:
    def __init__(self, repo: Path, env: dict, release: str | None = None, cid: str | None = None,
                 shell_kwargs: dict | None = None, store: Store | None = None, first: str | None = None):
        self.repo = Path(repo)
        self.first = first  # the first line, sent once the banner is shown (the page's opening box)
        self.store = store or Store(self.repo)
        self.lock = threading.Condition()
        self.events: list = []
        self.seq = 0
        self.inbox: queue.Queue = queue.Queue()
        self.alive = False
        self.waiting = False
        resumed = None
        if cid:
            resumed = self.store.meta(cid)
            self.id = cid
            for e in self.store.events(cid):
                self.events.append(e)
                self.seq = max(self.seq, int(e.get("seq", 0)))
            self.meta = resumed
        else:
            self.id = datetime.now().strftime("%Y%m%d-%H%M%S-") + secrets.token_hex(3)
            self.meta = {"title": "", "release": release, "created": now_text(), "updated": now_text(), "thread": None}
        self.shell = WebShell(self.repo, env, session=self, panel=WebPanel(self.emit), **(shell_kwargs or {}))
        target = release or (resumed or {}).get("release")
        if target and target in self.shell.releases:
            self.shell.active = target
        if resumed and resumed.get("thread"):
            self.shell.thread = resumed["thread"]
        chosen = (resumed or {}).get("model")
        if isinstance(chosen, dict):  # the model picked for this conversation, kept with it
            for k in ("harness", "provider", "model"):
                self.shell.settings[k] = chosen.get(k) or None
        self.meta["release"] = self.shell.active
        self.thread = threading.Thread(target=self._run, name=f"wire-session-{self.id}", daemon=True)

    # -------------------------------------------------- events

    def emit(self, kind: str, **data) -> dict:
        with self.lock:
            self.seq += 1
            event = {"seq": self.seq, "ts": time.time(), "type": kind, **data}
            self.events.append(event)
            # on disk before anyone is told, so a conversation opened again
            # straight after never misses an event or reuses its number
            try:
                self.store.append(self.id, event)
            except OSError:
                pass
            self.lock.notify_all()
        return event

    def events_after(self, after: int, timeout: float = 25.0) -> list:
        """Events with seq above `after`, waiting up to `timeout` seconds for one."""
        deadline = time.time() + timeout
        with self.lock:
            while True:
                new = [e for e in self.events if int(e.get("seq", 0)) > after]
                if new or not self.alive or time.time() >= deadline:
                    return new
                self.lock.wait(max(0.05, deadline - time.time()))

    # -------------------------------------------------- input

    def send(self, line: str) -> None:
        line = clean(line).replace("\r", "")[:MAX_LINE]
        if "\n" in line:
            line = " ".join(line.split("\n"))
        if not self.meta.get("title") and line.strip():
            self.meta["title"] = line.strip()[:80]
        self.emit("input", text=line)
        self.inbox.put(line)

    def next_line(self, prompt: str | None = None, asking: bool = False):
        self._save_meta()
        if not asking:
            self.emit("ready", prompt=clean(prompt or ""))
        self.waiting = True
        try:
            line = self.inbox.get()
        finally:
            self.waiting = False
        return line

    def stop(self) -> None:
        self.inbox.put(None)

    # -------------------------------------------------- the model

    def model(self) -> dict:
        """The harness, provider and model the next command runs on."""
        return resolved_model(self.repo, self.shell.active, self.shell.settings, self.shell.env)

    def set_model(self, choice: dict) -> dict:
        """Run this conversation's next commands on `choice`, and keep it with
        the conversation so it applies when the conversation is opened again.
        A change of harness or provider starts a new director conversation:
        one harness cannot resume another's thread."""
        st = self.shell.settings
        if (st.get("harness"), st.get("provider")) != (choice.get("harness"), choice.get("provider")):
            self.shell.thread = None
        for k in ("harness", "provider", "model"):
            st[k] = choice.get(k) or None
        self.meta["model"] = {k: choice.get(k) for k in ("harness", "provider", "model")}
        self._save_meta()
        m = self.model()
        self.emit("out", text=f"(Model for this conversation: {m['label']}.)")
        return m

    # -------------------------------------------------- the session thread

    def start(self) -> "WebSession":
        self.alive = True
        self._save_meta()
        self.thread.start()
        return self

    def _run(self) -> None:
        try:
            if not self.events:
                self.shell.intro()
                if self.first and self.first.strip():
                    self.send(self.first)
            else:
                self.emit("out", text=f"(Resumed. Release {self.shell.active or 'none'}; "
                                      f"{'the director conversation continues' if self.shell.thread else 'no director conversation yet'}.)")
            while True:
                self.shell.show_band()
                line = self.shell._readline()
                if line is None:
                    break
                try:
                    if not self.shell.handle(line):
                        break
                except Exception as exc:  # noqa: BLE001 - the session survives one bad command
                    self.emit("out", text=f"error: {exc}")
        finally:
            self._save_meta()
            with self.lock:
                self.alive = False
                self.lock.notify_all()
            self.emit("end")

    def _save_meta(self) -> None:
        self.meta.update({"release": self.shell.active, "thread": self.shell.thread, "updated": now_text()})
        try:
            self.store.save_meta(self.id, self.meta)
        except OSError:
            pass

    def state(self) -> dict:
        return {"id": self.id, "alive": self.alive, "waiting": self.waiting, "release": self.shell.active,
                "title": self.meta.get("title", ""), "seq": self.seq, "model": self.model()}


# ---------------------------------------------------------------- several sessions

class Sessions:
    """The live sessions in one Studio process. One per conversation id; a
    conversation already open is returned, not started twice."""

    def __init__(self, repo: Path, env: dict, shell_kwargs: dict | None = None):
        self.repo = Path(repo)
        self.base_env = dict(env)
        self.reload_secrets()
        self.shell_kwargs = shell_kwargs or {}
        self.store = Store(self.repo)
        self.live: dict = {}
        self.lock = threading.Lock()

    def reload_secrets(self) -> None:
        """Read the keys again, as `wire` does before its session: after a key
        is set or removed in Studio's Settings. Sessions already running keep
        the keys they started with; the next one started gets the new ones."""
        from .secrets import load_secrets
        home = Path(self.base_env["HOME"]) if self.base_env.get("HOME") else None  # the HOME this session was given
        self.env, _notes = load_secrets(dict(self.base_env), self.repo, home=home)

    def start(self, release: str | None = None, cid: str | None = None, first: str | None = None,
              model: str | None = None) -> WebSession:
        """`model` is a key from models(), picked on the opening screen; it
        applies to a new conversation only."""
        choice = None
        if model and not cid:
            choice = next((c for c in self.models() if c["key"] == model), None)
            if choice is None and model != self.default_model(release)["key"]:
                raise ValueError("that model is not available; check the keys under Settings, API keys")
        with self.lock:
            if cid and cid in self.live and self.live[cid].alive:
                return self.live[cid]
            s = WebSession(self.repo, self.env, release=release, cid=cid, shell_kwargs=self.shell_kwargs, store=self.store,
                           first=None if cid else first)
            if choice is not None:
                for k in ("harness", "provider", "model"):
                    s.shell.settings[k] = choice.get(k) or None
                s.meta["model"] = {k: choice.get(k) for k in ("harness", "provider", "model")}
            self.live[s.id] = s
        return s.start()

    def default_model(self, release: str | None = None) -> dict:
        """What a new conversation runs on before anyone picks: the install's
        default, as `wire` in a terminal would resolve it for the release."""
        from .shell import releases_of
        if not release:
            rels = releases_of(self.repo)
            release = rels[0] if rels else None
        return resolved_model(self.repo, release, dict(self.shell_kwargs), self.env)

    def opening_commands(self, release: str | None = None) -> list:
        """The commands offered under the opening box for the release."""
        from .shell import releases_of
        if not release:
            rels = releases_of(self.repo)
            release = rels[0] if rels else None
        return opening_commands(self.repo, release, self.shell_kwargs.get("framework"))

    def get(self, cid: str) -> WebSession:
        s = self.live.get(cid)
        if s is None:
            raise KeyError(cid)
        return s

    def stop(self, cid: str) -> None:
        self.get(cid).stop()

    def stop_all(self) -> None:
        for s in list(self.live.values()):
            s.stop()

    def models(self) -> list:
        return model_choices(self.env)

    def unready(self) -> str | None:
        """Why no session can run on this machine, or None: no model is offered
        (no key, no `claude`) and no Codex agent is installed either."""
        if self.shell_kwargs.get("harness") or self.models():
            return None
        from .harness.codex import find_codex
        exe = find_codex(self.env)
        if Path(exe).is_file() or shutil.which(exe, path=self.env.get("PATH")):
            return None
        return ("no model is available: install Claude Code, or add a Claude or OpenAI API key "
                "under Settings, API keys")

    def set_model(self, cid: str, key: str) -> dict:
        """Set a conversation's model by its key from models(). A running
        conversation changes between commands; a stored one keeps it for
        when it is opened again."""
        choice = next((c for c in self.models() if c["key"] == key), None)
        if choice is None:
            raise ValueError("that model is not available; check the keys under Settings, API keys")
        s = self.live.get(cid)
        if s is not None and s.alive:
            if not s.waiting:
                raise RuntimeError("wait for the running command to finish")
            return s.set_model(choice)
        meta = self.store.meta(cid)
        meta["model"] = {k: choice.get(k) for k in ("harness", "provider", "model")}
        self.store.save_meta(cid, meta)
        return {"key": choice["key"], "harness": choice["harness"], "provider": choice["provider"],
                "model": choice["model"], "label": model_label(choice["harness"], choice["provider"], choice["model"])}

    def stored_model(self, meta: dict):
        m = meta.get("model")
        if not isinstance(m, dict):
            return None
        return {"key": model_key(m.get("harness"), m.get("provider"), m.get("model")), **m,
                "label": model_label(m.get("harness") or "codex", m.get("provider"), m.get("model"))}

    def listing(self) -> list:
        out = self.store.list()
        for m in out:
            s = self.live.get(m["id"])
            m["live"] = bool(s and s.alive)
        return out
