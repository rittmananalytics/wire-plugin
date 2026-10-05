"""Stage 1 of "Studio sends commands": open Claude Code with a directive.

Studio does not run Wire commands itself. It opens a new terminal in the
client repository running `claude "<directive>"`, so the director starts an
ordinary interactive session with the directive already typed. The session
does the work through the real Wire commands, holds or asks for the release
claim, and stays the single writer of the record. Nothing here writes to the
repository.

`build_launch` is pure (repository, directive, mode, platform in; argv out) so
the quoting can be tested without opening a terminal. The directive reaches the
shell only through `shlex.quote`, and AppleScript only through `_applescript_str`.
"""

import re
import shlex
import shutil
import subprocess
import sys

MAX_DIRECTIVE = 4000
PLACEHOLDER = re.compile(r"<(your decision|why|[a-z ]{2,40})>", re.I)
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
MODES = ("auto", "terminal", "linux", "print")


class LaunchError(ValueError):
    pass


def check_directive(directive):
    """A directive must be filled in (no `<your decision>` placeholders left),
    short, single-purpose text with no control characters."""
    if not isinstance(directive, str) or not directive.strip():
        raise LaunchError("the directive is empty")
    if len(directive) > MAX_DIRECTIVE:
        raise LaunchError(f"the directive is longer than {MAX_DIRECTIVE} characters")
    if CONTROL.search(directive):
        raise LaunchError("the directive contains control characters")
    m = PLACEHOLDER.search(directive)
    if m:
        raise LaunchError(f"replace the placeholder {m.group(0)} before running")
    return directive.strip()


def _applescript_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def shell_command(repo, directive, claude="claude"):
    """The one line the terminal runs. WIRE_INVOKED_BY=studio tags the session,
    so the Wire mod (4.1.0) records its commands as `invoked_by: studio` in
    telemetry (specs/utils/telemetry.md) and Studio's use can be measured."""
    return (f"cd {shlex.quote(str(repo))} && WIRE_INVOKED_BY=studio "
            f"{shlex.quote(claude)} {shlex.quote(directive)}")


def resolve_mode(mode, platform=None):
    platform = platform or sys.platform
    if mode != "auto":
        return mode
    if platform == "darwin":
        return "terminal"
    if platform.startswith("linux") and shutil.which("x-terminal-emulator"):
        return "linux"  # not tested on a Linux desktop yet
    return "print"


def build_launch(repo, directive, mode="auto", platform=None, claude="claude"):
    """Returns (mode, argv or None, the shell command line). argv is None in
    print mode: Studio shows the command for the director to run."""
    directive = check_directive(directive)
    mode = resolve_mode(mode, platform)
    if mode not in MODES:
        raise LaunchError(f"unknown launch mode {mode!r}")
    line = shell_command(repo, directive, claude)
    if mode == "terminal":
        script = f'tell application "Terminal"\nactivate\ndo script {_applescript_str(line)}\nend tell'
        return mode, ["osascript", "-e", script], line
    if mode == "linux":
        return mode, ["x-terminal-emulator", "-e", "bash", "-lc", line + "; exec bash"], line
    return "print", None, line


def launch(repo, directive, mode="auto"):
    """Open the terminal. Returns what happened, for the UI."""
    claude = shutil.which("claude")
    mode, argv, line = build_launch(repo, directive, mode, claude=claude or "claude")
    if not claude:
        return {"launched": False, "mode": "print", "command": line,
                "message": "Claude Code (`claude`) is not on PATH. Run this in a terminal yourself."}
    if argv is None:
        return {"launched": False, "mode": mode, "command": line,
                "message": "Studio is set to show commands, not open a terminal (--launch print, or no "
                           "supported terminal on this machine). Run this in a terminal yourself."}
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    return {"launched": True, "mode": mode, "command": line,
            "message": "Opened Claude Code in a new terminal. Approve the run plan there."}


def availability(mode="auto"):
    return {"mode": resolve_mode(mode), "claude_on_path": bool(shutil.which("claude"))}
