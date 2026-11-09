"""The argument parser and dispatch for the Wire CLI."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__

SUBCOMMANDS = ("run", "status", "gate", "exec", "codex-install", "version", "shell", "doctor", "bridge", "mcp", "tools-server", "eval", "update", "uninstall")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="wire", description="The Wire CLI (experimental)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", default=".", help="the engagement repository (default: the current directory)")
    common.add_argument("--framework", default=None, help="the Wire framework root (default: where this CLI ships)")
    common.add_argument("--harness", choices=("codex", "claude", "fake"), help="codex (default), claude or fake")
    common.add_argument("--model", help="model for the harness")
    common.add_argument("--provider", help="model provider (codex: the model_providers id, e.g. lmstudio)")
    common.add_argument("--sandbox", help="read-only, workspace-write (default) or danger-full-access")
    common.add_argument("--json", action="store_true", help="machine-readable output where supported")
    common.add_argument("--quiet", action="store_true", help="no banner")

    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run", parents=[common], help="orchestrate a release: runnable set, lanes, record")
    p.add_argument("release")
    p.add_argument("--yes", action="store_true", help="go without asking (the run plan is still printed)")
    p.add_argument("--dry-run", action="store_true", help="print the run plan and stop")
    p.add_argument("--once", action="store_true", help="one pass only")
    p.add_argument("--max-passes", type=int, default=10)
    p.add_argument("--take-over", action="store_true", help="take a claim another person left silent for over 30 minutes")
    p.add_argument("--request", action="append", help="put an optional artifact in scope (repeatable)")
    p.add_argument("--no-commit-record", action="store_true",
                   help="leave status.md, execution_log.md and decisions.md uncommitted after a pass")
    p.add_argument("--no-interaction", action="store_true",
                   help="never ask: a lane that stops on a question is parked (the default with no terminal)")

    p = sub.add_parser("status", parents=[common], help="states, runnable set, claim and next action")
    p.add_argument("release")
    p.add_argument("--request", action="append")

    p = sub.add_parser("gate", parents=[common], help="the precondition gate's answer for one command")
    p.add_argument("release")
    p.add_argument("command")

    p = sub.add_parser("exec", parents=[common], help="run one prompt headless through the harness")
    p.add_argument("prompt", nargs="?", default="-", help="the prompt, or - for stdin")

    p = sub.add_parser("codex-install", parents=[common], help="install the Codex plugin's install set into a repository")
    p.add_argument("--plugin", help="the built Codex plugin (default: the framework's dist/codex-plugin or the plugin root)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--copy", action="store_true",
                   help="copy the plugin into the repository even when wire-agent carries it (for OpenAI's own codex)")

    sub.add_parser("version", help="print the CLI version")
    p = sub.add_parser("bridge", parents=[common], help="Claude for the codex harness: a local Responses-to-Anthropic bridge")
    p.add_argument("action", choices=("start", "stop", "status"))
    sub.add_parser("doctor", parents=[common], help="check the harnesses, keys, local model server and the repository's install")
    p = sub.add_parser("update", help="install the newest Wire CLI release (--check only reports)")
    p.add_argument("--check", action="store_true")
    p = sub.add_parser("uninstall", help="remove the Wire CLI's install (--yes to do it; --all also removes keys and the agent home)")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("eval", parents=[common], help="run an eval suite on a harness and model, graded without a model")
    p.add_argument("suite", nargs="?", default="core", help="a suite name under cli/evals/, or a YAML path")
    p.add_argument("--case", action="append", help="run only this case (repeatable)")
    p.add_argument("--record", help="write the report JSON into this folder")
    p = sub.add_parser("tools-server", parents=[common], help="Wire's own tools for the agent, as an MCP server on stdio (started by the agent)")
    p = sub.add_parser("mcp", parents=[common], help="MCP servers: list, add, remove, login, check <release>")
    p.add_argument("action", choices=("list", "add", "remove", "login", "check"))
    p.add_argument("key", nargs="?", help="the server (add, remove, login) or the release (check)")
    p.add_argument("url", nargs="?", help="add: the server's URL when it is not in Wire's catalogue")

    return ap


def typed_parser() -> argparse.ArgumentParser:
    """`wire <command> <release> [args]`: the common flags anywhere on the
    line, everything else positional (name, release, the command's own args)."""
    ap = argparse.ArgumentParser(prog="wire <command>", add_help=True)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--framework", default=None)
    ap.add_argument("--harness", choices=("codex", "claude", "fake"))
    ap.add_argument("--model")
    ap.add_argument("--provider")
    ap.add_argument("--sandbox")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--override-gate", metavar="REASON")
    ap.add_argument("--first", metavar="DIRECTION", help="the session: take this as its first line (Wire Studio's Run in Wire CLI)")
    return ap


def main(argv: list | None = None, out=print, env: dict | None = None, ask=None, stream=None) -> int:
    """`ask`: the session's way to take an answer from the person, for a lane's
    question in `wire run` and for a typed command's conversation (tests pass one).
    `stream`: where a typed command or `exec` shows its reply as it is written
    (wire_cli/stream.py); on a terminal it defaults to stdout."""
    argv = list(sys.argv[1:] if argv is None else argv)
    env = dict(os.environ if env is None else env)
    if not argv or (len(argv) >= 1 and argv[0] == "shell") or (argv and argv[0].startswith("--first")):
        # `wire` alone: the interactive session.
        shell_args, rest = typed_parser().parse_known_args(argv[1:] if argv and argv[0] == "shell" else argv)
        from .secrets import load_secrets
        from .shell import run_shell
        env, _notes = load_secrets(env, Path(shell_args.repo).resolve())
        return run_shell(Path(shell_args.repo).resolve(), env, out=out, harness=shell_args.harness, model=shell_args.model,
                         provider=shell_args.provider, sandbox=shell_args.sandbox, framework=shell_args.framework,
                         first=shell_args.first)
    if argv and argv[0] not in SUBCOMMANDS and not argv[0].startswith("-"):
        args, rest = typed_parser().parse_known_args(argv)
        from .commands import NO_RELEASE
        from .framework import normalise_command
        if rest and normalise_command(rest[0]) in NO_RELEASE:
            args.cmd, args.name, args.release, args.extra = "command", rest[0], "", rest[1:]
        elif len(rest) < 2:
            out("usage: wire <command> <release> [args] [--harness ...] [--repo ...]")
            return 2
        else:
            args.cmd, args.name, args.release, args.extra = "command", rest[0], rest[1], rest[2:]
    else:
        ap = build_parser()
        args = ap.parse_args(argv)
    if args.cmd is None:
        from .shell import run_shell
        return run_shell(Path(args.repo).resolve() if hasattr(args, "repo") else Path.cwd(), env, out=out)
    if args.cmd == "version":
        out(f"wire {__version__}")
        return 0
    if args.cmd == "update":
        from .install_ops import update
        return update(__version__, args.check, out, env)
    if args.cmd == "uninstall":
        from .install_ops import uninstall
        return uninstall(args.yes, getattr(args, "all", False), out, env)
    if args.cmd == "tools-server":
        # stdout carries the protocol only: nothing else is printed here
        from .framework import framework_root
        from .tools_server import serve
        return serve(Path(args.repo).resolve(), framework_root(args.framework), env)
    repo = Path(args.repo).resolve()
    from . import commands as cmds
    from .secrets import load_secrets
    env, secret_notes = load_secrets(env, repo)
    for note in secret_notes:
        out(f"secrets: {note}")
    if args.cmd == "doctor":
        from .doctor import doctor
        return doctor(repo, env, args, out)
    if args.cmd == "bridge":
        from . import bridge
        return {"start": lambda: bridge.start(env, out=out), "stop": lambda: bridge.stop(out=out), "status": lambda: bridge.status(out=out)}[args.action]()

    if args.cmd == "eval":
        from .evals import command as eval_command
        from .framework import framework_root
        return eval_command(framework_root(args.framework), args, env, out)
    if args.cmd == "mcp":
        from .framework import framework_root
        from .mcp import command as mcp_command
        return mcp_command(repo, framework_root(args.framework), args, env, out)
    if args.cmd == "status":
        return cmds.show_status(repo, args.release, args, out)
    if args.cmd == "gate":
        return cmds.show_gate(repo, args.release, args.command, args, out)
    if args.cmd == "codex-install":
        from .framework import framework_root
        root = framework_root(args.framework)
        plugin = Path(args.plugin) if args.plugin else (root / "dist" / "codex-plugin" if (root / "dist" / "codex-plugin").is_dir() else root)
        from .framework import load_script
        pkg = load_script(root, "codex_package")
        carried = None
        if not args.plugin and not args.copy:
            from .agent_home import carried_framework, prepare
            from .harness.codex import find_codex, is_forked_agent
            exe = find_codex(env)
            if is_forked_agent(exe):
                agent_env, _n = prepare(repo, env, root)
                carried = carried_framework(exe, agent_env)
        try:
            if carried:
                out(f"wire-agent carries the Wire framework ({carried}); the plugin is not copied into the repository.")
                for w in pkg.install_bundled(carried, repo, args.force):
                    out(f"wrote {w}")
            else:
                for w in pkg.install(plugin, repo, args.force):
                    out(f"wrote {w}")
        except FileExistsError as exc:
            out(f"refused: {exc}")
            return 1
        out("wire-agent trusts these hooks itself, in its own home (~/.wire/agent), while hooks.json is Wire's.")
        out("With OpenAI's own codex, trust them once with /hooks.")
        return 0
    if stream is None and out is print and args.cmd in ("exec", "command"):
        from .stream import for_terminal
        stream = for_terminal(env)
    args.stream = stream
    if args.cmd == "exec":
        prompt = sys.stdin.read() if args.prompt == "-" else args.prompt
        settings = cmds.settings_for(repo, None, args, env)
        return cmds.run_exec(repo, prompt, settings, args, out, env)
    if args.cmd == "run":
        from .orchestrator import run
        if ask is not None:
            args.ask = ask
        settings = cmds.settings_for(repo, args.release, args, env)
        return run(repo, args.release, settings, args, out, env)
    if args.cmd == "command":
        from .framework import normalise_command
        if ask is not None:
            args.ask = ask
        settings = cmds.settings_for(repo, args.release, args, env)
        return cmds.run_typed(repo, normalise_command(args.name), args.release, args.extra, settings, args, out, env)
    build_parser().print_help()
    return 2
