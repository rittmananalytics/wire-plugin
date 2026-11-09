"""A typed run of one Wire command through the harness, and the read-only
commands (status, gate, exec).

A typed run is what a person typing `/wire:<command>` is on Claude Code: the
spec runs in the repository itself (no worktree), with WIRE_INVOKED_BY=typed,
and the spec's own steps write the record. Afterwards the CLI fills the
Tokens, Duration and Cost cells of that row from the harness's measured
usage, as the Claude plugin's metrics hook does.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import framework as fw
from . import lanes as ln
from . import record as rec
from .harness import RunRequest, get_harness
from .orchestrator import read_context, read_release

EXIT_GATE = 5


# Engagement-level commands: they take no release (`/wire:new` creates one). The
# CLI runs them without one and puts none into the command line or the prompt.
NO_RELEASE = ("new", "adopt", "start", "help")


def typed_prompt(command: str, release: str, extra: list, spec_text: str, root: Path, override: str | None,
                 invoked_by: str = "typed") -> str:
    args = " ".join([release] + list(extra)).strip()
    typed = f"/wire:{command} {args}".strip()
    lines = [
        f"Run the Wire command `{typed}` by following the specification below, step by step,",
        f"in the current directory (the engagement repository). WIRE_INVOKED_BY={invoked_by} is set:",
        "record the run as the specification says (status.md keys in place, one row in",
        "execution_log.md with Tokens and Cost as n/a; the Wire CLI fills them in).",
        "",
        "Path configuration:",
        "- `.wire/` means `.wire/` in the current directory.",
        f"- `specs/<path>.md`, `TEMPLATES/<file>`, `scripts/<name>.py`, `conventions/`,",
        f"  `release-types/` and the other framework files are under `{root}`.",
        "- A `specs/<path>.md` that is itself a Wire command is that command.",
        "",
        f"Start your work with the line `Running: {typed}` and end your report with",
        f"`Ran: {typed}` (or `Not run: {typed}, gate: <precondition>` if a gate stopped it).",
    ]
    if override:
        lines += ["", f"The precondition gate was overridden by the person running this, reason: {override}.",
                  "Record the override as specs/utils/precondition_gate.md says."]
    lines += ["", f"=== Specification: {typed} ===", "", spec_text]
    return "\n".join(lines)


def ran_line_present(final_message: str, command: str) -> bool:
    return bool(re.search(rf"(^|\n)\s*\**(Ran|Not run):?\**\s*`?/?(wire:)?{re.escape(command)}", final_message or ""))


def show(result, out, stream) -> None:
    """The reply: already on screen when it was streamed, printed whole otherwise."""
    if stream is not None and result.streamed:
        stream.end()
    elif result.final_message:
        out(result.final_message)


def run_typed(repo: Path, command: str, release: str, extra: list, settings, args, out=print, env=None) -> int:
    env = dict(env if env is not None else os.environ)
    root = fw.framework_root(getattr(args, "framework", None))
    cat = fw.catalogue(root)
    entry = cat.get(command)
    if not entry:
        near = [c for c in sorted(cat) if command.split("-")[0] in c][:5]
        out(f"Unknown Wire command {command!r}." + (f" Near: {', '.join(near)}" if near else ""))
        return 2
    spec_text = fw.spec_path(root, entry).read_text(encoding="utf-8")

    # the gate, when the release exists and the command belongs to its graph
    override = getattr(args, "override_gate", None)
    rel_dir = repo / ".wire" / "releases" / release
    if (rel_dir / "status.md").is_file():
        gate = fw.load_script(root, "wire_gate")
        framework, split_fm, read_rulings, resolve = fw.load_studio(root)
        g = gate.gate(framework, str(repo), release, command, split_fm, read_rulings, resolve)
        if g["decision"] == "refuse" and not override:
            out(f"Not run: /wire:{command} {release}, gate: {g['reason']}. Pass --override-gate \"<reason>\" to run anyway.")
            return EXIT_GATE

    invoked_by = env.get("WIRE_INVOKED_BY") if env.get("WIRE_INVOKED_BY") in ("orchestrator", "autopilot") else "typed"
    from . import telemetry
    telemetry.send(command, invoked_by, release, repo, settings.harness, settings.provider, env)
    prompt = typed_prompt(command, release, extra, spec_text, root, override, invoked_by)
    ask = getattr(args, "ask", None)
    if ask is not None:
        # ROADMAP.md phase 2: in the session a typed command is a conversation,
        # as it is in Claude Code (a review's stakeholder dialogue, a setup's questions)
        prompt += ("\n\nThis run is a conversation with the person in a terminal session. Where the "
                   "specification asks the person something, end your message with the question and stop; "
                   "their answer comes back in the next turn. Put its options, if any, as a numbered list after "
                   "the question, with nothing after them. Write the record and the `Ran:` line only once the "
                   "step is done, not when you stop to ask.")
    env.update({"WIRE_INVOKED_BY": invoked_by, "WIRE_PLUGIN_ROOT": str(root)})
    log_dir = repo / ".wire" / "local" / "lane-logs"
    from .mcp import servers_for_run
    mcp_servers, mcp_notes = servers_for_run(repo, settings.harness)
    for note in mcp_notes:
        out(f"mcp: {note}")
    stream = getattr(args, "stream", None)
    live = dict(on_text=stream.text, on_activity=stream.activity, ask=stream.asking(ask)) if stream else {}
    req = RunRequest(prompt=prompt, cwd=repo, env=env, model=settings.model, provider=settings.provider,
                     sandbox=settings.sandbox, log_dir=log_dir, label=f"typed-{command}", mcp=mcp_servers, wire_tools=True,
                     **live)
    out(f"Running: /wire:{command} {release} ({settings.describe()})")
    harness = get_harness(settings.harness)
    result = harness.run(req)
    show(result, out, stream)
    turns = 1
    while ask is not None and result.ok and result.thread_id and ln.question_in(result.final_message):
        answer = (ask("you> ") or "").strip()
        if not answer:
            out("(left there; the command can be run again)")
            break
        prev = result
        req = RunRequest(prompt=answer, cwd=repo, env=env, model=settings.model, provider=settings.provider,
                         sandbox=settings.sandbox, log_dir=log_dir, label=f"typed-{command}-{turns}", mcp=mcp_servers,
                         resume_thread=prev.thread_id, wire_tools=True, **live)
        result = harness.run(req)
        turns += 1
        result.duration_s += prev.duration_s
        for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
            setattr(result.usage, key, getattr(result.usage, key, 0) + getattr(prev.usage, key, 0))
        if prev.usage.cost_usd is not None or result.usage.cost_usd is not None:
            result.usage.cost_usd = (prev.usage.cost_usd or 0) + (result.usage.cost_usd or 0)
        result.blocked = list(prev.blocked) + list(result.blocked)
        result.thread_id = result.thread_id or prev.thread_id
        show(result, out, stream)
    if result.blocked:
        out(f"{len(result.blocked)} call(s) refused by hooks.")
    if result.ok and not ran_line_present(result.final_message, command):
        # the Wire mod's rule-7 check: every Wire run ends with `Ran:` (or `Not run:`)
        out(f"Note: the reply did not end with `Ran: /wire:{command} ...`; check the record before relying on it.")
        telemetry.send(command, invoked_by, release, repo, settings.harness, settings.provider, env,
                       event="wire_ran_line_missing", wait=True)
    log_path = rel_dir / "execution_log.md"
    if log_path.is_file() and result.usage.total:
        text = log_path.read_text(encoding="utf-8")
        new = rec.backfill_metrics(text, f"/wire:{command}", result.usage.tokens_cell(),
                                   rec.duration_text(result.duration_s), result.usage.cost_cell())
        if new != text:
            log_path.write_text(new, encoding="utf-8")
            out(f"Metrics filled in: {result.usage.total} tokens, {rec.duration_text(result.duration_s)}.")
    if result.error:
        out(f"Harness error: {result.error}")
        return result.exit_code or 1
    return 0


def run_exec(repo: Path, prompt: str, settings, args, out=print, env=None) -> int:
    env = dict(env if env is not None else os.environ)
    root = fw.framework_root(getattr(args, "framework", None))
    env.setdefault("WIRE_INVOKED_BY", "typed")
    env["WIRE_PLUGIN_ROOT"] = str(root)
    from .mcp import servers_for_run
    mcp_servers, mcp_notes = servers_for_run(repo, settings.harness)
    for note in mcp_notes:
        out(f"mcp: {note}")
    stream = None if getattr(args, "json", False) else getattr(args, "stream", None)
    live = dict(on_text=stream.text, on_activity=stream.activity) if stream else {}
    req = RunRequest(prompt=prompt, cwd=repo, env=env, model=settings.model, provider=settings.provider,
                     sandbox=settings.sandbox, label="exec", mcp=mcp_servers, wire_tools=True, **live)
    result = get_harness(settings.harness).run(req)
    if getattr(args, "json", False):
        out(json.dumps({"harness": result.harness, "exit_code": result.exit_code, "final_message": result.final_message,
                        "usage": result.usage.__dict__, "blocked": result.blocked, "duration_s": round(result.duration_s, 2),
                        "thread_id": result.thread_id, "error": result.error}, indent=2))
    else:
        show(result, out, stream)
        if result.error:
            out(f"Harness error: {result.error}")
    return result.exit_code


def ticket_states(root: Path, rel_dir: Path) -> dict | None:
    """For a release built from tickets (`delivery: tickets`): each ticket's
    state from scripts/ticket_delivery.py (the rules Studio's Tickets view
    uses), or None for any other release."""
    td = fw.load_script(root, "ticket_delivery")
    status = td.load_status(rel_dir)
    if str(status.get("delivery") or "") != "tickets":
        return None
    graph = td.load_graph(status, None)
    return td.runnable(td.load_map(rel_dir), td.load_records(rel_dir), graph, status.get("artifacts") or {})


def show_status(repo: Path, release: str, args, out=print) -> int:
    root = fw.framework_root(getattr(args, "framework", None))
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    status, _text, decisions_md, rel_dir, problems = read_release(root, repo, release)
    gate = fw.load_script(root, "wire_gate")
    resolved = resolve(framework, status, decisions_md, requested=tuple(getattr(args, "request", None) or ()))
    nxt = gate.next_action(framework, str(repo), release, split_fm, read_rulings, resolve)
    claim = (status.get("agents") or {}).get("coordinator_session") or None
    tickets = ticket_states(root, rel_dir)
    if getattr(args, "json", False):
        out(json.dumps({"release": release, "problems": problems, "states": resolved["states"], "order": resolved["order"],
                        "parallel": resolved["parallel"], "lanes_max": resolved["lanes_max"], "profile": resolved["profile"],
                        "claim": claim, "next": nxt, "tickets": (tickets or {}).get("tickets")}, indent=2))
        return 0
    out(f"Release {release} ({status.get('project_type') or status.get('release_type')}, phase {status.get('current_phase', '?')})")
    for p in problems:
        out(f"  status file: {p}")
    for g in resolved["graph"]:
        out(f"  {g['id']:<28} {g['state']}")
    out(f"Runnable, in order: {', '.join(resolved['order']) or 'nothing'}")
    out(f"Parallel set (lanes_max {resolved['lanes_max']}): {', '.join(resolved['parallel']) or 'none'}")
    if claim:
        out(f"Claim: {claim.get('user')} [{claim.get('session_id')}] on {claim.get('branch')}, last write {claim.get('last_write')}")
    else:
        out("Claim: none")
    out(f"Next: {nxt.get('next') or nxt.get('kind')} ({nxt.get('reason')})")
    if tickets:
        out("Built from tickets; each ticket is worked with `wire work <release> <ticket>`:")
        for t in tickets.get("tickets") or []:
            extra = f" (waits on {', '.join(t['waits_on'])})" if t.get("waits_on") else ""
            out(f"  {t['ticket']:<14} {t['state']}{extra}")
    return 0


def show_gate(repo: Path, release: str, command: str, args, out=print) -> int:
    root = fw.framework_root(getattr(args, "framework", None))
    gate = fw.load_script(root, "wire_gate")
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    g = gate.gate(framework, str(repo), release, command, split_fm, read_rulings, resolve)
    if getattr(args, "json", False):
        out(json.dumps(g, indent=2))
    else:
        out(f"{g['decision']}: /wire:{g['command']} {release} ({g['reason']})")
    return 0 if g["decision"] == "allow" else EXIT_GATE


def settings_for(repo: Path, release: str | None, args, env: dict):
    from .settings import resolve_settings
    root = fw.framework_root(getattr(args, "framework", None))
    context = read_context(repo, root)
    status = {}
    if release and (repo / ".wire" / "releases" / release / "status.md").is_file():
        try:
            status = read_release(root, repo, release)[0]
        except (OSError, ValueError):
            status = {}
    flags = {"harness": getattr(args, "harness", None), "model": getattr(args, "model", None),
             "provider": getattr(args, "provider", None), "sandbox": getattr(args, "sandbox", None)}
    return resolve_settings(context, status, flags, env)
