"""Studio's Session view: the Wire CLI's session, driven from the page.

Studio does not run Wire itself. It loads the CLI's session module
(`wire_cli/web_session.py`) from the CLI that ships beside it (`<framework
root>/cli`), starts sessions there, and relays lines in and events out. The
session is the single writer of the record, as in a terminal. Local mode
only: hosted Studio has no sessions.

The Claude Code plugin (from 4.6.4) and the Codex plugin both ship the CLI
beside Studio. When it is not there (an older plugin) or cannot be loaded,
the view says why and the rest of Studio is unchanged.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def cli_root(framework_root: Path) -> Path | None:
    for candidate in (Path(framework_root) / "cli", Path(framework_root).parent / "cli"):
        if (candidate / "wire_cli" / "web_session.py").is_file():
            return candidate
    return None


class Unavailable(Exception):
    pass


def load(framework_root: Path, repo: Path, env: dict | None = None):
    """A `Sessions` object for `repo`, or raise Unavailable with the reason."""
    root = cli_root(framework_root)
    if root is None:
        raise Unavailable("the Wire CLI is not beside this Studio; update the Wire plugin to 4.6.4 or later "
                          "(/plugin update wire@rittman-analytics, then /reload-plugins)")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from wire_cli.web_session import Sessions  # noqa: PLC0415
    except ImportError as exc:
        raise Unavailable(f"the Wire CLI beside Studio could not be loaded: {exc}") from exc
    return Sessions(Path(repo), dict(os.environ if env is None else env))


def cli_modules(framework_root: Path, *names: str) -> tuple:
    """Modules of the CLI beside Studio (`wire_cli.<name>`, "" for the package), or raise
    Unavailable. The CLI owns where keys are kept, the MCP selection and the
    machine check, so Studio and `wire` in a terminal agree."""
    import importlib  # noqa: PLC0415
    root = cli_root(framework_root)
    if root is None:
        raise Unavailable("the Wire CLI is not beside this Studio; update the Wire plugin to 4.6.4 or later "
                          "(/plugin update wire@rittman-analytics, then /reload-plugins)")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        return tuple(importlib.import_module(f"wire_cli.{n}" if n else "wire_cli") for n in names)
    except ImportError as exc:
        raise Unavailable(f"the Wire CLI beside Studio could not be loaded: {exc}") from exc


def key_modules(framework_root: Path):
    """(keystore, secrets): the Settings page's API keys."""
    return cli_modules(framework_root, "keystore", "secrets")
