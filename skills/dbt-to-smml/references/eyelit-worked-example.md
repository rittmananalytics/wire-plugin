# Worked example: eyelit-dbt → eyelit_smml

A concrete case study of applying `meta.oac` to a real dbt project, using the
same pairing that grounds this skill's schema and vocabulary:
[`eyelit-dbt`](https://github.com/rittmananalytics/eyelit-dbt) (the source
dbt project) and [`eyelit_smml`](https://github.com/rittmananalytics/eyelit_smml)
(a real, OAC-imported semantic model built from it). Read this alongside
`meta-oac-vocabulary.md` — that file documents each tag in the abstract, this
shows them applied, including the tagging gaps a real project actually had
and how they got fixed.

## What eyelit-dbt's meta.oac originally had

`fact_attendance_log` and `fact_activity_log` both join `dim_date` more than
once — three date roles on `fact_attendance_log` (account date, clock-in,
clock-out), two on `fact_activity_log` (start date, end date).
`fact_activity_log` also joins `dim_workflow_nodes` twice (the current node,
and a "visit" role). Before this pass, only the *first* FK into each
dimension was tagged `role: foreign_key` — the rest (`clock_in_dt`,
`clock_out_dt`, `end_date_key`, `workflow_node_visit_id`) were tagged
`role: degenerate`, meaning a generator reading the file would treat them as
plain fact-table attributes with no dimension relationship at all. Every
model also shared one flat `subject_area: "MESTEC Operations"` tag.

## What the real, shipped SMML model actually looks like

`eyelit_smml` has none of that flatness. It ships two purpose-built subject
areas — `Attendance` (7 tables: the fact, its directly-joined dimensions, and
two of its three date roles) and `Activity` (11 tables, similarly scoped) —
and it aliases most (not all — see below) of the multi-role dimensions:
`DIM_ACCOUNT_DATE`, `DIM_CLOCK_IN_DATE`, `DIM_CLOCK_OUT_DATE`, `DIM_END_DATE`,
`DIM_WORKFLOW_VISIT_NODES` all exist as real physical aliases with their own
logical tables and (mostly) their own presentation tables.

**But it isn't a clean example to copy mechanically.** Two things in the
shipped model are inconsistent with Oracle's own documented best practice
(*Building Semantic Models in Oracle Analytics Cloud*, F42737-41, Ch.19:
alias every role once a dimension plays more than one within a fact):

- `fact_activity_log.start_date_key` joins the **base** `DIM_DATE` table
  directly, with only a presentation-layer rename ("Activity Start Date")
  papering over the missing alias — while its sibling `end_date_key` got a
  proper alias (`DIM_END_DATE`).
- `fact_activity_log.workflow_node_id` similarly stays unaliased while its
  sibling `workflow_node_visit_id` (`DIM_WORKFLOW_VISIT_NODES`) is properly
  aliased.

Both were confirmed to be oversights in that build, not deliberate design.
Reproducing them in a fresh generation would mean deliberately shipping worse
SMML than the tool is capable of. **The lesson, not just for this project:
when a real reference model and documented best practice disagree, default
to best practice and flag the disagreement — don't silently copy it.** This
skill's generator enforces "alias every role once a fact has more than one FK
into the same dimension" automatically, specifically so this class of mistake
can't recur even if a future `meta.oac` author forgets to tag every column.

## The tags that closed the gap

Applied to `eyelit-dbt/models/warehouse/core/_warehouse__models.yml` (see
that repo's own `OAC-SEMANTIC-LAYER-META-TAGS.md` for the full table):

```yaml
- name: fact_attendance_log
  meta:
    oac:
      object_type: fact
      subject_area: "Attendance"
      presentation_name: "Attendance Fact"
  columns:
    - name: account_date_key
      meta: { oac: { role: foreign_key, dimension: dim_date, role_alias: "Account Date" } }
    - name: clock_in_dt          # was role: degenerate
      meta: { oac: { role: foreign_key, dimension: dim_date,
                     role_alias: "Clock In Date", presentation_label: "Clock In Dates" } }
    - name: clock_out_dt         # was role: degenerate
      meta: { oac: { role: foreign_key, dimension: dim_date, role_alias: "Clock Out Date" } }

- name: fact_activity_log
  meta:
    oac:
      object_type: fact
      subject_area: "Activity"
      presentation_name: "Activity Log Facts"
  columns:
    - name: start_date_key       # already an FK — added role_alias to fix the oversight above
      meta: { oac: { role: foreign_key, dimension: dim_date,
                     role_alias: "Start Date", presentation_label: "Activity Start Date" } }
    - name: end_date_key         # was role: degenerate
      meta: { oac: { role: foreign_key, dimension: dim_date,
                     role_alias: "End Date", presentation_label: "Activity End Date" } }
    - name: workflow_node_id     # already an FK — added role_alias to fix the same class of oversight
      meta: { oac: { role: foreign_key, dimension: dim_workflow_nodes, role_alias: "Workflow Node" } }
    - name: workflow_node_visit_id   # was role: degenerate
      meta: { oac: { role: foreign_key, dimension: dim_workflow_nodes, role_alias: "Workflow Visit Nodes" } }

- name: dim_date
  meta:
    oac:
      subject_area: ["Attendance", "Activity"]   # shared across both — see below

- name: dim_teams   # shared across both facts, only ONE FK each — no aliasing needed
  meta:
    oac:
      subject_area: ["Attendance", "Activity"]
```

Note the difference between `dim_date` (aliased — each fact has *multiple*
FKs into it) and `dim_teams`/`dim_users` (not aliased, just tagged into both
subject areas — each fact has exactly *one* FK into it). Aliasing triggers
per fact, scoped to "does this one fact have more than one FK into this
dimension" — two different facts each having their own single, ordinary join
to a shared/conformed dimension is completely normal star-schema reuse and
must never trigger aliasing on its own. Getting this scoping wrong (counting
FK references globally instead of per fact) would force-alias every shared
dimension in a multi-fact project, which is a real bug this skill's
generator specifically guards against — see `generate_smml.py`'s
`resolve_roles()` docstring.

## What still doesn't match, and why that's fine

Even with these tags, a generated model won't be byte-identical to
`eyelit_smml`:

- `fact_attendance_log.shift_id → dim_shifts` is a normal declared FK and
  gets joined by default; `eyelit_smml` doesn't join it, for reasons not
  captured anywhere in `meta.oac`. Left as a normal FK here rather than
  guessing at a business reason to exclude it — see
  `meta-oac-vocabulary.md`'s `include_join` entry if there turns out to be
  one.
- Dimensions not referenced by either subject area (`dim_departments`,
  `dim_sites`, `dim_shifts`, and others) still get full logical +
  presentation tables generated, since the generator mechanically translates
  every tagged model. `eyelit_smml` omits them. That's the intended
  behavior — the generator proposes completely, a human curates the final
  subject-area membership before shipping.
- `dim_date`'s declared `Calendar` hierarchy will actually get built this
  time; `eyelit_smml` ships it flat. That's a feature addition over what
  shipped, not a bug to fix.

See `dbt-to-smml/SKILL.md`'s caveats and `meta-oac-vocabulary.md`'s "Don't
just replicate what a previous project shipped" section for the general
version of this lesson.
