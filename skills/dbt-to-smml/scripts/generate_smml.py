#!/usr/bin/env python3
"""
Generate an OAC semantic model in SMML from dbt artifacts — all layers.

Reads dbt's target/manifest.json + target/catalog.json (+ `meta.oac` on
models and columns) and emits a full SMML semantic model, one JSON file per
object, in the layout OAC expects:

  <out>/physical/<Database>.json
  <out>/physical/<Database>/<Schema>.json
  <out>/physical/<Database>/<Schema>/<table>.json          (+ role-play aliases)
  <out>/logical/<BusinessModel>.json
  <out>/logical/<BusinessModel>/<logical table>.json        (+ alias logical tables)
  <out>/presentation/<SubjectArea>.json
  <out>/presentation/<SubjectArea>/<presentation table>.json

Every emitted object is wrapped in its singular SMML type key, e.g.
{"physicalTable": {...}} — see ../smml-semantic-modeling/references/smml-schema.md
for the full object model this generator targets, and
../smml-semantic-modeling/references/modeling-patterns.md for the modeling
judgement (role-playing dimensions, hierarchies, derived measures, subject
area design) encoded below.

Phases, all implemented here:
  1 Physical     — database, schema, physical tables + columns; role-playing
                   dimension aliases; physical joins (fact -> dim/alias)
  2 Logical      — business model, logical fact/dim/alias tables, logical
                   columns, logical table sources, logical joins
  3 Hierarchy    — level-based hierarchies (+ Grand Total, chronologicalKey
                   for time dimensions) from meta.oac
  3 Measures     — aggregation rules; derived/ratio measures over
                   already-aggregated sibling logical columns
  4 Presentation — subject areas (a model can belong to more than one),
                   named presentation "roles" for FK columns (with or without
                   a real physical/logical alias — see role_alias/
                   presentation_label below), implicit fact column on
                   multi-fact subject areas

Deterministic: same inputs -> identical output (sorted keys). No network/LLM.

`meta.oac` drives the semantics; where absent, light inference fills in so
the output is still meaningful. meta.oac always wins — that's the
human-in-the-loop override. See references/meta-oac-vocabulary.md.

Role-playing dimensions — the default is Oracle's own stated best practice:
once a dimension is targeted by more than one FK anywhere in the model, EVERY
one of those FKs gets a real physical + logical alias — never leave one role
joined to the base table once any other role has been aliased (that
ambiguity is exactly the fan-trap Oracle's guide warns about). A dimension
targeted by exactly one FK needs no alias at all. On top of that default,
two independent per-column overrides are available:
  - `role_alias` names the alias explicitly (recommended whenever a
    dimension plays multiple roles — without it, the generator still builds
    the alias but derives a name from the column's label, which is usually
    worse).
  - `presentation_label` gives that FK's dimension its own presentation
    display name, independent of the alias's physical/logical name (e.g. a
    short alias name `DIM_END_DATE` with a longer presentation label
    "Activity End Date").
  - A dimension whose *every* FK reference declares role_alias/
    presentation_label never gets its own generic presentation table — it
    only appears via its named roles.

VALIDATED against a real OAC-imported export (see smml-schema.md's [ground
truth] tags) for: object wrapper keys, physical/logical table+column shapes,
physical+logical join shapes, UPPER_SNAKE naming convention, presentation
column visibility. The role-playing default above is Oracle's documented
best practice (F42737-41 Ch.19), not a mechanical replay of the one real
export this generator was validated against — that export left one date role
unaliased, which turned out to be an oversight in that build, not a pattern
to reproduce. NOT validated against a real export at all (PDF-only — see
smml-schema.md's [F38574-15]/[gap] tags): hierarchies, derived measures.
"""
import argparse, json, os, re

# Oracle/ADW catalog type -> SMML physicalColumn DataType. Full DataType enum
# is documented in smml-schema.md; this maps the Oracle catalog types dbt
# actually reports. Ground-truth-confirmed: NUMBER->NUMERIC, DATE->DATETIME,
# VARCHAR2->VARCHAR, CHAR->CHAR, TIMESTAMP->TIMESTAMP. The rest are reasonable
# defaults within the confirmed enum, not independently validated.
TYPE_MAP = {
    "NUMBER": "NUMERIC",
    "FLOAT": "DOUBLE", "BINARY_DOUBLE": "DOUBLE", "BINARY_FLOAT": "DOUBLE",
    "INTEGER": "INT", "INT": "INT",
    "SMALLINT": "SMALLINT", "TINYINT": "TINYINT",
    "VARCHAR2": "VARCHAR", "VARCHAR": "VARCHAR", "NVARCHAR2": "VARCHAR",
    "CHAR": "CHAR", "NCHAR": "CHAR",
    "CLOB": "LONGVARCHAR", "NCLOB": "LONGVARCHAR",
    "DATE": "DATETIME", "TIMESTAMP": "TIMESTAMP",
    "BOOLEAN": "BOOLEAN",
}
NUMERIC_SMML = {"NUMERIC", "DOUBLE", "INT", "SMALLINT", "TINYINT", "FLOAT"}


def map_type(raw):
    if not raw:
        return "VARCHAR", 0
    base = re.split(r"[ (]", raw.strip().upper())[0]
    m = re.search(r"\((\d+)", raw)
    length = int(m.group(1)) if m else 0
    return TYPE_MAP.get(base, "VARCHAR"), length


def esc(part):
    """Escape '.' inside a name part for SMML fully-qualified names."""
    return str(part).replace(".", "\\.")


def fqn(objtype, *parts):
    return f"{objtype}:" + ".".join(esc(p) for p in parts)


def wrap(objtype, body):
    """Every SMML object is wrapped in its singular type key — see smml-schema.md."""
    return {objtype: body}


def oac(meta):
    return (meta or {}).get("oac", {}) or {}


def slug(label):
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").upper()


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")


def presentation_name(m):
    return m["presentation_name"] or m["name"].replace("_", " ").title()


# ----------------------------------------------------------------------------
# Load + build an internal model from the dbt artifacts
# ----------------------------------------------------------------------------
def build_models(manifest, catalog, layer, schema_override):
    models = {}
    for uid, node in manifest.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue
        if layer != "all" and layer not in node.get("fqn", []):
            continue
        cat = catalog.get("nodes", {}).get(uid, {})
        meta = oac(node.get("meta"))
        name = node["name"]
        is_fact = (meta.get("object_type") == "fact") or \
                  (meta.get("object_type") is None and name.startswith("fact_"))
        schema = schema_override or cat.get("metadata", {}).get("schema") or node.get("schema") or "PUBLIC"
        relation = cat.get("metadata", {}).get("name") or name.upper()

        cols = []
        man_cols = {k.lower(): v for k, v in (node.get("columns") or {}).items()}
        cat_cols = cat.get("columns") or {}
        for cname, cinfo in sorted(cat_cols.items(), key=lambda kv: kv[1].get("index", 0)):
            cmeta = oac((man_cols.get(cname.lower()) or {}).get("meta"))
            dtype, length = map_type(cinfo.get("type"))
            role = cmeta.get("role") or infer_role(cname, dtype, is_fact)
            phys = cinfo.get("name") or cname
            cols.append({
                "phys": phys,
                "label": cmeta.get("label") or phys.replace("_", " ").title(),
                "dtype": dtype,
                "length": length,
                "nullable": cmeta.get("nullable", True),
                "role": role,
                "aggregation": (cmeta.get("aggregation") or ("SUM" if role == "measure" else None)),
                "dimension": cmeta.get("dimension"),
                "role_alias": cmeta.get("role_alias"),
                "presentation_label": cmeta.get("presentation_label"),
                "expose_presentation": cmeta.get("expose_presentation", True),
                "include_join": cmeta.get("include_join", True),
                "description": (man_cols.get(cname.lower()) or {}).get("description"),
            })

        derived = []
        for dm in (meta.get("derived_measures") or []):
            derived.append({
                "name": dm["name"],
                "colname": slug(dm["name"]),
                "description": dm.get("description", "Derived measure."),
                "expression": dm["expression"],
                "expressionObjects": dm.get("expressionObjects", []),
            })

        sa_raw = meta.get("subject_area") or "Semantic Model"
        subject_areas = sa_raw if isinstance(sa_raw, list) else [sa_raw]

        models[name] = {
            "uid": uid, "name": name, "relation": relation, "schema": schema,
            "is_fact": is_fact,
            "description": node.get("description"),
            "subject_areas": subject_areas,
            "presentation_name": meta.get("presentation_name"),
            "implicit_fact": bool(meta.get("implicit_fact")),
            "hierarchies": meta.get("hierarchies") or [],
            "is_time": bool(meta.get("is_time_dimension")),
            "derived": derived,
            "columns": cols,
        }
    return models


def infer_role(name, dtype, is_fact):
    n = name.lower()
    id_like = n.endswith("_id") or n.endswith("_key") or n.endswith("_fk") or n.endswith("_pk")
    if is_fact:
        if id_like:
            return "degenerate"          # can't infer the dim target without meta.oac
        return "measure" if dtype in NUMERIC_SMML else "degenerate"
    return "attribute"


def dim_pk(dim):
    """Best-effort PK of a dimension: role key/primary_key, else first id-like, else first column."""
    for c in dim["columns"]:
        if c["role"] in ("key", "primary_key"):
            return c
    for c in dim["columns"]:
        if c["phys"].lower().endswith("_id") or c["phys"].lower().endswith("_key"):
            return c
    return dim["columns"][0] if dim["columns"] else None


# ----------------------------------------------------------------------------
# Role-playing dimensions — resolve which FK columns get a named role
# ----------------------------------------------------------------------------
def resolve_roles(models):
    """
    Best-practice default: when ONE FACT has more than one FK into the SAME
    dimension, EVERY one of those FKs gets a real physical + logical alias —
    never leave one role joined to the base table once another has been
    aliased (that's the fan-trap scenario Oracle's guide warns about). This
    is scoped per fact deliberately: two *different* facts each having their
    own single FK to a shared/conformed dimension (e.g. both `fact_a` and
    `fact_b` join `dim_teams` once each) is normal star-schema reuse, not a
    role-playing scenario — it must never trigger aliasing on its own.

    `role_alias` (per-column meta.oac) names an alias explicitly — do this
    whenever a dimension plays multiple roles within one fact; without it, an
    alias is still built (per the rule above) but named from the column's
    label, which is usually a worse name. `presentation_label` independently
    overrides just the presentation display name. Either one, even on a
    single, unrepeated FK reference, opts it into a named presentation role
    too (useful for a friendly display name with no aliasing need).

    Returns:
      role_by_ref: {(fact_model_name, fk_column_phys_name): role_record}
        role_record = {"dim": <dim model name>, "alias": <alias_record or None>,
                        "presentation_name": <str>, "expose": <bool>}
      unique_aliases: [alias_record, ...]  (deduped by (dim, label))
        alias_record = {"dim": ..., "label": ..., "relation": <derived name>}
      suppress_generic: {dim model name, ...} — dimensions with zero "plain"
        (unroled) FK references anywhere; their own default presentation
        table is omitted (they only appear via named roles).
    """
    role_by_ref, alias_by_key = {}, {}
    dim_has_plain_ref, dim_has_role_ref = set(), set()

    for fact_name, m in models.items():
        if not m["is_fact"]:
            continue
        fact_dim_cols = {}
        for c in m["columns"]:
            if c["role"] == "foreign_key" and c["dimension"] in models:
                fact_dim_cols.setdefault(c["dimension"], []).append(c)
        for dim, cols in fact_dim_cols.items():
            alias_every_role = len(cols) > 1  # >1 role for THIS fact into THIS dimension
            base = models[dim]
            prefix = base["relation"].split("_")[0] or "DIM"
            for c in cols:
                explicit = bool(c["role_alias"] or c["presentation_label"])
                if not alias_every_role and not explicit:
                    dim_has_plain_ref.add(dim)
                    continue
                dim_has_role_ref.add(dim)
                alias = None
                if alias_every_role or c["role_alias"]:
                    label = c["role_alias"] or c["presentation_label"] or c["label"] or c["phys"].replace("_", " ").title()
                    akey = (dim, label)
                    if akey not in alias_by_key:
                        alias_by_key[akey] = {"dim": dim, "label": label, "relation": f"{prefix}_{slug(label)}"}
                    alias = alias_by_key[akey]
                role_by_ref[(fact_name, c["phys"])] = {
                    "dim": dim, "alias": alias,
                    "presentation_name": c["presentation_label"] or (alias["label"] if alias else c["label"]),
                    "expose": c["expose_presentation"],
                }

    suppress_generic = dim_has_role_ref - dim_has_plain_ref
    return role_by_ref, list(alias_by_key.values()), suppress_generic


# ----------------------------------------------------------------------------
# Phase 1 — physical layer
# ----------------------------------------------------------------------------
def emit_physical(models, role_by_ref, unique_aliases, out, db, db_type, connection):
    base = os.path.join(out, "physical")
    write_json(os.path.join(base, f"{db}.json"), wrap("database", {
        "name": db, "databaseType": db_type,
        "connectionPools": [{
            "name": f"{db} Connection Pool", "connection": connection,
            "remoteConnection": False, "maxConnections": 10,
            "requiresFullyQualifiedTableNames": True,
            "connectionTimeout": 5, "connectionTimeoutUnit": "MINUTES",
            "multithreaded": True, "supportParams": True, "isolationLevel": "default",
            "writeBackConfig": {"dbSupportsUnicode": False, "bulkInsertBufferSize": 10240,
                                 "transactionBoundary": 1000, "tempTablePrefix": "TT"},
        }],
        "virtualPrivateDatabase": False, "crmMetadataTables": False,
        "allowDirectDatabaseRequests": False, "allowPopulateQueries": False,
    }))
    schemas = sorted({m["schema"] for m in models.values()})
    for sch in schemas:
        write_json(os.path.join(base, db, f"{sch}.json"), wrap("schema", {"name": sch}))

    for m in models.values():
        phys_cols = [{"name": c["phys"], "dataType": c["dtype"], "length": c["length"] or 0,
                      "nullable": c["nullable"]} for c in m["columns"]]
        tbl = {"name": m["relation"], "sourceType": "TABLE", "physicalColumns": phys_cols,
               "caching": {"enable": True, "expiryTime": 0}}
        if m["description"]:
            tbl["description"] = m["description"]

        joins = []
        if m["is_fact"]:
            for c in m["columns"]:
                if c["role"] != "foreign_key" or c["dimension"] not in models or not c["include_join"]:
                    continue
                d = models[c["dimension"]]
                dpk = dim_pk(d)
                if not dpk:
                    continue
                role = role_by_ref.get((m["name"], c["phys"]))
                alias = role["alias"] if role else None
                right_schema = d["schema"]
                right_relation = alias["relation"] if alias else d["relation"]
                joins.append({
                    "rightTable": fqn("physicalTable", db, right_schema, right_relation),
                    "useJoinExpression": False,
                    "joinConditions": [{
                        "leftColumn": fqn("physicalColumn", db, m["schema"], m["relation"], c["phys"]),
                        "rightColumn": fqn("physicalColumn", db, right_schema, right_relation, dpk["phys"]),
                    }],
                    "joinType": "INNER", "cardinality": "MANY_TO_ONE",
                })
        if joins:
            tbl["joins"] = joins
        write_json(os.path.join(base, db, m["schema"], f"{m['relation']}.json"), wrap("physicalTable", tbl))

    for a in unique_aliases:
        d = models[a["dim"]]
        write_json(os.path.join(base, db, d["schema"], f"{a['relation']}.json"), wrap("physicalTable", {
            "name": a["relation"],
            "sourceTable": fqn("physicalTable", db, d["schema"], d["relation"]),
            "overrideSourceCacheSetting": False,
        }))


# ----------------------------------------------------------------------------
# Phases 2 + 3 — logical layer
# ----------------------------------------------------------------------------
def logical_columns_for(m, db, relation):
    cols = []
    for c in m["columns"]:
        lc = {
            "name": c["phys"], "dataType": c["dtype"], "writeable": False,
            "logicalColumnSource": {
                "derivedFrom": "PHYSICAL_COLUMNS",
                "physicalMappings": [{
                    "logicalTableSource": relation,
                    "physicalExpression": {"expressionTemplate": "%1",
                        "expressionObjects": [fqn("physicalColumn", db, m["schema"], relation, c["phys"])]},
                }],
            },
        }
        if c["description"]:
            lc["description"] = c["description"]
        if c["role"] == "measure" and c["aggregation"]:
            lc["aggregation"] = {"rule": c["aggregation"]}
        cols.append(lc)
    return cols


def resolve_expression_object(ref, m, models, bm):
    """meta.oac.derived_measures[].expressionObjects entries: a bare column
    name (this model), 'model.column' (cross-model), or an already-qualified
    'logicalColumn:...' reference (passed through verbatim)."""
    if ":" in ref:
        return ref
    if "." in ref:
        model_name, col_name = ref.split(".", 1)
    else:
        model_name, col_name = m["name"], ref
    target = models.get(model_name)
    if not target:
        return ref  # unresolved -> passed through as-is; validate_smml.py will flag it
    col = next((c for c in target["columns"] if c["phys"].lower() == col_name.lower()), None)
    phys = col["phys"] if col else col_name.upper()
    return fqn("logicalColumn", bm, target["relation"], phys)


def emit_logical(models, role_by_ref, unique_aliases, out, db, bm):
    base = os.path.join(out, "logical")
    write_json(os.path.join(base, f"{bm}.json"), wrap("businessModel", {"name": bm, "disable": False}))

    def logical_table_source(relation):
        return {"name": relation, "disable": False,
                "tableMapping": {"tables": [fqn("physicalTable", db, schema_for(relation), relation)]},
                "combineWithOtherFragments": False, "enableFragmentSelection": False, "distinctValues": False}

    def schema_for(relation):
        for m in models.values():
            if m["relation"] == relation:
                return m["schema"]
        for a in unique_aliases:
            if a["relation"] == relation:
                return models[a["dim"]]["schema"]
        return None

    for m in models.values():
        lt_name = m["relation"]
        logical_columns = logical_columns_for(m, db, lt_name)

        for dm in m["derived"]:
            objs = [resolve_expression_object(r, m, models, bm) for r in dm["expressionObjects"]]
            logical_columns.append({
                "name": dm["colname"], "dataType": "NUMERIC", "writeable": False,
                "description": dm["description"],
                "logicalColumnSource": {
                    "derivedFrom": "LOGICAL_COLUMNS",
                    "logicalExpression": {"expressionTemplate": dm["expression"], "expressionObjects": objs},
                },
            })

        lt = {
            "name": lt_name, "type": "FACT" if m["is_fact"] else "DIMENSION",
            "logicalColumns": logical_columns,
            "logicalTableSources": [logical_table_source(lt_name)],
        }
        if m["description"]:
            lt["description"] = m["description"]
        if not m["is_fact"]:
            pk = dim_pk(m)
            if pk:
                lt["primaryKey"] = [pk["phys"]]

        if m["is_fact"]:
            joins = []
            for c in m["columns"]:
                if c["role"] != "foreign_key" or c["dimension"] not in models or not c["include_join"]:
                    continue
                role = role_by_ref.get((m["name"], c["phys"]))
                alias = role["alias"] if role else None
                right_name = alias["relation"] if alias else models[c["dimension"]]["relation"]
                joins.append({"rightTable": fqn("logicalTable", bm, right_name),
                              "joinType": "INNER", "cardinality": "MANY_TO_ONE", "drivingTable": "None"})
            if joins:
                lt["joins"] = joins

        hiers = emit_hierarchies(m)
        if hiers:
            lt["levelBasedHierarchy"] = hiers
            lt["hierarchyType"] = "TIME" if m["is_time"] else "LEVEL_BASED"
        write_json(os.path.join(base, bm, f"{lt_name}.json"), wrap("logicalTable", lt))

    # Alias logical tables — full column set copied from the base dimension,
    # flat (no hierarchy — see modeling-patterns.md §1; role-play aliases in
    # the one real example never carried a hierarchy either).
    for a in unique_aliases:
        d = models[a["dim"]]
        cols = logical_columns_for(d, db, a["relation"])
        lt = {"name": a["relation"], "type": "DIMENSION", "logicalColumns": cols,
              "logicalTableSources": [logical_table_source(a["relation"])]}
        pk = dim_pk(d)
        if pk:
            lt["primaryKey"] = [pk["phys"]]
        write_json(os.path.join(base, bm, f"{a['relation']}.json"), wrap("logicalTable", lt))


def emit_hierarchies(m):
    """PDF-only construct (F38574-15 + F42737-41) — never seen in a real
    OAC export. See smml-schema.md's Hierarchies section and
    modeling-patterns.md §2 before trusting this in production."""
    if not m["hierarchies"]:
        return None

    def resolve(colname):
        """meta.oac level_columns keys are bare dbt column names (lowercase);
        logical column names are the UPPER_SNAKE physical name — resolve."""
        col = next((c for c in m["columns"] if c["phys"].lower() == colname.lower()), None)
        return col["phys"] if col else colname.upper()

    logical_levels = [{"name": "Grand Total", "grandTotalLevel": True, "numberOfElements": 1}]
    logical_hierarchies = []
    for h in m["hierarchies"]:
        lvl_cols = h.get("level_columns", {})
        is_time = (h.get("type") == "time") or m["is_time"]
        for lvl in h["levels"]:
            if any(l["name"] == lvl for l in logical_levels):
                continue
            spec = lvl_cols.get(lvl, {})
            level = {"name": lvl}
            if spec.get("key"):
                key = [resolve(k) for k in spec["key"]]
                level["primaryKey"] = key
                if is_time:
                    level["chronologicalKey"] = key
            if spec.get("label"):
                level["displayKey"] = resolve(spec["label"])
            logical_levels.append(level)
        logical_hierarchies.append({"name": h["name"], "levels": ["Grand Total"] + list(h["levels"])})
    return {"logicalLevels": logical_levels, "logicalHierarchies": logical_hierarchies,
            "defaultRootLevel": "Grand Total"}


# ----------------------------------------------------------------------------
# Phase 4 — presentation layer
# ----------------------------------------------------------------------------
def implicit_fact_column(m, bm):
    meas = next((c for c in m["columns"] if c["role"] == "measure"), None)
    return fqn("logicalColumn", bm, m["relation"], meas["phys"]) if meas else None


def emit_presentation(models, role_by_ref, suppress_generic, out, bm):
    base = os.path.join(out, "presentation")

    by_sa = {}
    for m in models.values():
        if not m["is_fact"] and m["name"] in suppress_generic:
            continue
        for sa in m["subject_areas"]:
            by_sa.setdefault(sa, []).append(m)

    # named roles, grouped by the *owning fact's* subject area(s) — a role
    # belongs to the fact that declared it, not to the dimension's own tags
    sa_roles = {}
    for (fact_name, _col), role in role_by_ref.items():
        if not role["expose"]:
            continue
        for sa in models[fact_name]["subject_areas"]:
            sa_roles.setdefault(sa, {})[role["presentation_name"]] = role

    for sa, members in by_sa.items():
        role_map = sa_roles.get(sa, {})
        names = [presentation_name(m) for m in members] + list(role_map.keys())
        sa_obj = {
            "name": sa, "sourceBusinessModel": fqn("businessModel", bm),
            "tableOrder": [{"name": fqn("presentationTable", sa, n), "children": []} for n in names],
        }
        facts_in_sa = [m for m in members if m["is_fact"]]
        implicit_candidates = [m for m in facts_in_sa if m["implicit_fact"]]
        if len(facts_in_sa) > 1 and len(implicit_candidates) == 1:
            col = implicit_fact_column(implicit_candidates[0], bm)
            if col:
                sa_obj["implicitFactColumn"] = col
        write_json(os.path.join(base, f"{sa}.json"), wrap("subjectArea", sa_obj))

        for m in members:
            pcols = [{"name": c["label"],
                      "sourceLogicalColumn": fqn("logicalColumn", bm, m["relation"], c["phys"])}
                     for c in m["columns"]]
            for dm in m["derived"]:
                pcols.append({"name": dm["name"],
                              "sourceLogicalColumn": fqn("logicalColumn", bm, m["relation"], dm["colname"])})
            pt_name = presentation_name(m)
            write_json(os.path.join(base, sa, f"{pt_name}.json"),
                       wrap("presentationTable", {"name": pt_name, "presentationColumns": pcols}))

        for pname, role in role_map.items():
            d = models[role["dim"]]
            source_relation = role["alias"]["relation"] if role["alias"] else d["relation"]
            pcols = [{"name": c["label"],
                      "sourceLogicalColumn": fqn("logicalColumn", bm, source_relation, c["phys"])}
                     for c in d["columns"]]
            write_json(os.path.join(base, sa, f"{pname}.json"),
                       wrap("presentationTable", {"name": pname, "presentationColumns": pcols}))


# ----------------------------------------------------------------------------
# Documentation — emit a human-readable description of the generated model
# ----------------------------------------------------------------------------
def emit_docs(models, role_by_ref, unique_aliases, suppress_generic, out, db, bm):
    by_sa = {}
    for m in models.values():
        if not m["is_fact"] and m["name"] in suppress_generic:
            continue
        for sa in m["subject_areas"]:
            by_sa.setdefault(sa, []).append(m)

    L = []
    L.append(f"# Semantic model — {bm}\n")
    L.append("Generated from a dbt project by `generate_smml.py`. This describes the "
             "SMML model emitted alongside it; it is documentation, not an SMML object.\n")
    facts = [m for m in models.values() if m["is_fact"]]
    dims = [m for m in models.values() if not m["is_fact"]]
    L.append(f"- **Database**: {db}")
    L.append(f"- **Business model**: {bm}")
    L.append(f"- **Tables**: {len(models)} ({len(facts)} fact, {len(dims)} dimension)"
              + (f" + {len(unique_aliases)} role-playing alias(es)" if unique_aliases else ""))
    L.append(f"- **Subject areas**: {', '.join(sorted(by_sa))}\n")

    if unique_aliases:
        L.append("## Role-playing dimensions\n")
        for a in unique_aliases:
            L.append(f"- `{a['relation']}` — alias of `{models[a['dim']]['relation']}`, role \"{a['label']}\"")
        L.append("")
    if suppress_generic:
        L.append("## Dimensions exposed only via named roles (no generic presentation table)\n")
        for d in sorted(suppress_generic):
            L.append(f"- `{models[d]['relation']}`")
        L.append("")

    for sa in sorted(by_sa):
        L.append(f"## Subject area: {sa}\n")
        for m in sorted(by_sa[sa], key=lambda x: (not x["is_fact"], x["name"])):
            kind = "Fact" if m["is_fact"] else "Dimension"
            L.append(f"### {presentation_name(m)} ({kind})")
            if m["description"]:
                L.append(f"\n{m['description']}\n")
            L.append(f"\n*Physical*: `{m['schema']}.{m['relation']}`\n")
            L.append("| Column | Type | Role | Aggregation |")
            L.append("|--------|------|------|-------------|")
            for c in m["columns"]:
                L.append(f"| {c['phys']} | {c['dtype']} | {c['role']} | {c['aggregation'] or ''} |")
            for dm in m["derived"]:
                L.append(f"| {dm['colname']} | NUMERIC | derived measure | `{dm['expression']}` |")
            joins = []
            for c in m["columns"]:
                if c["role"] == "foreign_key" and c["dimension"] in models and c["include_join"]:
                    role = role_by_ref.get((m["name"], c["phys"]))
                    alias = role["alias"] if role else None
                    joins.append(alias["relation"] if alias else models[c["dimension"]]["relation"])
            if joins:
                L.append(f"\n*Joins* → {', '.join(joins)} (MANY_TO_ONE)")
            for h in m["hierarchies"]:
                L.append(f"\n*Hierarchy* `{h['name']}`: Grand Total → {' → '.join(h['levels'])}"
                         + ("  _(time)_" if m["is_time"] else ""))
            L.append("")
    L.append("---\n")
    L.append("> Generated by the `dbt-to-smml` skill. Semantics come from `meta.oac` in "
             "the dbt `schema.yml`; columns/types from dbt's catalog. Hierarchies and "
             "derived measures are unvalidated against a real OAC import — see the "
             "skill README caveats before shipping.\n")
    write_text(os.path.join(out, "MODEL.md"), "\n".join(L))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Generate an OAC SMML semantic model from dbt artifacts.")
    ap.add_argument("--manifest", default="target/manifest.json")
    ap.add_argument("--catalog", default="target/catalog.json")
    ap.add_argument("--out", default="smml")
    ap.add_argument("--database-name", default="MESTEC ADW")
    ap.add_argument("--database-type", default="ORACLE_ADW",
                     help="SMML DatabaseType enum value, e.g. ORACLE_ADW or ORACLE_DATABASE")
    ap.add_argument("--connection", default="REPLACE_WITH_OAC_CONNECTION")
    ap.add_argument("--business-model", default="MESTEC")
    ap.add_argument("--schema", default=None, help="override physical schema name")
    ap.add_argument("--layer", default="warehouse", help="dbt layer to expose, or 'all'")
    args = ap.parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)
    with open(args.catalog) as f:
        catalog = json.load(f)

    models = build_models(manifest, catalog, args.layer, args.schema)
    if not models:
        raise SystemExit(f"No models found for layer '{args.layer}'. Run `dbt docs generate` first.")

    role_by_ref, unique_aliases, suppress_generic = resolve_roles(models)

    emit_physical(models, role_by_ref, unique_aliases, args.out, args.database_name, args.database_type, args.connection)
    emit_logical(models, role_by_ref, unique_aliases, args.out, args.database_name, args.business_model)
    emit_presentation(models, role_by_ref, suppress_generic, args.out, args.business_model)
    emit_docs(models, role_by_ref, unique_aliases, suppress_generic, args.out, args.database_name, args.business_model)

    n_files = sum(len(fs) for _, _, fs in os.walk(args.out))
    facts = sum(1 for m in models.values() if m["is_fact"])
    print(f"Generated SMML for {len(models)} tables ({facts} fact, {len(models)-facts} dim) "
          f"+ {len(unique_aliases)} role-playing alias(es) -> {args.out}/  "
          f"({n_files} JSON files across physical/logical/presentation)")


if __name__ == "__main__":
    main()
