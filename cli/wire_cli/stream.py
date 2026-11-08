"""What a person watching a run sees while it runs (ROADMAP.md phase 2).

The harness hands over the reply as it is written (text) and a line for each
command, edit or tool call as it starts (activity). This keeps the two apart
on the terminal: activity lines go on their own line, dimmed, and the reply
carries on below them.
"""

from __future__ import annotations

import sys

DIM, RESET = "\x1b[2m", "\x1b[0m"


class Stream:
    def __init__(self, write=None, color: bool = False, on_note=None, on_lane=None, pause=None):
        self._write = write or _stdout_write
        self.color = color
        self.at_line_start = True
        self.wrote = False
        self.on_note = on_note    # the live panel's "last:" (panel.py)
        self.on_lane = on_lane    # the live panel's lanes during `wire run`
        self.pause = pause        # a context manager that holds the panel while the person types

    def text(self, s: str) -> None:
        if not s:
            return
        self._write(s)
        self.at_line_start = s.endswith("\n")
        self.wrote = True

    def activity(self, line: str) -> None:
        if not self.at_line_start:
            self._write("\n")
        shown = f"  · {line}"
        self._write((f"{DIM}{shown}{RESET}" if self.color else shown) + "\n")
        self.at_line_start = True
        if self.on_note:
            self.on_note(line)

    def lane(self, label: str, state: str) -> None:
        if self.on_lane:
            self.on_lane(label, state)

    def end(self) -> None:
        """Finish the line the reply was on."""
        if not self.at_line_start:
            self._write("\n")
            self.at_line_start = True

    def asking(self, ask):
        """The person's answer function, wrapped so its prompt starts on a new line."""
        if ask is None:
            return None

        def wrapped(prompt: str) -> str:
            self.end()
            if self.pause is not None:
                with self.pause():
                    return ask(prompt)
            return ask(prompt)
        return wrapped


def _stdout_write(s: str) -> None:
    sys.stdout.write(s)
    sys.stdout.flush()


def for_terminal(env: dict) -> Stream | None:
    """A Stream on stdout when it is a terminal, else None (pipes and CI get the final message only)."""
    if not sys.stdout.isatty():
        return None
    return Stream(color=not env.get("NO_COLOR"))
