"""Harness, provider and model resolution.

Sources, highest first: command-line flags; WIRE_HARNESS, WIRE_MODEL,
WIRE_MODEL_PROVIDER, WIRE_SANDBOX in the environment; the release's
`budget.harness` block in status.md; the engagement's `harness:` block in
.wire/engagement/context.md; defaults. With none of these naming a harness,
model or provider and ANTHROPIC_API_KEY set, the default is Claude Opus 5.5
(claude-opus-5-5) on the claude harness, or on codex's Anthropic provider
when `claude` is not installed. With no key set at all and `claude` installed
(the Claude Code plugin), it is Opus 5.5 on the claude harness on Claude
Code's own sign-in. Otherwise, codex with its own default model. The claude harness with no model named also runs Opus 5.5. Sandbox
defaults to workspace-write.

    harness:
      default: codex            # codex | claude
      codex:
        model_provider: lmstudio
        model: qwen/qwen3.6-35b-a3b
        sandbox: workspace-write
      claude:
        model: claude-sonnet-5-5

The lane model (specs/delegate.md, "Lane model"): the command's workload tier
(rule 1), the economy model when budget.model_tier is economy and the command
is not client-facing (rule 2), else the configured model (rule 3). The routing
file's tier values are Claude model ids; they apply to the claude harness. A
`tiers_<harness>:` block (none today) would carry another harness's ids. Item
4 of wire#408 makes the routing file provider-neutral.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

HARNESSES = ("codex", "claude", "fake")
DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"  # the latest Claude Opus


@dataclass
class Settings:
    harness: str = "codex"
    model: str | None = None
    provider: str | None = None
    sandbox: str = "workspace-write"
    sources: dict = field(default_factory=dict)

    def describe(self) -> str:
        bits = [f"harness={self.harness}"]
        if self.provider:
            bits.append(f"provider={self.provider}")
        bits.append(f"model={self.model or 'default'}")
        return " ".join(bits)


def _harness_block(data: dict) -> dict:
    block = (data or {}).get("harness")
    return block if isinstance(block, dict) else {}


def resolve_settings(context: dict, status: dict, flags: dict, env: dict, claude_bin: str | None = "auto") -> Settings:
    s = Settings()
    layers = [
        ("engagement", _harness_block(context)),
        ("release", _harness_block((status or {}).get("budget") or {})),
    ]
    for name, block in layers:
        if block.get("default") in HARNESSES:
            s.harness, s.sources["harness"] = block["default"], name
    if env.get("WIRE_HARNESS") in HARNESSES:
        s.harness, s.sources["harness"] = env["WIRE_HARNESS"], "env"
    if flags.get("harness") in HARNESSES:
        s.harness, s.sources["harness"] = flags["harness"], "flag"
    for name, block in layers:
        hb = block.get(s.harness)
        if isinstance(hb, dict):
            for key, attr in (("model", "model"), ("model_provider", "provider"), ("sandbox", "sandbox")):
                if hb.get(key):
                    setattr(s, attr, str(hb[key]))
                    s.sources[attr] = name
    for key, attr in (("WIRE_MODEL", "model"), ("WIRE_MODEL_PROVIDER", "provider"), ("WIRE_SANDBOX", "sandbox")):
        if env.get(key):
            setattr(s, attr, env[key])
            s.sources[attr] = "env"
    for key, attr in (("model", "model"), ("provider", "provider"), ("sandbox", "sandbox")):
        if flags.get(key):
            setattr(s, attr, flags[key])
            s.sources[attr] = "flag"
    unset = not {"harness", "model", "provider"} & s.sources.keys()
    if unset and claude_bin == "auto":
        claude_bin = shutil.which("claude", path=env.get("PATH"))  # on the run's own PATH
    no_keys = not (env.get("OPENAI_API_KEY") or env.get("CODEX_API_KEY"))
    if unset and (env.get("ANTHROPIC_API_KEY") or (claude_bin and no_keys)):
        s.harness, s.provider = ("claude", None) if claude_bin else ("codex", "anthropic")
        s.model = DEFAULT_CLAUDE_MODEL
        s.sources.update(harness="default", model="default")
    elif s.harness == "claude" and not s.model:
        s.model, s.sources["model"] = DEFAULT_CLAUDE_MODEL, "default"
    return s


# ---------------------------------------------------------------- model routing

def read_routing(path: Path) -> dict:
    """tiers, lane_economy and any tiers_<harness> / lane_economy_<harness>
    from wire/model-routing.yaml, without a YAML library."""
    out: dict = {"tiers": {}, "lane_economy": None, "per_harness": {}}
    if not path.is_file():
        return out
    section = None
    for raw in path.read_text(encoding="utf-8").split("\n"):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(tiers(?:_([a-z]+))?):\s*$", line)
        if m:
            section = ("tiers", m.group(2))
            continue
        m = re.match(r'^lane_economy(?:_([a-z]+))?:\s*"([^"]*)"', line)
        if m:
            if m.group(1):
                out["per_harness"].setdefault(m.group(1), {}).setdefault("lane_economy", m.group(2) or None)
            else:
                out["lane_economy"] = m.group(2) or None
            section = None
            continue
        m = re.match(r'^  ([a-z-]+):\s*"([^"]*)"', line)
        if m and section:
            if section[1]:
                out["per_harness"].setdefault(section[1], {}).setdefault("tiers", {})[m.group(1)] = m.group(2)
            else:
                out["tiers"][m.group(1)] = m.group(2)
    return out


CLAUDE_PROVIDERS = ("anthropic", "wirebridge")


def routing_key(settings: Settings) -> str:
    """Which block of model-routing.yaml a run reads (ROADMAP.md phase 6): Claude's
    tiers for any run on Claude (the claude harness, or the codex harness with
    the native Anthropic provider or the bridge); else `tiers_<provider>` for a
    named provider (lmstudio, ollama, ...); else `tiers_<harness>`."""
    if settings.harness == "claude" or (settings.provider or "") in CLAUDE_PROVIDERS:
        return "claude"
    return settings.provider or settings.harness


def lane_model(settings: Settings, routing: dict, workload: str, client_facing: bool, status: dict) -> tuple[str | None, str]:
    """(model, rule) for one lane, by the order in specs/delegate.md."""
    key = routing_key(settings)
    if key == "claude":
        tiers, economy = routing.get("tiers", {}), routing.get("lane_economy")
    else:
        ph = routing.get("per_harness", {}).get(key, {})
        tiers, economy = ph.get("tiers", {}), ph.get("lane_economy")
    if workload and tiers.get(workload):
        return tiers[workload], f"rule 1: workload tier {workload}"
    tier_mode = ((status or {}).get("budget") or {}).get("model_tier")
    if tier_mode == "economy" and not client_facing:
        if economy:
            return economy, "rule 2: economy"
        return settings.model, "rule 3: economy model unknown for this harness, session default"
    return settings.model, "rule 3: session default"
