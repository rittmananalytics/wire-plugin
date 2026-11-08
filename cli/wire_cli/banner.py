"""The Wire banner: the lowercase wordmark and the stepped mark from
wire/docs/images/wire_logo_transparent.svg, in block characters.

Shown once, when the interactive session opens (`wire` alone), never by a
command run from the command line or inside the session. On a dark
terminal the ink parts are white, on a light one the brand ink; when the
theme is unknown (theme.py could not tell) they take the default foreground. The ASCII logo Codex
draws when its own interactive TUI starts belongs to the Codex binary;
replacing it is a fork change (wire#408). The headless `codex exec` runs the
CLI makes show no logo.
"""

from __future__ import annotations

import os
import sys

# The wordmark and the mark are drawn with shade characters, as Codex's own
# logo is, from full-cell glyphs: letters in medium shade (ink), the mark's
# blue step in dark shade. Seven rows: the dot of the i, a gap, five rows of
# x-height. `.` is an empty cell.
SHADE = "▒"        # the letters and the mark's ink step
SHADE_BLUE = "▓"   # the mark's blue step
GLYPHS = {
    "w": ["..........", "..........", "##..##..##", "##..##..##", "##..##..##", "##..##..##", "..######.."],
    "i": ["##", "..", "##", "##", "##", "##", "##"],
    "r": [".......", ".......", "##.####", "####...", "##.....", "##.....", "##....."],
    "e": ["......", "......", ".####.", "##..##", "######", "##....", ".#####"],
}
# The mark sits one row above the x-height, as it does in the logo.
MARK_INK_CELLS = ["........", "####....", "####....", "##......", "........", "........", "........"]
MARK_BLUE_CELLS = ["........", "....####", "....####", "..######", "########", "........", "........"]
GAP = ".."


def _rows(text: str) -> list:
    """The wordmark's seven rows as cell strings ('#' ink, '.' empty)."""
    glyphs = [GLYPHS[c] for c in text]
    return ["".join(GAP.join(g[r] for g in glyphs)) for r in range(7)]


WORDMARK = _rows("wire")
MARK_INK = MARK_INK_CELLS
MARK_BLUE = MARK_BLUE_CELLS

INK_LIGHT = "\x1b[38;2;26;27;35m"   # #1A1B23, the wordmark on a light background
INK_DARK = "\x1b[97m"                # bright white, the wordmark on a dark background
INK_UNKNOWN = ""                      # the terminal's default foreground, readable on either
BLUE = "\x1b[38;2;79;96;255m"        # #4F60FF
RESET = "\x1b[0m"


def ink_for(theme: str | None) -> str:
    return {"light": INK_LIGHT, "dark": INK_DARK}.get(theme or "", INK_UNKNOWN)


def banner(color: bool | None = None, version: str = "", theme: str | None = None) -> str:
    """The banner, with a blank line above it. `theme` is dark, light or None
    (unknown: the ink parts use the terminal's default foreground)."""
    if color is None:
        color = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    ink_code = ink_for(theme)

    def ink(ch: str) -> str:
        return (ink_code + ch + RESET) if (color and ink_code) else ch

    def blue(ch: str) -> str:
        return (BLUE + ch + RESET) if color else ch

    lines = [""]
    for word, mark_ink, mark_blue in zip(WORDMARK, MARK_INK, MARK_BLUE):
        word_text = "".join(ink(SHADE) if c == "#" else " " for c in word)
        mark_text = "".join(blue(SHADE_BLUE) if b == "#" else (ink(SHADE) if i == "#" else " ")
                            for i, b in zip(mark_ink, mark_blue))
        lines.append(word_text + "      " + mark_text)
    tail = f"  Wire CLI {version} (experimental)".rstrip()
    return "\n".join(lines) + "\n\n" + tail + "\n"


