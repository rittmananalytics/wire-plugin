"""The HTTP server for Wire Studio. Standard library only.

- Binds to 127.0.0.1 and answers only requests whose Host header names this
  machine, so a web page elsewhere cannot read the record through the
  browser (DNS rebinding).
- Answers GET and HEAD for everything it shows.
- One POST endpoint, `/api/launch`, opens Claude Code in a new terminal with a
  directive (stage 1, `launcher.py`). It writes nothing to the repository. It
  needs the per-run token served in Studio's own page and an Origin header
  naming this server, so another web page cannot make the browser call it.
- Every other POST, and every PUT, PATCH and DELETE, gets 405.
"""

import json
import mimetypes
import secrets
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .launcher import LaunchError, availability, launch
from .record import load_release, read_engagement, release_summaries, safe_file

STATIC = Path(__file__).resolve().parent / "static"
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
MAX_BODY = 16_000


def make_handler(framework, repo, clock=datetime.now, launch_mode="auto", launch_fn=launch, token=None):
    repo = Path(repo).resolve()
    token = token or secrets.token_urlsafe(32)

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

        def do_POST(self):
            if not self._host_ok():
                return self._send(403, {"error": "host not allowed"})
            if urlparse(self.path).path != "/api/launch":
                return self._refuse()
            if not self._origin_ok():
                return self._send(403, {"error": "launch requests must come from Studio's own page"})
            if not secrets.compare_digest(self.headers.get("X-Studio-Token", ""), token):
                return self._send(403, {"error": "missing or wrong Studio token; reload the page"})
            if "application/json" not in (self.headers.get("Content-Type") or ""):
                return self._send(415, {"error": "send JSON"})
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._send(413, {"error": "request body missing or too large"})
            try:
                body = json.loads(self.rfile.read(length))
                return self._send(200, launch_fn(repo, body.get("directive"), launch_mode))
            except (LaunchError, ValueError) as e:
                return self._send(400, {"error": str(e)})

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self._host_ok():
                return self._send(403, {"error": "host not allowed"})
            url = urlparse(self.path)
            path, q = url.path, parse_qs(url.query)
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
            name = "index.html" if path in ("/", "") else path.lstrip("/")
            target = (STATIC / name).resolve()
            try:
                target.relative_to(STATIC)
            except ValueError:
                return self._send(403, {"error": "forbidden"})
            if not target.is_file():
                return self._send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype == "application/javascript":
                ctype += "; charset=utf-8"
            data = target.read_bytes()
            if target.name == "index.html":
                # The token is only readable by a page served from this origin:
                # no CORS headers are sent, and the Host check blocks rebinding.
                data = data.replace(b"__STUDIO_TOKEN__", token.encode("ascii"))
            return self._send(200, data, ctype)

    return Handler


def serve(framework, repo, port=4800, clock=datetime.now, launch_mode="auto", launch_fn=launch, token=None):
    return ThreadingHTTPServer(("127.0.0.1", port),
                               make_handler(framework, repo, clock, launch_mode, launch_fn, token))
