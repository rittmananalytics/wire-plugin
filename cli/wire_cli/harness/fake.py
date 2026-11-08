"""A scripted harness for tests. Never a real model.

The plan is JSON, from WIRE_FAKE_PLAN (a path) in the request's environment:

    {
      "writes": [{"path": "models/staging/x.sql", "content": "..."},
                 {"path": "...", "append": "..."}],
      "report": {"result": "complete", "detail": "...", "files_written": []},
      "final_message": "...",            # used when there is no report
      "usage": {"input_tokens": 1200, "output_tokens": 300},
      "exit_code": 0,
      "blocked": ["Wire rule 6 ..."],
      "record_prompt": "path",           # write the prompt here, for assertions
      "resume": {...},                   # the plan for a resumed turn (same keys)
      "activity": ["$ dbt parse"],       # lines for on_activity, when a person is watching
      "ask": [{"id": "q1", "question": "...", "options": [...]}],
                                         # questions put to the person inside the turn (RunRequest.ask)
      "record_answers": "path"           # write the answers here, as JSON
    }

With on_text set the final message is streamed in pieces, as the app-server
path does, and the result says it was streamed.

Paths are relative to the request's cwd (the lane's worktree), so a plan that
writes outside the lane's tree exercises the consolidation checks. `{label}`,
`{state_file}` and `{cwd}` in a path are filled from the lane's environment.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import Harness, RunRequest, RunResult, Usage


class FakeHarness(Harness):
    name = "fake"

    def run(self, req: RunRequest) -> RunResult:
        plan_path = req.env.get("WIRE_FAKE_PLAN")
        plan = json.loads(Path(plan_path).read_text(encoding="utf-8")) if plan_path else {}
        if req.resume_thread and isinstance(plan.get("resume"), dict):
            # the turn after the director's answer (`"resume": {...}`, same keys)
            plan = plan["resume"]
        subs = {"{label}": req.env.get("WIRE_LANE_LABEL", req.label),
                "{state_file}": req.env.get("WIRE_LANE_STATE_FILE", ""),
                "{cwd}": str(req.cwd)}

        def fill(text: str) -> str:
            for k, v in subs.items():
                text = text.replace(k, v)
            return text

        if plan.get("record_prompt"):
            Path(fill(plan["record_prompt"])).write_text(req.prompt, encoding="utf-8")
        for w in plan.get("writes", []):
            p = req.cwd / fill(w["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            if "append" in w:
                with open(p, "a", encoding="utf-8") as fh:
                    fh.write(w["append"])
            else:
                p.write_text(w.get("content", ""), encoding="utf-8")
        u = plan.get("usage") or {}
        final = json.dumps(plan["report"]) if plan.get("report") else plan.get("final_message", "done")
        if req.on_activity:
            for line in plan.get("activity", []):
                req.on_activity(line)
        answers = {}
        if req.ask is not None:
            from .app_server import chosen, question_text
            for q in plan.get("ask", []):
                answers[q["id"]] = chosen(q, req.ask(question_text(q) + "\nyou> ") or "")
        if plan.get("record_answers"):
            Path(fill(plan["record_answers"])).write_text(json.dumps(answers), encoding="utf-8")
        streamed = False
        if req.on_text is not None:
            for i in range(0, len(final), 7):
                req.on_text(final[i:i + 7])
            streamed = bool(final)
        return RunResult(
            streamed=streamed,
            harness=self.name,
            exit_code=int(plan.get("exit_code", 0)),
            final_message=final,
            usage=Usage(input_tokens=int(u.get("input_tokens", 0)), output_tokens=int(u.get("output_tokens", 0)),
                        cached_input_tokens=int(u.get("cached_input_tokens", 0)), cost_usd=u.get("cost_usd")),
            blocked=list(plan.get("blocked", [])),
            duration_s=float(plan.get("duration_s", 1.0)),
            thread_id="fake-thread",
            error=plan.get("error"),
            argv=["fake"],
        )
