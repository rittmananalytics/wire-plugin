#!/usr/bin/env python3
"""
agents_schema_plan.py — the deterministic half of /wire:agents_schema-generate.

Agents Schema (https://github.com/dbt-labs/agents_schema) publishes metadata
about a warehouse into the warehouse itself, in a schema named AGENTS, so an
agent that queries the warehouse finds governed context next to the data:
which dbt models exist and what their columns mean (AGENTS.DBT_*), what the
semantic layer exposes (AGENTS.LOOKML_*, AGENTS.OMNI_*, AGENTS.OSI_*,
AGENTS.SIGMA_*), and warehouse-delivered skills (rows in AGENTS.ROOT whose key
starts with skill/). The `agents-schema` CLI and its reusable GitHub workflows
do the publishing. This script plans that publication for one Wire release and
writes everything the publication needs, without an AI call and without a
warehouse connection:

  * the GitHub Actions workflow that publishes on every push to the default
    branch (`.github/workflows/agents-schema.yml`), one job per detected
    provider, chained in a fixed order, every job pinned to one release tag;
  * `agents.yml` at the repository root, the file the agents-schema consumer
    skills read to find the warehouse (project and location on BigQuery, the
    Snowflake CLI connection name, the Databricks host, path and catalog; never
    a credential);
  * the skills directory the skills provider publishes: every source markdown
    file copied with a `uses:` front-matter derived from the dbt manifest
    (the tables of the models colocated with it), plus a draft
    `warehouse_guide.md` built from the manifest that the consultant
    completes;
  * `plan.json` (what will be published, with the counts validate compares
    against the warehouse), `run.sh` (the same publication from a laptop) and
    `checks.sql` (the validate queries in the destination's dialect);
  * when the LookML lives in another repository (`--lookml-repo`), a second
    workflow file, `lookml_repo/agents-schema-lookml.yml` under --out, to commit
    in that repository as `.github/workflows/agents-schema-lookml.yml`. The
    upstream Looker workflow checks out the repository that calls it, so the
    LookML repository has to publish itself; each provider replaces only its own
    tables, so two repositories writing into one AGENTS schema is by design.

The same inputs always produce the same files; wire/tests/development/
validate_agents_schema_plan.py holds that to be true byte for byte. Anything
the script cannot decide goes to `needs_human` in plan.json with a reason.

Standard library only. Paths given on the command line are relative to
--repo-root unless absolute.

Usage:
    python3 agents_schema_plan.py --repo-root . --out .wire/releases/<r>/dev/agents_schema \
        --destination bigquery --project-id my-project --location EU \
        --dbt-project-dir dbt --dbt-profile my_profile --dbt-target prod \
        [--lookml-dir looker | --lookml-repo owner/repo[@ref] [--lookml-repo-dir .] [--lookml-repo-local ~/GitHub/looker]] \
        [--omni-dir "omni/My Connection"] [--osi-dir osi] [--sigma-dir sigma] \
        [--skills-source dbt/models/marts]... [--provider acme] \
        [--skills-out agents_schema/skills] [--workflow-path .github/workflows/agents-schema.yml] \
        [--branch main] [--agents-schema-version v0.0.11] [--layer-path models/warehouse] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

SCRIPT_VERSION = "1.3.0"
DEFAULT_AGENTS_SCHEMA_VERSION = "v0.0.11"
AGENTS_SCHEMA_REPO = "dbt-labs/agents_schema"

# The order the jobs chain in, and the order run.sh runs them. dbt first, so the
# built-in analyst skill and the dbt ROOT rows exist before anything reads them;
# skills last, so a skill's uses: can be checked against tables already described.
PROVIDER_ORDER = ("dbt", "looker", "omni", "osi", "sigma", "skills")

# CLI source name -> the provider value the CLI writes into AGENTS.ROOT.
ROOT_PROVIDER = {"dbt": "dbt", "looker": "lookml", "omni": "omni", "osi": "osi", "sigma": "sigma", "skills": "skills"}

# The table family each source replaces (SPEC.md, "Delivered Source Tables").
TABLES = {
    "dbt": ("DBT_MODEL", "DBT_COLUMN", "DBT_DEPENDENCY"),
    "looker": ("LOOKML_VIEW", "LOOKML_DIMENSION", "LOOKML_MEASURE", "LOOKML_EXPLORE"),
    "omni": ("OMNI_VIEW", "OMNI_DIMENSION", "OMNI_MEASURE", "OMNI_TOPIC", "OMNI_TOPIC_JOIN"),
    "osi": ("OSI_MODEL", "OSI_DATASET", "OSI_FIELD", "OSI_METRIC", "OSI_RELATIONSHIP"),
    "sigma": ("SIGMA_DATA_MODEL", "SIGMA_ELEMENT", "SIGMA_COLUMN", "SIGMA_METRIC"),
    "skills": ("SKILL_USE",),
}

# The reusable workflow input that names the source directory, per source.
WORKFLOW_INPUT = {"dbt": "dbt-project-dir", "looker": "lookml-dir", "omni": "omni-dir",
                  "osi": "osi-dir", "sigma": "sigma-dir", "skills": "skills-dir"}

# dbt adapter package per destination, for the workflow's managed parse.
ADAPTER_PACKAGE = {"bigquery": "dbt-bigquery", "snowflake": "dbt-snowflake", "databricks": "dbt-databricks"}


def dbt_parse_command(project_dir: str, profile: str, target: str | None, destination: str) -> str:
    """The managed-parse command the workflow runs when target/manifest.json is not
    committed. The upstream action's default is `uvx --with <adapter> dbt parse`,
    in which `dbt` resolves to an unrelated PyPI package of that name and dbt-core
    then mismatches the adapter (ImportError: ArtifactMixin, seen on v0.0.11).
    Pinning `--from dbt-core` makes `dbt` the real dbt-core entry point. $profiles_dir
    is the action's own variable, expanded when it evals the command."""
    adapter = ADAPTER_PACKAGE[destination]
    common = f'--project-dir {project_dir} --profiles-dir "$profiles_dir" --profile {profile}' + (f" --target {target}" if target else "")
    return (f"uvx --from dbt-core --with {adapter} dbt deps {common} && "
            f"uvx --from dbt-core --with {adapter} dbt parse {common} --no-partial-parse")


# The CLI flag that names the source directory, per source.
CLI_FLAG = {"dbt": "--project-dir", "looker": "--lookml-dir", "omni": "--omni-dir",
            "osi": "--osi-dir", "sigma": "--sigma-dir", "skills": "--skills-dir"}

# What each source ingester reads (agents_schema/{lookml,omni,osi,sigma}.py).
SOURCE_GLOBS = {
    "looker": ("**/*.lkml",),
    "omni": ("**/*.view.yaml", "**/*.topic.yaml"),
    "osi": ("*.osi.yaml",),
    "sigma": ("**/*.sigma.yaml",),
}

BUILTIN_SKILL_KEY = "skill/agents-schema-analyst"
DRAFT_MARKER = "<!-- wire: complete"
DOCS_BLOCK_RE = re.compile(r"\{%-?\s*docs\b")
PROVIDER_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ROLE_SUFFIXES = (("_fact", "fact"), ("_dim", "dimension"), ("_xa", "cross-attribute"), ("_agg", "aggregate"))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def posix(path: Path) -> str:
    return PurePosixPath(path).as_posix()


def rel_to(path: Path, root: Path) -> str:
    try:
        return posix(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return posix(path)


def resolve(root: Path, given: str | None) -> Path | None:
    if given is None:
        return None
    p = Path(given)
    return p if p.is_absolute() else root / p


def yaml_str(value: str) -> str:
    """Quote a scalar for the YAML we write when it would otherwise be misread."""
    if value == "" or re.search(r"[:#{}\[\],&*!|>'\"%@`]|^\s|\s$|^[-?]", value) or value.lower() in ("true", "false", "null", "yes", "no", "~"):
        return json.dumps(value)
    return value


def write_text(path: Path, text: str, written: list[str], root: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    written.append(rel_to(path, root))


# ---------------------------------------------------------------------------
# dbt manifest
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def model_nodes(manifest: dict) -> dict[str, dict]:
    """Exactly the nodes agents_schema/dbt.py publishes: every node with
    resource_type == 'model', whatever its config says. A disabled model that
    dbt still lists under nodes is published too; the plan reports those."""
    return {uid: node for uid, node in sorted(manifest.get("nodes", {}).items())
            if node.get("resource_type") == "model"}


def dbt_counts(models: dict[str, dict]) -> dict:
    columns = sum(len(node.get("columns") or {}) for node in models.values())
    deps = sum(len((node.get("depends_on") or {}).get("nodes") or []) for node in models.values())
    return {"models": len(models), "columns": columns, "dependencies": deps}


def relation(node: dict) -> str | None:
    schema = node.get("schema")
    name = node.get("alias") or node.get("name")
    if not schema or not name:
        return None
    return f"{schema}.{name}"


def model_dir(node: dict) -> str | None:
    p = node.get("original_file_path")
    return posix(Path(p).parent) if p else None


# ---------------------------------------------------------------------------
# LookML pre-check (mirrors agents_schema/lookml.py's parser, so a file the
# upstream CLI would refuse is named here instead of failing the publish)
# ---------------------------------------------------------------------------

LKML_BLOCK_RE = re.compile(r"\b(view|explore|dimension|dimension_group|measure)\s*:\s*([A-Za-z_][\w.]*)\s*\{")


def lkml_strip_comments(text: str) -> str:
    out, quote, i = [], None, 0
    while i < len(text):
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < len(text):
                i += 1; out.append(text[i])
            elif ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch; out.append(ch)
        elif ch == "#":
            while i < len(text) and text[i] != "\n":
                i += 1
            if i < len(text):
                out.append("\n")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def lkml_unterminated(text: str) -> int | None:
    """The 1-based line of the first block the upstream parser cannot close, else None.
    The upstream matcher honours ' and " quotes but knows nothing of SQL -- comments,
    so an apostrophe in a comment inside a sql: block opens a quote that never closes."""
    text = lkml_strip_comments(text)
    pos = 0
    while (m := LKML_BLOCK_RE.search(text, pos)):
        depth, quote, i = 0, None, m.end() - 1
        while i < len(text):
            ch = text[i]
            if quote:
                if ch == "\\":
                    i += 1
                elif ch == quote:
                    quote = None
            elif ch in ("'", '"'):
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        else:
            return text.count("\n", 0, m.start()) + 1
        pos = i + 1
    return None


def lkml_precheck(ldir: Path, files: list[str], label: str, needs_human: list[dict]) -> None:
    bad = []
    for rel in files:
        line = lkml_unterminated((ldir / rel).read_text(encoding="utf-8", errors="replace"))
        if line is not None:
            bad.append(f"{rel} (block opened at line {line})")
    if bad:
        needs_human.append({"item": "looker", "reason": "lookml_unparseable",
                            "detail": f"{len(bad)} file(s) in {label} the agents-schema LookML parser cannot close, so the looker publish would fail with 'unterminated LookML block': {'; '.join(bad)}. The usual cause is an apostrophe or quote inside a SQL -- comment in a sql: block; reword the comment."})


# ---------------------------------------------------------------------------
# skills
# ---------------------------------------------------------------------------

def split_frontmatter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    return None, text


def uses_from_frontmatter(fm: str) -> list[tuple[str, str]]:
    """The (use_kind, object_ref) pairs under uses:, read with the same shape
    agents_schema/skills.py accepts. Anything else in the front-matter is left
    alone; this is a count for the plan, not a validation."""
    rows: list[tuple[str, str]] = []
    in_uses, kind = False, None
    for raw in fm.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            in_uses = line.startswith("uses:")
            kind = None
            continue
        if not in_uses:
            continue
        if line.startswith("schemas:"):
            kind = "schema"
        elif line.startswith("tables:"):
            kind = "table"
        elif line.startswith("- ") and kind:
            rows.append((kind, line[2:].strip().strip("'\"")))
    return rows


def skill_key_for(source: Path, source_root: Path) -> str:
    """skill/<domain> for a colocated DOMAIN_REFERENCE.md, otherwise the CLI's
    own rule: skill/<path relative to the skills dir, without .md>."""
    if source.name == "DOMAIN_REFERENCE.md":
        return "skill/" + source.parent.name
    if source == source_root:
        return "skill/" + source.stem
    return "skill/" + posix(source.relative_to(source_root).with_suffix(""))


def collect_skill_sources(root: Path, given: list[str], skipped: list[dict]) -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    for g in given:
        p = resolve(root, g)
        if p is None or not p.exists():
            skipped.append({"path": g, "reason": "missing_source"})
            continue
        files = [p] if p.is_file() else sorted(q for q in p.rglob("*.md") if q.is_file())
        for f in files:
            text = f.read_text(encoding="utf-8", errors="replace")
            if DOCS_BLOCK_RE.search(text):
                skipped.append({"path": rel_to(f, root), "reason": "docs_block",
                                "detail": "a dbt {% docs %} block, not a skill"})
                continue
            out.append((f, p))
    return out


def derived_uses(source: Path, dbt_project: Path | None, models: dict[str, dict]) -> tuple[list[str], str | None]:
    """Tables of the models that sit in the same folder as the skill file.
    Returns (tables, reason_if_none)."""
    if dbt_project is None:
        return [], "no dbt project to derive uses from"
    try:
        folder = posix(source.parent.resolve().relative_to(dbt_project.resolve()))
    except ValueError:
        return [], "skill file is outside the dbt project"
    tables, unresolved = [], []
    for node in models.values():
        if model_dir(node) != folder:
            continue
        r = relation(node)
        (tables if r else unresolved).append(r or node.get("name"))
    if not tables and not unresolved:
        return [], f"no models in {folder}"
    if unresolved:
        return sorted(set(tables)), f"{len(unresolved)} colocated model(s) carry no schema in the manifest"
    return sorted(set(tables)), None


def uses_frontmatter(tables: list[str]) -> str:
    lines = ["---", "uses:", "  tables:"] + [f"    - {t}" for t in tables] + ["---", "", ""]
    return "\n".join(lines)


def warehouse_guide(models: dict[str, dict], layer_path: str, dbt_project_rel: str) -> tuple[str, list[str]]:
    """A draft skill describing the warehouse layer, one section per subject
    area (the folder under the layer), one row per model. Returns the markdown
    and the tables it declares in uses:."""
    layer = layer_path.strip("/")
    areas: dict[str, list[dict]] = {}
    for node in models.values():
        d = model_dir(node)
        if d is None or not (d == layer or d.startswith(layer + "/")):
            continue
        if (node.get("config") or {}).get("materialized") == "ephemeral":
            continue
        if (node.get("config") or {}).get("enabled") is False:
            continue
        sub = d[len(layer):].strip("/")
        if sub:
            area = re.sub(r"^(wh?_)", "", sub.split("/")[0])
        else:
            m = re.match(r"^wh_([a-z0-9]+)__", node["name"])
            area = m.group(1) if m else PurePosixPath(layer).name
        areas.setdefault(area, []).append(node)

    pk_by_model = {}
    for node in models.values():
        for col in (node.get("columns") or {}):
            if col.endswith("_pk"):
                pk_by_model.setdefault(node["name"], col)
    dim_by_pk = {}
    for node in models.values():
        for col in (node.get("columns") or {}):
            if col.endswith("_pk"):
                dim_by_pk.setdefault(col[:-3], node["name"])

    tables: list[str] = []
    out = []
    out.append("# Warehouse guide")
    out.append("")
    out.append(f"<!-- Draft written by Wire's agents_schema_plan.py from {dbt_project_rel}/target/manifest.json.")
    out.append("     Complete every section marked \"wire: complete\" before publishing;")
    out.append("     /wire:agents_schema-validate fails while a marker remains. -->")
    out.append("")
    out.append("Use this skill when a question is about the data in this warehouse: which table answers it, how the tables join, and what the column names mean. Read the governed definitions in the `AGENTS` schema first (`AGENTS.DBT_MODEL`, `AGENTS.DBT_COLUMN`, and the metric tables of any semantic-layer provider listed in `AGENTS.ROOT`), then query the tables named here.")
    out.append("")
    out.append("## How the warehouse is organised")
    out.append("")
    out.append(f"The warehouse layer (`{layer}`) holds one folder per subject area. A fact (`_fact`) holds measures at a stated grain; a dimension (`_dim`) holds the attributes facts join to; a cross-attribute model (`_xa`) bridges two entities. Column names carry their meaning: `_pk` is the primary key, `_fk` a foreign key to a dimension's `_pk`, `_dt` a date, `_ts` a timestamp, `_amount` money, and `is_`, `has_`, `was_` are flags.")
    out.append("")
    out.append("## Subject areas")
    out.append("")
    for area in sorted(areas):
        nodes = sorted(areas[area], key=lambda n: n["name"])
        folders = sorted({model_dir(n) for n in nodes if model_dir(n)})
        out.append(f"### {area} (`{'`, `'.join(folders)}`)")
        out.append("")
        out.append("| Model | Role | Table | Description | Keys | Dates |")
        out.append("|---|---|---|---|---|---|")
        for n in nodes:
            role = next((r for suf, r in ROLE_SUFFIXES if n["name"].endswith(suf)), "other")
            rel = relation(n)
            if rel:
                tables.append(rel)
            cols = list((n.get("columns") or {}).keys())
            keys = []
            pk = pk_by_model.get(n["name"])
            if pk:
                keys.append(f"pk `{pk}`")
            for c in cols:
                if c.endswith("_fk"):
                    target = dim_by_pk.get(c[:-3])
                    keys.append(f"fk `{c}`" + (f" → `{target}`" if target else ""))
            dates = [f"`{c}`" for c in cols if c.endswith("_dt") or c.endswith("_ts") or c.endswith("_date")]
            desc = (n.get("description") or "").strip().replace("|", "\\|").replace("\n", " ") or "(no description in schema.yml)"
            out.append(f"| `{n['name']}` | {role} | `{rel or 'not in manifest'}` | {desc} | {'; '.join(keys) or ''} | {', '.join(dates)} |")
        out.append("")
    out.append("## Business definitions")
    out.append("")
    out.append("<!-- wire: complete. One entry per agreed metric from business_rules/register.md, or from the requirements where no register exists: the name, the definition in plain words, the column and filter that implement it, and who approved it. -->")
    out.append("")
    out.append("## Known caveats")
    out.append("")
    out.append("<!-- wire: complete. Feeds that have stopped, partial history, columns not to use and why. Delete this section if there are none. -->")
    out.append("")
    return "\n".join(out), sorted(set(tables))


# ---------------------------------------------------------------------------
# outputs
# ---------------------------------------------------------------------------

def workflow_yaml(plan: dict, branch: str) -> str:
    tag = plan["agents_schema_version"]
    lines = [
        "# Written by Wire (/wire:agents_schema-generate). Publishes this repository's",
        "# metadata into the warehouse AGENTS schema on every push to the default branch.",
        f"# Reusable workflows: https://github.com/{AGENTS_SCHEMA_REPO}, pinned at {tag}.",
        "# Secrets: WAREHOUSE_CREDENTIALS (the destination credentials YAML from the",
        "# agents_schema setup guide); DBT_PROFILES_YML only when the dbt job below",
        "# runs a managed parse. Never write either into this file.",
        "name: Agents Schema",
        "",
        "on:",
        "  workflow_dispatch:",
        "  push:",
        f"    branches: [{branch}]",
        "",
        "permissions:",
        "  contents: read",
        "",
        "jobs:",
    ]
    previous = None
    for p in plan["providers"]:
        if p.get("source_repo"):
            continue  # published by that repository's own workflow (see lookml_repo_workflow_yaml)
        src = p["source_type"]
        job = p["job"]
        lines.append(f"  {job}:")
        if previous:
            lines.append(f"    needs: [{previous}]")
        lines.append(f"    uses: {AGENTS_SCHEMA_REPO}/.github/workflows/agents-schema-{src}.yml@{tag}")
        lines.append("    with:")
        lines.append(f"      {WORKFLOW_INPUT[src]}: {yaml_str(p['source_dir'])}")
        if src == "dbt":
            if p.get("dbt_profile"):
                lines.append(f"      dbt-profile-name: {yaml_str(p['dbt_profile'])}")
            if p.get("dbt_target"):
                lines.append(f"      dbt-target: {yaml_str(p['dbt_target'])}")
            if p.get("dbt_parse_command"):
                lines.append("      # pinned --from dbt-core: the action's default parse resolves `dbt` to an unrelated PyPI package")
                lines.append(f"      dbt-parse-command: {yaml_str(p['dbt_parse_command'])}")
        if src == "skills":
            lines.append(f"      provider: {yaml_str(p['skill_provider'])}")
        lines.append("    secrets:")
        lines.append("      WAREHOUSE_CREDENTIALS: ${{ secrets.WAREHOUSE_CREDENTIALS }}")
        if src == "dbt" and p.get("dbt_profile"):
            lines.append("      DBT_PROFILES_YML: ${{ secrets.DBT_PROFILES_YML }}")
        previous = job
    lines.append("")
    return "\n".join(lines)


def lookml_repo_workflow_yaml(plan: dict, p: dict) -> str:
    tag = plan["agents_schema_version"]
    lines = [
        f"# Written by Wire (/wire:agents_schema-generate) for the LookML repository {p['source_repo']}.",
        f"# Commit this file there as {p['workflow_destination']}. It publishes that repository's",
        f"# LookML into the warehouse AGENTS schema (AGENTS.LOOKML_*) on every push to {p['publish_branch']},",
        "# alongside the dbt repository's own publication; each provider replaces only its own tables.",
        f"# Reusable workflow: https://github.com/{AGENTS_SCHEMA_REPO}, pinned at {tag}.",
        "# Secret: WAREHOUSE_CREDENTIALS, the same destination credentials YAML as the dbt repository's.",
        "name: Agents Schema (LookML)",
        "",
        "on:",
        "  workflow_dispatch:",
        "  push:",
        f"    branches: [{p['publish_branch']}]",
        "",
        "permissions:",
        "  contents: read",
        "",
        "jobs:",
        "  agents-schema-looker:",
        f"    uses: {AGENTS_SCHEMA_REPO}/.github/workflows/agents-schema-looker.yml@{tag}",
        "    with:",
        f"      lookml-dir: {yaml_str(p['source_dir'])}",
        "    secrets:",
        "      WAREHOUSE_CREDENTIALS: ${{ secrets.WAREHOUSE_CREDENTIALS }}",
        "",
    ]
    return "\n".join(lines)


def run_sh(plan: dict) -> str:
    req = plan["pypi_requirement"]
    lines = [
        "#!/usr/bin/env bash",
        "# Written by Wire (/wire:agents_schema-generate). The same publication the",
        "# GitHub workflow runs, from this machine. Needs uv (for uvx) and the",
        "# destination credentials YAML in WAREHOUSE_CREDENTIALS. Never commit that value.",
        "set -euo pipefail",
        'REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel)}"',
        'cd "$REPO_ROOT"',
        ': "${WAREHOUSE_CREDENTIALS:?set WAREHOUSE_CREDENTIALS to the destination credentials YAML (see the agents_schema setup guide)}"',
        f'AGENTS_SCHEMA="uvx --from {req} agents-schema"',
        "",
    ]
    for p in plan["providers"]:
        lines.append(f"# {p['source_type']}: {', '.join('AGENTS.' + t for t in p['tables'])}")
        if p.get("cli_args"):
            if p.get("source_repo"):
                lines.append(f"# from the local clone of {p['source_repo']}; CI publishes it from that repository's own workflow")
            lines.append("$AGENTS_SCHEMA " + p["cli_args"])
        else:
            lines.append(f"# published from {p['source_repo']} by its own workflow ({p['workflow_destination']}); no local clone was given")
    lines.append("")
    return "\n".join(lines)


def checks_sql(plan: dict) -> str:
    dest = plan["destination"]
    kind = dest["type"]
    if kind == "bigquery":
        proj = dest.get("project_id") or "<project_id>"
        def t(name: str) -> str:
            return f"`{proj}.agents.{name.lower()}`"
    elif kind == "snowflake":
        def t(name: str) -> str:
            return f"AGENTS.{name}"
    else:
        def t(name: str) -> str:
            return f"agents.{name.lower()}"

    providers = [p for p in plan["providers"]]
    root_providers = sorted({p["root_provider"] for p in providers})
    skills = plan["skills"]
    skill_provider = next((p["skill_provider"] for p in providers if p["source_type"] == "skills"), None)
    uses_total = sum(len(s["uses"]) for s in skills)

    out = [
        "-- Written by Wire (/wire:agents_schema-generate). The queries",
        "-- /wire:agents_schema-validate runs against the warehouse after a publish,",
        f"-- with the values plan.json expects. Destination: {kind}. Read-only.",
        "",
        f"-- Check 5: one overview row per planned provider. Expect {len(root_providers)} row(s): {', '.join(root_providers)}.",
        f"SELECT provider, key FROM {t('ROOT')} WHERE key = 'overview' ORDER BY provider;",
        "",
    ]
    count_rows = []
    for p in providers:
        for table in p["tables"]:
            expect = p["expected_rows"].get(table)
            label = f"= {expect}" if isinstance(expect, int) else "> 0"
            count_rows.append((table, label))
    if count_rows:
        out.append("-- Check 6: row counts per delivered table. Expect: " + "; ".join(f"{tb} {lb}" for tb, lb in count_rows) + ".")
        parts = []
        for tb, _ in count_rows:
            parts.append(f"SELECT '{tb}' AS table_name, COUNT(*) AS n FROM {t(tb)}")
        out.append("\nUNION ALL\n".join(parts) + ";")
        out.append("")
    dbt = next((p for p in providers if p["source_type"] == "dbt"), None)
    if dbt:
        out.append(f"-- Check 8: no stale models. Expect exactly the {dbt['counts']['models']} unique_id values listed in plan.json (providers[].model_ids).")
        out.append(f"SELECT unique_id FROM {t('DBT_MODEL')} ORDER BY unique_id;")
        out.append("")
    out.append(f"-- Check 7: skill rows. Expect ({'skills'}, {BUILTIN_SKILL_KEY})" + (f" plus {len(skills)} row(s) under provider '{skill_provider}'." if skill_provider else "; no Wire-published skills planned."))
    out.append(f"SELECT provider, key FROM {t('ROOT')} WHERE key LIKE 'skill/%' ORDER BY provider, key;")
    out.append("")
    if skill_provider:
        out.append(f"-- Check 7: skill use declarations. Expect {uses_total} row(s) under provider '{skill_provider}'.")
        out.append(f"SELECT provider, skill_key, use_kind, object_ref FROM {t('SKILL_USE')} WHERE provider = '{skill_provider}' ORDER BY skill_key, use_kind, object_ref;")
        out.append("")
    out.append("-- Check 9: providers present in ROOT beyond the plan are listed, not failed on.")
    out.append(f"SELECT DISTINCT provider FROM {t('ROOT')} ORDER BY provider;")
    out.append("")
    return "\n".join(out)


def agents_yml(dest: dict) -> str:
    lines = [
        "# Written by Wire (/wire:agents_schema-generate). Read by the agents-schema",
        "# consumer skills (connect-warehouse, agents-schema-analyst) to find the",
        "# warehouse. Connection settings only; credentials never go here.",
    ]
    kind = dest["type"]
    if kind == "bigquery":
        lines.append(f"project_id: {yaml_str(dest.get('project_id') or '<project_id>')}")
        if dest.get("location"):
            lines.append(f"location: {yaml_str(dest['location'])}")
    elif kind == "snowflake":
        lines.append(f"snow_cli_connection: {yaml_str(dest.get('snow_connection') or '<snow connection name>')}")
    elif kind == "databricks":
        lines.append(f"host: {yaml_str(dest.get('databricks_host') or '<workspace host>')}")
        lines.append(f"http_path: {yaml_str(dest.get('databricks_http_path') or '<sql warehouse http path>')}")
        lines.append(f"catalog: {yaml_str(dest.get('databricks_catalog') or '<catalog>')}")
        lines.append("# token: set in the environment or the agent's connection, never in this file")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", required=True, help="the client repository root; every relative path is resolved against it")
    ap.add_argument("--out", required=True, help="where plan.json, run.sh and checks.sql are written (the release's dev/agents_schema folder)")
    ap.add_argument("--destination", required=True, choices=["bigquery", "snowflake", "databricks"])
    ap.add_argument("--project-id", help="BigQuery destination project")
    ap.add_argument("--location", help="BigQuery dataset location")
    ap.add_argument("--snow-connection", help="Snowflake CLI connection name for agents.yml")
    ap.add_argument("--databricks-host")
    ap.add_argument("--databricks-http-path")
    ap.add_argument("--databricks-catalog")
    ap.add_argument("--dbt-project-dir", help="the dbt project (directory holding dbt_project.yml)")
    ap.add_argument("--manifest", help="manifest.json to read; default <dbt-project-dir>/target/manifest.json")
    ap.add_argument("--dbt-profile", help="profile for the workflow's managed dbt parse (needs the DBT_PROFILES_YML secret)")
    ap.add_argument("--dbt-target")
    ap.add_argument("--layer-path", default="models/warehouse", help="warehouse layer folder inside the dbt project, for the guide")
    ap.add_argument("--lookml-dir", help="LookML inside this repository")
    ap.add_argument("--lookml-repo", help="owner/repo[@ref] of a separate LookML repository; writes a workflow for that repository instead of a job here")
    ap.add_argument("--lookml-repo-dir", default=".", help="directory holding the *.lkml files inside --lookml-repo (default: its root)")
    ap.add_argument("--lookml-repo-local", help="a local clone of --lookml-repo, used to count the files and for run.sh")
    ap.add_argument("--lookml-repo-branch", help="the branch of --lookml-repo whose pushes publish (default: the @ref, else main)")
    ap.add_argument("--omni-dir")
    ap.add_argument("--osi-dir")
    ap.add_argument("--sigma-dir")
    ap.add_argument("--skills-source", action="append", default=[], help="a markdown file or a directory of them to publish as skills; repeatable")
    ap.add_argument("--no-guide", action="store_true", help="do not draft warehouse_guide.md")
    ap.add_argument("--provider", default="user", help="publisher for the skill rows in AGENTS.ROOT (lowercase, [a-z0-9_])")
    ap.add_argument("--skills-out", default="agents_schema/skills", help="where the assembled skills are written, relative to the repo root")
    ap.add_argument("--workflow-path", default=".github/workflows/agents-schema.yml")
    ap.add_argument("--agents-yml-path", default="agents.yml")
    ap.add_argument("--branch", default="main", help="the branch whose pushes publish")
    ap.add_argument("--agents-schema-version", default=DEFAULT_AGENTS_SCHEMA_VERSION, help="release tag of dbt-labs/agents_schema to pin")
    ap.add_argument("--force", action="store_true", help="overwrite the workflow, agents.yml and the guide draft if they exist")
    ap.add_argument("--force-workflow", action="store_true", help="overwrite only the workflow (a provider was added or removed); the guide and agents.yml are left alone")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    a = parse_args(argv)
    root = Path(a.repo_root).resolve()
    if not root.is_dir():
        print(f"error: --repo-root {a.repo_root} is not a directory", file=sys.stderr)
        return 1
    if not PROVIDER_RE.match(a.provider):
        print(f"error: --provider {a.provider!r} must match [a-z][a-z0-9_]*", file=sys.stderr)
        return 1
    if not re.match(r"^v\d+\.\d+\.\d+$", a.agents_schema_version):
        print(f"error: --agents-schema-version {a.agents_schema_version!r} must look like v0.0.11", file=sys.stderr)
        return 1
    if a.lookml_dir and a.lookml_repo:
        print("error: give --lookml-dir (LookML in this repository) or --lookml-repo (a separate repository), not both", file=sys.stderr)
        return 1
    if a.lookml_repo and not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(@[A-Za-z0-9_./-]+)?$", a.lookml_repo):
        print(f"error: --lookml-repo {a.lookml_repo!r} must look like owner/repo or owner/repo@ref", file=sys.stderr)
        return 1
    out_dir = resolve(root, a.out)
    skills_out = resolve(root, a.skills_out)
    workflow_path = resolve(root, a.workflow_path)
    agents_yml_path = resolve(root, a.agents_yml_path)

    needs_human: list[dict] = []
    skipped: list[dict] = []
    written: list[str] = []
    skipped_existing: list[str] = []
    providers: list[dict] = []

    # -- dbt -----------------------------------------------------------------
    models: dict[str, dict] = {}
    dbt_project = resolve(root, a.dbt_project_dir)
    if dbt_project is not None:
        manifest_path = resolve(root, a.manifest) if a.manifest else dbt_project / "target" / "manifest.json"
        if not (dbt_project / "dbt_project.yml").exists():
            needs_human.append({"item": "dbt", "reason": "no_dbt_project", "detail": f"{rel_to(dbt_project, root)}/dbt_project.yml not found"})
        elif not manifest_path.exists():
            needs_human.append({"item": "dbt", "reason": "no_manifest", "detail": f"{rel_to(manifest_path, root)} not found; run dbt compile (or dbt parse) first"})
        else:
            models = model_nodes(load_manifest(manifest_path))
            counts = dbt_counts(models)
            disabled = sorted(uid for uid, n in models.items() if (n.get("config") or {}).get("enabled") is False)
            no_schema = sorted(n["name"] for n in models.values() if relation(n) is None)
            p = {
                "source_type": "dbt", "root_provider": "dbt", "job": "agents-schema-dbt",
                "source_dir": rel_to(dbt_project, root), "manifest": rel_to(manifest_path, root),
                "dbt_profile": a.dbt_profile, "dbt_target": a.dbt_target,
                "dbt_parse_command": dbt_parse_command(rel_to(dbt_project, root), a.dbt_profile, a.dbt_target, a.destination) if a.dbt_profile else None,
                "counts": counts, "model_ids": sorted(models),
                "disabled_models_included": disabled,
                "tables": list(TABLES["dbt"]),
                "expected_rows": {"DBT_MODEL": counts["models"], "DBT_COLUMN": counts["columns"], "DBT_DEPENDENCY": counts["dependencies"]},
                "cli_args": f"dbt --project-dir {rel_to(dbt_project, root)}",
            }
            providers.append(p)
            if disabled:
                needs_human.append({"item": "dbt", "reason": "disabled_models_in_manifest",
                                    "detail": f"{len(disabled)} disabled model(s) are listed under nodes and will be published as models: {', '.join(disabled)}. Rebuild the manifest with those models removed, or accept them in the review."})
            if no_schema:
                needs_human.append({"item": "dbt", "reason": "models_without_schema",
                                    "detail": f"{len(no_schema)} model(s) carry no schema in the manifest, so no table name can be derived for skills: {', '.join(no_schema)}"})
            if not a.dbt_profile:
                needs_human.append({"item": "dbt", "reason": "no_dbt_profile",
                                    "detail": "the workflow's dbt job needs target/manifest.json committed, or --dbt-profile (with the DBT_PROFILES_YML secret) for a managed parse; neither is set"})

    # -- file-based providers --------------------------------------------------
    for src in ("looker", "omni", "osi", "sigma"):
        given = getattr(a, f"{src.replace('looker', 'lookml')}_dir")
        d = resolve(root, given)
        if d is None:
            continue
        if not d.is_dir():
            needs_human.append({"item": src, "reason": "missing_source", "detail": f"{given} is not a directory"})
            continue
        files = sorted({posix(f.relative_to(d)) for pat in SOURCE_GLOBS[src] for f in d.glob(pat) if f.is_file()})
        if not files:
            needs_human.append({"item": src, "reason": "empty_source", "detail": f"{rel_to(d, root)} holds no {', '.join(SOURCE_GLOBS[src])} files; provider not planned"})
            continue
        if src == "looker":
            lkml_precheck(d, files, rel_to(d, root), needs_human)
        providers.append({
            "source_type": src, "root_provider": ROOT_PROVIDER[src], "job": f"agents-schema-{src}",
            "source_dir": rel_to(d, root), "counts": {"files": len(files)}, "files": files,
            "tables": list(TABLES[src]), "expected_rows": {t: ">0" for t in TABLES[src]},
            "cli_args": f"{src} {CLI_FLAG[src]} {json.dumps(rel_to(d, root)) if ' ' in rel_to(d, root) else rel_to(d, root)}",
        })

    # -- LookML in a separate repository ----------------------------------------
    if a.lookml_repo:
        repo, _, ref = a.lookml_repo.partition("@")
        branch = a.lookml_repo_branch or ref or "main"
        local = resolve(root, a.lookml_repo_local) if a.lookml_repo_local else None
        files = None
        if local is not None:
            ldir = local / a.lookml_repo_dir if a.lookml_repo_dir not in (".", "") else local
            if not ldir.is_dir():
                needs_human.append({"item": "looker", "reason": "missing_source", "detail": f"--lookml-repo-local {a.lookml_repo_local}/{a.lookml_repo_dir} is not a directory"})
            else:
                files = sorted({posix(f.relative_to(ldir)) for pat in SOURCE_GLOBS["looker"] for f in ldir.glob(pat) if f.is_file()})
                if not files:
                    needs_human.append({"item": "looker", "reason": "empty_source", "detail": f"{a.lookml_repo_local}/{a.lookml_repo_dir} holds no *.lkml files; the repository workflow is still written"})
                else:
                    lkml_precheck(ldir, files, f"{repo} ({a.lookml_repo_local})", needs_human)
        else:
            needs_human.append({"item": "looker", "reason": "lookml_repo_not_cloned", "detail": f"no --lookml-repo-local clone of {repo}; the file count is unknown until the LookML repository's workflow runs, and run.sh cannot publish LookML from this machine"})
        p = {
            "source_type": "looker", "root_provider": "lookml", "job": "agents-schema-looker",
            "source_repo": repo, "source_ref": ref or None, "publish_branch": branch,
            "source_dir": a.lookml_repo_dir or ".", "local_clone": rel_to(local, root) if local else None,
            "counts": {"files": len(files) if files is not None else "unknown"}, "files": files,
            "tables": list(TABLES["looker"]), "expected_rows": {t: ">0" for t in TABLES["looker"]},
            "workflow_file": rel_to(out_dir / "lookml_repo" / "agents-schema-lookml.yml", root),
            "workflow_destination": ".github/workflows/agents-schema-lookml.yml",
            "cli_args": (f"looker --lookml-dir {rel_to(ldir, root)}" if files is not None else None),
        }
        providers.append(p)

    # -- skills ----------------------------------------------------------------
    skills: list[dict] = []
    seen_keys: dict[str, str] = {}
    for source, source_root in collect_skill_sources(root, a.skills_source, skipped):
        key = skill_key_for(source, source_root)
        if key in seen_keys:
            needs_human.append({"item": key, "reason": "duplicate_skill_key",
                                "detail": f"{rel_to(source, root)} and {seen_keys[key]} both map to {key}; the second is skipped"})
            skipped.append({"path": rel_to(source, root), "reason": "duplicate_skill_key"})
            continue
        seen_keys[key] = rel_to(source, root)
        text = source.read_text(encoding="utf-8", errors="replace")
        fm, body = split_frontmatter(text)
        if fm is not None and "uses:" in fm:
            uses = uses_from_frontmatter(fm)
            content = text if text.endswith("\n") else text + "\n"
            mode = "kept"
        else:
            tables, reason = derived_uses(source, dbt_project, models)
            if reason:
                needs_human.append({"item": key, "reason": "uses_not_derived", "detail": f"{rel_to(source, root)}: {reason}; the skill is published without a uses: declaration unless one is added"})
            uses = [("table", t) for t in tables]
            content = (uses_frontmatter(tables) if tables else "") + (text if fm is None else text)
            if not content.endswith("\n"):
                content += "\n"
            mode = "derived" if tables else "none"
        target = skills_out / (key[len("skill/"):] + ".md")
        write_text(target, content, written, root)
        skills.append({"key": key, "path": rel_to(target, root), "source": rel_to(source, root),
                       "frontmatter": mode, "uses": [list(u) for u in uses], "kind": "copied"})

    if models and not a.no_guide:
        key = "skill/warehouse_guide"
        target = skills_out / "warehouse_guide.md"
        guide, tables = warehouse_guide(models, a.layer_path, rel_to(dbt_project, root))
        if key in seen_keys:
            needs_human.append({"item": key, "reason": "duplicate_skill_key", "detail": f"a source skill already uses {key}; the draft guide was not written"})
        elif target.exists() and not a.force:
            skipped_existing.append(rel_to(target, root))
            existing = target.read_text(encoding="utf-8", errors="replace")
            fm, _ = split_frontmatter(existing)
            skills.append({"key": key, "path": rel_to(target, root), "source": "warehouse_guide draft (existing, left unchanged)",
                           "frontmatter": "kept", "uses": [list(u) for u in (uses_from_frontmatter(fm) if fm else [])], "kind": "draft"})
        else:
            content = (uses_frontmatter(tables) if tables else "") + guide
            write_text(target, content, written, root)
            skills.append({"key": key, "path": rel_to(target, root), "source": "warehouse_guide draft from the manifest",
                           "frontmatter": "derived" if tables else "none", "uses": [["table", t] for t in tables], "kind": "draft"})
            needs_human.append({"item": key, "reason": "draft_to_complete",
                                "detail": f"{rel_to(target, root)} carries '{DRAFT_MARKER}' markers: business definitions and caveats are the consultant's to write"})

    if skills:
        providers.append({
            "source_type": "skills", "root_provider": "skills", "job": "agents-schema-skills",
            "source_dir": rel_to(skills_out, root), "skill_provider": a.provider,
            "counts": {"skills": len(skills), "uses": sum(len(s["uses"]) for s in skills)},
            "skill_keys": [s["key"] for s in skills],
            "tables": list(TABLES["skills"]), "expected_rows": {"SKILL_USE": sum(len(s["uses"]) for s in skills)},
            "cli_args": f"skills --skills-dir {rel_to(skills_out, root)} --provider {a.provider}",
        })

    providers.sort(key=lambda p: PROVIDER_ORDER.index(p["source_type"]))
    if not providers:
        print("error: nothing to publish — no provider source was found (see needs_human above)", file=sys.stderr)
        for nh in needs_human:
            print(f"  {nh['item']}: {nh['reason']}: {nh['detail']}", file=sys.stderr)
        return 2

    dest = {"type": a.destination, "schema": "AGENTS" if a.destination == "snowflake" else "agents"}
    if a.destination == "bigquery":
        dest["project_id"] = a.project_id
        dest["location"] = a.location
        if not a.project_id:
            needs_human.append({"item": "destination", "reason": "bigquery_project_id_missing", "detail": "agents.yml and checks.sql carry a <project_id> placeholder until --project-id is given"})
    elif a.destination == "snowflake":
        dest["snow_connection"] = a.snow_connection
    else:
        dest["databricks_host"] = a.databricks_host
        dest["databricks_http_path"] = a.databricks_http_path
        dest["databricks_catalog"] = a.databricks_catalog

    plan = {
        "plan_version": SCRIPT_VERSION,
        "agents_schema_version": a.agents_schema_version,
        "pypi_requirement": f"agents-schema=={a.agents_schema_version[1:]}",
        "destination": dest,
        "branch": a.branch,
        "providers": providers,
        "skills": skills,
        "skipped": skipped,
        "needs_human": needs_human,
        "files": {
            "workflow": rel_to(workflow_path, root),
            "agents_yml": rel_to(agents_yml_path, root),
            "skills_dir": rel_to(skills_out, root) if skills else None,
            "run_script": rel_to(out_dir / "run.sh", root),
            "checks": rel_to(out_dir / "checks.sql", root),
        },
        "written": written,
        "skipped_existing": skipped_existing,
    }

    for path, text, force in ((workflow_path, workflow_yaml(plan, a.branch), a.force or a.force_workflow),
                              (agents_yml_path, agents_yml(dest), a.force)):
        if path.exists() and not force:
            skipped_existing.append(rel_to(path, root))
        else:
            write_text(path, text, written, root)
    for p in providers:
        if p.get("source_repo"):
            write_text(out_dir / "lookml_repo" / "agents-schema-lookml.yml", lookml_repo_workflow_yaml(plan, p), written, root)
            plan["files"]["lookml_repo_workflow"] = p["workflow_file"]
    write_text(out_dir / "run.sh", run_sh(plan), written, root)
    (out_dir / "run.sh").chmod(0o755)
    write_text(out_dir / "checks.sql", checks_sql(plan), written, root)
    plan["written"] = sorted(written)
    plan["skipped_existing"] = sorted(skipped_existing)
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"agents_schema_plan {SCRIPT_VERSION}: agents-schema {a.agents_schema_version} -> {a.destination}")
    for p in providers:
        c = ", ".join(f"{k} {v}" for k, v in p["counts"].items())
        where = f"{p['source_repo']}:{p['source_dir']} (own workflow)" if p.get("source_repo") else p["source_dir"]
        print(f"  {p['source_type']:7s} {where}  ({c})  -> {', '.join('AGENTS.' + t for t in p['tables'])}")
    print(f"  skills: {len(skills)}  skipped sources: {len(skipped)}  needs_human: {len(needs_human)}")
    print(f"  written: {len(written)}  skipped existing: {len(skipped_existing)}" + (f" ({', '.join(plan['skipped_existing'])})" if skipped_existing else ""))
    print(f"  plan: {rel_to(out_dir / 'plan.json', root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
