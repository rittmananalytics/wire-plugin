"""Is the terminal dark or light?

No terminal reports "dark mode" as such. Three sources, first answer wins:

1. WIRE_THEME=dark|light in the environment (the override).
2. COLORFGBG, which some terminals set to "<fg>;<bg>" with ANSI colour
   numbers: a background of 0 to 6 or 8 is dark, 7 or 15 is light.
3. The OSC 11 query: the terminal is asked for its background colour on the
   tty and answers `rgb:RRRR/GGGG/BBBB` (Terminal.app, iTerm2, kitty,
   WezTerm, Alacritty, most others). Perceived luminance below 0.5 is dark.
   The query waits at most 150 ms and leaves the tty as it found it.

None when nothing answers; the caller then uses the terminal's default
foreground, which is readable on either background by definition.
"""

from __future__ import annotations

import os
import re
import select
import sys

OSC11_REPLY = re.compile(r"\x1b\]11;rgb:([0-9a-fA-F]+)/([0-9a-fA-F]+)/([0-9a-fA-F]+)")


def _channel(hex_text: str) -> float:
    """A 1 to 4 hex-digit colour channel as 0.0 to 1.0."""
    return int(hex_text, 16) / (16 ** len(hex_text) - 1)


def luminance(r: float, g: float, b: float) -> float:
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def theme_from_colorfgbg(value: str | None) -> str | None:
    if not value or ";" not in value:
        return None
    try:
        bg = int(value.split(";")[-1])
    except ValueError:
        return None
    if bg in (7, 15):
        return "light"
    if 0 <= bg <= 8:
        return "dark"
    return None


def theme_from_reply(reply: str) -> str | None:
    m = OSC11_REPLY.search(reply or "")
    if not m:
        return None
    r, g, b = (_channel(m.group(i)) for i in (1, 2, 3))
    return "dark" if luminance(r, g, b) < 0.5 else "light"


def query_background(timeout: float = 0.15) -> str | None:
    """The terminal's OSC 11 reply, or None. Needs a tty on stdin and stdout."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return None
    try:
        import termios
        import tty
    except ImportError:
        return None
    fd = sys.stdin.fileno()
    try:
        saved = termios.tcgetattr(fd)
    except termios.error:
        return None
    reply = ""
    try:
        tty.setcbreak(fd)
        # Echo off while the terminal answers, so the reply never reaches the screen.
        attrs = termios.tcgetattr(fd)
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        sys.stdout.write("\x1b]11;?\x07")
        sys.stdout.flush()
        deadline = timeout
        while deadline > 0:
            ready, _, _ = select.select([fd], [], [], deadline)
            if not ready:
                break
            chunk = os.read(fd, 64).decode("utf-8", errors="replace")
            reply += chunk
            if "\x07" in chunk or "\x1b\\" in chunk:
                break
            deadline = timeout / 3
    except (OSError, ValueError):
        return None
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSANOW, saved)
        except termios.error:
            pass
    return reply or None


def detect_theme(env: dict | None = None) -> str | None:
    env = os.environ if env is None else env
    override = (env.get("WIRE_THEME") or "").strip().lower()
    if override in ("dark", "light"):
        return override
    from_env = theme_from_colorfgbg(env.get("COLORFGBG"))
    if from_env:
        return from_env
    return theme_from_reply(query_background() or "")
