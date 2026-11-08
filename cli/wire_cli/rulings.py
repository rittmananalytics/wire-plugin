"""The director's record writes from the session (ROADMAP.md phase 2): approvals,
parked decisions and rulings, in the forms the Wire mod writes in Claude Code
(hooks/wire/review.ts) and specs/utils/director_operating_model.md defines.

- /approve <artifact> [--final] [--as internal|client] [--evidence <url>]
  appends a `review_events` entry on the artifact in status.md; --final also
  sets review: approved, reviewed_by and reviewed_date.
- /park <artifact> "<question>" [--awaiting <who>]
  appends a `parked_decisions` entry (record.append_parked_decision).
- /rule <PD-n | artifact.depends_on.dep> <ruling> [-- <reason>]
  appends `## R-n | when | who | summary` to decisions.md the moment it is
  given; a ruling on a parked decision also removes that entry from
  status.md, since the ruling now holds the question and the answer.

Pure text in, text out. The session writes the files (the single writer).
"""

from __future__ import annotations

import re
import shlex

RULING_HEAD = re.compile(r"^##\s*R-(\d+)\s*\|", re.M)


def _yq(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- arguments

def parse_approve(args: str) -> dict:
    try:
        toks = shlex.split(args or "")
    except ValueError as exc:
        return {"error": f"cannot read the arguments: {exc}"}
    out = {"artifact": None, "final": False, "as": "internal", "evidence": None}
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "--final":
            out["final"] = True
        elif t == "--as" and i + 1 < len(toks):
            i += 1
            out["as"] = toks[i]
        elif t == "--evidence" and i + 1 < len(toks):
            i += 1
            out["evidence"] = toks[i]
        elif not t.startswith("--") and out["artifact"] is None:
            out["artifact"] = t
        else:
            return {"error": f"unexpected {t!r}. /approve <artifact> [--final] [--as internal|client] [--evidence <url>]"}
        i += 1
    if not out["artifact"] or not re.match(r"^[A-Za-z0-9_]+$", out["artifact"]):
        return {"error": "an artifact id is required. /approve <artifact> [--final] [--as internal|client] [--evidence <url>]"}
    if out["as"] not in ("internal", "client"):
        return {"error": "--as is internal or client"}
    return out


def parse_park(args: str) -> dict:
    try:
        toks = shlex.split(args or "")
    except ValueError as exc:
        return {"error": f"cannot read the arguments: {exc}"}
    awaiting = None
    if "--awaiting" in toks:
        i = toks.index("--awaiting")
        awaiting = toks[i + 1] if i + 1 < len(toks) else None
        toks = toks[:i] + toks[i + 2:]
    if len(toks) < 2 or not re.match(r"^[A-Za-z0-9_]+$", toks[0]):
        return {"error": '/park <artifact> "<question>" [--awaiting <who>]'}
    return {"artifact": toks[0], "question": " ".join(toks[1:]), "awaiting": awaiting}


def parse_rule(args: str) -> dict:
    """`<target> <ruling> [-- <reason>]`; the target is PD-n or artifact.depends_on.dep."""
    text = (args or "").strip()
    m = re.match(r"^(\S+)\s+(.+)$", text, re.S)
    if not m:
        return {"error": "/rule <PD-n | artifact.depends_on.dep> <ruling> [-- <reason>]"}
    target, rest = m.group(1), m.group(2).strip()
    ruling, _, reason = rest.partition(" -- ")
    if not (re.match(r"^PD-\d+$", target) or re.match(r"^[A-Za-z0-9_]+\.depends_on\.[A-Za-z0-9_]+$", target)):
        return {"error": f"{target!r} is neither a parked decision (PD-n) nor <artifact>.depends_on.<dep>"}
    return {"target": target, "ruling": ruling.strip(), "reason": reason.strip()}


# ---------------------------------------------------------------- status.md

def _artifact_range(lines: list, artifact: str):
    top = next((i for i, l in enumerate(lines) if re.match(r"^artifacts:", l)), -1)
    if top < 0:
        return None
    start = -1
    for i in range(top + 1, len(lines)):
        l = lines[i]
        if re.match(r"^\S", l) and l.strip():
            break
        if re.match(rf"^  {re.escape(artifact)}:", l):
            start = i
            break
    if start < 0:
        return None
    flow = bool(re.match(r"^  [A-Za-z0-9_]+:\s*\{", lines[start]))
    end = start + 1
    while end < len(lines) and (re.match(r"^\s{4,}", lines[end]) or not lines[end].strip()):
        end += 1
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return start, end, flow


def append_review_event(status_text: str, artifact: str, actor: str, date: str, kind: str = "internal",
                        evidence: str | None = None, final: bool = False):
    """The new text, or {"error": ...}. Mirrors review.ts appendReviewEvent."""
    lines = status_text.split("\n")
    rng = _artifact_range(lines, artifact)
    if not rng:
        return {"error": f"status.md has no artifacts.{artifact} entry."}
    start, end, flow = rng
    if flow:
        return {"error": f"artifacts.{artifact} is written on one line; expand it to the block form first (/wire:status-sync)."}
    block = lines[start + 1:end]
    item = [f"      - actor: {_yq(actor)}", f"        date: {_yq(date)}", f"        kind: {kind}"]
    if evidence:
        item.append(f"        evidence: {_yq(evidence)}")
    item.append("        outcome: approved")
    idx = next((i for i, l in enumerate(block) if re.match(r"^    review_events:", l)), -1)
    if idx >= 0:
        at = idx + 1
        while at < len(block) and re.match(r"^\s{6,}", block[at]):
            at += 1
        block[idx] = re.sub(r"\[\s*\]\s*$", "", block[idx]).rstrip()
        block[at:at] = item
    else:
        block += ["    review_events:"] + item
    if final:
        def setkey(key, value, after):
            i = next((j for j, l in enumerate(block) if re.match(rf"^    {key}:", l)), -1)
            if i >= 0:
                block[i] = f"    {key}: {value}"
            else:
                r = next((j for j, l in enumerate(block) if re.match(rf"^    {after}:", l)), -1)
                block.insert(r + 1 if r >= 0 else len(block), f"    {key}: {value}")
        setkey("review", "approved", "validate")
        setkey("reviewed_by", _yq(actor), "review")
        setkey("reviewed_date", date, "reviewed_by")
    return "\n".join(lines[:start + 1] + block + lines[end:])


def parked_decision(status_text: str, pd_id: str) -> dict | None:
    """The parked decision's fields (artifact, question) as written, or None."""
    lines = status_text.split("\n")
    for i, l in enumerate(lines):
        if re.match(rf"^  - id:\s*{re.escape(pd_id)}\s*$", l):
            fields = {"id": pd_id}
            for j in range(i + 1, len(lines)):
                m = re.match(r"^    ([a-z_]+):\s*(.*)$", lines[j])
                if not m:
                    break
                v = m.group(2).strip()
                fields[m.group(1)] = v[1:-1].replace('\\"', '"') if v.startswith('"') and v.endswith('"') else v
            return fields
    return None


def remove_parked_decision(status_text: str, pd_id: str) -> str:
    lines = status_text.split("\n")
    out, skip = [], False
    for l in lines:
        if re.match(rf"^  - id:\s*{re.escape(pd_id)}\s*$", l):
            skip = True
            continue
        if skip and re.match(r"^    \S", l):
            continue
        skip = False
        out.append(l)
    text = "\n".join(out)
    # an emptied block reads as an empty list
    return re.sub(r"(?m)^parked_decisions:\n(?=\S|---)", "parked_decisions: []\n", text)


# ---------------------------------------------------------------- decisions.md

def next_ruling_id(decisions_text: str) -> str:
    ids = [int(n) for n in RULING_HEAD.findall(decisions_text or "")]
    return f"R-{(max(ids) + 1) if ids else 1}"


def summary_of(ruling: str, words: int = 5) -> str:
    return " ".join(re.sub(r"[|\n]", " ", ruling).split()[:words])


def append_ruling(decisions_text: str, when: str, who: str, applies_to: str, ruling: str, reason: str = "",
                  release: str = "") -> tuple:
    """(new text, ruling id). Creates the file's heading when it is empty."""
    rid = next_ruling_id(decisions_text)
    text = decisions_text or (f"# Decisions: {release}\n" if release else "# Decisions\n")
    if not text.endswith("\n"):
        text += "\n"
    body = ruling.strip().rstrip(".") + "."
    if reason:
        body += f" Reason: {reason.strip().rstrip('.')}."
    text += f"\n## {rid} | {when} | {who} | {summary_of(ruling)}\nApplies to: {applies_to}\nRuling: {body}\n"
    return text, rid
