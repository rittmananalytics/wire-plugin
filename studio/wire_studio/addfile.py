"""Add Files to release: copy a file the person picks into the repository.

Two of the operating system's own dialogs, one after the other, opened on the
machine Studio runs on (local mode only): the file picker, then the save
dialog, starting in the release's folder. Any file can be picked. The copy
goes only inside the repository: a location outside it, inside `.git/`, or on
a release's `status.md` or `execution_log.md` (the orchestrating session is
their single writer) is refused, and the save dialog opens again saying why.
Nothing is written until a location is accepted; cancelling either dialog
writes nothing.

The dialogs are AppleScript's `choose file` and `choose file name` on macOS
and `zenity` on Linux. Strings reach AppleScript only as arguments (`on run
argv`), never inside the script text. `Dialogs` can be replaced, so the path
rules are tested without opening a window.
"""

import shutil
import subprocess
import sys
from pathlib import Path

RECORD_FILES = ("status.md", "execution_log.md")
MAX_TRIES = 3


class AddFileError(ValueError):
    pass


def check_destination(repo, dest):
    """The resolved destination, or AddFileError saying why it is refused."""
    repo = Path(repo).resolve()
    dest = Path(dest)
    try:
        dest = dest.parent.resolve() / dest.name  # a link in the folder path is followed; the name is checked below
    except OSError as e:
        raise AddFileError(f"that location cannot be read: {e}") from e
    try:
        rel = dest.relative_to(repo)
    except ValueError:
        raise AddFileError("choose a location inside the repository") from None
    if not rel.parts:
        raise AddFileError("choose a file name, not the repository folder")
    if rel.parts[0] == ".git":
        raise AddFileError("files cannot be added inside .git/")
    if dest.is_symlink():
        raise AddFileError("that name is a link; choose another name")
    if dest.is_dir():
        raise AddFileError("that name is a folder; choose a file name")
    if len(rel.parts) >= 4 and rel.parts[:2] == (".wire", "releases") and rel.name in RECORD_FILES:
        raise AddFileError(f"{rel.name} is written only by the orchestrating session; choose another name")
    if not dest.parent.is_dir():
        raise AddFileError("that folder does not exist")
    return dest


def start_folder(repo, release):
    """The release's folder when it exists, else the repository."""
    repo = Path(repo).resolve()
    if release and "/" not in release and "\\" not in release and release not in (".", ".."):
        folder = repo / ".wire" / "releases" / release
        if folder.is_dir():
            return folder
    return repo


class Dialogs:
    """The operating system's file dialogs. choose() and save() return a path,
    or None when the person cancels."""

    def __init__(self, platform=None, run=subprocess.run, which=shutil.which):
        self.platform = platform or sys.platform
        self.run = run
        self.which = which

    def available(self):
        if self.platform == "darwin":
            return bool(self.which("osascript"))
        if self.platform.startswith("linux"):
            return bool(self.which("zenity"))
        return False

    def _out(self, argv):
        r = self.run(argv, capture_output=True, text=True)
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            if self.platform == "darwin" and "-128" not in err and err:
                raise AddFileError(f"the file dialog failed: {err}")
            return None  # cancelled
        out = (r.stdout or "").strip()
        return Path(out) if out else None

    def choose(self, prompt):
        if self.platform == "darwin":
            return self._out(["osascript", "-e", "on run argv", "-e", "tell me to activate",
                              "-e", "return POSIX path of (choose file with prompt (item 1 of argv))",
                              "-e", "end run", prompt])
        return self._out(["zenity", "--file-selection", f"--title={prompt}"])

    def save(self, prompt, folder, name):
        if self.platform == "darwin":
            return self._out(["osascript", "-e", "on run argv", "-e", "tell me to activate",
                              "-e", "return POSIX path of (choose file name with prompt (item 1 of argv) "
                                    "default name (item 2 of argv) default location (POSIX file (item 3 of argv)))",
                              "-e", "end run", prompt, name, str(folder)])
        return self._out(["zenity", "--file-selection", "--save", "--confirm-overwrite", f"--title={prompt}",
                          f"--filename={Path(folder) / name}"])


def add_file(repo, release=None, dialogs=None):
    """Pick a file, choose where it goes in the repository, copy it there.
    {"added": <path relative to the repository>} or {"cancelled": True}."""
    repo = Path(repo).resolve()
    dialogs = dialogs or Dialogs()
    if not dialogs.available():
        raise AddFileError("no file dialog is available on this machine (macOS, or Linux with zenity)")
    src = dialogs.choose("Choose a file to add to the release")
    if src is None:
        return {"cancelled": True}
    src = Path(src)
    if not src.is_file():
        raise AddFileError("choose a file, not a folder")
    folder, prompt = start_folder(repo, release), "Save the file in the repository"
    for _ in range(MAX_TRIES):
        dest = dialogs.save(prompt, folder, src.name)
        if dest is None:
            return {"cancelled": True}
        try:
            dest = check_destination(repo, dest)
        except AddFileError as e:
            prompt = f"{e}. Save the file in the repository"
            folder = start_folder(repo, release)
            continue
        if dest.exists() and dest.resolve() == src.resolve():
            raise AddFileError("that is the file you picked; choose another location")
        shutil.copyfile(src, dest)
        return {"added": dest.relative_to(repo).as_posix()}
    raise AddFileError("no location inside the repository was chosen; nothing was added")
