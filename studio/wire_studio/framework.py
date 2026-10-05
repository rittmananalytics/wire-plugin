"""Locate and load the Wire framework files Studio reads.

Studio runs in one of two layouts:

- **repo**: inside a checkout of the Wire repository. The framework root is
  `wire/`, with `release-types/`, `specs/` and the command registry in
  `scripts/build-packages.sh`.
- **plugin**: inside a built Claude Code plugin. The framework root is the
  plugin root, with `release-types/`, `specs/` and one file per command in
  `commands/`.

Both give the same three things: the release-type YAML, the set of registered
command slugs, and the generate commands that opt out of auto-validate.
Command slugs are normalised to the hyphenated form the user types
(`requirements-generate`), because that is the only form both layouts share.
"""

import re
from functools import lru_cache
from pathlib import Path

import yaml

# specs/utils/runnable_set.md Step 1: the one status value that does not match
# a release-type file name.
RELEASE_TYPE_ALIASES = {"discovery": "discovery_shape_up"}


class Framework:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.release_types_dir = self.root / "release-types"
        self.specs_dir = self.root / "specs"
        if not self.release_types_dir.is_dir():
            raise FileNotFoundError(f"no release-types/ under {self.root}")
        build = self.root / "scripts" / "build-packages.sh"
        commands = self.root / "commands"
        if build.is_file():
            self.layout = "repo"
            self.commands = _commands_from_build_script(build)
        elif commands.is_dir():
            self.layout = "plugin"
            self.commands = {p.stem for p in commands.glob("*.md")}
        else:
            raise FileNotFoundError(
                f"no command registry under {self.root} "
                "(expected scripts/build-packages.sh or commands/)")
        self.no_auto_validate = _auto_validate_false(self.specs_dir)

    @lru_cache(maxsize=None)
    def release_type(self, name):
        resolved = RELEASE_TYPE_ALIASES.get(name, name)
        path = self.release_types_dir / f"{resolved}.yaml"
        if not path.exists():
            raise ValueError(f"release type {name!r} resolves to no YAML file")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def release_type_names(self):
        return sorted(p.stem for p in self.release_types_dir.glob("*.yaml"))

    def has_step(self, command, step):
        """Does this artifact's `<step>` exist as a registered command? A command
        registered with no lifecycle suffix (the droughty commands) is a single
        action, treated as a generate step only."""
        base = command.replace("/", "-")
        if f"{base}-{step}" in self.commands:
            return True
        return step == "generate" and base in self.commands

    def known_command(self, command):
        base = command.replace("/", "-")
        return base in self.commands or any(
            self.has_step(command, s) for s in ("generate", "validate", "review"))


def _commands_from_build_script(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"COMMANDS=\(\s*(.*?)\n\)", text, re.S)
    if not m:
        raise ValueError(f"COMMANDS array not found in {path}")
    return {
        e.split("|")[0].strip().strip('"').replace("/", "-")
        for e in m.group(1).splitlines()
        if e.strip().startswith('"')
    }


def _auto_validate_false(specs_dir):
    out = set()
    if not specs_dir.is_dir():
        return out
    for path in specs_dir.rglob("*.md"):
        head = path.read_text(encoding="utf-8", errors="replace").split("\n---", 1)[0]
        if not re.search(r"^auto_validate:\s*false", head, re.M):
            continue
        m = re.search(r"^artifact:\s*(\S+)", head, re.M)
        if m:
            out.add(m.group(1).strip().strip('"'))
    return out


def default_framework_root():
    """The framework this copy of Studio ships with: `wire/` in a repo checkout
    (studio/ sits inside it) or the plugin root in a built plugin."""
    return Path(__file__).resolve().parents[2]
