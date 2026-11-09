"""The HTTP server for Wire Studio. Standard library only.

- Binds to 127.0.0.1 and answers only requests whose Host header names this
  machine, so a web page elsewhere cannot read the record through the
  browser (DNS rebinding).
- Answers GET and HEAD for everything it shows.
- One POST endpoint, `/api/launch`, opens Claude Code in a new terminal with a
  directive (stage 1, `launcher.py`). It writes nothing to the repository. It
  needs the per-run token served in Studio's own page and an Origin header
  naming this server, so another web page cannot make the browser call it.
- The Session view's endpoints, `/api/sessions` and `/api/session/...`, drive
  the Wire CLI's session from the page (`session_bridge.py`). Studio relays;
  the session is the writer, as in a terminal. Every one of them, GET
  included, needs the token; the POSTs also need the Origin header.
- `/api/files/add` is Add Files to release: it opens the operating system's
  file picker and then its save dialog on this machine and copies the picked
  file to the chosen place, inside the repository only and never onto a
  release's status.md or execution_log.md (`addfile.py`). It is the one
  place Studio writes to the repository, and only a file the person chose.
  Same token and Origin checks.
- Settings, API keys: `GET /api/settings/keys` says which keys are set and
  where from (never a value; the last four characters at most), and
  `POST /api/settings/keys/set` and `/delete` write or remove the Claude and
  OpenAI keys in the operating system's secure store (the macOS Keychain or
  the Linux keyring, `wire_cli/keystore.py`), never in the repository. Same
  token and Origin checks; the GET needs the token too.
- Settings, the rest (all read only, token needed): `GET /api/settings/mcp`
  (the MCP catalogue, the engagement's selection, and with `?signin=1` each
  server's status as a Claude Code run sees it, from one probe run stopped
  before the model is asked, and its Codex sign-in when Codex is installed), `GET /api/settings/machine` (`wire doctor`),
  `GET /api/settings/update` (is a newer Wire CLI out; reads GitHub on
  request only), `GET /api/settings/persona` (the persona list and yours).
  `POST /api/settings/mcp/login` starts Codex's sign-in for a selected server
  (a browser opens; the token stays in Codex's store, never Studio's). The
  changes to the engagement (adding or removing a server, setting a persona)
  are not here: the Wire CLI box's + menu sends them to the session, which
  writes them as a typed command would.
- Every other POST, and every PUT, PATCH and DELETE, gets 405.
"""

import json
import mimetypes
import os
import secrets
import shutil
import subprocess
import tempfile
import types
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .addfile import AddFileError, add_file
from .launcher import LaunchError, availability, launch
from .record import load_release, read_engagement, release_summaries, safe_file
from . import session_bridge

STATIC = Path(__file__).resolve().parent / "static"
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
MAX_BODY = 16_000


def make_handler(framework, repo, clock=datetime.now, launch_mode="auto", launch_fn=launch, token=None,
                 sessions_factory=None, dialogs=None, env=None):
    repo = Path(repo).resolve()
    env = dict(os.environ if env is None else env)
    token = token or secrets.token_urlsafe(32)
    sessions_box = {}

    def sessions():
        """The CLI's sessions for this repository, loaded on first use."""
        if "value" not in sessions_box:
            try:
                factory = sessions_factory or (lambda: session_bridge.load(framework.root, repo, env))
                sessions_box["value"], sessions_box["error"] = factory(), None
            except session_bridge.Unavailable as e:
                sessions_box["value"], sessions_box["error"] = None, str(e)
        if sessions_box["value"] is None:
            raise session_bridge.Unavailable(sessions_box["error"])
        return sessions_box["value"]

    def keys_listing():
        """What the Settings page shows. Never a key's value."""
        keystore, secrets_mod = session_bridge.key_modules(framework.root)
        store, reason = keystore.store_for(env)
        found = secrets_mod.sources(env, repo, store=store)
        in_store = keystore.read_all(store)
        keys = []
        for spec in keystore.SETTABLE:
            src = found.get(spec["name"], {})
            keys.append({"name": spec["name"], "label": spec["label"], "prefix": spec["prefix"],
                         "source": src.get("source"), "hint": src.get("hint", ""), "also": src.get("also", []),
                         "in_store": spec["name"] in in_store,
                         "store_hint": keystore.hint(in_store.get(spec["name"]))})
        return {"available": store is not None, "store": store.label if store else None, "reason": reason,
                "keys": keys}

    logins = {}  # MCP server key -> {"proc", "log"}: Codex sign-ins started from Settings

    def login_state(key):
        job = logins.get(key)
        if job is None:
            return None
        rc = job["proc"].poll()
        if rc is None:
            return {"state": "running"}
        job["log"].seek(0)
        tail = job["log"].read().decode("utf-8", "replace").strip().split("\n")[-1:]
        return {"state": "done" if rc == 0 else "failed", "message": tail[0] if tail else ""}

    def find_codex():
        (codex_mod,) = session_bridge.cli_modules(framework.root, "harness.codex")
        exe = codex_mod.find_codex(env)
        return exe if (Path(exe).is_file() or shutil.which(exe, path=env.get("PATH"))) else None

    def find_claude():
        return shutil.which("claude", path=env.get("PATH"))

    def mcp_listing(signin):
        """The catalogue and the engagement's selection, and with signin each
        selected server's status: on Claude Code as a CLI run sees it (one
        probe run, stopped before the model is asked), on Codex from its store."""
        (mcp,) = session_bridge.cli_modules(framework.root, "mcp")
        cat = mcp.catalogue(framework.root)
        selection = mcp.load_selection(repo)
        named = mcp.claude_names(selection, mcp.plugin_servers(framework.root))
        run_name = {k: n for n in named for k in selection if n in (k, mcp.PLUGIN_PREFIX + k)}
        codex, claude = find_codex(), find_claude()
        auth = mcp.sign_in_status(codex, selection, repo, env) if (signin and codex and selection) else None
        seen = mcp.claude_sign_in_status(claude, named, repo, env) if (signin and claude and selection) else None
        servers = []
        for key in sorted(set(cat) | set(selection)):
            info = cat.get(key, {})
            chosen = key in selection
            name = run_name.get(key)
            servers.append({"key": key, "url": selection.get(key) or info.get("url", ""), "purpose": info.get("purpose", ""),
                            "placeholder": bool(info.get("placeholder")) and not chosen, "selected": chosen,
                            # Claude Code: the name a run uses; a plugin server shares the person's /mcp sign-in
                            "claude_name": name, "plugin": bool(name and name.startswith(mcp.PLUGIN_PREFIX)),
                            "claude_status": (seen or {}).get(name) if (chosen and seen is not None) else None,
                            "codex_signed_in": (auth.get(key) != mcp.NOT_SIGNED_IN) if (chosen and auth is not None) else None,
                            "login": login_state(key)})
        return {"servers": servers, "file": str(mcp.SELECTION_FILE), "claude": bool(claude), "codex": bool(codex),
                "checked": bool(signin and selection and (auth is not None or seen is not None))}

    def captured(fn):
        """(return value, printed lines) of a CLI function that prints through `out`."""
        lines = []
        rc = fn(lambda text="": lines.extend(str(text).split("\n")))
        return rc, [ln for ln in lines if ln.strip()]

    def keys_changed():
        # sessions started from now on read the new keys; running ones keep theirs
        if sessions_box.get("value") is not None:
            sessions_box["value"].reload_secrets()

    class Handler(BaseHTTPRequestHandler):
        server_version = f"WireStudio/{__version__}"
        studio_token = token

        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def _host_name(self):
            host = self.headers.get("Host") or ""
            return host.split("]")[0] + "]" if host.startswith("[") else host.split(":")[0]

        def _host_ok(self):
            return self._host_name() in ALLOWED_HOSTS

        def _origin_ok(self):
            origin = self.headers.get("Origin")
            if not origin:
                return False
            o = urlparse(origin)
            port = self.server.server_address[1]
            name = f"[{o.hostname}]" if o.hostname and ":" in o.hostname else o.hostname
            return o.scheme == "http" and name in ALLOWED_HOSTS and (o.port or 80) == port

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _refuse(self):
            self._send(405, {"error": "Wire Studio does not change the record. Use the directive in the orchestrating session."})

        do_PUT = do_PATCH = do_DELETE = _refuse

        def _token_ok(self):
            return secrets.compare_digest(self.headers.get("X-Studio-Token", ""), token)

        def _json_body(self):
            """The request's JSON object, or None after sending the error."""
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                self._send(415, {"error": "send JSON"})
                return None
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                self._send(413, {"error": "request body missing or too large"})
                return None
            try:
                body = json.loads(self.rfile.read(length))
            except ValueError:
                self._send(400, {"error": "not JSON"})
                return None
            if not isinstance(body, dict):
                self._send(400, {"error": "send a JSON object"})
                return None
            return body

        def do_POST(self):
            if not self._host_ok():
                return self._send(403, {"error": "host not allowed"})
            path = urlparse(self.path).path
            if (path not in ("/api/launch", "/api/files/add", "/api/settings/keys/set", "/api/settings/keys/delete",
                             "/api/settings/mcp/login")
                    and not path.startswith("/api/session/")):
                return self._refuse()
            if not self._origin_ok():
                return self._send(403, {"error": "requests that act must come from Studio's own page"})
            if not self._token_ok():
                return self._send(403, {"error": "missing or wrong Studio token; reload the page"})
            if path.startswith("/api/session/"):
                body = self._json_body()
                return None if body is None else self._session_post(path, body)
            if path == "/api/settings/mcp/login":
                body = self._json_body()
                return None if body is None else self._mcp_login(body)
            if path.startswith("/api/settings/keys/"):
                body = self._json_body()
                return None if body is None else self._keys_post(path, body)
            if path == "/api/files/add":
                # Add Files to release: the OS file picker, then its save dialog, the copy
                # only inside the repository (addfile.py). Never the record files.
                body = self._json_body()
                if body is None:
                    return None
                release = body.get("release")
                if release is not None and not isinstance(release, str):
                    return self._send(400, {"error": "release must be text"})
                try:
                    return self._send(200, add_file(repo, release or None, dialogs))
                except AddFileError as e:
                    return self._send(400, {"error": str(e)})
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                return self._send(415, {"error": "send JSON"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._send(413, {"error": "request body missing or too large"})
            try:
                body = json.loads(self.rfile.read(length))
                if body.get("target") == "wire":
                    # the Wire CLI's session in place of Claude Code
                    return self._send(200, launch_fn(repo, body.get("directive"), launch_mode, target="wire"))
                return self._send(200, launch_fn(repo, body.get("directive"), launch_mode))
            except (LaunchError, ValueError) as e:
                return self._send(400, {"error": str(e)})

        def _mcp_login(self, body):
            key = body.get("key")
            try:
                (mcp,) = session_bridge.cli_modules(framework.root, "mcp")
                selection = mcp.load_selection(repo)
                if not isinstance(key, str) or key not in selection:
                    return self._send(400, {"error": "add the server to the engagement first (+ menu, Add MCP server)"})
                codex = find_codex()
                if codex is None:
                    return self._send(409, {"error": "Codex is not installed here; on Claude Code, sign in with /mcp"})
                if (login_state(key) or {}).get("state") == "running":
                    return self._send(200, mcp_listing(False))
                log = tempfile.TemporaryFile()
                argv = [codex, *mcp.codex_overrides({key: selection[key]}), "mcp", "login", key]
                proc = subprocess.Popen(argv, cwd=str(repo), env=mcp.agent_env(codex, repo, env), stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT)
                logins[key] = {"proc": proc, "log": log}
                return self._send(200, mcp_listing(False))
            except session_bridge.Unavailable as e:
                return self._send(503, {"error": str(e)})
            except OSError as e:
                return self._send(500, {"error": f"Codex could not be started: {e}"})

        def _settings_get(self, path, q):
            try:
                if path == "/api/settings/mcp":
                    return self._send(200, mcp_listing(q.get("signin", ["0"])[0] == "1"))
                if path == "/api/settings/machine":
                    secrets_mod, doctor_mod, cli = session_bridge.cli_modules(framework.root, "secrets", "doctor", "")
                    full, _notes = secrets_mod.load_secrets(env, repo)
                    _rc, lines = captured(lambda out: doctor_mod.doctor(repo, full, types.SimpleNamespace(json=True), out))
                    try:
                        rows = json.loads("\n".join(lines))
                    except ValueError:
                        rows = {"doctor": " ".join(lines)}
                    return self._send(200, {"version": cli.__version__, "rows": rows})
                if path == "/api/settings/update":
                    ops, cli = session_bridge.cli_modules(framework.root, "install_ops", "")
                    rc, lines = captured(lambda out: ops.update(cli.__version__, True, out, env))
                    return self._send(200, {"version": cli.__version__, "ok": rc == 0, "lines": lines})
                if path == "/api/settings/persona":
                    (fw,) = session_bridge.cli_modules(framework.root, "framework")
                    ps = fw.load_script(framework.root, "persona")
                    personas = ps.load_personas()
                    known = [p["id"] for p in personas]
                    _name, email = ps.git_user(repo)
                    mine = ps.resolve(known, None, env.get("WIRE_PERSONA"), ps.read_local(repo),
                                      ps.roster_persona(ps.read_roster(repo), email))
                    return self._send(200, {"personas": personas, "current": mine, "email": email})
                return self._send(404, {"error": "no such setting"})
            except session_bridge.Unavailable as e:
                return self._send(503, {"error": str(e)})

        def _keys_post(self, path, body):
            name, value = body.get("name"), body.get("value")
            try:
                keystore, _secrets = session_bridge.key_modules(framework.root)
            except session_bridge.Unavailable as e:
                return self._send(503, {"error": str(e)})
            try:
                if not isinstance(name, str) or name not in keystore.NAMES:
                    return self._send(400, {"error": f"name must be one of {', '.join(keystore.NAMES)}"})
                store, reason = keystore.store_for(env)
                if store is None:
                    return self._send(409, {"error": f"no secure store on this machine: {reason}"})
                if path.endswith("/set"):
                    store.set(name, keystore.check_value(name, value))
                else:
                    store.delete(name)
                keys_changed()
                return self._send(200, keys_listing())
            except keystore.KeystoreError as e:
                return self._send(400, {"error": str(e)})

        def _session_post(self, path, body):
            parts = path[len("/api/session/"):].split("/")
            try:
                ss = sessions()
                if parts == ["start"]:
                    first = body.get("first")
                    if first is not None and not isinstance(first, str):
                        return self._send(400, {"error": "first must be text"})
                    model = body.get("model")
                    if model is not None and not isinstance(model, str):
                        return self._send(400, {"error": "model must be text"})
                    try:
                        s = ss.start(release=body.get("release") or None, cid=body.get("id") or None, first=first,
                                     model=model or None)
                    except ValueError as e:
                        return self._send(400, {"error": str(e)})
                    return self._send(200, s.state())
                if len(parts) == 2:
                    cid, action = parts
                    if action == "input":
                        line = body.get("line")
                        if not isinstance(line, str):
                            return self._send(400, {"error": "send {\"line\": \"...\"}"})
                        s = ss.get(cid)
                        if not s.alive:
                            return self._send(409, {"error": "this session has ended; open the conversation again"})
                        s.send(line)
                        return self._send(200, s.state())
                    if action == "stop":
                        ss.stop(cid)
                        return self._send(200, {"stopped": cid})
                    if action == "model":
                        key = body.get("key")
                        if not isinstance(key, str):
                            return self._send(400, {"error": "send {\"key\": \"...\"}"})
                        try:
                            return self._send(200, ss.set_model(cid, key))
                        except ValueError as e:
                            return self._send(400, {"error": str(e)})
                        except RuntimeError as e:
                            return self._send(409, {"error": str(e)})
                    if action == "rename":
                        return self._send(200, ss.store.rename(cid, str(body.get("title", ""))))
                    if action == "delete":
                        live = ss.live.get(cid)
                        if live is not None and live.alive:
                            return self._send(409, {"error": "stop the session before deleting it"})
                        ss.store.delete(cid)
                        ss.live.pop(cid, None)
                        return self._send(200, {"deleted": cid})
                return self._send(404, {"error": "no such session action"})
            except session_bridge.Unavailable as e:
                return self._send(503, {"error": str(e)})
            except KeyError:
                return self._send(404, {"error": "no such conversation"})

        def _session_get(self, path, q):
            if not self._token_ok():
                return self._send(403, {"error": "missing or wrong Studio token; reload the page"})
            try:
                if path == "/api/sessions":
                    try:
                        ss = sessions()
                    except session_bridge.Unavailable as e:
                        return self._send(200, {"available": False, "reason": str(e), "conversations": []})
                    release = q.get("release", [None])[0] or None
                    reason = ss.unready()
                    if reason:
                        return self._send(200, {"available": False, "reason": reason, "conversations": []})
                    return self._send(200, {"available": True, "conversations": ss.listing(), "models": ss.models(),
                                            "default_model": ss.default_model(release),
                                            "opening": ss.opening_commands(release)})
                parts = path[len("/api/session/"):].split("/")
                if len(parts) == 2 and parts[1] == "events":
                    ss = sessions()
                    cid = parts[0]
                    try:
                        after = int(q.get("after", ["0"])[0])
                        wait = min(25.0, max(0.0, float(q.get("wait", ["25"])[0])))
                    except ValueError:
                        return self._send(400, {"error": "after and wait are numbers"})
                    s = ss.live.get(cid)
                    if s is None:
                        events = [e for e in ss.store.events(cid) if int(e.get("seq", 0)) > after]
                        meta = ss.store.meta(cid)
                        return self._send(200, {"events": events, "state": {"id": cid, "alive": False, "waiting": False,
                                                                            "release": meta.get("release"), "title": meta.get("title", ""),
                                                                            "model": ss.stored_model(meta) or ss.default_model(meta.get("release"))}})
                    return self._send(200, {"events": s.events_after(after, wait), "state": s.state()})
                if len(parts) == 2 and parts[1] == "export":
                    ss = sessions()
                    text = ss.store.markdown(parts[0])
                    data = text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/markdown; charset=utf-8")
                    self.send_header("Content-Disposition", f'attachment; filename="wire-session-{parts[0]}.md"')
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    if self.command != "HEAD":
                        self.wfile.write(data)
                    return None
                return self._send(404, {"error": "no such session resource"})
            except session_bridge.Unavailable as e:
                return self._send(503, {"error": str(e)})
            except KeyError:
                return self._send(404, {"error": "no such conversation"})

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, {"error": "host not allowed"})
            url = urlparse(self.path)
            path, q = url.path, parse_qs(url.query)
            if path == "/api/sessions" or path.startswith("/api/session/"):
                return self._session_get(path, q)
            if path == "/api/settings/keys":
                if not self._token_ok():
                    return self._send(403, {"error": "missing or wrong Studio token; reload the page"})
                try:
                    return self._send(200, keys_listing())
                except session_bridge.Unavailable as e:
                    return self._send(200, {"available": False, "store": None, "reason": str(e), "keys": []})
            if path.startswith("/api/settings/"):
                if not self._token_ok():
                    return self._send(403, {"error": "missing or wrong Studio token; reload the page"})
                return self._settings_get(path, q)
            try:
                if path == "/api/summary":
                    return self._send(200, {
                        "version": __version__, "repo": repo.name,
                        "framework": {"root": str(framework.root), "layout": framework.layout},
                        "engagement": read_engagement(repo),
                        "releases": release_summaries(framework, repo, clock()),
                        "launch": availability(launch_mode),
                        "now": clock().strftime("%Y-%m-%d %H:%M"),
                    })
                if path.startswith("/api/release/"):
                    name = unquote(path[len("/api/release/"):])
                    return self._send(200, load_release(framework, repo, name, clock()))
                if path == "/api/file":
                    p = safe_file(repo, q.get("release", [""])[0], q.get("path", [""])[0])
                    return self._send(200, {"path": str(p.relative_to(repo)),
                                            "text": p.read_text(encoding="utf-8", errors="replace")})
                return self._static(path)
            except KeyError as e:
                return self._send(404, {"error": f"no release {e}"})
            except FileNotFoundError as e:
                return self._send(404, {"error": f"not found: {e}"})
            except PermissionError as e:
                return self._send(403, {"error": str(e)})

        def _static(self, path):
            # The token is only readable by a page served from this origin:
            # no CORS headers are sent, and the Host check blocks rebinding.
            code, data, ctype = static_file(path, {"token": token, "mode": "local", "base": "/", "back": ""})
            return self._send(code, data, ctype)

    return Handler


def static_file(path, page):
    """(status, body, content type) for a file under static/. index.html gets
    the page settings: the launch token (local mode only), the mode (`local`
    or `hosted`), the base path the page's own requests go to, and an
    optional link back to whatever serves the page."""
    name = "index.html" if path in ("/", "") else path.lstrip("/")
    target = (STATIC / name).resolve()
    try:
        target.relative_to(STATIC)
    except ValueError:
        return 403, {"error": "forbidden"}, "application/json; charset=utf-8"
    if not target.is_file():
        return 404, {"error": "not found"}, "application/json; charset=utf-8"
    ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype == "application/javascript":
        ctype += "; charset=utf-8"
    data = target.read_bytes()
    if target.name == "index.html":
        for key, value in (("TOKEN", page.get("token", "")), ("MODE", page.get("mode", "local")),
                           ("BASE", page.get("base", "/")), ("BACK", page.get("back", ""))):
            data = data.replace(f"__STUDIO_{key}__".encode("ascii"), html_attr(value).encode("utf-8"))
    return 200, data, ctype


def html_attr(value):
    return (str(value).replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def serve(framework, repo, port=4800, clock=datetime.now, launch_mode="auto", launch_fn=launch, token=None,
          sessions_factory=None, dialogs=None, env=None):
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 make_handler(framework, repo, clock, launch_mode, launch_fn, token, sessions_factory, dialogs,
                                              env))
    server.daemon_threads = True  # a waiting events request never holds Studio open on exit
    return server
