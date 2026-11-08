"""Usage telemetry from the Wire CLI (ROADMAP.md phase 4), the event the
plugin sends: `wire_command` to Segment, same properties as the Wire mod's
trackBody (packaging/claude-plugin/hooks/wire/logic.ts), plus `runtime:
wire-cli`, `harness` and `model_provider`. Never the command's arguments or
any prompt text.

Off when WIRE_TELEMETRY=false, and in a source checkout: the write key below is
a placeholder that build-packages.sh stamps into the shipped copy. The
anonymous id is the plugin's own (~/.wire/telemetry_id), so a person who uses
both front ends is counted once. Sent from a background thread with a short
timeout; a failure is silent and never slows a run.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import threading
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

WRITE_KEY = "DxXwrT6ucDMRmouCsYDwthdChwDLsNYL"
TRACK = "https://api.segment.io/v1/track"
IDENTIFY = "https://api.segment.io/v1/identify"


def enabled(env: dict) -> bool:
    if str(env.get("WIRE_TELEMETRY", "true")).lower() == "false":
        return False
    return not WRITE_KEY.startswith("__")


def _git(repo: Path, *args) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=5).stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def user_id(env: dict) -> tuple:
    """(id, new): the anonymous id in ~/.wire/telemetry_id, made on first use."""
    p = Path(env.get("HOME") or Path.home()) / ".wire" / "telemetry_id"
    if p.is_file():
        return p.read_text(encoding="utf-8").strip() or "unknown", False
    uid = str(uuid.uuid4())
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(uid + "\n", encoding="utf-8")
    except OSError:
        pass
    return uid, True


def track_body(uid: str, command: str, invoked_by: str, release: str | None, repo: Path, harness: str,
               provider: str | None, version: str, persona: str = "", event: str = "wire_command") -> dict:
    return {
        "writeKey": WRITE_KEY,
        "userId": uid,
        "event": event,
        "properties": {
            "command": command,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "git_repo": _git(repo, "config", "--get", "remote.origin.url"),
            "git_branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            "username": os.environ.get("USER", "unknown"),
            "hostname": socket.gethostname(),
            "plugin_version": version,
            "os": platform.system(),
            "runtime": "wire-cli",
            "invoked_by": invoked_by,
            "persona": persona,
            "release": release,
            "harness": harness,
            "model_provider": provider or "",
        },
    }


def _post(url: str, body: dict) -> None:
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:  # noqa: BLE001 - telemetry never fails a run
        pass


def send(command: str, invoked_by: str, release: str | None, repo: Path, harness: str, provider: str | None,
         env: dict, event: str = "wire_command", wait: bool = False):
    """Queue one event. Returns the body (for tests), or None when telemetry is off."""
    if not enabled(env):
        return None
    from . import __version__
    uid, new = user_id(env)
    persona = "".join(c for c in str(env.get("WIRE_PERSONA", "")) if c.isalpha() or c == "-")
    body = track_body(uid, command, invoked_by, release, repo, harness, provider, __version__, persona, event)

    def go():
        if new:
            _post(IDENTIFY, {"writeKey": WRITE_KEY, "userId": uid,
                             "traits": {"username": body["properties"]["username"], "hostname": body["properties"]["hostname"],
                                        "os": body["properties"]["os"], "plugin_version": __version__,
                                        "first_seen": body["properties"]["timestamp"]}})
        _post(TRACK, body)
    t = threading.Thread(target=go, daemon=True)
    t.start()
    if wait:
        t.join(timeout=5)
    return body
