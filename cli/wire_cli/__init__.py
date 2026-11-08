"""The Wire CLI package (experimental, wire#408).

Modules:
  framework   where the specs, release types, catalogue and Studio resolver are
  record      status.md and execution_log.md writes: the single writer
  claim       the release claim (director_operating_model.md, "The release claim")
  settings    harness, provider and model resolution; the lane model order
  harness     the adapter interface and the codex, claude and fake adapters
  lanes       lane briefs, worktrees, ownership checks, merge
  orchestrator  `wire run`: runnable set, dispatch, consolidation
  commands    a typed run of one Wire command
  main        the argument parser
"""



def _version() -> str:
    """The Wire version this CLI ships with: the package's VERSION file (an
    install), the plugin manifest beside it (the built Codex or Claude Code
    plugin), or the Claude plugin manifest in a checkout."""
    import json
    from pathlib import Path
    here = Path(__file__).resolve()
    root = here.parents[2]
    for candidate in (root / "VERSION",):
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8").strip()
    for manifest in (root / "plugin.json", root / ".claude-plugin" / "plugin.json",
                     root / "packaging" / "claude-plugin" / ".claude-plugin" / "plugin.json"):
        if manifest.is_file():
            try:
                return json.loads(manifest.read_text(encoding="utf-8")).get("version", "unknown")
            except ValueError:
                pass
    return "unknown"


__version__ = _version()
