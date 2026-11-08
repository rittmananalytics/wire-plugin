"""Lanes: the brief, the worktree, the ownership check, the merge.

A lane is one scoped task in its own git worktree (`.wire/local/worktrees/`,
git-ignored), run by a harness with WIRE_INVOKED_BY=lane. When it reports, the
CLI reads what the worktree changed and applies the director rules itself,
whatever the harness did: a change to the release record fails the lane (rule
6, the consolidation pass's check 3), a change outside the lane's Owns: trees
fails it (rule 3). A clean lane is committed on its branch and merged; a failed
lane keeps its worktree for inspection and is parked.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .record import is_record_path

WORKTREES = Path(".wire") / "local" / "worktrees"
BRANCH_PREFIX = "wire/lane"


@dataclass
class Lane:
    label: str
    artifact: str
    action: str
    command: str          # slug as typed, e.g. dbt-generate
    release: str
    owns: list = field(default_factory=list)
    state_file: str = ""
    model: str | None = None
    model_rule: str = ""
    spec_path: Path | None = None
    worktree: Path | None = None
    branch: str | None = None

    @property
    def typed(self) -> str:
        return f"/wire:{self.command}-{self.action} {self.release}"

    @property
    def safe_label(self) -> str:
        return re.sub(r"[^a-z0-9._-]+", "-", self.label.lower()).strip("-")


# The client-code trees a development artifact writes, beside its release
# folders. Only the ones that exist in the repository are granted. A dbt lane
# refused for writing models/ (seen live) is a lane that cannot do its job.
CODE_TREES = {
    "dbt": ("models", "tests", "macros", "seeds", "snapshots", "analyses", "dbt_project.yml", "packages.yml"),
    "data_refactor": ("models", "tests", "macros", "seeds", "snapshots", "dbt_project.yml"),
    "data_quality": ("models", "tests", "macros"),
    "pipeline": ("pipelines", "ingestion", "functions", "src", "cloud_functions"),
    "semantic_layer": ("models", "views", "explores", "lookml", "dashboards", "cube", "semantic_models"),
    "lookml_model": ("views", "explores", "models", "dashboards"),
    "looker_content": ("dashboards", "looks", "views"),
    "orchestration": ("dags", "orchestration", "dagster", "airflow", "jobs", ".github/workflows"),
    "dbtcharts": ("charts",),
    "agents_schema": ("agents.yml", ".github/workflows", "skills"),
    "data_app": ("apps",),
    "deployment": (".github/workflows", "deploy", "infra", "terraform"),
    "omni_model": ("omni", "models"),
    "omni_content": ("omni", "documents"),
}


def default_owns(release: str, artifact: str, graph_entry: dict, repo: Path | None = None) -> list:
    """The trees a lane for `artifact` may write, when the release type does
    not say: the artifact's folder under the release, the release's dev/ (and
    test/, deploy/) tree for development-phase work, and the client-code
    trees the artifact writes (CODE_TREES) that exist in the repository."""
    declared = (graph_entry or {}).get("owns")
    if isinstance(declared, list) and declared:
        # The release type says (`owns:` per artifact in the registry). Paths
        # under .wire/ are always the lane's; a client-code path counts only
        # where it exists in the repository, as with CODE_TREES below.
        out = []
        for o in declared:
            path = str(o).replace("{release}", release).replace("{artifact}", artifact).rstrip("/")
            if path.startswith(".wire/") or repo is None or (repo / path).exists():
                out.append(path)
        return out
    owns = [f".wire/releases/{release}/artifacts/{artifact}"]
    phase = (graph_entry or {}).get("phase", "")
    if phase in ("development", "testing", "deployment"):
        owns.append(f".wire/releases/{release}/dev")
    if phase == "testing":
        owns.append(f".wire/releases/{release}/test")
    if phase == "deployment":
        owns.append(f".wire/releases/{release}/deploy")
    if "design" in phase or phase in ("requirements",):
        owns.append(f".wire/releases/{release}/{phase}")
    for tree in CODE_TREES.get(artifact, ()):
        if repo is None or (repo / tree).exists():
            owns.append(tree)
    return owns


# Folders dbt and the CLI write while a step runs, writable in every lane.
SCRATCH_TREES = ("target", "logs", "dbt_packages", ".wire/local")


def write_paths(lane: Lane, worktree: Path) -> list:
    """The absolute paths the lane's operating-system sandbox lets it write
    (ROADMAP.md phase 5): its owned trees, its state file, decisions.md, and
    the scratch folders. Everything else in the worktree is read-only. The
    folders are made first, since the sandbox names paths that must exist."""
    out = []
    rel_dir = worktree / ".wire" / "releases" / lane.release
    for rel in list(lane.owns) + list(SCRATCH_TREES):
        p = worktree / rel
        p.mkdir(parents=True, exist_ok=True)
        out.append(str(p))
    if lane.state_file:
        sf = worktree / lane.state_file
        sf.parent.mkdir(parents=True, exist_ok=True)
        out.append(str(sf.parent))
    rel_dir.mkdir(parents=True, exist_ok=True)
    out.append(str(rel_dir / "decisions.md"))
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def compose_brief(lane: Lane, budget_line: str) -> str:
    # A tree is written with a trailing slash so the brief parsers (this hook's and the
    # Claude mod's) read a bare directory name such as `models` as a path.
    owns = "\n               ".join(o if ("/" in o or "." in o) else o + "/" for o in lane.owns) if lane.owns else "(none declared)"
    return (
        f"Lane:          {lane.label}\n"
        f"Release:       {lane.release}\n"
        f"Task:          {lane.typed}\n"
        f"Owns:          {owns}\n"
        f"State file:    {lane.state_file}\n"
        f"Resume:        Read the state file first; skip every completed item.\n"
        f"               Rewrite it after each completed item, not at the end.\n"
        f"Budget:        {budget_line}\n"
        f"Flat:          Do not spawn sub-agents. If the work is bigger than one lane,\n"
        f"               report that and stop; the orchestrator splits it.\n"
        f"Status:        Do not write status.md or execution_log.md. The orchestrator\n"
        f"               writes them from your state file. If the precondition gate\n"
        f"               stops on the status file, record it in your state file and\n"
        f"               report blocked; do not fix it.\n"
        f"Report:        Report once, at completion, at a stall, or when you hit a\n"
        f"               decision you cannot make. No running commentary.\n"
    )


RULINGS_CHARS = 6000


def rulings_text(worktree: Path, lane: Lane) -> str:
    """The release's decisions.md (its rulings) and the open parked decisions
    from status.md, for the lane's prompt. A lane that asks what the director
    has already ruled wastes a pass."""
    rel_dir = worktree / ".wire" / "releases" / lane.release
    parts = []
    decisions = rel_dir / "decisions.md"
    if decisions.is_file():
        text = decisions.read_text(encoding="utf-8", errors="replace").strip()
        if len(text) > RULINGS_CHARS:
            text = "(earlier rulings omitted)\n" + text[-RULINGS_CHARS:]
        if text:
            parts.append("=== Rulings the director has made (decisions.md) ===\n" + text)
    status = rel_dir / "status.md"
    if status.is_file():
        m = re.search(r"^parked_decisions:\n((?:[ \t]+.*\n?)+)", status.read_text(encoding="utf-8", errors="replace"), re.M)
        if m and m.group(1).strip():
            parts.append("=== Decisions parked, still open (do not ask them again; work around or report blocked) ===\n" + m.group(1).rstrip())
    return "\n\n".join(parts)


def lane_prompt(lane: Lane, brief: str, spec_text: str, framework_root: Path, rulings: str = "") -> str:
    return (
        f"{brief}\n"
        f"You are a Wire lane running on a harness driven by the Wire CLI. WIRE_INVOKED_BY=lane\n"
        f"is set. Run the Wire command `{lane.typed}` by following the specification below,\n"
        f"step by step, in this working tree (the current directory, a git worktree of the\n"
        f"engagement repository).\n\n"
        f"Path configuration:\n"
        f"- `.wire/` means `.wire/` in the current directory.\n"
        f"- `specs/<path>.md`, `TEMPLATES/<file>`, `scripts/<name>.py`, `conventions/`,\n"
        f"  `release-types/` and the other framework files are under `{framework_root}`.\n"
        f"- A `specs/<path>.md` that is itself a Wire command is that command; its\n"
        f"  specification is under the same folder.\n"
        f"- Write only under the trees your brief lists, plus your state file and\n"
        f"  `.wire/releases/{lane.release}/decisions.md`.\n\n"
        f"When you finish, stall, or need a ruling, your final message must be one JSON\n"
        f"object and nothing else: {{\"result\": \"complete|pass|fail|blocked|stalled|needs_ruling\",\n"
        f"\"detail\": \"<one line, under 120 characters, what happened>\", \"files_written\":\n"
        f"[\"<paths>\"], \"decision_needed\": \"<the question, or empty>\"}}. A generate that\n"
        f"finished is complete; a validate is pass or fail. Before reporting needs_ruling, check\n"
        f"the rulings below: a question the director has already answered is not asked again.\n\n"
        + (f"{rulings}\n\n" if rulings else "")
        + f"=== Specification: {lane.typed} ===\n\n{spec_text}\n"
    )


# ---------------------------------------------------------------- git

def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def worktree_path(repo: Path, lane: Lane) -> Path:
    return repo / WORKTREES / lane.safe_label


def create_worktree(repo: Path, lane: Lane) -> tuple[Path, str]:
    path = worktree_path(repo, lane)
    branch = f"{BRANCH_PREFIX}/{lane.release}/{lane.safe_label}"
    if path.exists():
        _git(repo, "worktree", "remove", "--force", str(path), check=False)
    _git(repo, "branch", "-D", branch, check=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    _git(repo, "worktree", "add", "-b", branch, str(path), "HEAD")
    lane.worktree, lane.branch = path, branch
    return path, branch


def changed_paths(worktree: Path) -> list:
    """Every path the worktree changed since its branch point: tracked
    changes and untracked files, renames as their new name."""
    out = _git(worktree, "status", "--porcelain", "--untracked-files=all").stdout
    paths = []
    for line in out.split("\n"):
        if not line.strip():
            continue
        rest = line[3:]
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        paths.append(rest.strip().strip('"'))
    return paths


def _under(path: str, tree: str) -> bool:
    p, t = path.rstrip("/"), tree.rstrip("/")
    return p == t or p.startswith(t + "/")


def check_ownership(paths: list, lane: Lane) -> dict:
    """{record: [...], outside: [...]} for the paths a lane changed. The
    worktrees folder itself is never a change of the lane's."""
    record, outside = [], []
    allowed_files = {lane.state_file, f".wire/releases/{lane.release}/decisions.md"}
    for p in paths:
        if p.startswith(str(WORKTREES)):
            continue
        if is_record_path(p, lane.release):
            record.append(p)
            continue
        if p in allowed_files:
            continue
        if lane.owns and not any(_under(p, o) for o in lane.owns):
            outside.append(p)
    return {"record": record, "outside": outside}


def commit_lane(worktree: Path, message: str) -> str | None:
    """Commit everything in the worktree; the commit id, or None when nothing changed."""
    _git(worktree, "add", "-A")
    if not _git(worktree, "status", "--porcelain").stdout.strip():
        return None
    _git(worktree, "-c", "user.name=Wire CLI", "-c", "user.email=wire-cli@local",
         "commit", "-q", "-m", message)
    return _git(worktree, "rev-parse", "HEAD").stdout.strip()


def merge_lane(repo: Path, lane: Lane) -> tuple[bool, str]:
    """Merge the lane's branch into the repository's current branch, no fast
    forward. On conflict, abort and report."""
    proc = _git(repo, "merge", "--no-ff", "-q", "-m", f"wire: merge lane {lane.label} ({lane.typed})",
                lane.branch or "", check=False)
    if proc.returncode != 0:
        _git(repo, "merge", "--abort", check=False)
        return False, (proc.stderr.strip() or proc.stdout.strip() or "merge failed")[:200]
    return True, _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()


def remove_worktree(repo: Path, lane: Lane, delete_branch: bool = False) -> None:
    if lane.worktree and lane.worktree.exists():
        _git(repo, "worktree", "remove", "--force", str(lane.worktree), check=False)
    if delete_branch and lane.branch:
        _git(repo, "branch", "-D", lane.branch, check=False)


def read_state_file(worktree: Path, lane: Lane) -> str:
    p = worktree / lane.state_file
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def write_brief_file(worktree: Path, lane: Lane, brief: str) -> Path:
    p = worktree / ".wire" / "local" / "briefs" / f"{lane.safe_label}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(brief, encoding="utf-8")
    return p


def lane_env(base: dict, lane: Lane, brief_file: Path, framework_root: Path, log_dir: Path,
             warehouse_spend: str | None = None) -> dict:
    env = dict(base)
    if warehouse_spend:
        # read by the lane hook: none refuses warehouse MCP calls that run SQL
        env["WIRE_LANE_WAREHOUSE_SPEND"] = warehouse_spend
    env.update({
        "WIRE_INVOKED_BY": "lane",
        "WIRE_LANE_LABEL": lane.label,
        "WIRE_LANE_OWNS": ":".join(lane.owns),
        "WIRE_LANE_STATE_FILE": lane.state_file,
        "WIRE_LANE_BRIEF": str(brief_file),
        "WIRE_PLUGIN_ROOT": str(framework_root),
        "WIRE_HOOK_LOG": str(log_dir / f"{lane.safe_label}.hooks.jsonl"),
    })
    return env


QUESTION_RE = re.compile(r"\?\s*$|\b(which|please (choose|confirm|let me know)|your choice|do you want)\b", re.I)


def question_in(final_message: str) -> str | None:
    """A question the lane asked a person instead of reporting needs_ruling:
    the last paragraph of its final message, when it reads as one."""
    text = (final_message or "").strip()
    if not text:
        return None
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    tail = " ".join(paragraphs[-3:])
    if QUESTION_RE.search(tail):
        line = next((l.strip() for l in reversed(tail.split("\n")) if "?" in l), None) or tail
        line = re.sub(r"[*_`#]+", "", line)
        return line[:200]
    return None


def outcome_for(action: str, report: dict | None, final_message: str = "") -> tuple[str | None, str, str]:
    """(status value or None, log result, detail) from a lane's report. With
    no report, a final message that asks a person something is a ruling
    needed (the lane stopped where a decision is required)."""
    if not report:
        q = question_in(final_message)
        if q:
            return None, "blocked", f"needs_ruling: {q}"
        return None, "blocked", "lane returned no report"
    result = str(report.get("result", "")).lower()
    detail = str(report.get("detail", "")).strip() or result
    if action == "generate" and result in ("complete", "pass"):
        return "complete", "complete", detail
    if action == "validate" and result in ("pass", "fail", "complete"):
        value = "pass" if result in ("pass", "complete") else "fail"
        return value, value, detail
    if result == "fail":
        return None, "fail", detail
    if result in ("blocked", "stalled", "needs_ruling"):
        q = str(report.get("decision_needed", "")).strip()
        if result == "needs_ruling":
            return None, "blocked", f"needs_ruling: {q or detail}"
        return None, "blocked", f"{result}: {detail}"
    return None, "blocked", f"unexpected result {result!r}: {detail}"


def report_json(obj: dict) -> str:
    return json.dumps(obj, indent=2)
