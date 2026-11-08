"""`wire run <release>`: the orchestrating loop in code.

One pass: check the status file; read the release; resolve the claim; compute
the runnable set with Studio's resolver (the executable form of
specs/utils/runnable_set.md); show the run plan (director rule 8) and wait
for go unless --yes; dispatch the parallel set as lanes, each in its own
worktree on the configured harness; consolidate each lane (ownership, record,
report), merge the clean ones, update status.md in place, append the log row,
refresh the claim; then recompute. Stops at a review, a block, a parked lane
or --once.

The CLI is the single writer of status.md and execution_log.md.
"""

from __future__ import annotations

import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import claim as claim_mod
from . import framework as fw
from . import lanes as ln
from . import record as rec
from .harness import RunRequest, get_harness, parse_report
from .settings import lane_model, read_routing

EXIT_OK, EXIT_STATUS_FILE, EXIT_NO_GO, EXIT_CLAIM, EXIT_PARKED = 0, 1, 3, 4, 6


class Say:
    def __init__(self, out):
        self.out = out

    def __call__(self, *parts):
        self.out(" ".join(str(p) for p in parts))


def session_id(repo: Path) -> str:
    p = repo / ".wire" / "local" / "cli_session"
    try:
        sid = p.read_text(encoding="utf-8").strip()
        if sid:
            return sid
    except OSError:
        pass
    sid = uuid.uuid4().hex[:8]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(sid + "\n", encoding="utf-8")
    return sid


def read_release(root: Path, repo: Path, release: str):
    """(status dict, status text, decisions_md, release_dir, problems)."""
    status_file = fw.load_script(root, "status_file")
    rel_dir = repo / ".wire" / "releases" / release
    status_path = rel_dir / "status.md"
    if not status_path.is_file():
        raise FileNotFoundError(f"no status.md for release {release!r} under {rel_dir}")
    problems = status_file.check_paths([status_path])
    text = status_path.read_text(encoding="utf-8")
    data, body, _ = status_file.read_status(text)
    data = dict(data or {})
    if not data.get("artifacts"):
        # Older (3.x) status files keep the artifact states in a fenced YAML
        # block in the body, as Studio's load_release reads them.
        from_body = status_file.body_artifacts(text)[0] if hasattr(status_file, "body_artifacts") else {}
        if from_body:
            data["artifacts"] = from_body
    decisions = rel_dir / "decisions.md"
    decisions_md = decisions.read_text(encoding="utf-8") if decisions.is_file() else ""
    return data, text, decisions_md, rel_dir, problems


def read_context(repo: Path, root: Path) -> dict:
    p = repo / ".wire" / "engagement" / "context.md"
    if not p.is_file():
        return {}
    status_file = fw.load_script(root, "status_file")
    data, _body, _ = status_file.front_matter(p.read_text(encoding="utf-8"))
    return data or {}


def plan_lanes(resolved: dict, release: str, status: dict, root: Path, cat: dict, settings, routing: dict, repo: Path | None = None) -> list:
    graph = {g["id"]: g for g in resolved["graph"]}
    lanes = []
    for art in resolved["parallel"]:
        state = resolved["states"][art]
        action = state.split(": ", 1)[1]
        g = graph[art]
        command = g["command"]
        entry = cat.get(f"{command}-{action}")
        spec_path = fw.spec_path(root, entry) if entry else None
        spec_text = spec_path.read_text(encoding="utf-8") if spec_path else ""
        model, rule = lane_model(settings, routing, fw.workload_of(spec_text), fw.is_client_facing(spec_text), status)
        lane = ln.Lane(label=f"{art}", artifact=art, action=action, command=command, release=release,
                       owns=ln.default_owns(release, art, g, repo),
                       state_file=f".wire/releases/{release}/lanes/{art}.md",
                       model=model, model_rule=rule, spec_path=spec_path)
        lanes.append(lane)
    return lanes


def run_plan_text(lanes: list, settings, resolved: dict, release: str) -> str:
    lines = [f"Run plan for {release} ({settings.describe()}; lanes_max {resolved['lanes_max']}):"]
    for i, lane in enumerate(lanes, 1):
        lines.append(f"  {i}. {lane.typed}")
        lines.append(f"     lane {lane.label}; owns {', '.join(lane.owns)}; model {lane.model or 'default'} ({lane.model_rule})")
    waiting = [g["id"] for g in resolved["graph"] if resolved["states"].get(g["id"]) == "parked: needs ruling (review)"]
    if waiting:
        lines.append(f"  Reviews waiting (a review is a ruling, never dispatched): {', '.join(waiting)}")
    lines.append("  Stops after this pass at the first review, block or parked lane.")
    return "\n".join(lines)


def _lane_request(lane: ln.Lane, path: Path, brief_file: Path, prompt: str, root: Path, settings, base_env: dict,
                  budget_line: str, log_dir: Path, mcp_servers: dict | None, resume_thread: str | None = None,
                  suffix: str = "") -> RunRequest:
    env = ln.lane_env(base_env, lane, brief_file, root, log_dir,
                      warehouse_spend=budget_line.split(":", 1)[1].strip() if ":" in budget_line else None)
    # the spend ledger is the main repository's, not the worktree's (budget.py)
    from .budget import ledger_path
    env["WIRE_SPEND_LEDGER"] = str(ledger_path(log_dir.parents[2], lane.release))
    env["WIRE_LANE_RELEASE"] = lane.release
    stamp = rec.utc_now().strftime("%Y%m%dT%H%M%SZ")
    env["WIRE_HOOK_LOG"] = str(log_dir / f"{lane.safe_label}-{stamp}{suffix}.hooks.jsonl")
    return RunRequest(prompt=prompt, cwd=path, env=env, model=lane.model, provider=settings.provider,
                      sandbox=settings.sandbox, output_schema=Path(__file__).with_name("lane_report.schema.json"),
                      log_dir=log_dir, label=f"{lane.safe_label}-{stamp}{suffix}", mcp=dict(mcp_servers or {}),
                      resume_thread=resume_thread, wire_tools=True, write_paths=ln.write_paths(lane, path))


def dispatch(lane: ln.Lane, repo: Path, root: Path, settings, base_env: dict, budget_line: str, log_dir: Path,
             mcp_servers: dict | None = None):
    path, _branch = ln.create_worktree(repo, lane)
    brief = ln.compose_brief(lane, budget_line)
    brief_file = ln.write_brief_file(path, lane, brief)
    spec_text = lane.spec_path.read_text(encoding="utf-8") if lane.spec_path else "(no specification shipped for this command)"
    prompt = ln.lane_prompt(lane, brief, spec_text, root, ln.rulings_text(path, lane))
    req = _lane_request(lane, path, brief_file, prompt, root, settings, base_env, budget_line, log_dir, mcp_servers)
    from . import telemetry
    telemetry.send(lane.command, "lane", lane.release, repo, settings.harness, settings.provider, base_env)
    return get_harness(settings.harness).run(req)


def lane_question(lane: ln.Lane, result) -> str | None:
    """The question a lane stopped on (needs_ruling, or a question in its reply), else None."""
    if not result.ok:
        return None
    _status, _log, detail = ln.outcome_for(lane.action, parse_report(result.final_message), result.final_message)
    return detail[len("needs_ruling: "):] if detail.startswith("needs_ruling: ") else None


RESUME_PROMPT = ("The release director answered your question (ruling {rid} in decisions.md): {answer}\n"
                 "Continue the step from where you stopped, within the same lane brief and rules. "
                 "When you finish, report again in the same JSON form.")


def answer_in_session(lane: ln.Lane, result, question: str, ask, repo: Path, rel_dir: Path, root: Path, settings,
                      base_env: dict, budget_line: str, log_dir: Path, mcp_servers: dict | None, by: str, say):
    """ROADMAP.md phase 2: a lane's question shown in the session, the answer
    recorded as a ruling, the lane's own conversation resumed with it. Returns
    (result, ruling id), or (result, None) when the director leaves it parked."""
    say(f"  {lane.label} asks: {question}")
    answer = (ask("  Your answer (blank to park it): ") or "").strip()
    if not answer:
        return result, None
    decisions_path = rel_dir / "decisions.md"
    from . import rulings as rl
    text = decisions_path.read_text(encoding="utf-8") if decisions_path.is_file() else ""
    text, rid = rl.append_ruling(text, rec.utc_now().strftime("%Y-%m-%d %H:%M"), by,
                                 f"{lane.artifact} (decision): {question}", answer, release=rel_dir.name)
    decisions_path.write_text(text, encoding="utf-8")
    say(f"  Recorded as {rid}; resuming {lane.label}...")
    brief_file = lane.worktree / ".wire" / "local" / "briefs" / f"{lane.safe_label}.md"
    req = _lane_request(lane, lane.worktree, brief_file, RESUME_PROMPT.format(rid=rid, answer=answer), root, settings,
                        base_env, budget_line, log_dir, mcp_servers, resume_thread=result.thread_id, suffix="-answer")
    second = get_harness(settings.harness).run(req)
    second.duration_s += result.duration_s
    for key in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens"):
        setattr(second.usage, key, getattr(second.usage, key, 0) + getattr(result.usage, key, 0))
    if result.usage.cost_usd is not None or second.usage.cost_usd is not None:
        second.usage.cost_usd = (result.usage.cost_usd or 0) + (second.usage.cost_usd or 0)
    second.blocked = list(result.blocked) + list(second.blocked)
    if not second.thread_id:
        second.thread_id = result.thread_id
    return second, rid


def consolidate(lane: ln.Lane, result, repo: Path, status_path: Path, log_path: Path, by: str, say,
                answered: str | None = None) -> dict:
    """Apply the rules to one finished lane and write the record. Returns
    {merged, status_value, log_result, detail}."""
    changed = ln.changed_paths(lane.worktree)
    own = ln.check_ownership(changed, lane)
    report = parse_report(result.final_message) if result.ok else None
    status_value, log_result, detail = ln.outcome_for(lane.action, report, result.final_message)
    merged = False
    if not result.ok:
        log_result, detail = "blocked", f"harness error: {result.error or result.exit_code}"
    elif own["record"]:
        log_result, detail = "blocked", f"single writer: lane changed {', '.join(own['record'])} (rule 6)"
    elif own["outside"]:
        log_result, detail = "blocked", f"tree ownership: lane changed {', '.join(own['outside'][:3])} outside its trees (rule 3)"
    elif status_value or log_result == "fail":
        commit = ln.commit_lane(lane.worktree, f"wire: {lane.typed} ({log_result})")
        if commit:
            ok, info = ln.merge_lane(repo, lane)
            if ok:
                merged = True
            else:
                log_result, detail, status_value = "blocked", f"merge failed: {info}", None
        else:
            merged = True  # nothing to merge, the outcome still stands (a validate that only reports)
    extra = f"{result.harness}"
    if lane.model:
        extra += f" {lane.model}"
    if result.blocked:
        extra += f"; {len(result.blocked)} call(s) refused by hooks"
    if answered:
        extra += f"; answered in session as {answered}"
    # The Detail cell is capped at 120 characters (execution_log.md rule 5):
    # the lane's own text gives way, the harness tag at the end stays whole.
    room = max(24, 120 - len(extra) - 3)
    short = detail if len(detail) <= room else detail[:room - 3].rstrip() + "..."
    detail_full = f"{short} [{extra}]"
    parked_id = ""
    if merged and status_value:
        text = status_path.read_text(encoding="utf-8")
        text = rec.update_artifact_outcome(text, lane.artifact, lane.action, status_value)
        text = rec.set_top_key(text, "last_updated", rec.utc_now().strftime("%Y-%m-%d"))
        text = rec.refresh_last_write(text, rec.claim_ts())
        text = rec.set_last_orchestrated(text, rec.claim_ts())
        status_path.write_text(text, encoding="utf-8")
    elif detail.startswith("needs_ruling: "):
        # The lane stopped where a decision is required: park it for the director.
        text = status_path.read_text(encoding="utf-8")
        text, parked_id = rec.append_parked_decision(text, lane.artifact, detail[len("needs_ruling: "):], rec.claim_ts())
        text = rec.refresh_last_write(text, rec.claim_ts())
        status_path.write_text(text, encoding="utf-8")
        tag = f"{extra}; parked as {parked_id}"
        room = max(24, 120 - len(tag) - 3)
        short = detail if len(detail) <= room else detail[:room - 3].rstrip() + "..."
        detail_full = f"{short} [{tag}]"
    rec.append_log_row(log_path, lane.typed, log_result, detail_full, by, lane.label,
                       rec.duration_text(result.duration_s), result.usage.tokens_cell(), result.usage.cost_cell())
    if merged:
        ln.remove_worktree(repo, lane)
        say(f"  {lane.label}: {log_result}; merged {lane.branch}")
    elif parked_id:
        ln.remove_worktree(repo, lane)
        say(f"  {lane.label}: decision needed, parked as {parked_id} in status.md: {detail[len('needs_ruling: '):]}")
    else:
        say(f"  {lane.label}: {log_result}; {detail}; worktree kept at {lane.worktree}")
    return {"merged": merged, "status_value": status_value, "log_result": log_result, "detail": detail, "parked": parked_id}


def run(repo: Path, release: str, settings, args, out=print, env: dict | None = None) -> int:
    say = Say(out)
    env = dict(env if env is not None else os.environ)
    root = fw.framework_root(getattr(args, "framework", None))
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    cat = fw.catalogue(root)
    routing = read_routing(root / "model-routing.yaml")
    by = rec.git_user(repo)
    sid = session_id(repo)
    passes = 0
    max_passes = 1 if getattr(args, "once", False) else int(getattr(args, "max_passes", 10) or 10)
    exit_code = EXIT_OK

    while passes < max_passes:
        passes += 1
        status, text, decisions_md, rel_dir, problems = read_release(root, repo, release)
        if problems:
            for p in problems:
                say(f"status file: {p}")
            say("Fix the status file first (a lane never fixes it).")
            return EXIT_STATUS_FILE
        status_path, log_path = rel_dir / "status.md", rel_dir / "execution_log.md"
        if str(status.get("delivery") or "") == "tickets":
            # a release built from tickets is worked ticket by ticket: on a ticket
            # branch only iterations/<ticket>.md is written, never status.md
            # (specs/utils/ticket_delivery.md), so wire run does not orchestrate it
            from .commands import ticket_states
            ts = ticket_states(root, rel_dir) or {}
            ready = [t["ticket"] for t in ts.get("tickets") or [] if t.get("state") == "can_start"]
            say(f"{release} is built from tickets; it is worked one ticket at a time, not dispatched as lanes.")
            say("Ready to start: " + (", ".join(ready) or "none") + (f". Next: wire work {release} {ready[0]}" if ready else ""))
            return EXIT_NO_GO

        # the claim
        now = rec.claim_ts()
        decision = claim_mod.resolve_claim(status, by, sid, now)
        if not decision["dispatch_allowed"]:
            holder, age = decision["held_by"], decision["age_minutes"]
            if decision["outcome"] == "ask_takeover" and getattr(args, "take_over", False):
                say(f"Taking over the claim from {holder} (last write {age} minutes ago).")
            else:
                if decision["outcome"] == "ask_join":
                    say(f"{release} is claimed by {holder}, who wrote {age} minutes ago. Join as a reviewer or move to another release; nothing is dispatched.")
                else:
                    say(f"{release} is claimed by {holder}, silent for {age if age is not None else 'an unknown number of'} minutes. Re-run with --take-over to take it, or move to another release.")
                return EXIT_CLAIM
        branch = rec.git_branch(repo)
        existing = (status.get("agents") or {}).get("coordinator_session") or {}
        claimed_at = existing.get("claimed_at") if decision["outcome"] == "resume" else None
        text = rec.write_claim(text, claim_mod.claim_block(by, sid, branch, now, claimed_at))
        status_path.write_text(text, encoding="utf-8")
        status, text, decisions_md, rel_dir, _ = read_release(root, repo, release)

        resolved = resolve(framework, status, decisions_md, requested=tuple(getattr(args, "request", None) or ()))
        lanes = plan_lanes(resolved, release, status, root, cat, settings, routing, repo)
        if not lanes:
            say(next_action_text(root, repo, release))
            return exit_code
        say(run_plan_text(lanes, settings, resolved, release))
        if getattr(args, "dry_run", False):
            return EXIT_OK
        if not getattr(args, "yes", False):
            session_ask = getattr(args, "ask", None)
            if session_ask is None and not os.isatty(0):
                say("Nothing dispatched: pass --yes to go, or --dry-run to see the plan only.")
                return EXIT_NO_GO
            answer = ((session_ask or input)("go / cancel? ") or "").strip().lower()
            if answer not in ("go", "y", "yes"):
                say("Cancelled.")
                return EXIT_NO_GO

        budget = status.get("budget") or {}
        budget_line = f"warehouse_spend: {budget.get('warehouse_spend', 'estimate_required')}"
        if park_if_over_cap(repo, release, status_path, budget, say):
            return EXIT_PARKED
        log_dir = repo / ".wire" / "local" / "lane-logs"
        from .mcp import servers_for_run
        mcp_servers, mcp_notes = servers_for_run(repo, settings.harness)
        if mcp_servers:
            say("MCP servers for this run: " + ", ".join(sorted(mcp_servers)))
        for note in mcp_notes:
            say(f"  {note}")
        say(f"Dispatching {len(lanes)} lane(s) on {settings.harness}...")
        results = {}
        watcher = getattr(args, "stream", None)
        lane_state = getattr(watcher, "lane", None) or (lambda _label, _state: None)

        def watched(lane):
            lane_state(lane.label, "running")
            try:
                r = dispatch(lane, repo, root, settings, env, budget_line, log_dir, mcp_servers)
            except Exception:
                lane_state(lane.label, "failed")
                raise
            lane_state(lane.label, "done" if r.ok else "failed")
            return r
        with ThreadPoolExecutor(max_workers=max(1, len(lanes))) as pool:
            futures = {pool.submit(watched, lane): lane for lane in lanes}
            for fut, lane in futures.items():
                try:
                    results[lane.label] = fut.result()
                except Exception as exc:  # noqa: BLE001 - one lane's failure must not lose the others
                    from .harness import RunResult
                    results[lane.label] = RunResult(harness=settings.harness, exit_code=1, error=str(exc))

        # a lane that stopped on a question: answered here when someone is at the
        # terminal (unattended runs, --no-interaction, keep parking it)
        ask = getattr(args, "ask", None) or (input if os.isatty(0) else None)
        interactive = ask is not None and not getattr(args, "no_interaction", False)
        answered = {}
        if interactive:
            for lane in lanes:
                q = lane_question(lane, results[lane.label])
                if q and results[lane.label].thread_id:
                    results[lane.label], answered[lane.label] = answer_in_session(
                        lane, results[lane.label], q, ask, repo, rel_dir, root, settings, env, budget_line, log_dir,
                        mcp_servers, by, say)

        parked = False
        for lane in lanes:
            outcome = consolidate(lane, results[lane.label], repo, status_path, log_path, by, say,
                                  answered=answered.get(lane.label))
            if not outcome["merged"] or outcome["log_result"] in ("blocked", "fail"):
                parked = True
        if park_if_over_cap(repo, release, status_path, budget, say):
            parked = True
        problems = fw.load_script(root, "status_file").check_paths([status_path])
        if problems:
            for p in problems:
                say(f"status file after write: {p}")
            return EXIT_STATUS_FILE
        if not getattr(args, "no_commit_record", False) and str(env.get("WIRE_COMMIT_RECORD", "true")).lower() != "false":
            commit_record(repo, rel_dir, release, by, say)
        say(next_action_text(root, repo, release))
        if parked:
            return EXIT_PARKED
    return exit_code


def park_if_over_cap(repo: Path, release: str, status_path: Path, budget: dict, say) -> bool:
    """Past `warehouse_spend: cap:<amount>`: park one budget decision (the CLI is
    the single writer) and dispatch nothing until the director rules. True when over."""
    from . import budget as bg
    cap = bg.cap_of((budget or {}).get("warehouse_spend"))
    if cap is None:
        return False
    usd = bg.spent(bg.ledger_path(repo, release))["usd"]
    if usd <= cap:
        return False
    text = status_path.read_text(encoding="utf-8")
    if not re.search(r"^\s+kind:\s*budget\s*$", text, re.M):
        text, pid = rec.append_parked_decision(text, "budget", bg.budget_question(usd, cap), rec.claim_ts(), kind="budget")
        status_path.write_text(text, encoding="utf-8")
        say(f"Warehouse spend for {release} is ${usd:.2f}, past cap:{cap:g}; parked as {pid}. Rule on it (/rule {pid} ...), "
            "or raise the cap in status.md.")
    else:
        say(f"Warehouse spend for {release} is ${usd:.2f}, past cap:{cap:g}, and a budget decision is parked. Nothing dispatched.")
    return True


def commit_record(repo: Path, rel_dir: Path, release: str, by: str, say) -> None:
    """ROADMAP.md phase 5: the record travels with the lanes' merges. status.md,
    execution_log.md and decisions.md are committed after each pass, and
    nothing else in the working tree."""
    import subprocess
    paths = [str(p.relative_to(repo)) for p in (rel_dir / "status.md", rel_dir / "execution_log.md", rel_dir / "decisions.md")
             if p.is_file()]
    if not paths:
        return
    subprocess.run(["git", "add", "--", *paths], cwd=str(repo), capture_output=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet", "--", *paths], cwd=str(repo)).returncode == 0:
        return
    proc = subprocess.run(["git", "commit", "-q", "-m", f"wire: record for {release} (wire run)", "--", *paths],
                          cwd=str(repo), capture_output=True, text=True)
    if proc.returncode == 0:
        say(f"Record committed: {', '.join(Path(p).name for p in paths)}.")
    else:
        say(f"Record left uncommitted: {(proc.stderr or proc.stdout).strip()[:160]}")


def next_action_text(root: Path, repo: Path, release: str) -> str:
    gate = fw.load_script(root, "wire_gate")
    framework, split_fm, read_rulings, resolve = fw.load_studio(root)
    nxt = gate.next_action(framework, str(repo), release, split_fm, read_rulings, resolve)
    if nxt.get("next"):
        return f"Next: {nxt['next']} ({nxt['kind']}: {nxt['reason']})"
    return f"Next: {nxt.get('kind')}: {nxt.get('reason')}"
