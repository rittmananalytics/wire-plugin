# `meta.oac` vocabulary

The metadata that turns a dbt project into a *semantic* model. It lives under
`meta.oac` in the dbt `schema.yml`, travels with the model in Git, and is
ignored by dbt itself. The generator reads it from `manifest.json`. Where
it's absent, the generator infers sensible defaults (see "Inference" below) —
but `meta.oac` always wins. This is the human-in-the-loop layer: the model
proposes it, a human approves it into `schema.yml`.

This vocabulary exists to let `schema.yml` express the modeling constructs
covered in the sibling `smml-semantic-modeling` skill — read
`../smml-semantic-modeling/references/modeling-patterns.md` before proposing
`hierarchies`, `role_alias`, or `derived_measures` on a real project; each
key below is a direct encoding of a pattern documented there.

## Model-level (`models[].meta.oac`)

| Key | Values | Meaning |
|-----|--------|---------|
| `object_type` | `fact` \| `dimension` | logical table type |
| `subject_area` | string or list of strings | presentation grouping. **One value per fact** (plus its directly-joined dimensions) — not one global tag for the whole project. A shared dimension used by facts in more than one subject area takes a **list** (e.g. `[Attendance, Activity]`) so it gets its own presentation-table copy in each. See "Subject area" below. |
| `implicit_fact` | bool | marks this fact as the implicit fact column source for its subject area — set when a subject area will expose more than one fact table (chasm-trap mitigation; see modeling-patterns.md §4) |
| `presentation_name` | string | friendly presentation-table name, e.g. `"Attendance Fact"` for `fact_attendance_log`. Presentation names are human-authored and diverge from the model name — there's no dbt-native source for this, so declare it explicitly when the default (Title Case of the model name) isn't right. |
| `is_time_dimension` | bool | marks the dimension as a time dimension — every non-Grand-Total level in its hierarchies gets a `chronologicalKey` |
| `hierarchies` | list | level-based hierarchies (see below) |
| `derived_measures` | list | calculated/ratio measures over already-aggregated sibling measures (see below) |

## Column-level (`models[].columns[].meta.oac`)

| Key | Values | Meaning |
|-----|--------|---------|
| `role` | `measure` \| `attribute` \| `degenerate` \| `foreign_key` \| `key` | column's semantic role |
| `aggregation` | `SUM` \| `COUNT` \| `COUNT_DISTINCT` \| `AVG` \| `MAX` \| `MIN` \| `FIRST` \| `LAST` \| `MEDIAN` \| `STD_DEV` \| `STD_DEV_POP` | aggregation rule (measures). Note: `MIN` is not valid as a plain top-level rule in SMML's own enum — only as part of a dimension-based rule. If you need `MIN`, flag it for manual review rather than emitting it as-is (see `smml-schema.md`'s `AggregationRule` note). |
| `dimension` | model name | for `foreign_key` — the dimension this FK joins to |
| `role_alias` | string | for `foreign_key` — names the physical/logical alias this FK gets. **The generator builds an alias automatically once a dimension is targeted by more than one FK anywhere in the model**, even without `role_alias` (Oracle's own best practice: never leave one role joined to the base table once another has been aliased) — but the auto-derived name falls back to the column's `label`, which is usually worse. Declare `role_alias` explicitly whenever a dimension plays multiple roles. A dimension with exactly one FK reference doesn't need it — no alias is built. See `modeling-patterns.md` §1. |
| `presentation_label` | string | for `foreign_key` — overrides just the presentation display name for this FK's dimension, independent of `role_alias` (which names the alias itself). Use when the presentation name should read differently from the physical/logical alias name (e.g. alias `DIM_END_DATE`, presentation "Activity End Date"). Setting this alone (no `role_alias`) on a dimension with only one FK reference still gives it a named presentation role without building any alias. |
| `expose_presentation` | bool, default `true` | for `foreign_key` — set `false` to build the join (and alias, if `role_alias` is set) without generating a presentation table for it. For plumbing that isn't ready to expose yet; don't use it to silently reproduce another project's incomplete build — see the caveat below. |
| `include_join` | bool, default `true` | for `foreign_key` — set `false` to declare the relationship (documentation, lineage) without emitting an actual physical/logical join. Use only when there's a real reason to skip it; a declared FK gets joined by default, and that default is deliberate — the generator proposes the complete, correct model, a human prunes afterward with a stated reason, not the other way around. |
| `label` | string | friendly presentation-column display name |
| `description` | string | (or use dbt's standard column `description`) |

## Hierarchies (`meta.oac.hierarchies`, model-level, on a dimension)

```yaml
hierarchies:
  - name: Calendar
    type: time              # time | level_based (default level_based)
    levels: [Year, Quarter, Month, Day]
    level_columns:
      Year:    { key: [year],             label: year }
      Quarter: { key: [year, quarter_no], label: month_name }
      Month:   { key: [year, month_no],   label: month_name }
      Day:     { key: [date_key],         label: full_date }
```

- `levels` is top (root) to bottom (leaf) order — the generator adds an
  implicit `Grand Total` level above the first one automatically.
- `level_columns[<level>].key` is that level's primary key (list of column
  names). When the hierarchy's `type: time`, the generator also uses each
  level's `key` as its `chronologicalKey` — every non-Grand-Total level of a
  time hierarchy needs one, not just the leaf, per `modeling-patterns.md` §2.
  There's no separate `chronological:` flag to set per level; it follows
  from the hierarchy's `type`.
- `level_columns[<level>].label` is that level's display key.
- **Declare a hierarchy only when something actually needs to roll up
  through it or drive a time-series calculation.** A dimension with natural
  grain levels doesn't need a hierarchy just because the levels exist — see
  modeling-patterns.md §2's "reality check."
- **Unvalidated construct** — see the skill's caveats. Review the generated
  `levelBasedHierarchy` JSON against a real OAC import before trusting it.

## Derived / calculated measures (`meta.oac.derived_measures`, model-level, on a fact)

```yaml
derived_measures:
  - name: "Labour Utilisation"
    description: "Direct hours as a proportion of paid hours."
    expression: "%1 / %2"
    expressionObjects: [direct_hours, paid_hours]
```

- `expressionObjects` entries are **column names already declared as
  `role: measure` on this model** (bare dbt column names, lowercase) — the
  generator resolves them to the correctly-cased `logicalColumn` FQN
  automatically. You can also give a fully-qualified `logicalColumn:...`
  reference directly for an advanced/cross-model case (e.g. a compound
  measure spanning two facts — see modeling-patterns.md §3 on giving those
  their own logical table rather than bolting the ratio onto either fact);
  anything already containing a `:` is passed through verbatim.
- `expression` is the literal `expressionTemplate` — `%1`, `%2`… bind to
  `expressionObjects` by position. **Both operands must already be
  aggregated measures** (they divide post-aggregation); don't wrap them in
  `SUM()` again inside the template — see `modeling-patterns.md` §3. The
  query engine auto-guards divide-by-zero; don't hand-write a `NULLIF` guard.
- **Unvalidated construct** — same caveat as hierarchies. The one real
  project with a `derived_measures` declaration (`fact_ole_daily`'s OLE
  ratios) never actually got built into the shipped SMML export, so this
  shape has PDF backing only, not a real-import check.

## Worked example

```yaml
models:
  - name: fact_attendance_log
    description: "One row per attendance log — labour minutes breakdown."
    meta:
      oac:
        object_type: fact
        subject_area: Attendance
        presentation_name: "Attendance Fact"
    columns:
      - name: account_date_key
        meta: { oac: { role: foreign_key, dimension: dim_date, role_alias: "Account Date" } }
      - name: clock_in_dt
        meta: { oac: { role: foreign_key, dimension: dim_date, role_alias: "Clock In Date" } }
      - name: clock_out_dt
        meta: { oac: { role: foreign_key, dimension: dim_date, role_alias: "Clock Out Date" } }
      - name: user_id
        meta: { oac: { role: foreign_key, dimension: dim_users } }
      - name: attendance_log_id
        meta: { oac: { role: degenerate } }
      - name: paid_mins
        description: "Paid minutes."
        meta: { oac: { role: measure, aggregation: SUM, label: "Paid Minutes" } }
      - name: working_mins
        meta: { oac: { role: measure, aggregation: SUM, label: "Working Minutes" } }

  - name: dim_date
    meta:
      oac:
        object_type: dimension
        subject_area: Attendance
        is_time_dimension: true
        hierarchies:
          - name: Calendar
            type: time
            levels: [Year, Quarter, Month, Day]
            level_columns:
              Year:    { key: [year],             label: year }
              Quarter: { key: [year, quarter_no], label: month_name }
              Month:   { key: [year, month_no],   label: month_name }
              Day:     { key: [date_key],         label: full_date }
    columns:
      - name: date_key
        meta: { oac: { role: key } }
      - name: month_name
        meta: { oac: { label: "Month" } }
```

`account_date_key`, `clock_in_dt`, `clock_out_dt` all target `dim_date` with
distinct `role_alias` values — this is exactly the three-role pattern from
`modeling-patterns.md` §1. The generator emits three physical aliases
(`DIM_ACCOUNT_DATE`, `DIM_CLOCK_IN_DATE`, `DIM_CLOCK_OUT_DATE`), three logical
tables, three presentation tables, and joins `fact_attendance_log` to each —
never to the base `DIM_DATE` table.

## Inference (when `meta.oac` is absent)

- `object_type`: `fact` if the model name starts with `fact_`, else `dimension`.
- column `role`: in a fact, a numeric non-id column → `measure` (default
  aggregation `SUM`); an id/key-like column → `degenerate`. In a dimension, every
  non-key column → `attribute`.
- Foreign keys / joins are **only** created from explicit
  `role: foreign_key` + `dimension` (inference can't know the join target).
  A `role: foreign_key` declared on a *dimension* column (a snowflake FK)
  never becomes a join regardless — see modeling-patterns.md §5.
- Hierarchies and derived measures are never inferred — declare them.
- `role_alias` names are never inferred, but *aliasing itself* is: once any
  two FKs anywhere target the same dimension, both get aliased automatically
  (best-practice default), named from `label`/column-name if `role_alias`
  is absent.

Inference keeps output meaningful for a first pass; the point of `meta.oac` is
to make the semantics correct and explicit, under human sign-off.

## Don't just replicate what a previous project shipped

If you're proposing `meta.oac` by comparing against an existing OAC model
(as `dbt-to-smml`'s worked example was), treat that model as a reference, not
a specification. A shipped model can be incomplete — the `eyelit_smml`
project that grounds this skill's worked example left one date role on a
fact joined straight to the base dimension table while its siblings were
properly aliased. That was confirmed to be an oversight in that build, not a
deliberate pattern, and reproducing it would have meant deliberately
generating worse SMML than the tool is capable of. When a real model and
Oracle's own documented best practice disagree, default to best practice
(the generator does, per the rule above) and flag the disagreement for the
human to confirm rather than silently copying it.
