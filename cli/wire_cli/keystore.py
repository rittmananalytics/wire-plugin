"""Where Wire Studio's Settings page keeps the API keys.

    macOS          the login Keychain, through /usr/bin/security; one item per
                   key, service `wire`, account the key's name
    Linux, WSL     ~/.wire/secrets.env, the file the CLI already reads, written
                   with owner-only permissions (600, folder 700)
    Windows        nowhere: the Wire CLI does not run on Windows (use WSL)

`load_secrets` reads them for every harness run, so the CLI in a terminal and
Studio's sessions see the same keys.

A value never goes on a command line, where other processes could read it:
on macOS it is written through `security -i`, which reads its command from
standard input. The file is replaced in one step (a temporary file, then a
rename), keeping every other line. Values are never printed or logged;
`hint()` gives the last four characters only.

The store belongs to the person signed in to the machine, so it is used only
when HOME is that person's home directory. A test or a sandbox with another
HOME never reads or writes it. `WIRE_KEYSTORE=none` turns it off;
`WIRE_KEYSTORE=file:<path>` uses a JSON file instead and
`WIRE_KEYSTORE=env:<path>` a secrets file (tests only).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

SERVICE = "wire"
# The keys a person can set from Studio's Settings page, with their labels and
# the prefix every real key of that kind starts with.
SETTABLE = (
    {"name": "ANTHROPIC_API_KEY", "label": "Claude (Anthropic) API key", "prefix": "sk-ant-"},
    {"name": "OPENAI_API_KEY", "label": "OpenAI API key", "prefix": "sk-"},
)
NAMES = tuple(k["name"] for k in SETTABLE)
# No spaces, quotes or line breaks: nothing a shell or `security -i` would read
# as anything but the value.
VALUE_RE = re.compile(r"^[A-Za-z0-9_\-.:+/=]{20,512}$")


class KeystoreError(Exception):
    pass


def check_value(name: str, value: str) -> str:
    """The value stripped, or raise KeystoreError saying what is wrong."""
    spec = next((k for k in SETTABLE if k["name"] == name), None)
    if spec is None:
        raise KeystoreError(f"{name} cannot be set here; only {', '.join(NAMES)}")
    if not isinstance(value, str):
        raise KeystoreError("the key must be text")
    value = value.strip()
    if not VALUE_RE.match(value):
        raise KeystoreError("that does not look like an API key: paste the whole key, with no spaces or quotes")
    if not value.startswith(spec["prefix"]):
        raise KeystoreError(f"{spec['label']}s start with {spec['prefix']}; check you pasted the right key")
    return value


def hint(value: str | None) -> str:
    """The last four characters, for telling two keys apart."""
    return f"…{value[-4:]}" if value and len(value) >= 12 else ""


class Store:
    kind = ""
    label = ""

    def get(self, name: str) -> str | None:
        raise NotImplementedError

    def set(self, name: str, value: str) -> None:
        raise NotImplementedError

    def delete(self, name: str) -> None:
        raise NotImplementedError


def _run(argv: list, stdin: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KeystoreError(f"{argv[0]} could not be run: {exc}") from exc


class MacKeychain(Store):
    kind = "keychain"
    label = "macOS Keychain"

    def __init__(self, tool: str = "/usr/bin/security"):
        self.tool = tool

    def get(self, name):
        r = _run([self.tool, "find-generic-password", "-s", SERVICE, "-a", name, "-w"])
        return (r.stdout.rstrip("\n") or None) if r.returncode == 0 else None

    def set(self, name, value):
        # -U replaces an existing item. The command goes in on standard input.
        _run([self.tool, "-i"], stdin=f"add-generic-password -U -s {SERVICE} -a {name} -l Wire_{name} -w {value}\n")
        if self.get(name) != value:
            raise KeystoreError("the Keychain did not save the key; check the login keychain is unlocked")

    def delete(self, name):
        _run([self.tool, "delete-generic-password", "-s", SERVICE, "-a", name])
        if self.get(name) is not None:
            raise KeystoreError("the Keychain did not remove the key")


class SecretsFile(Store):
    """~/.wire/secrets.env: `KEY=value` lines, the format `secrets.parse` reads.
    Setting a key replaces its line (or adds one) and keeps every other line,
    comment and blank; removing it drops its lines."""
    kind = "secrets-file"

    def __init__(self, path: Path):
        self.path = Path(path)
        self.label = str(self.path)

    def _lines(self) -> list:
        try:
            return self.path.read_text(encoding="utf-8").split("\n")
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise KeystoreError(f"{self.path} could not be read: {exc}") from exc

    @staticmethod
    def _names(line: str, name: str) -> bool:
        return re.match(rf"^\s*(?:export\s+)?{re.escape(name)}\s*=", line) is not None

    def _write(self, lines: list) -> None:
        folder = self.path.parent
        folder.mkdir(parents=True, exist_ok=True)
        try:
            folder.chmod(0o700)
        except OSError:
            pass
        while lines and lines[-1] == "":
            lines = lines[:-1]
        text = "\n".join(lines) + "\n" if lines else ""
        tmp = folder / f".{self.path.name}.{os.getpid()}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            os.chmod(tmp, 0o600)
            os.replace(tmp, self.path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise KeystoreError(f"{self.path} could not be written: {exc}") from exc

    def get(self, name):
        from .secrets import parse  # noqa: PLC0415
        return parse("\n".join(self._lines())).get(name) or None

    def set(self, name, value):
        out, done = [], False
        for line in self._lines():
            if self._names(line, name):
                if not done:
                    out.append(f"{name}={value}")
                    done = True
                continue
            out.append(line)
        if not done:
            while out and out[-1] == "":
                out.pop()
            out.append(f"{name}={value}")
        self._write(out)

    def delete(self, name):
        self._write([line for line in self._lines() if not self._names(line, name)])


class FileStore(Store):
    """A JSON file, mode 600. For tests only (`WIRE_KEYSTORE=file:<path>`)."""
    kind = "file"
    label = "test key file"

    def __init__(self, path: Path):
        self.path = Path(path)

    def _all(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def get(self, name):
        return self._all().get(name) or None

    def set(self, name, value):
        data = self._all()
        data[name] = value
        self._write(data)

    def delete(self, name):
        data = self._all()
        data.pop(name, None)
        self._write(data)


def real_home() -> Path | None:
    try:
        import pwd  # noqa: PLC0415  (not on Windows)
        return Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    except (ImportError, KeyError, OSError):
        return None


def store_for(env: dict, home: Path | None = None) -> tuple:
    """(Store or None, reason when None). `env` is the environment the run was
    given; `home` the HOME it uses (from env when not passed)."""
    setting = str(env.get("WIRE_KEYSTORE") or "auto")
    if setting.startswith("file:"):
        return FileStore(Path(setting[len("file:"):])), None
    if setting.startswith("env:"):
        return SecretsFile(Path(setting[len("env:"):])), None
    if setting in ("none", "off", "false", "0"):
        return None, "turned off by WIRE_KEYSTORE"
    home = Path(home) if home else (Path(env["HOME"]) if env.get("HOME") else Path.home())
    real = real_home()
    if real is None:
        return None, "the Wire CLI does not run on this operating system; use WSL"
    if home.resolve() != real:
        return None, "HOME is not the signed-in user's home directory"
    if sys.platform == "darwin" and Path("/usr/bin/security").is_file():
        return MacKeychain(), None
    if os.name == "posix":
        return SecretsFile(home / ".wire" / "secrets.env"), None
    return None, "the Wire CLI does not run on this operating system; use WSL"


def read_all(store: Store | None) -> dict:
    """The settable keys present in the store, name to value."""
    out = {}
    if store is None:
        return out
    for name in NAMES:
        try:
            value = store.get(name)
        except KeystoreError:
            value = None
        if value:
            out[name] = value
    return out
