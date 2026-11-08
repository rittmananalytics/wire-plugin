"""Secrets for the harnesses, read from files the person writes themselves.

    ~/.wire/secrets.env            per person (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...)
    <repo>/.wire/local/secrets.env per repository (git-ignored), overrides

`KEY=value` lines, `#` comments, optional `export `. Values are loaded into
the environment handed to a harness and nowhere else: never printed, never
logged, never written into a prompt. `present()` says which names are set,
not their values. A file readable by others is refused.
"""

from __future__ import annotations

import os
import re
import stat
from pathlib import Path

LINE_RE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
KNOWN = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CODEX_API_KEY", "GOOGLE_API_KEY")


def secret_files(repo: Path | None, home: Path | None = None) -> list:
    home = home or Path.home()
    files = [home / ".wire" / "secrets.env"]
    if repo is not None:
        files.append(repo / ".wire" / "local" / "secrets.env")
    return files


def parse(text: str) -> dict:
    out = {}
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        value = m.group(2)
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[m.group(1)] = value
    return out


def too_open(path: Path) -> bool:
    try:
        mode = path.stat().st_mode
    except OSError:
        return False
    return bool(mode & (stat.S_IRWXG | stat.S_IRWXO))


def load_secrets(env: dict, repo: Path | None = None, home: Path | None = None) -> tuple:
    """(env with the secrets added, notes). A value already in `env` wins.
    Returns notes about files skipped (unreadable or too open)."""
    merged = dict(env)
    notes = []
    for path in secret_files(repo, home):
        if not path.is_file():
            continue
        if too_open(path):
            notes.append(f"{path} is readable by others; run chmod 600 on it. Skipped.")
            continue
        try:
            values = parse(path.read_text(encoding="utf-8"))
        except OSError as exc:
            notes.append(f"{path}: {exc}")
            continue
        for k, v in values.items():
            if k not in env and v:
                merged[k] = v
    return merged, notes


def present(env: dict) -> dict:
    """Which known keys are set, by name only."""
    return {k: bool(env.get(k)) for k in KNOWN}
