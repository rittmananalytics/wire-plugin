# Modeling patterns

The judgement calls behind the schema in `smml-schema.md` — how Oracle
recommends building the constructs that matter, plus what the one real,
OAC-validated project (`eyelit_smml`) actually shipped when its human curators
made those same calls. Sourced from *Building Semantic Models in Oracle
Analytics Cloud* (F42737-41, 341pp) and the ground-truth comparison. Citations
give the PDF page (as paginated in the doc) / chapter-internal page.

## 1. Role-playing dimensions (one dimension, multiple FKs from one fact)

**The problem**: a fact has several FKs into the same dimension — three date
roles (account date, clock-in, clock-out) into one date dimension, or two
employee roles (market manager, product manager) into one employee dimension.
Joining the fact straight to the base dimension table more than once causes a
**fan trap**: a query selecting both roles forces the base table's key to
equal two different values in the same generated WHERE clause, silently
returning zero rows (F42737-41 p.288/Ch.19 p.7).

**The fix — alias at the physical layer, one alias per role**:
1. Create a `physicalTable` alias per role: `sourceTable` points at the base
   table, no columns of its own (see `smml-schema.md`). Naming convention:
   include the base table name plus the role, e.g. `D01 Time Day Grain`
   (Oracle's own example) or, matching what actually shipped,
   `DIM_ACCOUNT_DATE` / `DIM_CLOCK_IN_DATE` / `DIM_CLOCK_OUT_DATE` — base
   table's own prefix (`DIM_`) plus the role, not the role alone.
2. **Never join the fact to the base table directly once it has any alias.**
   Every physical join from the fact goes to an alias, even a table that only
   plays one role, so the base table stays alias-only and joins stay
   unambiguous.
3. **Never join two aliases of the same table to each other** — technically
   possible, "useless and impacts performance" (F42737-41 p.289/Ch.19 p.8).
4. Each alias gets its **own logical table** (full column set copied from the
   base dimension, own `logicalTableSource` pointing at the alias's physical
   table, own `primaryKey`) and its **own logical join** from the fact.
   Two physical aliases → two separate logical table sources in the same
   business model, never one logical table with two sources
   (F42737-41 p.289/Ch.19 p.9).
5. Each alias gets its **own presentation table**, friendly-named per role —
   ground truth: "Account Date", "Clock In Dates", "Clock Out Date",
   "Workflow Visit Nodes".

**Modeler-preference note** (not an SMML property, but worth calling out in
generated docs): disable "Automatically create joins if tables added to the
physical layer have foreign keys" before importing a table that will be
aliased multiple times — otherwise the UI spawns spurious joins on the base
table that then need manual cleanup (F42737-41 p.93/Ch.8 p.18).

**When one dimension has only one FK across the whole model**: no alias
needed — join the fact straight to the base dimension table. Aliasing exists
to disambiguate *multiple* roles, not as a blanket convention.

**A cautionary real-world example of rule 2 above, not a counter-example**:
`eyelit_smml`'s own `fact_activity_log` has two date roles into `dim_date` —
`start_date_key` and `end_date_key`. Only `end_date_key` got a proper alias
(`DIM_END_DATE`); `start_date_key` stayed joined straight to the base
`DIM_DATE` table, with a presentation-only rename ("Activity Start Date")
papering over the missing alias. This was confirmed to be an oversight in
that build, not a deliberate pattern — Oracle's rule 2 is unambiguous, and a
tool generating SMML from this pattern should alias every role once a
dimension plays more than one, not copy the omission just because a real
project shipped it. Worth keeping in mind generally: a real, working OAC
model is evidence of what's *possible*, not proof that every choice in it
was *correct* — check disagreements with documented best practice against
the model's author before treating them as intentional.

## 2. Hierarchies

**Two types, chosen up front**: level-based (structure) hierarchies, where
members of one type occur only at one level — what time/calendar hierarchies
use — versus parent-child (value) hierarchies, where the same real-world
entity type recurs at every level (manager→employee) with no named levels.

**Level-based, general**: build top-down, starting with a **Grand Total**
level, then one level per grain. Every level except Grand Total needs a
primary key and a display key; anything not explicitly assigned to a level
defaults to the lowest level. Grand Total has `numberOfElements: 1`, no key,
and defining it auto-flags "supports rollup" on every other level. A
Grand-Total-level measure ignores filters on *that* dimension but still
respects filters on other dimensions in the query — the mechanism behind
share-of-total KPIs (F42737-41 p.176/Ch.12 p.9).

**Time hierarchies specifically**: set the hierarchy type to Time, not plain
Level-Based — this is what unlocks `Ago()`/`ToDate()`/`PeriodRolling()` time-
series functions. Every non-Grand-Total level needs its own
`chronologicalKey` (not just the leaf level), and the key must sort correctly
via plain `ORDER BY` across composite grains — `(Year, Quarter)`, not
`(Quarter, Year)` — since it defines oldest-to-newest ordering for the
time-series functions (F42737-41 pp.192–193, 298/Ch.12 pp.24–25, Ch.19 p.19).
The physical time table should be separate from the fact, have no gaps in the
member sequence, and generally shouldn't join to anything except at its most
detailed level. **Default to one generic time dimension per fact**, joined on
whichever date matters most to that fact; only add secondary time dimensions
for date-level drill-down or a simplified date picker (F42737-41
pp.282–283/Ch.19 pp.3–4). Don't `AVG()` a rolling window — divide the rolling
`SUM` manually, since `AVG` operates at storage grain, not the rolling window
(F42737-41 p.192/Ch.12 p.23).

**Parent-child**: needs a generated 4-column relationship table (member id,
ancestor id, distance, leaf flag) via "Generate Relationship Table" — a full
reload on every dimension change, not incremental. If facts exist at more
than one level (a manager's own individual contribution, not just the
rollup of subordinates), use **two logical table sources** against the same
fact — one through the relationship table for rollups, one direct via alias
for individual contribution — to avoid double-counting
(F42737-41 pp.184–187/Ch.12 pp.17–19).

**Ragged / skip-level**: a **skip-level** hierarchy is one where some members
lack an ancestor at every level (Washington DC has no State parent); a
**ragged/unbalanced** hierarchy is one where branches don't all reach the
deepest level. Both are whole-hierarchy checkboxes (`skipped`, `ragged`), not
per-level flags.

**Level vs. flat attribute — no hard rule documented.** Oracle's only stated
heuristic is usability/performance: promote to a level to avoid huge flat
member lists (their example: 500 car models grouped into 3 categories).
Nothing assigned to a level just stays flat with no penalty. Treat "does
anything roll up through this column" as the practical test, not a rule from
the source material.

**Content levels** (distinct from hierarchy levels): they define the grain of
a logical table source and drive which pre-aggregated source the query engine
picks. If you set content levels on a fact's logical table source, you must
set them on every dimension joined to it, or the engine assumes no join
exists and throws "Unable to navigate requested expression"
(F42737-41 p.299/Ch.19 p.20).

**Reality check**: the one dimension in ground truth that declared a time
hierarchy (`dim_date`, Year→Quarter→Month→Day) shipped with **no hierarchy
built at all** — a completely flat dimension with just a date PK. A model can
work fine in OAC without ever building a formal hierarchy; don't treat
"needs a hierarchy" as mandatory just because a dimension has natural grain
levels. Build one when drill-down or time-series functions are actually
needed, not by default.

## 3. Calculated / derived measures

**Two places to compute, and they mean different things** (F42737-41 p.32/Ch.2 p.9):
- **Before aggregation**, in the logical table source expression — for a
  calculation that must happen row-by-row before summing, e.g.
  `tons_sold = units_sold * unit_weight`.
- **After aggregation**, in a logical column derived from two other
  already-aggregated logical columns — e.g. `Revenue / Billed Quantity`.

**Ratio measures use the second pattern, always.** Oracle's own canonical
example: `Revenue` (aggregation rule `SUM`) and `Billed Quantity`
(aggregation rule `COUNT`) are each ordinary measures; `Actual Unit Price` is
a *third* logical column, `derivedFrom: LOGICAL_COLUMNS`, dividing the two
already-aggregated columns directly (F42737-41 p.128/Ch.10 p.5). Two rules
that follow from this:
- **Don't wrap `SUM()` inside the derived expression** — set
  `aggregation.rule` on each *operand* column instead, then divide the two
  logical columns. This is what makes the ratio recompute correctly at any
  query grain (ratio-of-sums, not sum-of-ratios).
- **Don't hand-write a divide-by-zero guard** — the query engine emits one
  automatically in the generated SQL.

**Grain-mismatched ratios**: if numerator and denominator naturally aggregate
at different grains, force one side with `AGGREGATE(measure AT level)` or
`AGGREGATE(measure BY column)` before dividing (F42737-41 pp.319–322/Ch.22
pp.4–7). There's no dedicated "safe divide" function beyond ordinary division
plus these grain-forcing functions, and `EVALUATE_AGGR` as an escape hatch
when the calculation genuinely has to run in the source database.

**Share-of-total measures**: a fine-grain measure divided by a level-based
(often Grand-Total) sibling — the practical use of the Grand Total mechanism
above.

**Compound facts (a ratio spanning two different fact tables)** — e.g.
`# Opportunities / # Orders` — get their **own separate logical table**,
distinct from either source fact. This is Oracle's documented chasm-trap
avoidance pattern for cross-fact calculations, not a column on either fact.

**Granularity discipline**: declare data granularity per logical table
source (fact and dimension alike) — skip it and Oracle assumes the most
detailed level. When a ratio's two operand measures come from logical table
sources at mismatched granularity, the engine can pick inconsistent aggregate
sources for each side independently. Keep numerator and denominator sourced
at matching grain.

## 4. Subject area / presentation catalog design

**A subject area draws from exactly one business model** — that's the hard
constraint. Within it, the deciding factor for what to include is dimension
*compatibility*: every column exposed must be usable with every dimension
exposed in the same subject area, or queries silently return wrong numbers or
hard-fail ("No fact table exists at the requested level of detail")
(F42737-41 p.152/Ch.11 p.4).

**Oracle's own default workflow is broad-then-prune**: drag the whole business
model into the presentation layer, duplicate it, and prune each copy down to
a purpose-built subject area (their worked example makes two subject areas
from one model by deleting different hierarchies from each copy). **Ground
truth did the opposite and it also worked**: two subject areas
(`Attendance`, `Activity`), each built narrow from the start — one fact plus
only the handful of dimensions it actually joins to (7 and 11 tables
respectively) — with no subject area matching the flat `"MESTEC Operations"`
tag every dbt model carried. **Recommendation for a generator**: default to
one subject area per fact table plus its directly-joined dimensions — it
matches what was actually shipped and avoids producing one undifferentiated
subject area from a project that tags everything with a single value. Treat
a broader, hand-curated subject area as something a human builds afterward,
not the generator's default.

**Chasm traps in multi-fact subject areas**: if a subject area exposes more
than one fact and a query has only dimension columns (no explicit measure),
Oracle has to guess which fact to join against — different facts can return
different dimension member lists for the same filter. The fix is
`subjectArea.implicitFactColumn`: a nominated fact column always joined in
for dimension-only queries against that subject area, guaranteeing
predictable results (F42737-41 pp.288–289/Ch.19 pp.9–10). **Any subject area
with more than one fact table should set an implicit fact.**

**Naming**: no prescriptive scheme for subject area/presentation names beyond
`alternateNames[]` for post-rename synonym preservation (set these only once
the logical model is stable — presentation objects get rebuilt often during
development). At the *logical* layer, Oracle's own convention prefixes tables
by type — `D` for dimension, `F` for fact (`D0 Time`, `F0 Sales Base
Measures`) — worth adopting for logical naming even though it's not a
presentation rule. **Presentation table names are friendly and
human-authored** regardless — `Attendance Fact`, not `FACT_ATTENDANCE_LOG` —
and diverge from both the logical and physical name.

**Reordering / hiding — both are UI concerns, not security**: tables can be
reordered and nested into folder-like groupings independent of build order.
Every subject area, table, column, and hierarchy has a `hideIfTrue`
expression (constant / session variable / session-variable comparison) — a
hidden object is still directly queryable, so don't treat hiding as access
control.

**Presentation hierarchies**: nested inside a presentation table (unlike a
logical dimension, which is a peer of tables). If a logical dimension carries
more than one logical hierarchy (calendar vs fiscal year), it splits into
separate presentation hierarchies, one per logical hierarchy, each with its
own drill path.

## 5. Star-schema defaults for a generator

- **Business model must always be a star**, whatever shape the physical
  layer is in — snowflaked, normalized, fully denormalized. The logical
  layer collapses all of them back to a star. One logical dimension table
  per real-world dimension, one logical fact table per fact — never merge
  dimensions into one logical table or end up with a catch-all fact.
- **Fact-to-dimension joins are many-to-one, fact on the many side, always**:
  "the query engine treats tables at the *one* end of a join as dimension
  tables, and tables at the *many* end as fact tables" (F42737-41 p.28/Ch.2
  p.6) — labeling is inferred from cardinality, so get the direction right.
- **A `role: foreign_key` column declared on a dimension (a snowflake FK) is
  not automatically a join.** Ground truth: `dim_teams.department_id →
  dim_departments` is declared with a `relationships` test in dbt, but
  neither the physical nor logical layer of the shipped model joins it —
  `dim_departments` isn't even built into the logical layer, despite existing
  physically. Keep dimensions denormalized (flatten the FK's target
  attributes onto the dimension, or leave it as a plain attribute column)
  unless there's a specific reason to snowflake.
- **A declared FK is a ceiling, not a mandate, even on facts.**
  `fact_attendance_log.shift_id → dim_shifts` is declared with a
  `relationships` test but was never joined in the shipped model — a human
  curator pruned it. A generator can and should propose every declared FK as
  a join (that's its job — complete, mechanical translation for review); a
  human prunes before shipping, exactly as happened here. Don't read "the
  generator over-produces joins relative to what got shipped" as a bug.
- **Outer joins**: always logical-layer, use sparingly (they block the query
  engine's ability to pick the cheapest table set), and model as a *separate*
  logical dimension rather than forcing every consumer through one.
- **Degenerate dimensions** (fact-only attributes with no separate dimension
  table — an order number, a comments field) have no dedicated OAC construct
  in either the schema doc or the building guide. Model them as plain,
  non-aggregated attribute columns directly on the fact logical table, and
  expose them in the presentation layer same as any other column — ground
  truth never hides these.
