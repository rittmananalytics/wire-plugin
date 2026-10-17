#!/usr/bin/env python3
"""Start Wire Studio for a client repository.

    python3 wire/studio/studio.py --repo ~/github/client-delivery
    python3 wire/studio/studio.py                 # the current directory

Studio reads `.wire/` in the repository and the release-type graph of the
Wire framework it ships with, and serves a console at http://127.0.0.1:4800.
It writes nothing to the record; 'Run in Claude Code' opens a new
terminal with `claude "<directive>"`. Stop it with Ctrl+C.

Hosted mode (`--hosted`) serves the same views, read only, for releases read
from GitHub repositories, for a site that puts its own sign-in in front of it
(wire_studio/hosted.py). It has no launch endpoint. Settings come from the
environment: GITHUB_TOKEN (read-only), PORT (default 8080),
STUDIO_CACHE_DIR (default a temporary folder), STUDIO_ALLOWED_OWNERS
(comma-separated GitHub organisations; empty allows any the token can read).
"""

import argparse
import os
import sys
import tempfile
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import yaml  # noqa: F401  (Studio reads status.md front matter and release types with it)
except ImportError:
    sys.exit("Wire Studio needs PyYAML. Install it with:  python3 -m pip install pyyaml")

from wire_studio import __version__  # noqa: E402
from wire_studio.framework import Framework, default_framework_root  # noqa: E402
from wire_studio.server import serve  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description="Wire Studio: read-only director console")
    ap.add_argument("--repo", default=".", help="client repository holding .wire/ (default: current directory)")
    ap.add_argument("--port", type=int, default=4800)
    ap.add_argument("--framework", default=None,
                    help="Wire framework root (default: the one Studio ships with)")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--launch", default="auto", choices=["auto", "terminal", "linux", "print"],
                    help="how 'Run in Claude Code' opens a session (default: Terminal on macOS; "
                         "print shows the command instead)")
    ap.add_argument("--hosted", action="store_true",
                    help="serve releases read from GitHub, read only, with no launch endpoint (see above)")
    args = ap.parse_args(argv)
    if args.hosted:
        return hosted_main(args)

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".wire").is_dir():
        print(f"No .wire/ folder in {repo}. Point --repo at a Wire engagement repository.", file=sys.stderr)
        return 2
    try:
        fw = Framework(args.framework or default_framework_root())
    except (FileNotFoundError, ValueError) as e:
        print(f"Cannot load the Wire framework: {e}", file=sys.stderr)
        return 2

    httpd = serve(fw, repo, args.port, launch_mode=args.launch)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"Wire Studio {__version__}: {repo}\n  framework: {fw.root} ({fw.layout})\n  open {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def hosted_main(args):
    from wire_studio.hosted import GitClient, HostedRecord, serve_hosted
    try:
        fw = Framework(args.framework or default_framework_root())
    except (FileNotFoundError, ValueError) as e:
        print(f"Cannot load the Wire framework: {e}", file=sys.stderr)
        return 2
    cache = os.environ.get("STUDIO_CACHE_DIR") or tempfile.mkdtemp(prefix="wire-studio-")
    client = GitClient(cache, token=os.environ.get("GITHUB_TOKEN") or None)
    owners = [o.strip() for o in (os.environ.get("STUDIO_ALLOWED_OWNERS") or "").split(",") if o.strip()]
    port = int(os.environ.get("PORT") or (args.port if args.port != 4800 else 8080))
    httpd = serve_hosted(HostedRecord(fw, client, allowed_owners=owners), "0.0.0.0", port)
    print(f"Wire Studio {__version__} hosted, read only, on port {port}\n  framework: {fw.root} ({fw.layout})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
