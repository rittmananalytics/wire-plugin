"""Secrets for the harnesses, from these places, the later winning:

    ~/.wire/secrets.env            per person (ANTHROPIC_API_KEY, OPENAI_API_KEY, ...)
    the macOS Keychain             per person, written from Wire Studio's
                                   Settings page (keystore.py); elsewhere the
                                   page writes ~/.wire/secrets.env itself
    <repo>/.wire/local/secrets.env per repository (git-ignored)

A value already in the environment wins over all of them.

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


def _file_values(path: Path, notes: list) -> dict:
    if not path.is_file():
        return {}
    if too_open(path):
        notes.append(f"{path} is readable by others; run chmod 600 on it. Skipped.")
        return {}
    try:
        return parse(path.read_text(encoding="utf-8"))
    except OSError as exc:
        notes.append(f"{path}: {exc}")
        return {}


def layers(env: dict, repo: Path | None = None, home: Path | None = None, store=False) -> tuple:
    """([(source, values)] lowest first, notes). `store` is a keystore Store,
    None for no store, or False to pick the default for `env` and `home`."""
    from . import keystore
    notes = []
    personal, *repo_file = secret_files(repo, home)
    if store is False:
        store, _reason = keystore.store_for(env, home)
    out = [(str(personal), _file_values(personal, notes))]
    if store is not None and not (store.kind == "secrets-file" and store.path == personal):
        out.append((store.label, keystore.read_all(store)))  # the personal file is already read above
    for path in repo_file:
        out.append((str(path), _file_values(path, notes)))
    return out, notes


def load_secrets(env: dict, repo: Path | None = None, home: Path | None = None, store=False) -> tuple:
    """(env with the secrets added, notes). A value already in `env` wins.
    Returns notes about files skipped (unreadable or too open)."""
    merged = dict(env)
    found, notes = layers(env, repo, home, store)
    for _source, values in found:
        for k, v in values.items():
            if k not in env and v:
                merged[k] = v
    return merged, notes


def sources(env: dict, repo: Path | None = None, home: Path | None = None, store=False) -> dict:
    """For each known key: where the value in use comes from ("environment" or
    a layer's name), its last four characters, and the other places that also
    set it. Never the value."""
    from .keystore import hint
    found, _notes = layers(env, repo, home, store)
    out = {}
    for name in KNOWN:
        places = [(src, vals[name]) for src, vals in found if vals.get(name)]
        if env.get(name):
            out[name] = {"source": "environment", "hint": hint(env[name]), "also": [p for p, _ in places]}
        elif places:
            src, val = places[-1]
            out[name] = {"source": src, "hint": hint(val), "also": [p for p, _ in places[:-1]]}
        else:
            out[name] = {"source": None, "hint": "", "also": []}
    return out


def present(env: dict) -> dict:
    """Which known keys are set, by name only."""
    return {k: bool(env.get(k)) for k in KNOWN}
