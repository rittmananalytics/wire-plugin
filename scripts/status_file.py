#!/usr/bin/env python3
"""status_file.py: read a release's status.md and ticket records, and say
when one has a key twice or does not parse (wire-plugin#2).

`yaml.safe_load` keeps the last value when a key appears twice in one block,
with no error. In a status file that can replace a new `reviewed_date` with an
old one, or hide a release claim. Every Wire reader of status.md loads it
through this module, so a duplicate is reported instead of read silently.

A problem is a dict:

  kind    duplicate | parse
  file    the path, when known
  line    the line in the file (1-based)
  key     duplicate: the key path, dotted (`artifacts.dashboards.reviewed_date`)
  first   duplicate: the line of the first copy
  drift   the `/wire:status-sync` drift category: status_duplicate_key or
          status_unparseable (specs/utils/status_sync.md Step 1b)
  message one plain sentence

It checks three places, the same ones Wire reads:

  - the YAML front matter of `status.md` (between the first two `---` lines)
  - the fenced YAML block under `## Artifacts` / `## Artifact Status` that
    3.x status files keep in the body
  - the front matter of each ticket record, `iterations/<ticket>.md`

Usage:
    python3 status_file.py check [<path> ...] [--json]

Each path is a client repository (has `.wire/`), a release folder (has
`status.md`) or a file. With no path, the current directory. Prints one line
per problem and exits 1 when there is any, 0 when there is none. Reads only.
Stdlib plus PyYAML.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

DRIFT = {"duplicate": "status_duplicate_key", "parse": "status_unparseable"}
BODY_BLOCK = re.compile(r"^##\s+Artifacts?(?:\s+Status)?\s*$.*?^```ya?ml\s*$(.*?)^```", re.M | re.S)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _key_text(node):
    if isinstance(node, yaml.ScalarNode):
        return str(node.value)
    return yaml.safe_dump(yaml.safe_load(yaml.serialize(node)), default_flow_style=True).strip()


def _duplicates(node, path, offset, out):
    if isinstance(node, yaml.MappingNode):
        seen = {}
        for key_node, value_node in node.value:
            if key_node.tag == "tag:yaml.org,2002:merge":
                continue
            key = _key_text(key_node)
            line = offset + key_node.start_mark.line + 1
            full = f"{path}.{key}" if path else key
            if key in seen:
                out.append({"kind": "duplicate", "line": line, "key": full, "first": seen[key],
                            "message": f"key `{full}` appears twice (first at line {seen[key]}); "
                                       "YAML keeps the last value, so the first is ignored"})
            else:
                seen[key] = line
            _duplicates(value_node, full, offset, out)
    elif isinstance(node, yaml.SequenceNode):
        for i, item in enumerate(node.value):
            _duplicates(item, f"{path}[{i}]", offset, out)


def load_yaml(text, offset=0):
    """(data, problems). `offset` is the number of file lines before `text`,
    so problem lines are file lines. Data is what `yaml.safe_load` gives;
    None when the text does not parse."""
    problems = []
    try:
        node = yaml.compose(text, Loader=yaml.SafeLoader)
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None) or getattr(e, "context_mark", None)
        line = offset + mark.line + 1 if mark else offset + 1
        reason = getattr(e, "problem", None) or str(e).splitlines()[0]
        return None, [{"kind": "parse", "line": line,
                       "message": f"does not parse as YAML: {reason}"}]
    if node is not None:
        _duplicates(node, "", offset, problems)
    return data, problems


def front_matter(text):
    """(data, body, problems) for a file with YAML front matter. A file that
    does not start with `---` has none: ({}, text, [])."""
    if not text.startswith("---"):
        return {}, text, []
    end = text.find("\n---", 3)
    head = text[3:end] if end >= 0 else text[3:]
    rest = text[end + 4:] if end >= 0 else ""
    body = rest.split("\n", 1)[1] if "\n" in rest else ""
    data, problems = load_yaml(head)
    return (data if isinstance(data, dict) else {}), body, problems


def body_artifacts(text):
    """(data, problems) for the fenced YAML block a 3.x status file keeps in
    its body under `## Artifacts` or `## Artifact Status`. Takes the whole
    file text so the lines are file lines."""
    start = 0
    if text.startswith("---"):
        end = text.find("\n---", 3)
        start = end + 4 if end >= 0 else len(text)
    m = BODY_BLOCK.search(text, start)
    if not m:
        return {}, []
    data, problems = load_yaml(m.group(1), offset=text[:m.start(1)].count("\n"))
    return (data if isinstance(data, dict) else {}), problems


def read_status(text):
    """(front matter, body, problems) for a status.md, with the 3.x body
    block's problems included."""
    data, body, problems = front_matter(text)
    _, more = body_artifacts(text)
    return data, body, problems + more


# ---------------------------------------------------------------------------
# Checking files
# ---------------------------------------------------------------------------
def check_text(text, name=""):
    """Problems in one status.md or ticket record."""
    if Path(name).name == "status.md":
        problems = read_status(text)[2]
    else:
        problems = front_matter(text)[2]
    for p in problems:
        p["file"] = name
        p["drift"] = DRIFT[p["kind"]]
    return problems


def release_files(release_dir):
    release_dir = Path(release_dir)
    out = [release_dir / "status.md"] if (release_dir / "status.md").is_file() else []
    folder = release_dir / "iterations"
    if folder.is_dir():
        out += [p for p in sorted(folder.glob("*.md")) if not p.name.endswith(".execution_log.md")]
    return out


def files_under(path):
    """The status files and ticket records a path names."""
    path = Path(path)
    if path.is_file():
        return [path]
    wire = path / ".wire"
    if wire.is_dir():
        out = []
        for status in sorted((wire / "releases").glob("*/status.md")):
            out += release_files(status.parent)
        for status in sorted(wire.glob("*/status.md")):  # pre-3.4 flat layout
            if status.parent.name not in {"releases", "engagement"}:
                out += release_files(status.parent)
        return out
    return release_files(path)


def check_paths(paths):
    problems = []
    for path in paths:
        for f in files_under(path):
            problems += check_text(f.read_text(encoding="utf-8", errors="replace"), str(f))
    return problems


def describe(p):
    return f"{p.get('file', '')}:{p['line']}: {p['message']}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("paths", nargs="*", default=["."])
    c.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    missing = [p for p in args.paths if not Path(p).exists()]
    if missing:
        print(f"No such path: {', '.join(missing)}", file=sys.stderr)
        return 2
    problems = check_paths(args.paths)
    if args.json:
        print(json.dumps({"problems": problems}, indent=2))
    else:
        for p in problems:
            print(describe(p))
        if not problems:
            print("No duplicate keys or parse errors found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
