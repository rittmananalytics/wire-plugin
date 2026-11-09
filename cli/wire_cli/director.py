"""Release director mode: plain text is direction, not a prompt.

The person states intent ("get the semantic layer validated", "what is
left before the dbt review?"). The harness reads the release as data (the
states, the runnable set, the parked decisions, the last log rows, the
commands the release's graph knows) and answers with a short reply and the
Wire commands that carry the intent out, in full, as they would be typed
(director rule 7). The CLI, not the model, then shows the run plan (rule 8),
waits for go, and runs the commands one at a time in the repository with
WIRE_INVOKED_BY=orchestrator. The model resolves intent; it runs nothing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import framework as fw
from .harness import RunRequest, get_harness, parse_report
from .orchestrator import read_release, session_id

UTILITY_COMMANDS = ("status", "status-sync", "session-plan", "work", "delegate", "help", "start",
                    "business-rules-generate", "utils-pr-create", "new", "adopt")
REPLY_SCHEMA = Path(__file__).with_name("director_reply.schema.json")


def relevant_commands(cat: dict, resolved: dict) -> list:
    """Catalogue entries for the release's artifacts, plus the utilities."""
    arts = {g["command"] for g in resolved["graph"]}
    out = []
    for name, entry in sorted(cat.items()):
        base = re.sub(r"-(generate|validate|review)$", "", name)
        if base in arts or name in UTILITY_COMMANDS:
            out.append(entry)
    return out


def log_tail(rel_dir: Path, n: int = 6) -> str:
    p = rel_dir / "execution_log.md"
    if not p.is_file():
        return "(no execution log yet)"
    rows = [l for l in p.read_text(encoding="utf-8", errors="replace").split("\n") if l.startswith("| 20")]
    return "\n".join(rows[-n:]) or "(no rows yet)"


def director_prompt(release: str, direction: str, status: dict, resolved: dict, commands: list, log_rows: str,
                    settings_desc: str, context_text: str = "") -> str:
    states = "\n".join(f"  {g['id']:<24} {resolved['states'][g['id']]}" for g in resolved["graph"]
                       if resolved["states"][g["id"]] != "not applicable")
    parked = status.get("parked_decisions") or []
    parked_text = "\n".join(f"  {d.get('id')}: {d.get('question')} ({d.get('artifact')})" for d in parked if isinstance(d, dict)) or "  none"
    cat_text = "\n".join(f"  /wire:{e['command']} {e.get('arguments', '')}  — {e['description'][:110]}" for e in commands)
    return f"""(Wire CLI run: WIRE_INVOKED_BY=orchestrator is set.)
You are the orchestrating session for Wire release `{release}`, taking direction from the
release director (the person). Resolve the direction below into Wire commands. You run
nothing: the Wire CLI shows the plan, waits for go, and runs the commands.

Direction from the director:
\"\"\"{direction}\"\"\"

Release state (data, computed by the runnable-set resolver; trust it over your own reading):
{states}
Runnable now, in graph order: {', '.join(resolved['order']) or 'nothing'}
Parked decisions (a ruling is needed before the artifact can move):
{parked_text}
{context_text}
Last execution-log rows:
{log_rows}
Harness for the run: {settings_desc}

Commands this release knows (name, arguments, purpose):
{cat_text}

Rules:
- To create a new release (or a new engagement), propose `/wire:new`. It asks its own
  questions (release type, name, inputs) in the session; do not answer them in the command.
  `/wire:start new` is onboarding for someone new to Wire, not a new release.
- `/wire:new`, `/wire:adopt`, `/wire:start` and `/wire:help` take no release: write them
  without one. Every other command takes the release, as below.
- A review is a ruling by a person: never propose a review as something to run unless the
  director asked for it in words.
- Propose only commands whose preconditions are met (runnable now), or say what blocks the
  rest and which ruling or command would clear it.
- Each release command in full, as typed: `/wire:<command> {release}` plus flags.
- A question or a request for information gets an answer and no commands.
- Keep the reply under 120 words, plain English, the answer first.

Answer with one JSON object and nothing else:
{{"reply": "<plain-language reply>", "commands": ["/wire:<command> {release} ...", ...]}}"""


def parse_reply(final_message: str) -> dict:
    obj = parse_report(final_message) or {}
    reply = str(obj.get("reply", "")).strip() if obj else ""
    commands = [str(c).strip() for c in (obj.get("commands") or []) if str(c).strip()] if obj else []
    if not reply:
        reply = (final_message or "").strip() or "(no reply)"
    cleaned = []
    for c in commands:
        c = c if c.startswith("/wire:") else f"/wire:{c.lstrip('/')}"
        cleaned.append(c)
    return {"reply": reply, "commands": cleaned}


ESCAPES = {"n": "\n", "t": "\t", "r": "", "b": "", "f": "", '"': '"', "\\": "\\", "/": "/"}


class ReplyStreamer:
    """Shows the `reply` field of the director's JSON answer as it is written.
    The answer streams as raw JSON (`{"reply": "...", "commands": [...]}`); this
    finds the reply string and writes its decoded characters, so the person reads
    the reply, not the JSON. Nothing is written if the answer is not that shape;
    the session then prints the parsed reply at the end, as before."""

    def __init__(self, write):
        self.write = write
        self.buf = ""
        self.pos: int | None = None
        self.done = False
        self.shown = False

    def feed(self, chunk: str) -> None:
        self.buf += chunk
        if self.done:
            return
        if self.pos is None:
            m = re.search(r'"reply"\s*:\s*"', self.buf)
            if not m:
                return
            self.pos = m.end()
        out, i, b = [], self.pos, self.buf
        while i < len(b):
            c = b[i]
            if c == "\\":
                if i + 1 >= len(b):
                    break
                n = b[i + 1]
                if n == "u":
                    if i + 6 > len(b):
                        break
                    try:
                        out.append(chr(int(b[i + 2:i + 6], 16)))
                    except ValueError:
                        pass
                    i += 6
                    continue
                out.append(ESCAPES.get(n, n))
                i += 2
                continue
            if c == '"':
                self.done = True
                i += 1
                break
            out.append(c)
            i += 1
        self.pos = i
        if out:
            self.write("".join(out))
            self.shown = True


def command_argv(command: str, release: str) -> tuple:
    """`/wire:dbt-validate 02-x --slice y` -> ('dbt-validate', ['--slice', 'y'])."""
    words = command.replace("/wire:", "").split()
    if not words:
        return "", []
    name = fw.normalise_command(words[0])
    rest = [w for w in words[1:] if w != release]
    return name, rest


def direct(repo: Path, release: str, direction: str, settings, args, out=print, env: dict | None = None,
           thread: str | None = None, on_text=None, on_activity=None) -> dict:
    """Ask the harness to resolve the direction. Returns {reply, commands, thread_id}.
    With `thread`, the turn continues that conversation (ROADMAP.md phase 2), so
    a follow-up ("and the dashboards?") has the earlier turns; the release state
    is sent fresh every turn, since it may have changed."""
    root = fw.framework_root(getattr(args, "framework", None))
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    status, _text, decisions_md, rel_dir, problems = read_release(root, repo, release)
    if problems:
        return {"reply": "The status file has problems; fix it first: " + "; ".join(problems), "commands": []}
    resolved = resolve(framework, status, decisions_md)
    cat = fw.catalogue(root)
    prompt = director_prompt(release, direction, status, resolved, relevant_commands(cat, resolved), log_tail(rel_dir),
                             settings.describe(), release_context_text(root, repo, release, status, _text))
    run_env = dict(env or {})
    run_env.update({"WIRE_INVOKED_BY": "orchestrator", "WIRE_SESSION_ID": session_id(repo), "WIRE_PLUGIN_ROOT": str(root)})
    req = RunRequest(prompt=prompt, cwd=repo, env=run_env, model=settings.model, provider=settings.provider,
                     sandbox="read-only", output_schema=REPLY_SCHEMA if REPLY_SCHEMA.is_file() else None,
                     log_dir=repo / ".wire" / "local" / "lane-logs", label="director", resume_thread=thread,
                     on_text=on_text, on_activity=on_activity)
    result = get_harness(settings.harness).run(req)
    if result.error and not result.final_message:
        return {"reply": f"The harness failed: {result.error}", "commands": []}
    reply = parse_reply(result.final_message)
    reply["usage"] = result.usage.total
    reply["input_tokens"] = result.usage.input_tokens
    reply["thread_id"] = result.thread_id or thread
    return reply


def release_context_text(root: Path, repo: Path, release: str, status: dict, status_text: str) -> str:
    """The Wire mod's release-context section (context.py), with the next action."""
    from .context import gather
    try:
        gate = fw.load_script(root, "wire_gate")
        framework, split_fm, read_rulings, resolve = fw.load_studio(root)
        nxt = gate.next_action(framework, str(repo), release, split_fm, read_rulings, resolve)
        next_action = nxt.get("next") or f"{nxt.get('kind')}: {nxt.get('reason')}"
    except Exception:  # noqa: BLE001
        next_action = None
    body = status_text.split("\n---", 2)[-1] if status_text.startswith("---") else status_text
    return gather(repo, release, status, body, next_action)


HANDOFF_FALLBACK = ("Write a Wire session handoff for the next session. Plain Markdown, four headings, short lists under "
                    "each: What was built; Rulings made; State; Next command. Record only what happened.")


def handoff_text(repo: Path, release: str, settings, args, env: dict | None, thread: str | None, on_text=None) -> tuple:
    """(handoff Markdown, thread id): TEMPLATES/handoff-template.md answered in the
    director conversation (or a fresh one with the release context)."""
    root = fw.framework_root(getattr(args, "framework", None))
    template = root / "TEMPLATES" / "handoff-template.md"
    ask = template.read_text(encoding="utf-8") if template.is_file() else HANDOFF_FALLBACK
    status, text, _d, rel_dir, _p = read_release(root, repo, release)
    prompt = (f"(Wire CLI run: WIRE_INVOKED_BY=orchestrator is set.) Release {release}. {ask}\n\nThe release now:\n{release_context_text(root, repo, release, status, text)}\n"
              f"Last execution-log rows:\n{log_tail(rel_dir)}\n\nReply with the handoff Markdown only.")
    run_env = dict(env or {})
    run_env.update({"WIRE_INVOKED_BY": "orchestrator", "WIRE_SESSION_ID": session_id(repo), "WIRE_PLUGIN_ROOT": str(root)})
    req = RunRequest(prompt=prompt, cwd=repo, env=run_env, model=settings.model, provider=settings.provider,
                     sandbox="read-only", log_dir=repo / ".wire" / "local" / "lane-logs", label="handoff", resume_thread=thread,
                     on_text=on_text)
    result = get_harness(settings.harness).run(req)
    return (result.final_message or "").strip(), result.thread_id or thread


def run_plan_lines(commands: list) -> list:
    lines = ["Run plan (one at a time, in the repository, recorded by each command):"]
    lines += [f"  {i}. {c}" for i, c in enumerate(commands, 1)]
    lines.append("go / adjust / cancel?")
    return lines
