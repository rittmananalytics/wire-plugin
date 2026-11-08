"""Studio's Session view: the Wire CLI's session, driven from the page.

Studio does not run Wire itself. It loads the CLI's session module
(`wire_cli/web_session.py`) from the CLI that ships beside it (`<framework
root>/cli`), starts sessions there, and relays lines in and events out. The
session is the single writer of the record, as in a terminal. Local mode
only: hosted Studio has no sessions.

When the CLI is not beside Studio (the Claude Code plugin ships Studio
without it) or cannot be loaded (PyYAML missing, an old CLI), the view says
why and the rest of Studio is unchanged.
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
        raise Unavailable("the Wire CLI is not installed beside this Studio (it ships in the Codex plugin "
                          "and the CLI install, not the Claude Code plugin)")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    try:
        from wire_cli.web_session import Sessions  # noqa: PLC0415
    except ImportError as exc:
        raise Unavailable(f"the Wire CLI beside Studio could not be loaded: {exc}") from exc
    return Sessions(Path(repo), dict(os.environ if env is None else env))
