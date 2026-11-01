#!/usr/bin/env python3
"""Deterministic, AI-free linter for Wire's per-domain conventions.

Reads a wire/conventions/<domain>.yml file (see
wire/schemas/convention-schema.md) and checks target files against whichever
rules in it are mechanically checkable — filename patterns, forbidden/
required text patterns, style thresholds, and a handful of domain-specific
structural checks (dbt cast-macro suffixes, LookML refinement placement,
Cube required fields). Rules without a recognised check hook are
documentation for the agent, not enforced here.

This exists so the naming/style half of a review doesn't cost an AI call or
depend on an agent's semantic read of a 1000-line prose spec — it runs the
same way every time, for free. Judgment calls (grain choice, join direction,
whether a pre-aggregation is warranted) are explicitly out of scope; see the
matching skill file for those.

Usage:
  python3 wire/scripts/lint_conventions.py --domain dbt \\
      --convention wire/conventions/dbt.yml --path models/ [--format json] \\
      [--changed-from <base ref> | --new-project]
  python3 wire/scripts/lint_conventions.py --domain dbtcharts \\
      --convention wire/conventions/dbtcharts.yml --path charts/
  python3 wire/scripts/lint_conventions.py --domain airflow \\
      --convention .wire/conventions/airflow.yml --path dags/ \\
      [--changed-from <base ref>]

A client file with `extends: wire` (wire#380) is merged over Wire's own file
for the domain (wire/conventions/<domain>.yml beside this script's folder, or
--base-convention): its rules are added, a rule with the same id replaces
Wire's, and each `disable: [{id, reason}]` entry removes a Wire rule. The
removed rules and their reasons are listed in the output. A client file
without `extends` replaces Wire's file, as before.

Scope (wire#277): a rule carrying `applies_to: new_and_changed` is checked
only on files added or changed on the current branch, and one carrying
`applies_to: new_files` only on files added on it. --changed-from <ref> works
the changed set out from git (merge base of <ref> and HEAD, plus uncommitted
and untracked files). --new-project treats every file as new. With neither,
or where git cannot answer, those rules still run but report as warnings, so
an existing project never fails on a rule it predates.

Exit code: 1 if any error-severity finding fires, 0 otherwise. Warnings never
fail the run.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

DOMAIN_EXTENSIONS = {
    "dbt": (".sql", ".yml", ".yaml", ".csv"),
    "lookml": (".lkml",),
    "cube": (".yml", ".yaml"),
    "dbtcharts": (".yml", ".yaml"),
    "airflow": (".py", ".yml", ".yaml", ".sql"),
    "data_apps": (".js",),
}


class Finding:
    def __init__(self, rule_id, severity, file, message, line=None):
        self.rule_id = rule_id
        self.severity = severity
        self.file = file
        self.message = message
        self.line = line

    def to_dict(self):
        d = {"rule": self.rule_id, "severity": self.severity, "file": self.file, "message": self.message}
        if self.line is not None:
            d["line"] = self.line
        return d


def load_convention(path):
    with open(path) as fh:
        doc = yaml.safe_load(fh)
    for required in ("schema_version", "domain", "description"):
        if required not in doc:
            raise ValueError(f"{path}: convention file missing required field '{required}'")
    return doc


# ----------------------------------------------------------------------
# extends: wire (wire#380)
# ----------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Keys that describe the file, not rules; the client's own values are kept.
META_KEYS = {"schema_version", "domain", "description", "extends", "disable"}


def wire_convention_path(domain):
    """Wire's own file for a domain: conventions/ beside scripts/, which holds
    in this repo (wire/scripts, wire/conventions) and in the installed plugin."""
    return os.path.join(os.path.dirname(SCRIPT_DIR), "conventions", f"{domain}.yml")


def _is_rule_list(value):
    return isinstance(value, list) and all(isinstance(r, dict) and r.get("id") for r in value)


def merge_extending(base, client):
    """A client file with `extends: wire` merged over Wire's file.

    Rule sections (lists of rules with an id): a client rule with an id Wire
    already has replaces Wire's rule in place; any other client rule is added
    at the end. Settings sections (mappings) merge key by key, the client's
    value winning. Any other value: the client's wins. Then each `disable`
    entry removes the Wire rule with that id from every section.

    Returns (merged, info): info lists the rules disabled, with their reasons,
    and the ids the client added or replaced, for the lint output."""
    merged = {k: v for k, v in base.items() if k not in ("extends", "disable")}
    added, replaced = [], []
    for key, value in client.items():
        if key in ("extends", "disable"):
            continue
        if key in ("schema_version", "domain"):
            continue
        current = merged.get(key)
        if _is_rule_list(value) and isinstance(current, list):
            rules = list(current)
            index = {r.get("id"): i for i, r in enumerate(rules) if isinstance(r, dict)}
            for rule in value:
                if rule["id"] in index:
                    rules[index[rule["id"]]] = rule
                    replaced.append(rule["id"])
                else:
                    rules.append(rule)
                    added.append(rule["id"])
            merged[key] = rules
        elif isinstance(value, dict) and isinstance(current, dict):
            merged[key] = {**current, **value}
        else:
            merged[key] = value
            if _is_rule_list(value):
                added.extend(r["id"] for r in value)

    disabled, unknown = [], []
    all_ids = {r.get("id") for v in merged.values() if isinstance(v, list) for r in v if isinstance(r, dict)}
    for entry in client.get("disable") or []:
        if not isinstance(entry, dict) or not entry.get("id"):
            raise ValueError("each disable entry needs an id and a reason")
        if not str(entry.get("reason") or "").strip():
            raise ValueError(f"disable entry for '{entry['id']}' has no reason")
        if entry["id"] not in all_ids:
            unknown.append(entry["id"])
            continue
        for key, value in list(merged.items()):
            if isinstance(value, list):
                merged[key] = [r for r in value if not (isinstance(r, dict) and r.get("id") == entry["id"])]
        disabled.append({"id": entry["id"], "reason": str(entry["reason"]).strip()})

    info = {"extends": "wire", "added": added, "replaced": replaced,
            "disabled": disabled, "unknown_disabled": unknown}
    return merged, info


def resolve_convention(path, domain, base_path=None):
    """The convention a lint runs with. A file without `extends` is used as it
    is (a client file replaces Wire's, as before). A file with `extends: wire`
    is merged over Wire's own file for the domain."""
    doc = load_convention(path)
    extends = doc.get("extends")
    if not extends:
        return doc, None
    if extends != "wire":
        raise ValueError(f"{path}: extends must be 'wire', got '{extends}'")
    base_path = base_path or wire_convention_path(domain)
    if os.path.realpath(base_path) == os.path.realpath(path):
        raise ValueError(f"{path}: a file cannot extend itself")
    base = load_convention(base_path)
    if base.get("domain") != doc.get("domain"):
        raise ValueError(f"{path}: domain '{doc.get('domain')}' does not match Wire's '{base.get('domain')}'")
    merged, info = merge_extending(base, doc)
    info["base"] = base_path
    return merged, info


def get_rule(conv, section, rule_id):
    for rule in conv.get(section, []) or []:
        if isinstance(rule, dict) and rule.get("id") == rule_id:
            return rule
    return None


# Build output and installed packages, never the project's own code.
SKIPPED_DIRS = {"target", "dbt_packages", "dbt_modules", "node_modules", "logs", "__pycache__"}


def iter_target_files(path, extensions):
    if os.path.isfile(path):
        yield path
        return
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIPPED_DIRS]
        for fname in sorted(files):
            if fname.endswith(extensions):
                yield os.path.join(root, fname)


def _severity(rule, default="warning"):
    return rule.get("severity", default)


def _as_list(value):
    if value is None:
        return None
    return value if isinstance(value, list) else [value]


def _rule_patterns(rule):
    """Every pattern a rule accepts. A rule carries either one `pattern`, or
    `accepted_patterns` (a list of {form, pattern}) where the reference
    changed a convention without improving it: Wire generates the `new` form
    and still accepts the `old` one (wire#277)."""
    if rule.get("accepted_patterns"):
        return [p["pattern"] for p in rule["accepted_patterns"] if isinstance(p, dict) and p.get("pattern")]
    if rule.get("pattern"):
        return [rule["pattern"]]
    return []


def rule_accepts(rule, value):
    return any(re.search(p, value) for p in _rule_patterns(rule))


def _in_scope(rule, layer, kind):
    """`layer` restricts a rule to files inferred to be in that layer, and
    `kind` (dbt only) to a kind of file within it (base, staging, snapshot,
    macro, ...). A rule with neither applies everywhere."""
    layers = _as_list(rule.get("layer"))
    if layers is not None and layer not in layers:
        return False
    kinds = _as_list(rule.get("kind"))
    if kinds is not None and kind not in kinds:
        return False
    return True


# ----------------------------------------------------------------------
# Generic checks — driven entirely by the YAML, no domain-specific code
# ----------------------------------------------------------------------

def check_file_naming(conv, filepath, layer=None, kind=None):
    """Matches file_naming rules against the file's inferred layer (a plain
    path-segment check, done once by the caller — see infer_dbt_layer /
    infer_lookml_layer) rather than the rule's `path_glob`. `path_glob` is
    kept in the YAML as human-readable documentation of where a rule
    applies, but isn't matched literally: fnmatch has no brace-expansion
    (`{staging,aggregate}`) and treats `**` the same as a single `*`, so a
    file sitting directly under staging/ with no entity-group subfolder (or
    any .lkml file at all, since every lookml glob uses brace syntax) would
    silently skip its check under a literal glob match."""
    findings = []
    basename = os.path.basename(filepath)
    for rule in conv.get("file_naming", []) or []:
        if not _rule_patterns(rule):
            continue
        if not _in_scope(rule, layer, kind):
            continue
        if basename in (rule.get("exempt_filenames") or []):
            continue
        if not rule_accepts(rule, basename):
            findings.append(Finding(
                rule["id"], _severity(rule, "error"), filepath,
                f"{rule.get('description', rule['id'])} — got '{basename}'",
            ))
    return findings


def check_file_content_rules(conv, filepath, text, layer=None, kind=None):
    """Runs every rule (in any section) with scope: file_content. A rule may
    carry forbidden_pattern (flag every matching line) and/or required_pattern
    (flag if absent from the whole file). An optional `layer` field (string
    or list) restricts the rule to files inferred to be in that layer, and an
    optional `kind` field to a kind of file (dbt)."""
    findings = []
    lines = text.splitlines()
    for section_name, rules in conv.items():
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict) or rule.get("scope") != "file_content":
                continue
            if not _in_scope(rule, layer, kind):
                continue
            severity = _severity(rule)
            rid = rule["id"]
            desc = rule.get("description", rid)
            if "forbidden_pattern" in rule:
                pat = re.compile(rule["forbidden_pattern"], re.IGNORECASE)
                for i, line in enumerate(lines, start=1):
                    if pat.search(line):
                        findings.append(Finding(rid, severity, filepath, desc, line=i))
            if "required_pattern" in rule:
                pat = re.compile(rule["required_pattern"], re.IGNORECASE | re.MULTILINE)
                if not pat.search(text):
                    findings.append(Finding(rid, severity, filepath, f"{desc} — not found in file"))
            # A conditional check: only applies where a marker is present, so it
            # never fires on a project that has not opted into the convention.
            # Used by the wire_business_rule citation rules (wire#229): a model is
            # not required to cite a business rule, but one that does must cite it
            # in the form the register can be matched against.
            if "marker_pattern" in rule and "required_pattern_if_present" in rule:
                marker = re.compile(rule["marker_pattern"], re.IGNORECASE)
                if marker.search(text):
                    pat = re.compile(rule["required_pattern_if_present"],
                                     re.IGNORECASE | re.MULTILINE)
                    if not pat.search(text):
                        findings.append(Finding(
                            rid, severity, filepath,
                            f"{desc} — marker present but the required form is not"))
    return findings


def check_style_thresholds(conv, filepath, text, file_type=None):
    """Handles style rules keyed by a threshold value (max_line_length via
    `value`, tab-forbidding via `forbid_tabs`) rather than a regex pattern.

    `file_type` is passed by domains that lint more than one kind of text
    file (dbt: "sql" or "yml"). A rule then applies only to the types in its
    `file_types` list, defaulting to sql so a rule written before YAML was
    linted keeps its meaning. A rule with `file_types` and `indent_spaces`
    also checks every indented line is a multiple of that width."""
    findings = []
    lines = text.splitlines()
    for rule in conv.get("style", []) or []:
        rid = rule.get("id", "")
        if file_type is not None and file_type not in (_as_list(rule.get("file_types")) or ["sql"]):
            continue
        severity = _severity(rule)
        desc = rule.get("description", rid)
        if "value" in rule and "length" in rid:
            limit = rule["value"]
            for i, line in enumerate(lines, start=1):
                if len(line) > limit:
                    findings.append(Finding(rid, severity, filepath, f"{desc} — line is {len(line)} chars", line=i))
        if rule.get("forbid_tabs"):
            for i, line in enumerate(lines, start=1):
                if "\t" in line:
                    findings.append(Finding(rid, severity, filepath, f"{desc} — tab character found", line=i))
        if rule.get("indent_spaces") and rule.get("file_types"):
            width = int(rule["indent_spaces"])
            for i, line in enumerate(lines, start=1):
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip(" "))
                if indent % width:
                    findings.append(Finding(rid, severity, filepath,
                                            f"{desc} — indented {indent} spaces", line=i))
    return findings


def extract_brace_block(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx:i + 1]
    return text[open_idx:]


# ----------------------------------------------------------------------
# dbt
# ----------------------------------------------------------------------

def infer_dbt_layer(filepath):
    parts = filepath.replace(os.sep, "/").split("/")
    for layer in ("staging", "integration", "warehouse"):
        if layer in parts:
            return layer
    return None


def infer_dbt_kind(filepath, text=None):
    """The kind of dbt file, from its path and name: base, staging,
    intermediate, integration, warehouse, other_model (a model outside the
    three layers), snapshot, macro, seed, sources_yml (a YAML file declaring
    sources), or None. File-naming and content rules select on this."""
    parts = filepath.replace(os.sep, "/").split("/")
    base = os.path.basename(filepath)
    if base.endswith(".csv"):
        return "seed" if "seeds" in parts else None
    if base.endswith((".yml", ".yaml")):
        if text is not None:
            try:
                doc = yaml.safe_load(text)
            except Exception:
                doc = None
            if isinstance(doc, dict) and doc.get("sources"):
                return "sources_yml"
        return None
    if "macros" in parts:
        return "macro"
    if "snapshots" in parts:
        return "snapshot"
    layer = infer_dbt_layer(filepath)
    if layer == "staging":
        return "base" if base.startswith("base_") else "staging"
    if layer == "integration":
        return "intermediate" if "intermediate" in parts else "integration"
    if layer == "warehouse":
        return "warehouse"
    if "models" in parts:
        return "other_model"
    return None


ALIAS_RE = re.compile(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)\s*,?\s*$", re.IGNORECASE)
# The cast-to-alias checks. Generated models cast with a Jinja macro inside the
# cast — `cast(active as {{ dbt.type_boolean() }}) as user_is_active` — so the
# closing `}}` sits between the macro call and the `)`. Before 4.1.2 these
# patterns had no room for it and never fired (wire#277).
CAST_MACRO_ALIAS_RES = {
    "boolean_prefix": re.compile(r"type_boolean\(\)\s*(?:\}\})?\s*\)\s*as\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "timestamp_suffix": re.compile(r"type_timestamp\(\)\s*(?:\}\})?\s*\)\s*as\s+([A-Za-z_][A-Za-z0-9_]*)"),
    "date_suffix": re.compile(r"type_date\(\)\s*(?:\}\})?\s*\)\s*as\s+([A-Za-z_][A-Za-z0-9_]*)"),
}
RESERVED_ALIAS_WORDS = {"select", "from", "final", "where", "group", "order"}
MODEL_KINDS = ("base", "staging", "intermediate", "integration", "warehouse", "other_model")


def check_dbt_sql(conv, filepath, text):
    findings = []
    lines = text.splitlines()

    snake_rule = get_rule(conv, "naming", "snake_case")
    if snake_rule:
        pat = re.compile(snake_rule["pattern"])
        for i, line in enumerate(lines, start=1):
            m = ALIAS_RE.search(line.strip())
            if not m:
                continue
            alias = m.group(1)
            if alias.lower() in RESERVED_ALIAS_WORDS:
                continue
            if not pat.match(alias):
                findings.append(Finding(
                    snake_rule["id"], _severity(snake_rule), filepath,
                    f"{snake_rule.get('description')} — '{alias}'", line=i,
                ))

    for rule_id, cast_re in CAST_MACRO_ALIAS_RES.items():
        rule = get_rule(conv, "naming", rule_id)
        if not rule or not _rule_patterns(rule):
            continue
        for i, line in enumerate(lines, start=1):
            m = cast_re.search(line)
            if m and not rule_accepts(rule, m.group(1)):
                findings.append(Finding(
                    rule["id"], _severity(rule), filepath,
                    f"{rule.get('description')} — '{m.group(1)}'", line=i,
                ))

    surrogate_rule = get_rule(conv, "naming", "surrogate_key_suffix")
    if surrogate_rule:
        pat = re.compile(surrogate_rule["pattern"])
        for i, line in enumerate(lines):
            if "generate_surrogate_key(" not in line:
                continue
            for j in range(i, min(i + 3, len(lines))):
                m = re.search(r"\bas\s+([A-Za-z_][A-Za-z0-9_]*)", lines[j])
                if m:
                    alias = m.group(1)
                    if not pat.search(alias):
                        findings.append(Finding(
                            surrogate_rule["id"], _severity(surrogate_rule, "error"), filepath,
                            f"{surrogate_rule.get('description')} — got '{alias}'", line=j + 1,
                        ))
                    break

    return findings


def _layer_check(conv, rule_id, default_severity):
    """A layer_checks rule, or a stand-in when an older convention file has
    layer_rules but no layer_checks section (the source() check predates it)."""
    rule = get_rule(conv, "layer_checks", rule_id)
    if rule:
        return rule
    if conv.get("layer_checks") is None and rule_id == "no_source_outside_staging":
        return {"id": rule_id, "severity": default_severity}
    return None


def check_dbt_layer_rules(conv, filepath, text, kind=None):
    findings = []
    kind = kind or infer_dbt_kind(filepath)
    rules = conv.get("layer_rules") or {}
    # Older convention files key layer_rules by layer only; a base model then
    # takes the staging entry and an intermediate model the integration entry.
    layer_rule = rules.get(kind) or rules.get(infer_dbt_layer(filepath) or "")
    if not layer_rule:
        return findings
    may = layer_rule.get("may_select_from", [])

    source_rule = _layer_check(conv, "no_source_outside_staging", "error")
    if source_rule and "source" not in may and re.search(r"\{\{\s*source\(", text):
        findings.append(Finding(
            source_rule["id"], _severity(source_rule, "error"), filepath,
            f"{kind} models must not select from source() — only staging and base models do",
        ))

    base_rule = _layer_check(conv, "no_base_ref_outside_staging", "error")
    if base_rule and kind not in ("base", "staging"):
        for i, line in enumerate(text.splitlines(), start=1):
            if re.search(r"\bref\(\s*['\"]base_", line):
                findings.append(Finding(
                    base_rule["id"], _severity(base_rule, "error"), filepath,
                    f"{kind} models select from staging models, not base models", line=i,
                ))

    mat_rule = _layer_check(conv, "materialization_allowed", "warning")
    allowed = layer_rule.get("materialization")
    if mat_rule and allowed:
        m = re.search(r"materialized\s*=\s*['\"]([A-Za-z_]+)['\"]", text)
        if m and m.group(1) not in allowed:
            findings.append(Finding(
                mat_rule["id"], _severity(mat_rule), filepath,
                f"{kind} model materialized as '{m.group(1)}'; allowed: {allowed}",
            ))
    return findings


def _test_names(tests):
    names = set()
    for t in tests or []:
        if isinstance(t, str):
            names.add(t)
        elif isinstance(t, dict):
            names.update(t.keys())
    return names


def check_dbt_schema_yml(conv, filepath, text):
    findings = []
    try:
        doc = yaml.safe_load(text)
    except Exception:
        return findings
    if not isinstance(doc, dict):
        return findings

    pk_rule = get_rule(conv, "testing", "primary_key_tests_required")
    key_rule = get_rule(conv, "testing", "test_key_forms")
    doc_rule = get_rule(conv, "documentation", "warehouse_columns_documented")
    all_doc_rule = get_rule(conv, "documentation", "all_columns_documented")
    is_warehouse = "warehouse" in filepath.replace(os.sep, "/").split("/")

    def both_keys(node, what):
        if key_rule and isinstance(node, dict) and "tests" in node and "data_tests" in node:
            findings.append(Finding(
                key_rule["id"], _severity(key_rule, "error"), filepath,
                f"{what} carries both tests: and data_tests:; dbt allows one",
            ))

    for model in doc.get("models") or []:
        if not isinstance(model, dict):
            continue
        both_keys(model, f"model '{model.get('name')}'")
        for col in model.get("columns") or []:
            if not isinstance(col, dict):
                continue
            name = col.get("name", "")
            both_keys(col, f"column '{name}' in model '{model.get('name')}'")
            if pk_rule and name.endswith("_pk"):
                test_names = _test_names(col.get("data_tests") or col.get("tests"))
                missing = [t for t in pk_rule.get("required_tests", []) if t not in test_names]
                if missing:
                    findings.append(Finding(
                        pk_rule["id"], _severity(pk_rule, "error"), filepath,
                        f"primary key column '{name}' in model '{model.get('name')}' missing test(s): {missing}",
                    ))
            undocumented = not str(col.get("description") or "").strip()
            if doc_rule and is_warehouse and undocumented:
                findings.append(Finding(
                    doc_rule["id"], _severity(doc_rule), filepath,
                    f"column '{name}' in warehouse model '{model.get('name')}' has no description",
                ))
            elif all_doc_rule and undocumented:
                findings.append(Finding(
                    all_doc_rule["id"], _severity(all_doc_rule), filepath,
                    f"column '{name}' in model '{model.get('name')}' has no description",
                ))

    findings += check_dbt_sources_yml(conv, filepath, doc)
    return findings


def check_dbt_sources_yml(conv, filepath, doc):
    """Source declaration content rules from the reference (wire#277): a
    loader, a Grain: line opening each table's description, declared columns
    with descriptions, and freshness as the only test."""
    findings = []
    loader_rule = get_rule(conv, "documentation", "source_loader_declared")
    grain_rule = get_rule(conv, "documentation", "source_table_grain_line")
    cols_rule = get_rule(conv, "documentation", "source_columns_declared")
    fresh_rule = get_rule(conv, "testing", "sources_freshness_only")

    def has_tests(node):
        return isinstance(node, dict) and bool(node.get("tests") or node.get("data_tests"))

    for source in doc.get("sources") or []:
        if not isinstance(source, dict):
            continue
        sname = source.get("name", "<unnamed>")
        if loader_rule and not str(source.get("loader") or "").strip():
            findings.append(Finding(loader_rule["id"], _severity(loader_rule), filepath,
                                    f"source '{sname}' does not declare loader"))
        if fresh_rule and has_tests(source):
            findings.append(Finding(fresh_rule["id"], _severity(fresh_rule), filepath,
                                    f"source '{sname}' carries data tests; freshness is the only source test"))
        for table in source.get("tables") or []:
            if not isinstance(table, dict):
                continue
            tname = f"{sname}.{table.get('name', '<unnamed>')}"
            if grain_rule and not str(table.get("description") or "").strip().startswith("Grain:"):
                findings.append(Finding(grain_rule["id"], _severity(grain_rule), filepath,
                                        f"source table '{tname}' description does not open with 'Grain:'"))
            columns = table.get("columns") or []
            if cols_rule:
                if not columns:
                    findings.append(Finding(cols_rule["id"], _severity(cols_rule), filepath,
                                            f"source table '{tname}' declares no columns"))
                for col in columns:
                    if isinstance(col, dict) and not str(col.get("description") or "").strip():
                        findings.append(Finding(cols_rule["id"], _severity(cols_rule), filepath,
                                                f"source column '{tname}.{col.get('name')}' has no description"))
            if fresh_rule:
                if has_tests(table):
                    findings.append(Finding(fresh_rule["id"], _severity(fresh_rule), filepath,
                                            f"source table '{tname}' carries data tests; freshness is the only source test"))
                for col in columns:
                    if has_tests(col):
                        findings.append(Finding(fresh_rule["id"], _severity(fresh_rule), filepath,
                                                f"source column '{tname}.{col.get('name')}' carries data tests; "
                                                "freshness is the only source test"))
    return findings


def check_dbt_file(conv, filepath, text):
    layer = infer_dbt_layer(filepath)
    kind = infer_dbt_kind(filepath, text)
    # A file-naming rule keyed only by `layer` (an older convention file) is
    # written for models. It must not judge a YAML file, a seed or a macro by a
    # model pattern, so those files are named with no layer and only rules
    # keyed by `kind` reach them.
    if filepath.endswith(".csv"):
        return check_file_naming(conv, filepath, kind=kind)
    if filepath.endswith((".yml", ".yaml")):
        return (check_file_naming(conv, filepath, kind=kind)
                + check_style_thresholds(conv, filepath, text, file_type="yml")
                + check_dbt_schema_yml(conv, filepath, text))
    findings = []
    naming_layer = layer if kind in MODEL_KINDS else None
    findings += check_file_naming(conv, filepath, layer=naming_layer, kind=kind)
    findings += check_file_content_rules(conv, filepath, text, layer=layer, kind=kind)
    findings += check_style_thresholds(conv, filepath, text, file_type="sql")
    findings += check_dbt_sql(conv, filepath, text)
    findings += check_dbt_layer_rules(conv, filepath, text, kind=kind)
    return findings


# ----------------------------------------------------------------------
# Changed-code scope (wire#277)
# ----------------------------------------------------------------------

class Scope:
    """Which files count as new or changed. mode is one of:
      new_project  every file is new (--new-project)
      changed      worked out from git (--changed-from <ref>)
      unknown      no scope given, or git could not answer"""

    def __init__(self, mode, base=None, changed=None, added=None, note=None):
        self.mode = mode
        self.base = base
        self.changed = changed or set()
        self.added = added or set()
        self.note = note

    def to_dict(self):
        d = {"mode": self.mode}
        if self.base:
            d["base"] = self.base
        if self.mode == "changed":
            d["changed_files"] = len(self.changed)
            d["added_files"] = len(self.added)
        if self.note:
            d["note"] = self.note
        return d


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def git_scope(path, base_ref):
    """Files added or changed against the merge base of base_ref and HEAD:
    committed and uncommitted changes (git diff against the merge base reads
    the working tree) plus untracked files. A rename counts as changed, not
    added. Any git failure gives an unknown scope, never an exception."""
    start = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    try:
        root = _git(["rev-parse", "--show-toplevel"], start).strip()
        merge_base = _git(["merge-base", base_ref, "HEAD"], root).strip()
        diff = _git(["diff", "--name-status", "--no-renames", merge_base], root)
        untracked = _git(["ls-files", "--others", "--exclude-standard"], root)
    except (OSError, subprocess.CalledProcessError) as e:
        detail = getattr(e, "stderr", "") or str(e)
        return Scope("unknown", base=base_ref,
                     note=f"git could not work out changed files ({detail.strip()}); "
                          "new-and-changed rules report as warnings")
    changed, added = set(), set()
    for line in diff.splitlines():
        status, _, name = line.partition("\t")
        if not name or status.startswith("D"):
            continue
        full = os.path.realpath(os.path.join(root, name))
        changed.add(full)
        if status.startswith("A"):
            added.add(full)
    for name in untracked.splitlines():
        if name:
            full = os.path.realpath(os.path.join(root, name))
            changed.add(full)
            added.add(full)
    return Scope("changed", base=base_ref, changed=changed, added=added)


def _rules_by_id(conv):
    by_id = {}
    for rules in conv.values():
        if isinstance(rules, list):
            for rule in rules:
                if isinstance(rule, dict) and rule.get("id"):
                    by_id[rule["id"]] = rule
    return by_id


def apply_scope(conv, findings, scope):
    """Drops or softens findings from rules marked applies_to. In changed
    mode a new_and_changed rule keeps only findings on changed files and a
    new_files rule only those on added files. In unknown mode both keep every
    finding but as a warning. Rules without applies_to are untouched."""
    by_id = _rules_by_id(conv)
    kept = []
    for f in findings:
        applies_to = (by_id.get(f.rule_id) or {}).get("applies_to")
        if not applies_to or scope.mode == "new_project":
            kept.append(f)
            continue
        if scope.mode == "unknown":
            f.severity = "warning"
            kept.append(f)
            continue
        target = scope.added if applies_to == "new_files" else scope.changed
        if os.path.realpath(f.file) in target:
            kept.append(f)
    return kept


# ----------------------------------------------------------------------
# LookML
# ----------------------------------------------------------------------

def infer_lookml_layer(filepath):
    parts = filepath.replace(os.sep, "/").split("/")
    for layer in ("base", "staging", "aggregate", "int", "model"):
        if layer in parts:
            return layer
    return None


def check_lookml(conv, filepath, text):
    findings = []
    layer = infer_lookml_layer(filepath)
    findings += check_file_naming(conv, filepath, layer=layer)
    findings += check_file_content_rules(conv, filepath, text, layer=layer)
    findings += check_style_thresholds(conv, filepath, text)

    braces_rule = get_rule(conv, "style", "balanced_braces")
    if braces_rule:
        opens, closes = text.count("{"), text.count("}")
        if opens != closes:
            findings.append(Finding(
                braces_rule["id"], _severity(braces_rule, "error"), filepath,
                f"unbalanced braces: {opens} '{{' vs {closes} '}}'",
            ))

    view_rule = get_rule(conv, "naming", "warehouse_view_name")
    if view_rule and layer == "base":
        pat = re.compile(view_rule["pattern"])
        for m in re.finditer(r"view:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{", text):
            name = m.group(1)
            if not pat.match(name):
                findings.append(Finding(
                    view_rule["id"], _severity(view_rule, "error"), filepath,
                    f"{view_rule.get('description')} — got '{name}'",
                ))

    explore_rule = get_rule(conv, "required_fields", "explore_requires_label_and_description")
    if explore_rule:
        for m in re.finditer(r"explore:\s*([A-Za-z_][A-Za-z0-9_]*)\s*\{", text):
            block = extract_brace_block(text, m.end() - 1)
            for key in explore_rule.get("required_keys", []):
                if not re.search(rf"\b{key}\s*:", block):
                    findings.append(Finding(
                        explore_rule["id"], _severity(explore_rule, "error"), filepath,
                        f"explore '{m.group(1)}' missing required field '{key}'",
                    ))

    return findings


# ----------------------------------------------------------------------
# Cube
# ----------------------------------------------------------------------

def check_cube(conv, filepath, text):
    findings = []
    findings += check_file_naming(conv, filepath)
    findings += check_file_content_rules(conv, filepath, text)
    findings += check_style_thresholds(conv, filepath, text)

    try:
        doc = yaml.safe_load(text)
    except Exception as e:
        return findings + [Finding("yaml_parse_error", "error", filepath, f"could not parse YAML: {e}")]
    if not isinstance(doc, dict):
        return findings

    snake_rule = get_rule(conv, "naming", "snake_case_throughout")
    view_suffix_rule = get_rule(conv, "naming", "view_suffix")
    bool_prefix_rule = get_rule(conv, "naming", "boolean_dimension_prefix")
    cube_fields_rule = get_rule(conv, "required_fields", "cube_requires_core_fields")
    cube_pk_rule = get_rule(conv, "required_fields", "cube_requires_primary_key")
    dim_fields_rule = get_rule(conv, "required_fields", "dimension_requires_core_fields")
    measure_fields_rule = get_rule(conv, "required_fields", "measure_requires_core_fields")

    def check_snake_case(name, what):
        if snake_rule and name and not re.match(snake_rule["pattern"], name):
            findings.append(Finding(
                snake_rule["id"], _severity(snake_rule, "error"), filepath,
                f"{what} '{name}' is not snake_case",
            ))

    for cube in doc.get("cubes") or []:
        if not isinstance(cube, dict):
            continue
        name = cube.get("name", "<unnamed>")
        if cube_fields_rule:
            missing = [k for k in cube_fields_rule["required_keys"] if k not in cube]
            if missing:
                findings.append(Finding(
                    cube_fields_rule["id"], _severity(cube_fields_rule, "error"), filepath,
                    f"cube '{name}' missing required field(s): {missing}",
                ))
        check_snake_case(name if name != "<unnamed>" else None, "cube name")

        dims = cube.get("dimensions") or []
        if cube_pk_rule and not any(isinstance(d, dict) and d.get("primary_key") for d in dims):
            findings.append(Finding(
                cube_pk_rule["id"], _severity(cube_pk_rule, "error"), filepath,
                f"cube '{name}' has no dimension with primary_key: true",
            ))
        for dim in dims:
            if not isinstance(dim, dict):
                continue
            dname = dim.get("name", "<unnamed>")
            if dim_fields_rule:
                missing = [k for k in dim_fields_rule["required_keys"] if k not in dim]
                if missing:
                    findings.append(Finding(
                        dim_fields_rule["id"], _severity(dim_fields_rule, "error"), filepath,
                        f"dimension '{dname}' on cube '{name}' missing required field(s): {missing}",
                    ))
            check_snake_case(dname if dname != "<unnamed>" else None, f"dimension name (cube '{name}')")
            if bool_prefix_rule and dim.get("type") == "boolean" and dname != "<unnamed>" \
                    and not re.match(bool_prefix_rule["pattern"], dname):
                findings.append(Finding(
                    bool_prefix_rule["id"], _severity(bool_prefix_rule), filepath,
                    f"boolean dimension '{dname}' on cube '{name}' should read as a yes/no question",
                ))

        for meas in cube.get("measures") or []:
            if not isinstance(meas, dict):
                continue
            mname = meas.get("name", "<unnamed>")
            if measure_fields_rule:
                missing = [k for k in measure_fields_rule["required_keys"] if k not in meas]
                if missing:
                    findings.append(Finding(
                        measure_fields_rule["id"], _severity(measure_fields_rule, "error"), filepath,
                        f"measure '{mname}' on cube '{name}' missing required field(s): {missing}",
                    ))
            check_snake_case(mname if mname != "<unnamed>" else None, f"measure name (cube '{name}')")

    for view in doc.get("views") or []:
        if not isinstance(view, dict):
            continue
        vname = view.get("name", "<unnamed>")
        if view_suffix_rule and vname != "<unnamed>" and not re.search(view_suffix_rule["pattern"], vname):
            findings.append(Finding(
                view_suffix_rule["id"], _severity(view_suffix_rule, "error"), filepath,
                f"view name '{vname}' should end with _view",
            ))

    return findings


def _rules(conv, section):
    return [r for r in (conv.get(section) or []) if isinstance(r, dict) and r.get("id")]


def check_dbtcharts(conv, filepath, text):
    """dbt Charts boards under charts/ plus the project files (dbt_charts.yml, meta.yml).

    Mechanical half of wire/conventions/dbtcharts.yml: KPI label length and prefix, title/label
    and notes presence, KPI value formats, trend time_unit, hidden endpoint labels, section
    heading rows, board-level theme, BigQuery SQL forms the dct static checker rejects, and the
    anchor's allowed top-level keys. Presentation/window/shape settings are read by the generate
    command, not checked here."""
    findings = []
    base = os.path.basename(filepath)
    try:
        doc = yaml.safe_load(text)
    except Exception as e:
        return [Finding("yaml_parse_error", "error", filepath, f"could not parse YAML: {e}")]
    if not isinstance(doc, dict):
        return findings

    # --- project files -------------------------------------------------------------------
    for rule in _rules(conv, "project_files"):
        if rule.get("file") == base and rule.get("allowed_top_level_keys") is not None:
            extra = sorted(k for k in doc if k not in rule["allowed_top_level_keys"])
            if extra:
                findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                        f"{base} carries key(s) {extra}; allowed: {rule['allowed_top_level_keys']}"))
        if rule.get("file") == base and rule["id"] == "meta_sets_theme" and "theme" not in doc:
            findings.append(Finding(rule["id"], _severity(rule), filepath, "meta.yml does not set theme:"))
    if base in ("dbt_charts.yml", "meta.yml"):
        return findings
    if "charts" not in doc and "rows" not in doc and "text" not in doc:
        return findings  # not a board

    def text_rule(section, rule_id):
        r = get_rule(conv, section, rule_id)
        if not r or not r.get("forbidden_pattern"):
            return
        for i, line in enumerate(text.splitlines(), 1):
            if re.search(r["forbidden_pattern"], line):
                findings.append(Finding(r["id"], _severity(r), filepath, r["description"], line=i))

    if doc.get("charts"):  # a text-only board (the landing page) may use headings
        text_rule("layout", "no_section_heading_rows")
    text_rule("project_files", "board_no_own_theme")

    # --- SQL forms ------------------------------------------------------------------------
    for rule in _rules(conv, "sql"):
        pat = rule.get("forbidden_pattern")
        if not pat:
            continue
        for qname, q in (doc.get("queries") or {}).items():
            sql = q.get("sql") if isinstance(q, dict) else q
            if isinstance(sql, str) and re.search(pat, sql):
                findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                        f"query '{qname}': {rule['description']}"))

    # --- charts and queries -----------------------------------------------------------------
    notes_rule = get_rule(conv, "naming", "notes_required")
    title_rule = get_rule(conv, "naming", "chart_title_required")
    words_rule = get_rule(conv, "naming", "kpi_label_max_words")
    prefix_rule = get_rule(conv, "naming", "kpi_label_no_table_prefix")
    fmt_rule = get_rule(conv, "layout", "kpi_value_format_required")
    tu_rule = get_rule(conv, "layout", "trend_time_unit_required")
    ep_rule = get_rule(conv, "layout", "no_hidden_endpoint_labels")

    if notes_rule:
        for qname, q in (doc.get("queries") or {}).items():
            if isinstance(q, dict) and not str(q.get("notes") or "").strip():
                findings.append(Finding(notes_rule["id"], _severity(notes_rule, "error"), filepath,
                                        f"query '{qname}' has no notes:"))

    for cname, c in (doc.get("charts") or {}).items():
        if not isinstance(c, dict):
            continue
        ctype = c.get("type")
        style = c.get("style") if isinstance(c.get("style"), dict) else {}
        if notes_rule and not str(c.get("notes") or "").strip():
            findings.append(Finding(notes_rule["id"], _severity(notes_rule, "error"), filepath,
                                    f"chart '{cname}' has no notes:"))
        if ctype == "kpi":
            label = str(c.get("label") or "")
            if title_rule and not label.strip():
                findings.append(Finding(title_rule["id"], _severity(title_rule, "error"), filepath,
                                        f"KPI '{cname}' has no label:"))
            if words_rule and label and len(label.split()) > int(words_rule.get("value", 4)):
                findings.append(Finding(words_rule["id"], _severity(words_rule), filepath,
                                        f"KPI '{cname}' label '{label}' has {len(label.split())} words (max {words_rule['value']})"))
            if prefix_rule and label and re.search(prefix_rule["forbidden_pattern"], label):
                findings.append(Finding(prefix_rule["id"], _severity(prefix_rule), filepath,
                                        f"KPI '{cname}' label '{label}' starts with a table-name prefix"))
            value_style = style.get("value") if isinstance(style.get("value"), dict) else {}
            if fmt_rule and not value_style.get("format"):
                findings.append(Finding(fmt_rule["id"], _severity(fmt_rule), filepath,
                                        f"KPI '{cname}' has no style.value.format"))
        else:
            if title_rule and ctype and not str(c.get("title") or "").strip():
                findings.append(Finding(title_rule["id"], _severity(title_rule, "error"), filepath,
                                        f"chart '{cname}' ({ctype}) has no title:"))
            if tu_rule and ctype in ("line", "bar", "area") and str(c.get("x") or "").lower() == "month":
                axis_x = style.get("axis_x") if isinstance(style.get("axis_x"), dict) else {}
                labels = axis_x.get("labels") if isinstance(axis_x.get("labels"), dict) else {}
                if not (axis_x.get("time_unit") or labels.get("time_unit")):
                    findings.append(Finding(tu_rule["id"], _severity(tu_rule), filepath,
                                            f"chart '{cname}' plots month on x without style.axis_x.time_unit"))
            ep = style.get("endpoint_labels") if isinstance(style.get("endpoint_labels"), dict) else {}
            if ep_rule and ep.get("visible") is False:
                findings.append(Finding(ep_rule["id"], _severity(ep_rule), filepath,
                                        f"chart '{cname}' hides endpoint labels; alias the column instead"))
    return findings


# ----------------------------------------------------------------------
# Airflow (wire#380)
# ----------------------------------------------------------------------
#
# Python is read with the standard library ast module, never with regular
# expressions, so a comment or a string that mentions a call does not count
# as the call. Each rule names its check in `check:` and carries the check's
# settings (key lists, patterns, thresholds), so a client can add a second
# rule that runs the same check with its own settings.

FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def _dotted(node):
    """`requests.get` for requests.get, `Variable.get` for Variable.get, or
    None for anything that is not a plain name or attribute chain."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _call_name(call):
    return _dotted(call.func) if isinstance(call, ast.Call) else None


def _last(name):
    return (name or "").rsplit(".", 1)[-1]


def _walk_with_scope(tree):
    """Every node with a flag saying whether it sits inside a function body
    (code that runs when a task runs, not when the file is parsed)."""
    stack = [(tree, False)]
    while stack:
        node, in_function = stack.pop()
        yield node, in_function
        inside = in_function or isinstance(node, FUNCTION_NODES)
        for child in ast.iter_child_nodes(node):
            # A decorator runs when the file is parsed, so it is not inside.
            if isinstance(node, FUNCTION_NODES[:2]) and child in node.decorator_list:
                stack.append((child, in_function))
            else:
                stack.append((child, inside))


def _str_value(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _seconds(node):
    """A timeout in seconds when it is a number or timedelta(...) with literal
    arguments, else None (not judged)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.Call) and _last(_call_name(node)) == "timedelta":
        units = {"weeks": 604800, "days": 86400, "hours": 3600, "minutes": 60, "seconds": 1}
        total = 0.0
        if node.args:
            return None
        for kw in node.keywords:
            if kw.arg not in units or not isinstance(kw.value, ast.Constant) \
                    or not isinstance(kw.value.value, (int, float)):
                return None
            total += kw.value.value * units[kw.arg]
        return total
    return None


def _kw(call, name):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def af_safe_mode_words(rule, tree, text, filepath):
    parts = filepath.replace(os.sep, "/").split("/")
    if os.path.basename(filepath) == "__init__.py":
        return []
    if not set(_as_list(rule.get("path_segments")) or ["dags"]) & set(parts):
        return []
    lowered = text.lower()
    if "airflow" in lowered and "dag" in lowered:
        return []
    builds = any(
        not isinstance(stmt, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef, ast.Pass))
        and not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant))
        for stmt in tree.body
    )
    if not builds:
        return []  # a helper module that only defines functions
    missing = " or ".join(f"'{w}'" for w in ("airflow", "dag") if w not in lowered)
    return [Finding(rule["id"], _severity(rule, "error"), filepath,
                    f"no {missing} in the file; Airflow skips it in safe mode, with no error")]


def _default_args_dicts(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
            if any(isinstance(t, ast.Name) and t.id.endswith("default_args") for t in node.targets):
                yield node.value
        elif isinstance(node, ast.keyword) and node.arg == "default_args" and isinstance(node.value, ast.Dict):
            yield node.value


def af_default_args_dag_keys(rule, tree, text, filepath):
    keys = set(rule.get("keys") or [])
    findings = []
    for d in _default_args_dicts(tree):
        for k in d.keys:
            name = _str_value(k)
            if name in keys:
                findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                        f"'{name}' is a DAG argument; set it on the DAG, not in default_args",
                                        line=k.lineno))
    return findings


def af_mapped_fanout_cap(rule, tree, text, filepath):
    cap_kws = set(rule.get("cap_keywords") or [])
    dag_cap_kws = set(rule.get("dag_cap_keywords") or [])

    def has_cap(call, names):
        return any(kw.arg in names for kw in call.keywords)

    # A DAG with max_active_tasks caps every task in it.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _last(_call_name(node)) in ("DAG", "dag") and has_cap(node, dag_cap_kws):
            return []

    capped = set()  # names of tasks or partials that carry a cap
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and (_call_name(dec) or "").split(".")[0] == "task" \
                        and has_cap(dec, cap_kws):
                    capped.add(node.name)
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            v = node.value
            if isinstance(v.func, ast.Attribute) and v.func.attr == "partial" and has_cap(v, cap_kws):
                capped.update(t.id for t in node.targets if isinstance(t, ast.Name))

    findings = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("expand", "expand_kwargs")):
            continue
        receiver = node.func.value
        ok = False
        if isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Attribute) \
                and receiver.func.attr == "partial":
            ok = has_cap(receiver, cap_kws) or (isinstance(receiver.func.value, ast.Name)
                                                and receiver.func.value.id in capped)
        elif isinstance(receiver, ast.Name):
            ok = receiver.id in capped
        if not ok:
            findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                    f".{node.func.attr}() has no cap on parallel tasks; set "
                                    "max_active_tis_per_dag or a pool from the environment's config",
                                    line=node.lineno))
    return findings


def af_literal_value(rule, tree, text, filepath):
    names = set(rule.get("keyword_names") or [])
    patterns = [re.compile(p) for p in rule.get("literal_patterns") or []]
    skip = set()  # docstrings and the fixed parts of f-strings are not values
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            skip.update(id(v) for v in node.values)
        elif isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                skip.add(id(body[0].value))
    findings, reported = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in names:
            value = _str_value(node.value)
            if value is not None and "{{" not in value:
                reported.add(id(node.value))
                findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                        f"{node.arg}='{value}' is written into the code; read it from config",
                                        line=node.value.lineno))
    for node in ast.walk(tree):
        value = _str_value(node)
        if value is None or id(node) in skip or id(node) in reported or "{{" in value:
            continue
        if any(p.search(value) for p in patterns):
            findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                    f"'{value}' is written into the code; read it from config",
                                    line=node.lineno))
    return findings


def af_top_level_variable_get(rule, tree, text, filepath):
    return [Finding(rule["id"], _severity(rule), filepath,
                    "Variable.get() runs on every parse; use {{ var.value.<key> }} or read it inside the task",
                    line=node.lineno)
            for node, in_function in _walk_with_scope(tree)
            if not in_function and isinstance(node, ast.Call)
            and (_call_name(node) or "").endswith("Variable.get")]


MOVING_DATES = ("datetime.now", "datetime.utcnow", "datetime.today", "date.today", "pendulum.now",
                "pendulum.today", "timezone.utcnow", "days_ago")


def af_dynamic_start_date(rule, tree, text, filepath):
    values = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "start_date":
            values.append(node.value)
        elif isinstance(node, ast.Dict):
            values += [v for k, v in zip(node.keys, node.values) if _str_value(k) == "start_date"]
    findings = []
    for value in values:
        for sub in ast.walk(value):
            name = _call_name(sub) if isinstance(sub, ast.Call) else None
            if name and any(name == m or name.endswith("." + m) for m in MOVING_DATES):
                findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                        f"start_date uses {name}(); use a fixed date", line=sub.lineno))
                break
    return findings


def af_sensor_poke_timeout(rule, tree, text, filepath):
    limit = float(rule.get("max_poke_seconds", 3600))
    findings = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and _last(_call_name(node)).endswith("Sensor")):
            continue
        mode = _kw(node, "mode")
        if mode is not None and _str_value(mode) != "poke":
            continue  # reschedule, or a value the script cannot judge
        deferrable = _kw(node, "deferrable")
        if deferrable is not None and not (isinstance(deferrable, ast.Constant) and deferrable.value is False):
            continue
        timeout = _kw(node, "timeout")
        seconds = 604800.0 if timeout is None else _seconds(timeout)
        if seconds is not None and seconds > limit:
            findings.append(Finding(rule["id"], _severity(rule), filepath,
                                    f"{_last(_call_name(node))} pokes for up to {int(seconds)}s "
                                    f"(limit {int(limit)}s); use mode='reschedule' or deferrable=True",
                                    line=node.lineno))
    return findings


def af_top_level_io(rule, tree, text, filepath):
    prefixes = rule.get("call_prefixes") or []

    def matches(name):
        for p in prefixes:
            if p.endswith("."):
                if name.startswith(p) or ("." + p) in ("." + name):
                    return True
            elif name == p or name.endswith("." + p):
                return True
        return False

    return [Finding(rule["id"], _severity(rule), filepath,
                    f"{_call_name(node)}() runs on every parse; move it into a task",
                    line=node.lineno)
            for node, in_function in _walk_with_scope(tree)
            if not in_function and isinstance(node, ast.Call) and _call_name(node)
            and matches(_call_name(node))]


def af_deprecated_keyword(rule, tree, text, filepath):
    callables = set(rule.get("callables") or [])
    keywords = set(rule.get("keywords") or [])
    return [Finding(rule["id"], _severity(rule), filepath,
                    f"{_last(_call_name(node))}({kw.arg}=...) is deprecated", line=kw.value.lineno)
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _last(_call_name(node)) in callables
            for kw in node.keywords if kw.arg in keywords]


def af_deprecated_import(rule, tree, text, filepath):
    modules = rule.get("modules") or []
    names = set(rule.get("names") or [])

    def old(module):
        return any(module == m or module.startswith(m + ".") for m in modules)

    findings = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if old(node.module):
                findings.append(Finding(rule["id"], _severity(rule), filepath,
                                        f"import from {node.module} is deprecated", line=node.lineno))
            else:
                for alias in node.names:
                    if alias.name in names:
                        findings.append(Finding(rule["id"], _severity(rule), filepath,
                                                f"{alias.name} is deprecated", line=node.lineno))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if old(alias.name):
                    findings.append(Finding(rule["id"], _severity(rule), filepath,
                                            f"import {alias.name} is deprecated", line=node.lineno))
    return findings


AIRFLOW_CHECKS = {
    "safe_mode_words": af_safe_mode_words,
    "default_args_dag_keys": af_default_args_dag_keys,
    "mapped_fanout_cap": af_mapped_fanout_cap,
    "literal_value": af_literal_value,
    "top_level_variable_get": af_top_level_variable_get,
    "dynamic_start_date": af_dynamic_start_date,
    "sensor_poke_timeout": af_sensor_poke_timeout,
    "top_level_io": af_top_level_io,
    "deprecated_keyword": af_deprecated_keyword,
    "deprecated_import": af_deprecated_import,
}


def check_airflow(conv, filepath, text):
    """Airflow DAG folders: file_content rules on every file, and the ast
    checks named by each rule's `check:` on Python files. A rule naming a
    check this script does not have is reported once, not ignored."""
    findings = check_file_content_rules(conv, filepath, text)
    if not filepath.endswith(".py"):
        return findings
    try:
        tree = ast.parse(text, filename=filepath)
    except SyntaxError as e:
        return findings + [Finding("python_syntax_error", "error", filepath,
                                   f"could not parse Python: {e.msg}", line=e.lineno)]
    for rules in conv.values():
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict) or not rule.get("check"):
                continue
            fn = AIRFLOW_CHECKS.get(rule["check"])
            if fn is None:
                findings.append(Finding(rule.get("id", "?"), "warning", filepath,
                                        f"unknown check '{rule['check']}'; rule not run"))
                continue
            findings += fn(rule, tree, text, filepath)
    return findings


# ----------------------------------------------------------------------
# Looker Data Apps (wire#387): one Lit module per app. Every rule but one is a
# file_content regex (Google's tile sandbox rules and Wire's own); the one
# named check finds a widget id used twice.
# ----------------------------------------------------------------------

DATA_APPS_SKIP_SEGMENTS = {"runtime", "vendor", "preview-server", "skills", "node_modules", "dist"}
_DA_ID_RE = re.compile(r"""\bid\s*=\s*["']([A-Za-z][\w:.-]*)["']""")


def da_widget_ids_unique(rule, text, filepath):
    seen = {}
    findings = []
    for i, line in enumerate(text.splitlines(), start=1):
        for wid in _DA_ID_RE.findall(line):
            if wid in seen:
                findings.append(Finding(rule["id"], _severity(rule, "error"), filepath,
                                        f"id \"{wid}\" is also used on line {seen[wid]}", line=i))
            else:
                seen[wid] = i
    return findings


DATA_APPS_CHECKS = {"widget_ids_unique": da_widget_ids_unique}


def check_data_apps(conv, filepath, text):
    """A Data App's app.js: the file_content rules, plus the named checks.
    The toolkit's own folders are never linted."""
    parts = set(os.path.normpath(filepath).split(os.sep))
    if parts & DATA_APPS_SKIP_SEGMENTS:
        return []
    findings = check_file_content_rules(conv, filepath, text)
    for rules in conv.values():
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict) or not rule.get("check"):
                continue
            fn = DATA_APPS_CHECKS.get(rule["check"])
            if fn is None:
                findings.append(Finding(rule.get("id", "?"), "warning", filepath,
                                        f"unknown check '{rule['check']}'; rule not run"))
                continue
            findings += fn(rule, text, filepath)
    return findings


DISPATCH = {"dbt": check_dbt_file, "lookml": check_lookml, "cube": check_cube, "dbtcharts": check_dbtcharts,
            "airflow": check_airflow, "data_apps": check_data_apps}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--domain", required=True, choices=sorted(DOMAIN_EXTENSIONS))
    ap.add_argument("--convention", required=True, help="path to the domain's convention YAML")
    ap.add_argument("--path", required=True, help="file or directory to lint")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    scope_args = ap.add_mutually_exclusive_group()
    scope_args.add_argument("--changed-from", metavar="REF",
                            help="git ref of the release branch's base; rules marked applies_to "
                                 "are checked only on files added or changed since its merge base")
    scope_args.add_argument("--new-project", action="store_true",
                            help="treat every file as new, so every rule applies at its own severity")
    ap.add_argument("--base-convention", metavar="PATH",
                    help="Wire's file for the domain, read when --convention has extends: wire "
                         "(default: conventions/<domain>.yml beside this script's folder)")
    args = ap.parse_args()

    try:
        conv, extends_info = resolve_convention(args.convention, args.domain, args.base_convention)
    except (OSError, ValueError, yaml.YAMLError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)

    if conv.get("domain") != args.domain:
        print(f"ERROR: convention file domain '{conv.get('domain')}' does not match --domain {args.domain}", file=sys.stderr)
        sys.exit(2)

    if not os.path.exists(args.path):
        print(f"ERROR: --path '{args.path}' does not exist", file=sys.stderr)
        sys.exit(2)

    check_fn = DISPATCH[args.domain]
    extensions = DOMAIN_EXTENSIONS[args.domain]
    if args.new_project:
        scope = Scope("new_project")
    elif args.changed_from:
        scope = git_scope(args.path, args.changed_from)
    else:
        scope = Scope("unknown", note="no --changed-from or --new-project; new-and-changed rules report as warnings")

    all_findings = []
    files_checked = 0
    for f in iter_target_files(args.path, extensions):
        files_checked += 1
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            all_findings.append(Finding("read_error", "error", f, str(e)))
            continue
        all_findings.extend(check_fn(conv, f, text))
    all_findings = apply_scope(conv, all_findings, scope)

    errors = [f for f in all_findings if f.severity == "error"]
    warnings = [f for f in all_findings if f.severity == "warning"]

    if args.format == "json":
        report = {
            "domain": args.domain,
            "files_checked": files_checked,
            "scope": scope.to_dict(),
            "errors": len(errors),
            "warnings": len(warnings),
            "findings": [f.to_dict() for f in all_findings],
        }
        if extends_info:
            report["convention"] = extends_info
        print(json.dumps(report, indent=2))
    else:
        for f in sorted(all_findings, key=lambda x: (x.file, x.line or 0)):
            loc = f"{f.file}:{f.line}" if f.line else f.file
            print(f"  {f.severity.upper():7} [{f.rule_id}] {loc} — {f.message}")
        print()
        if extends_info:
            print(f"Convention: {args.convention} extends Wire's {extends_info['base']}")
            for d in extends_info["disabled"]:
                print(f"  Disabled by the client: [{d['id']}] {d['reason']}")
            for rid in extends_info["unknown_disabled"]:
                print(f"  WARNING: disable names '{rid}', which no Wire rule has")
        if scope.note:
            print(f"Scope: {scope.note}")
        elif scope.mode == "changed":
            print(f"Scope: {len(scope.changed)} file(s) changed since the merge base with {scope.base}")
        print(f"{files_checked} file(s) checked — {len(errors)} error(s), {len(warnings)} warning(s)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
