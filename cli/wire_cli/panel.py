"""The live panel: the Wire mod's band, kept on screen in the session.

ROADMAP.md phase 4. In Claude Code the Wire mod draws a band above the prompt
that stays put while the conversation scrolls. The session does the same with
a terminal scroll region: the bottom two rows are the panel, everything else
scrolls above it. The panel shows

    the status line (release, type, approvals, parked decisions, claim, context)
    what is running: the command, how long it has run, the last command or edit
      the agent started, and during `wire run` each lane with its time; a lane
      quiet for 30 minutes is flagged, as the mod's stall timer does
    when idle: the next action

A ticker redraws it once a second while something runs. Off when stdout is
not a terminal, the terminal is under 10 rows, TERM is dumb, or
WIRE_PANEL=false; the session then prints the status line when it changes,
as before.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
import threading
import time

HEIGHT = 2
STALL_SECONDS = 30 * 60  # the operating model's 30-minute rule, as in the mod's lane timer
DIM, RESET = "\x1b[2m", "\x1b[0m"


def wanted(env: dict, stdout=None) -> bool:
    stdout = stdout or sys.stdout
    if str(env.get("WIRE_PANEL", "true")).lower() in ("0", "false", "no", "off"):
        return False
    if (env.get("TERM") or "") == "dumb" or not hasattr(stdout, "isatty") or not stdout.isatty():
        return False
    return shutil.get_terminal_size((80, 24)).lines >= 10


def clock_text(seconds: float) -> str:
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def render(status: str, busy: str | None, busy_for: float, last: str | None, lanes: dict, now: float,
           next_action: str | None) -> list:
    """The panel's two lines (pure, for the tests). `lanes`: label -> (state, started, ended)."""
    second = ""
    if busy:
        parts = [f"running: {busy} {clock_text(busy_for)}"]
        if lanes:
            shown = []
            for label, (state, started, ended) in lanes.items():
                if state == "running":
                    quiet = now - started
                    mark = f" quiet {int(quiet // 60)}m (30-minute rule)" if quiet >= STALL_SECONDS else ""
                    shown.append(f"{label} {clock_text(quiet)}{mark}")
                else:
                    shown.append(f"{label} {state}")
            parts.append("lanes: " + ", ".join(shown))
        if last:
            parts.append(f"last: {last}")
        second = " · ".join(parts)
    elif next_action:
        second = f"next: {next_action}"
    return [status or "", second]


class Panel:
    def __init__(self, out=None, size=None, clock=time.monotonic):
        self.out = out or sys.stdout
        self._size = size or (lambda: shutil.get_terminal_size((80, 24)))
        self.clock = clock
        self.lock = threading.RLock()
        self.active = False
        self.paused = False
        self.status = ""
        self.next_action: str | None = None
        self.busy: str | None = None
        self.busy_since = 0.0
        self.last: str | None = None
        self.lanes: dict = {}
        self.rows = 0
        self._resized = False
        self._stop = threading.Event()
        self._ticker: threading.Thread | None = None
        self._old_winch = None

    # ------------------------------------------------------------ terminal

    def _raw(self, s: str) -> None:
        self.out.write(s)
        self.out.flush()

    def _region(self) -> None:
        """Reserve the bottom rows: make room, put the cursor on the last scrolling
        row, set the scroll region (which homes the cursor), put the cursor back."""
        self.rows = self._size().lines
        top = self.rows - HEIGHT
        self._raw("\n" * HEIGHT + f"\x1b[{HEIGHT}A" + "\x1b7" + f"\x1b[1;{top}r" + "\x1b8")

    def start(self) -> None:
        with self.lock:
            self._region()
            self.active = True
            self._draw_locked()
        try:
            self._old_winch = signal.signal(signal.SIGWINCH, self._on_winch)
        except (ValueError, AttributeError, OSError):  # not the main thread, or no SIGWINCH
            self._old_winch = None
        self._ticker = threading.Thread(target=self._tick, name="wire-panel", daemon=True)
        self._ticker.start()

    def stop(self) -> None:
        self._stop.set()
        with self.lock:
            if not self.active:
                return
            self.active = False
            rows = self._size().lines
            clear = "".join(f"\x1b[{rows - HEIGHT + 1 + i};1H\x1b[2K" for i in range(HEIGHT))
            self._raw("\x1b7\x1b[r" + clear + "\x1b8")
        if self._old_winch is not None:
            try:
                signal.signal(signal.SIGWINCH, self._old_winch)
            except (ValueError, OSError):
                pass

    def _on_winch(self, *_a) -> None:
        self._resized = True  # redrawn by the next draw; no lock taken in a signal handler

    def _tick(self) -> None:
        while not self._stop.wait(1.0):
            if self.busy:
                self.draw()

    # ------------------------------------------------------------ output through the panel

    def write(self, s: str) -> None:
        with self.lock:
            self.out.write(s)
            self.out.flush()

    def print(self, *parts) -> None:
        self.write(" ".join(str(p) for p in parts) + "\n")

    # ------------------------------------------------------------ state

    def set_status(self, status: str, next_action: str | None = None) -> None:
        with self.lock:
            self.status, self.next_action = status, next_action
        self.draw()

    def begin(self, label: str) -> None:
        with self.lock:
            self.busy, self.busy_since, self.last, self.lanes = label, self.clock(), None, {}
        self.draw()

    def note(self, line: str) -> None:
        with self.lock:
            self.last = line
        self.draw()

    def lane(self, label: str, state: str) -> None:
        with self.lock:
            now = self.clock()
            _s, started, _e = self.lanes.get(label, (None, now, None))
            self.lanes[label] = (state, started if state != "running" else now, None if state == "running" else now)
        self.draw()

    def end(self) -> None:
        with self.lock:
            self.busy, self.last, self.lanes = None, None, {}
        self.draw()

    def pause(self):
        """Stop redrawing while the person types an answer (readline owns the line)."""
        panel = self

        class _Paused:
            def __enter__(self):
                with panel.lock:
                    panel.paused = True

            def __exit__(self, *exc):
                with panel.lock:
                    panel.paused = False
                panel.draw()
        return _Paused()

    def lines(self) -> list:
        with self.lock:
            now = self.clock()
            return render(self.status, self.busy, now - self.busy_since, self.last, dict(self.lanes), now, self.next_action)

    def draw(self) -> None:
        with self.lock:
            if self.active and not self.paused:
                self._draw_locked()

    def _draw_locked(self) -> None:
        if self._resized:
            self._resized = False
            self._raw("\x1b7\x1b[r\x1b8")
            self._region()
        size = self._size()
        rows, cols = size.lines, size.columns
        out = ["\x1b7"]
        for i, text in enumerate(self.lines()):
            text = text[: max(1, cols - 1)]
            out.append(f"\x1b[{rows - HEIGHT + 1 + i};1H\x1b[2K{DIM}{text}{RESET}")
        out.append("\x1b8")
        self._raw("".join(out))


def from_env(env: dict) -> Panel | None:
    return Panel() if wanted(env) and os.name != "nt" else None
