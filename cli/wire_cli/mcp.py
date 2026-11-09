"""MCP servers through the Wire CLI (ROADMAP.md phase 1).

Three sources, one list:

- The catalogue: the servers the Wire plugin for Claude Code configures
  (`packaging/claude-plugin/.mcp.json`, shipped in the Codex plugin as
  `mcp_servers.json`) plus the two the /wire:mcp spec names that the plugin
  leaves to the person (Linear, Notion).
- The engagement's selection: `.wire/engagement/mcp_servers.yml`, committed,
  the servers this engagement uses and their URLs. `wire mcp add` writes it.
- Each person's sign-in: Codex's own token store (`codex mcp login`), or
  Claude Code's (`/mcp`). The CLI never reads or stores a token.

A run gets the selected servers that are signed in, as `-c mcp_servers.<key>.url=...`
overrides on the codex harness (a repository's .codex/config.toml is read only
for a folder the person trusted, so the CLI does not rely on it) and as
`--mcp-config` on the claude harness. Every selected server goes to the run.
Seen live on Codex 0.166.0: a server that needs a sign-in it does not have
fails at start-up with one error line and the run goes on (4 seconds), and a
server Codex reports as `not_logged_in` may still serve anonymous calls
(Context7 does). So a server that is not signed in is passed with a note,
never dropped.

Codex and Claude Code name MCP tools the same way, `mcp__<server>__<tool>`.
On the claude harness a server the plugin ships, at the plugin's URL, is named
`plugin:wire:<key>` (claude_names), so its tools are `mcp__plugin_wire_<key>__`
as in the plugin, and the person's /mcp sign-in in Claude Code applies. On the
codex harness the server key is used as it is; specs written for the plugin's
servers map by dropping `plugin_wire_`.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

SELECTION_FILE = Path(".wire") / "engagement" / "mcp_servers.yml"

PURPOSE = {
    "atlassian": "Jira issue tracking; Confluence document store and search",
    "linear": "Linear issue tracking (alternative or complement to Jira)",
    "fathom": "Meeting transcripts for review commands",
    "context7": "Library documentation during development",
    "notion": "Notion document store for client review",
    "amplitude": "Amplitude product analytics",
    "coupler-io": "Coupler.io data flows",
    "airbyte": "Airbyte connectors (ingestion audits and migrations)",
}

# In the /wire:mcp spec's catalogue but not configured by the plugin.
EXTRA = {
    "linear": "https://mcp.linear.app/mcp",
    "notion": "https://mcp.notion.com/mcp",
}

# Codex's auth_status values (`codex mcp list --json`). Only not_logged_in
# keeps a server out of a run: unsupported means it needs no sign-in.
NOT_SIGNED_IN = "not_logged_in"

KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def needs_url(url: str) -> bool:
    """The plugin ships a placeholder for servers each organisation hosts itself (Fathom)."""
    return not url or "your-" in url or not url.startswith("https://")


def plugin_servers(root: Path) -> dict:
    """key -> url: the servers the Wire plugin for Claude Code configures. Its
    .mcp.json is at the plugin root (Claude Code plugin), in mcp_servers.json
    (Codex plugin) or under packaging/ (a checkout)."""
    for candidate in (root / "mcp_servers.json", root / ".mcp.json", root / "packaging" / "claude-plugin" / ".mcp.json"):
        if candidate.is_file():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            return {key: (cfg or {}).get("url", "") for key, cfg in (data.get("mcpServers") or {}).items()}
    return {}


def catalogue(root: Path) -> dict:
    """key -> {url, purpose, placeholder}."""
    servers: dict = {}
    for key, url in plugin_servers(root).items():
        servers[key] = {"url": url}
    for key, url in EXTRA.items():
        servers.setdefault(key, {"url": url})
    for key, cfg in servers.items():
        cfg["purpose"] = PURPOSE.get(key, "")
        cfg["placeholder"] = needs_url(cfg["url"])
    return dict(sorted(servers.items()))


# ---------------------------------------------------------------- the selection

def parse_selection(text: str) -> dict:
    """`servers:` then `  <key>: <url>` lines. A tiny reader, so the file stays
    readable without PyYAML; the writer below is the only producer."""
    out: dict = {}
    in_servers = False
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^servers:\s*$", line):
            in_servers = True
            continue
        if not line.startswith(" "):
            in_servers = False
            continue
        m = re.match(r"^\s+([A-Za-z0-9_-]+):\s*[\"']?(https://[^\s\"']+)[\"']?\s*$", line)
        if in_servers and m:
            out[m.group(1)] = m.group(2)
    return out


def render_selection(selection: dict) -> str:
    lines = [
        "# MCP servers this engagement uses (Wire CLI, wire mcp add / remove).",
        "# URLs only: sign-in is per person (wire mcp login <server>), never stored here.",
        "servers:",
    ]
    for key in sorted(selection):
        lines.append(f"  {key}: {selection[key]}")
    return "\n".join(lines) + "\n"


def load_selection(repo: Path) -> dict:
    p = repo / SELECTION_FILE
    return parse_selection(p.read_text(encoding="utf-8")) if p.is_file() else {}


def save_selection(repo: Path, selection: dict) -> Path:
    p = repo / SELECTION_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_selection(selection), encoding="utf-8")
    return p


def add(selection: dict, cat: dict, key: str, url: str | None) -> tuple[dict, str | None]:
    """The selection with `key` added, or the reason it cannot be."""
    if not KEY_RE.match(key or ""):
        return selection, f"{key!r} is not a server key (letters, digits, - and _)"
    chosen = url or (cat.get(key) or {}).get("url", "")
    if not chosen:
        return selection, f"{key} is not in Wire's catalogue; give its URL: wire mcp add {key} https://..."
    if needs_url(chosen):
        return selection, f"{key} has no usable URL ({chosen}); give your organisation's: wire mcp add {key} https://..."
    out = dict(selection)
    out[key] = chosen
    return out, None


# ---------------------------------------------------------------- sign-in and runs

def parse_codex_list(text: str) -> dict:
    """key -> auth_status from `codex mcp list --json`."""
    try:
        rows = json.loads(text or "[]")
    except ValueError:
        return {}
    return {r.get("name"): r.get("auth_status") or "" for r in rows if isinstance(r, dict) and r.get("name")}


TOOLS_KEY = "wire"
# passed through to the tools server from the run's environment
TOOLS_ENV = ["WIRE_LANE_WAREHOUSE_SPEND", "WIRE_SPEND_LEDGER", "WIRE_LANE_LABEL", "WIRE_LANE_RELEASE", "WIRE_PLUGIN_ROOT", "WIRE_INVOKED_BY", "DBT_PROFILES_DIR", "DBT_TARGET",
             "DBT_PROJECT_DIR", "GOOGLE_APPLICATION_CREDENTIALS", "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER",
             "SNOWFLAKE_PASSWORD", "SNOWFLAKE_PRIVATE_KEY_PATH", "DATABRICKS_HOST", "DATABRICKS_TOKEN"]
WIRE_PY = Path(__file__).resolve().parents[1] / "wire.py"


def tools_server(cwd: Path, framework_root: str | None = None) -> dict:
    """The stdio server spec for Wire's own tools (tools_server.py) in this run's folder."""
    import sys
    args = [str(WIRE_PY), "tools-server", "--repo", str(cwd)]
    if framework_root:
        args += ["--framework", str(framework_root)]
    # Wire's own tools are approved for its runs: three only read, and the dbt
    # tool applies the lane's warehouse budget itself.
    return {"command": sys.executable, "args": args, "env_vars": list(TOOLS_ENV), "approve": True}


def with_tools(servers: dict, cwd: Path, env: dict) -> dict:
    """The run's servers plus Wire's tools server, unless WIRE_TOOLS=false."""
    if str((env or {}).get("WIRE_TOOLS", "")).lower() in ("false", "0", "no"):
        return dict(servers or {})
    out = dict(servers or {})
    out[TOOLS_KEY] = tools_server(cwd, (env or {}).get("WIRE_PLUGIN_ROOT"))
    return out


def prompt_note(servers: dict) -> str:
    """One paragraph appended to a run's prompt: Codex loads MCP tools on demand,
    and a model that is not told they exist sometimes answers without them."""
    if not servers:
        return ""
    names = ", ".join(f"{k} ({tool_prefix(k)}<tool>)" for k in sorted(servers))
    note = ("\n\nMCP servers in this run, with how their tools are named: " + names + ". "
            "When a step needs one of these services, look the tool up and call it rather than assuming it is absent.")
    if TOOLS_KEY in servers:
        note += (" The wire server is Wire's own: wire_status and wire_gate answer what a release's state is and "
                 "whether a command may run; wire_lint checks conventions on files you wrote; dbt runs dbt and "
                 "returns a short result. Prefer them to reading status.md or dbt's full log yourself.")
    return note + "\n"


def codex_overrides(servers: dict) -> list:
    """-c overrides: a URL is an HTTP server; a dict (command, args, env_vars) a stdio one."""
    argv: list = []
    for key in sorted(servers):
        v = servers[key]
        if isinstance(v, dict):
            argv += ["-c", f"mcp_servers.{key}.command={json.dumps(v['command'])}",
                     "-c", f"mcp_servers.{key}.args={json.dumps(v.get('args') or [])}"]
            if v.get("env_vars"):
                argv += ["-c", f"mcp_servers.{key}.env_vars={json.dumps(v['env_vars'])}"]
            if v.get("approve"):
                # a headless run cannot answer an approval prompt (seen live: "requires approval,
                # but this run's approval policy is set to never")
                argv += ["-c", f'mcp_servers.{key}.default_tools_approval_mode="approve"']
        else:
            argv += ["-c", f'mcp_servers.{key}.url="{v}"']
    return argv


# Claude Code files an MCP sign-in under the server's name. The Wire plugin's
# servers are named plugin:wire:<key> there, so a CLI run that names a plugin
# server the same way, at the same URL, uses the sign-in the person made with
# /mcp in Claude Code. Measured on Claude Code 2.1.319: `atlassian` at the
# plugin's URL reported needs-auth, `plugin:wire:atlassian` connected with
# 32 tools, after one /mcp sign-in. This is how Claude Code behaves, not a
# documented contract; validate_wire_cli.py checks the naming, and Settings in
# Studio shows the status a run actually sees.
PLUGIN_PREFIX = "plugin:wire:"


def claude_names(servers: dict, plugin: dict) -> dict:
    """The run's servers keyed by the name Claude Code should see: plugin:wire:<key>
    for a server the plugin ships at the same URL, the key otherwise."""
    out = {}
    for key, v in (servers or {}).items():
        same = isinstance(v, str) and key in (plugin or {}) and plugin[key] == v and not needs_url(v)
        out[PLUGIN_PREFIX + key if same else key] = v
    return out


def tool_prefix(name: str) -> str:
    """mcp__<server>__ as Claude Code and Codex name a server's tools
    (plugin:wire:coupler-io -> mcp__plugin_wire_coupler-io__)."""
    return "mcp__" + re.sub(r"[^A-Za-z0-9_-]", "_", name) + "__"


CLAUDE_STATUS = {"connected": "signed_in", "needs-auth": "not_signed_in"}


def parse_claude_init(line: str) -> dict | None:
    """name -> signed_in | not_signed_in | unreachable from the first event of a
    `claude -p --output-format stream-json` run, or None when it is not that event."""
    try:
        e = json.loads(line)
    except ValueError:
        return None
    if e.get("type") != "system" or e.get("subtype") != "init":
        return None
    return {s.get("name"): CLAUDE_STATUS.get(s.get("status"), "unreachable")
            for s in e.get("mcp_servers") or [] if isinstance(s, dict) and s.get("name")}


def claude_sign_in_status(claude: str, servers: dict, cwd: Path, env: dict | None = None,
                          timeout: int = 90) -> dict | None:
    """name -> status for servers (already named by claude_names), as a CLI run
    sees them. Starts a run with the CLI's flags, reads the first event, which
    reports each server once Claude Code has tried it, and stops the run before
    the model is asked anything. None when Claude Code could not be asked."""
    import os
    import threading
    if not servers:
        return {}
    # the prompt comes straight after -p: --mcp-config takes several values and
    # would read a prompt after it as another config
    argv = [claude, "-p", "Reply ok.", "--output-format", "stream-json", "--verbose", "--max-turns", "1",
            "--setting-sources", "project,local", "--strict-mcp-config",
            "--mcp-config", claude_mcp_config(servers)]
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, cwd=str(cwd), env=dict(os.environ if env is None else env))
    except OSError:
        return None
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    found = None
    try:
        for line in proc.stdout:
            found = parse_claude_init(line)
            if found is not None:
                break
    finally:
        timer.cancel()
        proc.kill()
        proc.wait()
    return found


def claude_mcp_config(servers: dict) -> str:
    out = {}
    for k in sorted(servers):
        v = servers[k]
        if isinstance(v, dict):
            out[k] = {"type": "stdio", "command": v["command"], "args": v.get("args") or []}
        else:
            out[k] = {"type": "http", "url": v}
    return json.dumps({"mcpServers": out})


def usable(selection: dict, auth: dict | None) -> tuple[dict, list]:
    """The servers a run gets (every selected one) and a note for each that
    Codex reports as not signed in. auth is None when Codex could not be asked."""
    notes = []
    for key in sorted(selection):
        if auth is not None and auth.get(key) == NOT_SIGNED_IN:
            notes.append(f"{key}: not signed in; its tools are missing if it needs a sign-in (wire mcp login {key})")
    return dict(selection), notes


def agent_env(codex: str, cwd: Path, env: dict | None = None) -> dict:
    """The environment for a codex call: the forked agent's own home (agent_home.py)."""
    import os
    from .harness.codex import is_forked_agent
    base = dict(os.environ if env is None else env)
    if is_forked_agent(codex):
        from .agent_home import prepare
        base, _notes = prepare(cwd, base)
    return base


def sign_in_status(codex: str, selection: dict, cwd: Path, env: dict | None = None) -> dict | None:
    if not selection:
        return {}
    try:
        proc = subprocess.run([codex, *codex_overrides(selection), "mcp", "list", "--json"],
                              capture_output=True, text=True, cwd=str(cwd), timeout=60, env=agent_env(codex, cwd, env))
    except (OSError, subprocess.TimeoutExpired):
        return None
    return parse_codex_list(proc.stdout) if proc.returncode == 0 else None


def servers_for_run(repo: Path, harness: str, codex: str | None = None) -> tuple[dict, list]:
    """The selected, signed-in servers for one run on this harness, and notes."""
    selection = load_selection(repo)
    if not selection or harness == "fake":
        return {}, []
    if harness == "codex":
        from .harness.codex import find_codex
        return usable(selection, sign_in_status(codex or find_codex(), selection, repo))
    # claude: Claude Code keeps its own sign-in (/mcp); it reports a server it
    # cannot reach and goes on, so every selected server is passed.
    return dict(selection), []


# ---------------------------------------------------------------- what a release needs

def required(status: dict) -> list:
    """(server, reason, in_catalogue) for a release, from its status.md front
    matter. The mapping is /wire:mcp Step 4.1."""
    out: list = []

    def need(key, reason, bundled=True):
        if not any(r[0] == key for r in out):
            out.append((key, reason, bundled))

    mig = status.get("migration") or {}
    rtype = status.get("release_type") or status.get("project_type") or ""
    if rtype == "platform_migration":
        if mig.get("source_platform") == "snowflake":
            need("snowflake", "platform_migration from Snowflake", False)
        if "bigquery" in (mig.get("source_platform"), mig.get("target_platform")):
            need("bigquery", "platform_migration to or from BigQuery (the bq CLI is the fallback)", False)
    if mig.get("ingestion_tool") == "fivetran":
        need("fivetran", "ingestion_tool: fivetran", False)
    if mig.get("ingestion_tool") == "rudderstack":
        need("rudderstack", "ingestion_tool: rudderstack", False)
    if (status.get("jira") or {}).get("project_key"):
        need("atlassian", "jira.project_key is set")
    if (status.get("linear") or {}).get("project_id") or (status.get("linear") or {}).get("team_key"):
        need("linear", "linear is configured")
    provider = (status.get("docstore") or {}).get("provider")
    if provider == "confluence":
        need("atlassian", "docstore.provider: confluence")
    if provider == "notion":
        need("notion", "docstore.provider: notion")
    need("fathom", "review steps read meeting context (optional: reviews go on without it)")
    return out


def check(status: dict, selection: dict, auth: dict | None) -> list:
    """Rows (server, reason, state) for `wire mcp check`."""
    rows = []
    for key, reason, bundled in required(status):
        if key not in selection:
            state = "not in this engagement (wire mcp add " + key + (" <url>)" if not bundled else ")")
        elif auth is not None and auth.get(key) == NOT_SIGNED_IN:
            state = f"selected, not signed in (wire mcp login {key})"
        elif auth is None:
            state = "selected; sign-in unknown"
        else:
            state = "ready"
        rows.append((key, reason, state))
    return rows


# ---------------------------------------------------------------- wire mcp

def command(repo: Path, root: Path, args, env: dict, out=print) -> int:
    """wire mcp list | add <key> [url] | remove <key> | login <key> | check <release>"""
    from .harness.codex import find_codex
    cat = catalogue(root)
    selection = load_selection(repo)
    action = args.action
    codex = find_codex()

    if action == "list":
        auth = sign_in_status(codex, selection, repo)
        out(f"MCP servers (catalogue: {len(cat)}; this engagement: {len(selection)}, in {SELECTION_FILE})")
        for key in sorted(set(cat) | set(selection)):
            info = cat.get(key, {})
            url = selection.get(key) or info.get("url", "")
            if key in selection:
                state = "selected, " + ("sign-in unknown" if auth is None else
                                        ("not signed in" if auth.get(key) == NOT_SIGNED_IN else "ready"))
            else:
                state = "not selected" + (" (needs your organisation's URL)" if info.get("placeholder") else "")
            out(f"  {key:12} {state:30} {url}")
            if info.get("purpose"):
                out(f"  {'':12} {info['purpose']}")
        out("Add one: wire mcp add <server> [url]   Sign in: wire mcp login <server>")
        return 0

    if action == "add":
        new, why = add(selection, cat, args.key or "", args.url)
        if why:
            out(f"Not added: {why}")
            return 2
        p = save_selection(repo, new)
        out(f"Added {args.key} ({new[args.key]}) to {p.relative_to(repo)}. Commit it so the team shares the list.")
        out(f"Then sign in: wire mcp login {args.key}")
        return 0

    if action == "remove":
        if args.key not in selection:
            out(f"{args.key} is not in {SELECTION_FILE}")
            return 2
        new = {k: v for k, v in selection.items() if k != args.key}
        save_selection(repo, new)
        out(f"Removed {args.key}. Your sign-in stays in Codex's store; codex mcp logout {args.key} removes it.")
        return 0

    if action == "login":
        if args.key not in selection:
            out(f"{args.key} is not selected for this engagement; wire mcp add {args.key} first.")
            return 2
        harness = getattr(args, "harness", None) or "codex"
        if harness == "claude":
            out(f"Claude Code keeps its own sign-in: run claude in this repository, then /mcp and choose {args.key}.")
            return 0
        argv = [codex, *codex_overrides({args.key: selection[args.key]}), "mcp", "login", args.key]
        out(f"Signing in to {args.key} through Codex (a browser opens; the token stays in Codex's store).")
        try:
            return subprocess.run(argv, cwd=str(repo), env=agent_env(codex, repo, env)).returncode
        except OSError as exc:
            out(f"Could not run {codex}: {exc}")
            return 1

    if action == "check":
        if not args.key:
            out("usage: wire mcp check <release>")
            return 2
        from .framework import load_script
        status_path = repo / ".wire" / "releases" / args.key / "status.md"
        if not status_path.is_file():
            out(f"No status.md for release {args.key}")
            return 2
        status, _body, _ = load_script(root, "status_file").front_matter(status_path.read_text(encoding="utf-8"))
        status = status or {}
        auth = sign_in_status(codex, selection, repo)
        rows = check(status, selection, auth)
        out(f"MCP check for {args.key}")
        for key, reason, state in rows:
            out(f"  {key:12} {state:45} {reason}")
        missing = [r for r in rows if r[2] != "ready" and r[0] != "fathom"]
        out("Ready." if not missing else f"{len(missing)} server(s) need attention; commands that use them take their fallback path.")
        return 0 if not missing else 1

    out("usage: wire mcp list | add <server> [url] | remove <server> | login <server> | check <release>")
    return 2
