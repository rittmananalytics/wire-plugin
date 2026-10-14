#!/usr/bin/env python3
"""Personas (wire#301; rules in specs/utils/personas.md). Plain script, no AI call.

  persona.py list                         the persona list
  persona.py resolve [--as <persona>]     the persona for this run and where it came from
  persona.py show                         yours, its source, and the team roster
  persona.py set <persona> [--local]      yours in the team roster (or this clone only)
  persona.py clear [--local]              remove it

Lookup order: --as, then WIRE_PERSONA, then this clone's override
(.wire/local/persona.yml, git-ignored), then the team roster
(.wire/engagement/team.yml, committed) by git user.email, so a person's
persona follows them to any machine. Run in the engagement repository (or
pass --repo). /wire:persona (specs/persona.md) runs this script. The list is the yaml block in
specs/utils/personas.md, found next to this script in the framework.

The spec lint (wire/tests/lint_specs.py) uses variant_problems() to check a
command's `personas:` front matter against its `## Persona: <id>` sections.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

FRAMEWORK = Path(__file__).resolve().parent.parent
PERSONAS_SPEC = FRAMEWORK / "specs" / "utils" / "personas.md"
LOCAL_FILE = Path(".wire") / "local" / "persona.yml"
ROSTER_FILE = Path(".wire") / "engagement" / "team.yml"
IGNORE_LINE = ".wire/local/"
SECTION_RE = re.compile(r"^## Persona: (\S+)\s*$", re.M)


def load_personas(spec: Path = PERSONAS_SPEC) -> list[dict]:
    """The persona list from the spec's yaml block: [{id, name, focus}]."""
    text = spec.read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(personas:\n.*?)```", text, re.S)
    if not block:
        raise ValueError(f"{spec}: no ```yaml personas: block")
    personas, current = [], None
    for line in block.group(1).splitlines()[1:]:
        m = re.match(r"\s*-\s+id:\s*(\S+)\s*$", line)
        if m:
            current = {"id": m.group(1)}
            personas.append(current)
            continue
        m = re.match(r"\s+(name|focus):\s*(.+?)\s*$", line)
        if m and current is not None:
            current[m.group(1)] = m.group(2)
    if not personas:
        raise ValueError(f"{spec}: the personas block lists none")
    return personas


def read_local(repo: Path) -> str:
    path = repo / LOCAL_FILE
    if not path.exists():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*persona:\s*['\"]?([^'\"#\s]+)", line)
        if m:
            return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Team roster: .wire/engagement/team.yml
#
#   team:
#     - name: Jane Smith
#       emails: [jane.smith@example.com, jane@laptop.example]
#       persona: delivery-manager
#
# Read and written here without a YAML library (the plugin needs none for
# this); the reader also takes block lists for emails, for hand edits.
# ---------------------------------------------------------------------------

def parse_roster(text: str) -> list[dict]:
    team, current, in_emails = [], None, False
    for raw in text.splitlines():
        line = raw.split(" #", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line.strip() or line.strip() == "team:":
            continue
        m = re.match(r"\s*-\s+name:\s*(.+)$", line)
        if m:
            current = {"name": m.group(1).strip().strip("'\""), "emails": [], "persona": ""}
            team.append(current)
            in_emails = False
            continue
        if current is None:
            continue
        m = re.match(r"\s+emails:\s*\[(.*)\]\s*$", line)
        if m:
            current["emails"] = [e.strip().strip("'\"").lower() for e in m.group(1).split(",") if e.strip()]
            in_emails = False
            continue
        if re.match(r"\s+emails:\s*$", line):
            in_emails = True
            continue
        m = re.match(r"\s+-\s+(\S+@\S+)\s*$", line)
        if m and in_emails:
            current["emails"].append(m.group(1).strip("'\"").lower())
            continue
        m = re.match(r"\s+persona:\s*(\S*)\s*$", line)
        if m:
            current["persona"] = m.group(1).strip("'\"")
            in_emails = False
    return team


def format_roster(team: list[dict]) -> str:
    lines = ["# Who plays which role on this engagement (specs/utils/personas.md).",
             "# Matched on git user.email; set yours with /wire:persona set <persona>.", "team:"]
    for e in team:
        lines += [f"  - name: {e['name']}", f"    emails: [{', '.join(e['emails'])}]", f"    persona: {e['persona']}"]
    return "\n".join(lines) + "\n"


def read_roster(repo: Path) -> list[dict]:
    path = repo / ROSTER_FILE
    return parse_roster(path.read_text(encoding="utf-8")) if path.exists() else []


def roster_persona(team: list[dict], email: str) -> str:
    email = (email or "").strip().lower()
    for e in team:
        if email and email in e["emails"]:
            return e["persona"]
    return ""


def set_in_roster(team: list[dict], name: str, email: str, persona: str | None) -> tuple[list[dict], str]:
    """Set (persona) or clear (None) this person's entry. Matched on email, then
    on name, so one person keeps one entry across machines with different
    emails. Returns the new roster and what changed."""
    email = email.strip().lower()
    team = [dict(e, emails=list(e["emails"])) for e in team]
    entry = next((e for e in team if email in e["emails"]), None)
    added_email = False
    if entry is None:
        entry = next((e for e in team if e["name"].strip().lower() == name.strip().lower()), None)
        if entry is not None:
            entry["emails"].append(email)
            added_email = True
    if persona is None:
        if entry is None:
            return team, "no roster entry for you"
        team.remove(entry)
        return team, f"removed {entry['name']} from the roster"
    if entry is None:
        team.append({"name": name, "emails": [email], "persona": persona})
        return team, f"added {name} ({email}) as {persona}"
    before = entry["persona"]
    entry["persona"] = persona
    note = f"{entry['name']}: {before or 'none'} to {persona}" if before != persona else f"{entry['name']} is already {persona}"
    return team, note + (f"; added {email} to {entry['name']}'s emails" if added_email else "")


def git_user(repo: Path) -> tuple[str, str]:
    import subprocess

    def cfg(key):
        r = subprocess.run(["git", "-C", str(repo), "config", "--get", key], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    return cfg("user.name"), cfg("user.email")


def resolve(known: list[str], as_value: str | None, env_value: str | None, file_value: str | None,
            roster_value: str | None = None) -> dict:
    """{persona, source, unknown}: the first set of --as, WIRE_PERSONA, the
    clone's override, the team roster.

    The first value that is set decides; an unknown one gives no persona (it
    does not fall through to the next source), so a typo is reported, not
    silently replaced by another role.
    """
    for source, value in (("--as", as_value), ("WIRE_PERSONA", env_value), (str(LOCAL_FILE), file_value),
                          (str(ROSTER_FILE), roster_value)):
        value = (value or "").strip()
        if value:
            if value in known:
                return {"persona": value, "source": source, "unknown": None}
            return {"persona": None, "source": source, "unknown": value}
    return {"persona": None, "source": None, "unknown": None}


def variant_problems(known: list[str], frontmatter: dict, body: str) -> list[str]:
    """Lint rule: listed personas are known and each has its section; no stray sections."""
    listed = frontmatter.get("personas") or []
    sections = SECTION_RE.findall(body)
    problems = []
    for p in listed:
        if p not in known:
            problems.append(f"personas: '{p}' is not in the persona list (specs/utils/personas.md)")
        elif p not in sections:
            problems.append(f"personas: '{p}' is listed but has no '## Persona: {p}' section")
    for s in sections:
        if s not in listed:
            problems.append(f"'## Persona: {s}' section, but '{s}' is not listed in the front matter's personas")
    return problems


def set_persona(repo: Path, persona: str) -> list[str]:
    """Write the local file and make sure .wire/local/ is git-ignored. Returns what changed."""
    changed = []
    path = repo / LOCAL_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Your role on this engagement (specs/utils/personas.md). Personal: not committed.\npersona: {persona}\n", encoding="utf-8")
    changed.append(str(LOCAL_FILE))
    gitignore = repo / ".gitignore"
    lines = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    if not any(l.strip() in (IGNORE_LINE, IGNORE_LINE.rstrip("/"), "/" + IGNORE_LINE) for l in lines):
        text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        if text and not text.endswith("\n"):
            text += "\n"
        gitignore.write_text(text + IGNORE_LINE + "\n", encoding="utf-8")
        changed.append(".gitignore")
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="engagement repository (default: current directory)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("resolve")
    r.add_argument("--as", dest="as_value")
    sub.add_parser("show")
    s = sub.add_parser("set")
    s.add_argument("persona")
    s.add_argument("--local", action="store_true", help="this clone only (git-ignored), not the team roster")
    c = sub.add_parser("clear")
    c.add_argument("--local", action="store_true")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    personas = load_personas()
    known = [p["id"] for p in personas]

    if args.cmd == "list":
        for p in personas:
            print(f"{p['id']}: {p.get('name', '')}. {p.get('focus', '')}")
        return 0
    name, email = git_user(repo)
    current = lambda as_value=None: resolve(known, as_value, os.environ.get("WIRE_PERSONA"), read_local(repo),
                                            roster_persona(read_roster(repo), email))
    if args.cmd == "show":
        out = current()
        if out["persona"]:
            print(f"You ({email or 'no git user.email'}): {out['persona']} (from {out['source']})")
        elif out["unknown"]:
            print(f"You: none (unknown persona '{out['unknown']}' from {out['source']})")
        else:
            print(f"You ({email or 'no git user.email'}): none")
        team = read_roster(repo)
        print("Team:" if team else "Team: no roster yet (.wire/engagement/team.yml)")
        for e in team:
            print(f"  {e['name']}: {e['persona'] or 'none'}")
        return 0
    if args.cmd == "resolve":
        out = current(args.as_value)
        if out["persona"]:
            print(f"{out['persona']} (from {out['source']})")
        elif out["unknown"]:
            print(f"none (unknown persona '{out['unknown']}' from {out['source']}; known: {', '.join(known)})")
        else:
            print("none")
        return 0
    if args.cmd == "set":
        if args.persona not in known:
            print(f"unknown persona '{args.persona}'; known: {', '.join(known)}", file=sys.stderr)
            return 2
        if args.local:
            print(f"persona set to {args.persona} for this clone; changed: {', '.join(set_persona(repo, args.persona))}")
            return 0
        if not email:
            print("git user.email is not set, so you cannot be found in the team roster; set it, or use --local", file=sys.stderr)
            return 3
        team, note = set_in_roster(read_roster(repo), name or email.split("@")[0], email, args.persona)
        (repo / ROSTER_FILE).parent.mkdir(parents=True, exist_ok=True)
        (repo / ROSTER_FILE).write_text(format_roster(team), encoding="utf-8")
        print(f"{note}; changed: {ROSTER_FILE} (commit it to share)")
        return 0
    if args.cmd == "clear" and not args.local:
        if not email:
            print("git user.email is not set; use --local", file=sys.stderr)
            return 3
        team, note = set_in_roster(read_roster(repo), name, email, None)
        if note.startswith("removed"):
            (repo / ROSTER_FILE).write_text(format_roster(team), encoding="utf-8")
            note += f"; changed: {ROSTER_FILE} (commit it to share)"
        print(note)
        return 0
    if args.cmd == "clear":
        path = repo / LOCAL_FILE
        if path.exists():
            path.unlink()
            print(f"removed {LOCAL_FILE}")
        else:
            print("no persona set")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
